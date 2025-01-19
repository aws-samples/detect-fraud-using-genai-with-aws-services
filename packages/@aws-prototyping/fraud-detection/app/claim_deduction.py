from datetime import datetime
from typing import Optional
import PIL
import pandas as pd
from chat_agent import get_claim_image_description
from langchain_aws import ChatBedrock
from langchain_core.prompts import PromptTemplate
from websearch import reverse_image_search
from exifdata import get_lat_lon_for_img, extract_exif_gps_timestamp
from map import address_lookup
from image_library import S3ImageLibrary
from generated_image_detector import detect_generated_image,does_endpoint_exist
import random


def get_random_weather() -> str:
    """
    Generate a random weather condition string.

    This function generates a random temperature between 7 and 35 degrees
    and randomly selects a weather condition from a predefined list. The
    weather condition is formatted as a string in the format:
    "<temperature> degrees, <condition>, <wind>".

    Returns:
        str: A string representing the random weather condition.
    """

    # Generate a random number between 7 and 35
    temperature = random.randint(7, 35)
    # Randmly select a weather condition - using the format similar to "30 degrees, sunny, light winds"

    weather_conditions = [
        f"{temperature} degrees, sunny, light winds",
        f"{temperature} degrees, sunny, moderate winds",
        f"{temperature} degrees, cloudy, moderate winds",
        f"{temperature} degrees, rainy, heavy winds",
        f"{temperature} degrees, sunny, calm winds",
        f"{temperature} degrees, overcast, light winds",
        f"{temperature} degrees, light rain, light winds",
        f"{temperature} degrees, thunderstorm, light winds"
        f"{temperature} degrees, hail, heavy winds"

    ]

    return random.choice(weather_conditions)


def perform_deduction(image: Optional[PIL.Image.Image], filename: str, claim_report: str, claim_type: str, csim_threshold:float=0.85) -> str:
    '''
    Perform deduction to determine if an insurance claim is fraudulent based on the provided image, filename, claim report, and claim type.
    Args:
        image (Optional[PIL.Image.Image]): The image associated with the claim.
        filename (str): The filename of the image.
        claim_report (str): The detailed report of the insurance claim.
        claim_type (str): The type of insurance claim (e.g., motor vehicle accident, theft, damage).
        csim_threshold (float, optional): The cosine similarity threshold for image matching. Defaults to 0.85.
    Returns:
        str: A markdown-formatted string containing the deduction results, including a summary of the claim report and a determination of whether the claim is fraudulent, inconclusive, or not fraudulent, with detailed reasoning.
    '''
    image_description = ""
    similar_images = ""
    similar_images_in_library = ""
    lat_lon_prompt = ""
    date_time_prompt = ""
    ai_generated_image = ""

    rand_weather = get_random_weather()
    weather_conditions = f'The weather on the date of the incident has been provided via an external API. The weather was {rand_weather}. If the claim report contains weather information, use this to cross-reference the weather in the image to check for discrepancies. Only use the weather information if it is relevant to the claim.'

    if image:

        lat, lon = get_lat_lon_for_img(image)

        if does_endpoint_exist():
            print("Sagemaker Endpoint for generated image detection exists")
            detection_result = detect_generated_image(img=image)
            if detection_result["confidence"] >= 0.98 and detection_result["prediction"] == 'FAKE':
                confidence = detection_result["confidence"]
                ai_generated_image = f"The image uploaded has a {str(round(confidence*100,2))} detected as a generated image. This indicates that the image is not an original photo and has been manipulated. This could be an attempt to deceive the insurance company and is a strong indicator of fraud."

        if lat and lon:
            print(f"Latitude: {lat}, Longitude: {lon}")
            address = address_lookup(lat=lat, lon=lon)
            lat_lon_prompt = f"The location specified in the EXIF data of the image uploaded is {address}, which is at latitude {lat} and longitude {lon}. If the claim report contains location information, use this to cross-reference the location in the image to check for discrepancies.\n"

        img_date_time = extract_exif_gps_timestamp(image)

        if img_date_time:
            print(f"Image date and time: {img_date_time}")
            date_time_prompt += f" Based on EXIF data, the uploaded image was taken on {img_date_time}. If the claim report contains the incident date and time information, use this to cross-reference the date and time in the image to check for discrepancies.\n"

        image_description = get_claim_image_description(image)
        image_description = f"You are provided a description of the image uploaded for the claim. Use the image description to cross reference against the claim report to check for discrepencies.\n <image_description>{image_description} </image_description >"

        if len(filename) > 0:

            rev_image_search = reverse_image_search(
                image=image, filename=filename, sim_thresh=0)
            
            reverse_matches =  [r for r in rev_image_search.results if r.csim > csim_threshold]
            reverse_match_count =len(reverse_matches)
                        
            if reverse_match_count > 0:
                similar_images = f"Similar images have been found on the internet that match the image uploaded by the user. A similarity of more than {round(csim_threshold*100, 2)}% shows possible usage of stock or internet photos, which indicate fraud:"
                for match in reverse_matches:
                    link = match.link
                    source = match.source
                    title = match.title   
                    similarity = str(round(match.csim*100, 2))
                    similar_images_str = f"<SimilarImage>Image source: {source}, Similarity: {similarity}, Image URL: {link}</SimilarImage>"
                    print(similar_images_str)
                    similar_images += f"\n{similar_images_str}\n"
                similar_images += "\nFor each image, include at least one link in the deduction where the image can be found on the internet.\n"

        image_library = S3ImageLibrary()
        similar_images_in_library_lst = image_library.search_images(image)
        similar_images_in_library_lst = [
            image for image in similar_images_in_library_lst if image.score > csim_threshold]
        if len(similar_images_in_library_lst) > 0:
            similar_images_in_library = f"{len(similar_images_in_library_lst)} similar image(s) have been found that match the image uploaded by the user. This means that the image uploaded by the user is not unique and has been used before in previous insurance claims. This indicates fraud."

    llm = ChatBedrock(
        region_name="us-west-2",
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.7},
    )

    prompt_template = PromptTemplate.from_template("""
    <instructions>
    You are an insurance fraud detection agent in Australia.

    Your job is to examine insurance claim reports, and determine if there is fraud. You are provided with a claim report.
    A claim can be for motor vehicle accidents, theft of personal property and damage to items (e.g. electronics).
    The claim report should have sufficient detail.
    For example, the weather, the date, time and location it occurred, any witnesses, the angle items are dropped or the amount of force of collisions. Consider all details in the claim report. Make sure you take into account any information you have already been provided with in the claim report.
    Provide step-by-step reasoning to make a deduction on whether there is fraud or not. Provide a score between 0% and 100% to indicate your confidence in the deduction.
    Do not say you are making a deduction or summary, just provide the information. Do not mention you are providing the output in markdown format.

    The current date and time is {current_datetime}.

    {lat_lon_prompt}
    {date_time_prompt}

    The type of claim that the user lodged is {claim_type}.

    <claim_report>{claim_report}</claim_report>

    {image_description}
    {weather_conditions}
    {similar_images}
    {similar_images_in_library}
    {ai_generated_image}

    The <claim_report> and <image_description> tags enclose the relevant information.

    To establish if there is fraud, perform these checks:

    <check>For motor vehicle accidents, you can ask the speed at which the user was travelling at. Use the speed to cross reference against the damage in the provided image to see if it matches up. If the user was travelling very slowly, it should not have resulted in extensive damage to the vehicle.</check>

    <check>logical contradictions in the report (e.g. the car is a modern car but did not have seatbelt warning alarms)</check>

    <check>data mismatch (for example, if the claim report says a laptop was damaged, but there is no laptop in the image description)</check>

    <check>look for factual inaccuracies (for example, the user says the it was not a rainy day but the car skidded)</check>

    <check>look for inconsistences (for example when the user uploads images that do not match the story)</check>

    <check>unlikely events (for example, breaking a phone screen when dropping in water or sand)</check>

    <check>Impossible scenarios, (for example, a car breaking its windscreen when flying upside down)</check>

    <check>Ask the user about their claim history to see if there is a pattern of similar claims</check>

    </instructions>
    """)

    user_input = """ Produce the following output:
    - A summary of the claim report
    - A deduction of whether the claim is fraudulent or not. This can be "Not fraudulent", "Inconclusive" or "Fraudulent" with a detailed explanation of why you think so.
    
    The output should be well-formatted in markdown format.
"""

    prompt = prompt_template.format(
        claim_report=claim_report,
        image_description=image_description,
        similar_images=similar_images,
        similar_images_in_library=similar_images_in_library,
        claim_type=claim_type,
        weather_conditions=weather_conditions,
        lat_lon_prompt=lat_lon_prompt,
        ai_generated_image=ai_generated_image,
        date_time_prompt=date_time_prompt, current_datetime=datetime.now().strftime(
            "%d %b %Y %H:%M:%S"))

    print(f'Prompt for deduction: {prompt}')

    messages = [
        (
            "system",
            prompt,
        ),
        ("human", user_input),
    ]

    ai_msg = llm.invoke(messages)

    print(f'Response from deduction: {ai_msg.content}')

    return ai_msg.content
