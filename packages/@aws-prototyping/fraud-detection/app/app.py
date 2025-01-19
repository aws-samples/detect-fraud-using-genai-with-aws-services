

import io
import os
import re
import string
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


from typing import Optional
import uuid
import PIL
import boto3
import pandas as pd
import streamlit as st
from PIL.Image import Image
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from geopy.distance import geodesic as GD
from streamlit_cognito_auth import CognitoHostedUIAuthenticator
from exifdata import get_lat_lon_for_img, get_exif, extract_exif_gps_timestamp
from generated_image_detector import detect_generated_image,does_endpoint_exist
from map import address_lookup
from paths import get_paths
from rekognition import detect_labels_in_image, display_labels_in_image
from websearch import reverse_image_search
from chat_agent import FraudDetectionAgent, get_claim_image_description
from image_library import S3ImageLibrary
from paths import is_running_on_ecs
from util.s3 import url_to_base64, generate_presigned_url
from claim_deduction import perform_deduction
from schemas.schemas import ReverseImageSearchResults
from api_client import FraudDetectionAPIClient

st.set_page_config(  # Alternate names: setup_page, page, layout
    # Can be "centered" or "wide". In the future also "dashboard", etc.
    layout="wide",
    initial_sidebar_state="auto",  # Can be "auto", "expanded", "collapsed"
    page_title="Insurance Claim Image Fraud Detection",
)

if not is_running_on_ecs():
    load_dotenv(".env")
    
print("Library files table",os.getenv("LIBRARY_FILES_TABLE"))

api_client = FraudDetectionAPIClient(os.getenv("API_ENDPOINT", "http://localhost:8000"))

# Do a healthcheck call to the API
try:
    api_client.healthcheck()
    print("API is healthy")
except Exception as e:
    st.error(
        f"An error occurred while connecting to the API: {e}. Please check the API endpoint and try again.")
    st.stop()

cognito_domain = os.getenv('COGNITO_DOMAIN')

STORAGE_BUCKET = os.getenv("STORAGE_BUCKET")

# Use SSM to get the Cognito domain
ssm = boto3.client('ssm')
if is_running_on_ecs():
    redirect_url = ssm.get_parameter(Name=os.getenv(
        "CLOUDFRONT_DIST_SSM_PARAMETER_NAME"))['Parameter']['Value']
else:
    redirect_url = "http://localhost:8501/"

authenticator = CognitoHostedUIAuthenticator(app_client_secret=os.getenv("APP_CLIENT_SECRET"),
                                             app_client_id=os.getenv(
                                                 "APP_CLIENT_ID"),
                                             pool_id=os.getenv("POOL_ID"),
                                             cognito_domain=cognito_domain,
                                             redirect_uri=redirect_url,
                                             use_cookies=False
                                             )


is_logged_in = authenticator.login()

# st.warning("Login failed")
if not is_logged_in:
    st.stop()


def logout():
    authenticator.logout()


def clear_cache():
    st.cache_data.clear()


# Initial value
location = st.empty()

TESTDATA_FOLDER, IMAGES_FOLDER, DATA_PATH = get_paths()


def render_image_library():

    st.title("Image Library")
    image_library = S3ImageLibrary()
    df_library = image_library.to_dataframe()
    df_library.drop(columns=['similarity'], inplace=True)

    st.dataframe(df_library, column_config={
        "thumbnail": st.column_config.ImageColumn(
            "Thumbnail", width="large"
        )}, hide_index=True)

    with st.expander("Add New Image", expanded=False):
        new_image_form = st.form("add_image_form")
        uploaded_file = st.file_uploader(
            "Choose an image file", type=['jpg', 'png'])

        if uploaded_file:
            new_image_form.image(PIL.Image.open(uploaded_file), width=500)

        submit_image_btn = new_image_form.form_submit_button("Add Image")

        if submit_image_btn and uploaded_file is not None:
            uploaded_image = PIL.Image.open(
                uploaded_file).convert("RGB")
            image_library.add_image(
                uploaded_image, filename=uploaded_file.name)
            uploaded_file = None
            st.rerun()

    st.button("Clear Image Library", help="Clears the entire image library. WARNING: Cannot be reversed.",
              on_click=image_library.clear_library)


@ st.cache_data()
def get_email_by_username(username):
    # Initialize a Cognito Identity Provider client
    client = boto3.client('cognito-idp')

    try:
        # Get the user's information
        response = client.admin_get_user(
            UserPoolId=os.getenv("POOL_ID"),
            Username=username
        )

        print(f'User attributes: {response["UserAttributes"]}')

        # Extract the email attribute from the user's attributes
        for attr in response['UserAttributes']:
            if attr['Name'] == 'email':
                return attr['Value']

        return None
    except client.exceptions.UserNotFoundException:
        print(f"User {username} not found.")
        return None
    except BotoCoreError as error:
        # Generic error from Boto3/Botocore
        print(f"An error occurred: {error}")
        return None
    except ClientError as error:
        # Error from the Cognito service
        print(f"Client error occurred: {error}")
        return None


@ st.cache_data(show_spinner="Performing fraud analysis...")
def perform_deduction_cached(_image: Optional[PIL.Image.Image], filename: str, claim_report: str, claim_type: str, csim_threshold=0.85):
    # if _image:
    #     return api_client.perform_claim_deduction(claim_report=claim_report, claim_type=claim_type, csim_threshold=csim_threshold,image=_image).deduction
    return perform_deduction(
        image=_image, filename=filename, claim_report=claim_report, claim_type=claim_type, csim_threshold=csim_threshold)


@ st.cache_data(show_spinner="Performing reverse image search...")
def get_reverse_img_search_results(_img: PIL.Image, filename: string, sim_thresh=0)->ReverseImageSearchResults:

    # Fetch the dataframe
    # return api_client.reverse_internet_search_search_internet_post(image_file=img_byte_arr, sim_thresh=sim_thresh).results
    return reverse_image_search(_img, filename, sim_thresh)


def reinit_chat_session():
    st.session_state.sessionId = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.image_descriptions = []
    st.session_state.is_new_session = True


def validate_gps_coordinates(coord_str: str):
    """
    Validates if the given string is in the format "lat,lon" and represents valid GPS coordinates.

    Args:
    - coord_str(str): The string to validate.

    Returns:
    - tuple: A tuple containing the(latitude, longitude) if valid, or None if invalid.
    """
    # Regular expression to check for a valid format
    pattern = re.compile(
        r'^([-+]?[1-8]?\d(\.\d+)?|90(\.0+)?),\s*([-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?))$')
    match = pattern.match(coord_str)

    if match:
        lat, lon = map(float, match.groups()[:2])
        # if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon

    return None


if __name__ == "__main__":

    with st.sidebar:

        st.title(
            f"Welcome,\n{get_email_by_username(authenticator.get_username())}")
       
        st.button("Clear Cache", "clear_cach_btn", on_click=clear_cache)
        st.button("Logout", "logout_btn", on_click=logout)

    claim_lat = 0
    claim_lon = 0

    st.header("Next Gen Claims Fraud Detection")

    tab_data_checks, tab_chatbot = st.tabs(["Data Checks", "Chatbot"])

    with tab_data_checks:

        claim_form = st.form("claim_form")

        asset_file = claim_form.file_uploader(
            "Upload image:", accept_multiple_files=False, type=["png", "jpg", "jpeg"]
        )

        if asset_file:
            claim_form.image(PIL.Image.open(asset_file), width=500)

        expander = claim_form.expander("Incident date/time")
        claim_date = expander.date_input("Claim date (Local)")
        claim_time = expander.time_input("Claim time (Local)")

        expander = claim_form.expander("Incident Location")

        claim_location = expander.text_input("GPS Coordinates", value='')

        if claim_location:
            # lat_lon_value = validate_gps_coordinates(claim_location)
            lat_lon_value = claim_location.replace(' ', '').split(',')
            print(f'Lat lon value {lat_lon_value}')
            if not lat_lon_value is None:
                claim_lat, claim_lon = lat_lon_value
                print(f'Claim lat {claim_lat}')

                print(f'Claim lon {claim_lon}')

                expander.caption(
                    f'Latitude: {claim_lat} Longitude: {claim_lon}')

        expander = claim_form.expander("Object Detection")

        labels_text = expander.text_area(
            "Objects to look for (comma-separated)")

        settings_expander = claim_form.expander("Settings")

        rebuild = settings_expander.checkbox(
            "Rebuild index and database (takes a few minutes)")

        sim_thresh = settings_expander.slider(
            "Image similarity match threshold:",
            -1.0,
            1.0,
            value=0.9,
            help="The cosine sim. value at which a image 'match' is assumed.",
        )

        confidence_thresh = settings_expander.slider(
            "Object detection matching confidence threshold:",
            0,
            100,
            value=80,
            help="The confidence threshold where a object detection label match is assumed.",
        )

        claim_type = claim_form.selectbox(
            "What type of claim is this?",
            ("Motor Vehicle",  "Home & Contents"),
        )
        claim_report = claim_form.text_area(
            "Claim report", value="", placeholder="Please provide details of the claim, like location where the incident occurred, date and time of incident, circumstances of the incident, any witnesses or police reports, etc.")

        run_similarity = claim_form.checkbox("Run similarity search")

        run_location = claim_form.checkbox("Run location search")

        run_object_detection = claim_form.checkbox("Run object detection")

        run_generated_image_detection = claim_form.checkbox(
            "Run generated image detection")

        submit_btn = claim_form.form_submit_button("Submit")

        with tab_data_checks:

            tab_similarity, tab_exif, tab_labels, tab_gen_image, tab_ai_deduction, tab_image_library = st.tabs(
                ["Image Similarity", "EXIF Data", "Object Detection", "Generated Image Detection", "AI Fraud Detection", "Manage Image Library"])

            if asset_file:
                img = PIL.Image.open(asset_file)
            #     img_byte_arr = io.BytesIO()
            #     img.save(img_byte_arr, format=img.format)
            #     img_byte_arr = img_byte_arr.getvalue()

            with tab_similarity:

                if submit_btn:
                    if run_similarity:
                        if asset_file:

                            st.subheader("Image Library Similarity Search")
                            
                            png_image = io.BytesIO()
                            img.save(png_image, format='PNG')
                            png_image.seek(0)
                            png_image = PIL.Image.open(png_image)
                          
                            reverse_matches = api_client.search_image_library(image=png_image, sim_thresh=sim_thresh)

                            if len(reverse_matches) > 0:
                                st.caption(
                                    f'❗{len(reverse_matches)} image(s) have a high similarity score - please review')

                                display_matches = []

                                for match in reverse_matches:
                                    # Generate the Base64 from presigned URL
                                    img_url = url_to_base64(generate_presigned_url(
                                        STORAGE_BUCKET, match.thumbnail_s3_key))
                                    display_matches.append(
                                        {"Filename": match.filename, "Similarity": match.score, "Thumbnail": img_url})

                                st.dataframe(pd.DataFrame(display_matches), column_config={
                                    "Thumbnail": st.column_config.ImageColumn(
                                        "Thumbnail", width="large")}, hide_index=True)

                            else:
                                st.info(
                                    f'✅ No images with high similarity scores were found in the image library.')

                            st.subheader("Internet Reverse Image Search")
                            reverse_search_results = get_reverse_img_search_results(
                                img, asset_file.name, 0).results

                            reverse_match_count = sum(result.csim is not None and result.csim > sim_thresh for result in reverse_search_results)

                            if reverse_match_count > 0:
                                st.caption(
                                    f'❗{reverse_match_count} image(s) have a high similarity score - please review')
                            else:
                                st.info(
                                    f'✅ No images with high similarity scores were found on the internet.')

                            reverse_search_df = pd.DataFrame(
                                [result.model_dump() for result in reverse_search_results])
                           
                            st.dataframe(reverse_search_df,
                                         column_order=[
                                             "csim", "data_url", "source", "link", "title",  "thumbnail"],
                                         column_config={
                                             "data_url": st.column_config.ImageColumn(
                                                 "Image", width="large"
                                             ),
                                             "csim": st.column_config.NumberColumn("Similarity", format="%.2f"),
                                             "link": st.column_config.LinkColumn("link")
                                         }, hide_index=True)

                        else:
                            st.warning("Please upload a valid image file.")

            with tab_exif:

                col1, col2 = st.columns(2)

                with col1:
                    if run_location:
                        if asset_file:
                            img2 = PIL.Image.open(asset_file)
                            
                            exif_result = api_client.extract_exif_data(image=img2)

                            lat, lon = exif_result.latitude, exif_result.longitude

                            img_date_time = exif_result.timestamp

                            if img_date_time:
                                st.caption(f"Image timestamp: {img_date_time}")

                                if claim_date and claim_time:
                                    claim_dt = datetime.strptime(
                                        f'{claim_date} {claim_time}', '%Y-%m-%d %H:%M:%S')

                                    if claim_dt:
                                        print(f'Claim date time: {claim_dt}')
                                        # Compute the timedelta difference
                                        delta = claim_dt - img_date_time

                                        # Convert timedelta difference to minutes
                                        minutes_difference = abs(
                                            delta.total_seconds() / 60)

                                        if minutes_difference > 60:
                                            st.warning(
                                                f'❗ Claim timestamp and image timestamp differs by {round(minutes_difference / 60, 2)} hour(s). Please review.')
                                        else:
                                            st.info(
                                                '✅ Claim timestamp and image timestamp match.')

                            if not lat or not lon:
                                st.warning(
                                    "❔Image does not contain GPS location information.")
                            else:

                                st.caption(
                                    f'Image GPS coordinates: {round(lat, 4)}, {round(lon, 4)}')
                                st.caption(
                                    f'Image address lookup: {address_lookup(lat, lon)}')

                                df_locations = pd.DataFrame({
                                    'lat': [lat],  # Example latitude value
                                    'lon': [lon]  # Example longitude value
                                })

                                if claim_lat and claim_lon:

                                    st.caption(
                                        f'Claim address lookup: {address_lookup(claim_lat, claim_lon)}')
                                    distance = round(
                                        float(GD((lat, lon), (float(claim_lat), float(claim_lon))).km), 2)

                                    if distance > 0.1:
                                        st.warning(
                                            f'❗Distance between claim and GPS data in image is {distance}km, please review.')
                                    else:
                                        st.info(
                                            '✅ Location in image and claim matches.')

                                    st.title("Distance comparison")

                                    df_locations = pd.concat([df_locations, pd.DataFrame({
                                        # Another example latitude value
                                        'lat': [claim_lat],
                                        # Another example longitude value
                                        'lon': [claim_lon]
                                    })], ignore_index=True)
                                    # Ensure that lat and lon columns are of type float
                                    df_locations['lat'] = df_locations['lat'].astype(
                                        float)
                                    df_locations['lon'] = df_locations['lon'].astype(
                                        float)

                                  
                                    st.map(df_locations)

                                    # st.dataframe(df_total_data)

                                else:
                                    st.warning(
                                        "Provide claim location to perform comparison.")

                            exif_data = get_exif(img2)

                            st.caption(f'Exif data {exif_data}')

                        else:
                            st.warning("Please upload a valid image file.")

            with tab_labels:
                if submit_btn and asset_file and run_object_detection:
                    labels = [s.strip().lower()
                              for s in labels_text.split(',')]
                    rekog_response = detect_labels_in_image(
                        img, confidence_thresh)
                    labels_above_threshold = [label['Name'] for label in rekog_response['Labels'] if
                                              label['Confidence'] >= confidence_thresh]
                    detected_labels = [s.strip().lower()
                                       for s in labels_above_threshold]

                    if len(labels) > 0:
                        # make sure the label is detected

                        # Extract labels with confidence above the given threshold

                        found_labels = 0
                        for label in labels:
                            if label:
                                print(
                                    f'labels {label} detected labels {detected_labels}')
                                if not label in detected_labels:
                                    st.warning(
                                        f'❗object \'{label}\' not detected in image.')
                                else:
                                    st.info(
                                        f'✅ Object \'{label}\' detected in image.')
                                    found_labels += 1

                    drawn_image = display_labels_in_image(
                        img, rekog_response, confidence_thresh)
                    st.image(drawn_image)

            with tab_gen_image:
                if submit_btn and asset_file and run_generated_image_detection:
                    if not does_endpoint_exist():
                        st.warning(
                            '❗SageMaker endpoint does not exist. Please contact your administrator.')
                    else:
                        detection_result = detect_generated_image(
                            PIL.Image.open(asset_file))
                        if detection_result["confidence"] < 0.99:
                            st.warning(
                                f'❗Unable to tell if image was generated from AI, please review.')
                        elif detection_result["confidence"] > 0.99 and detection_result["prediction"] == 'FAKE':
                            st.warning(
                                f'❗Image possibly generated from AI, please review.')

                        else:
                            st.info(f'✅ Image was not generated from AI.')

                        st.caption(
                            f'Class: {detection_result["prediction"]} Confidence: {round((detection_result["confidence"] * 100), 2)}%')

            with tab_ai_deduction:
                with st.form(key="fraud_deduction_form"):
                    fraud_check_clicked = st.form_submit_button(
                        "Perform Fraud Check")
                    st.caption("This might take a few minutes to complete.")
                    if fraud_check_clicked:
                        if len(claim_report) == 0:
                            # Perform analysis
                            st.warning("Please provide claim report")
                        else:

                            img_file = None

                            if asset_file:
                                img_file = PIL.Image.open(asset_file)
                                deduction = perform_deduction_cached(
                                    _image=img_file, filename=asset_file.name, claim_report=claim_report, claim_type=claim_type, csim_threshold=sim_thresh)
                                st.markdown(
                                    deduction, unsafe_allow_html=True)

            with tab_image_library:
                render_image_library()

    with tab_chatbot:
        st.title("Claim Verification Chatbot")

        claim_text_col, image_upload_col = st.columns(2)

        claim_text = ""

        with st.form("claim_bot_info"):
            with claim_text_col:
                claim_text = st.text_area(
                    "Claim details - Please be as descriptive as possible", height=200)

            agent = FraudDetectionAgent(
                claim_report=claim_text)
            with image_upload_col:

                claim_img_files = st.file_uploader(
                    "Upload image:", accept_multiple_files=True, type=["png", "jpg", "jpeg"]
                )
                with st.container():

                    if claim_img_files and len(claim_img_files) > 0:
                        img_cols = st.columns(4)
                        col_index = 0
                        for claim_img_file in claim_img_files:
                            if col_index >= 4:
                                col_index = 0
                            # Generate a thumbnail of the image
                            claim_img = PIL.Image.open(
                                claim_img_file)  # PIL.Image.Image
                            claim_img_clone = claim_img.copy()
                            claim_img_clone.thumbnail((150, 150))
                            img_col = img_cols[col_index]
                            img_col.image(claim_img_clone)
                            col_index += 1

            if st.form_submit_button("Start Verification"):

                if len(claim_text) == 0:
                    st.warning("Please enter claim details")
                    st.stop()

                reinit_chat_session()

                if claim_img_files and len(claim_img_files) > 0:
                    for claim_img_file in claim_img_files:
                        claim_img = PIL.Image.open(claim_img_file)
                        descriptions = []
                        with st.spinner("Please wait while we process your photos..."):
                            for claim_img_file in claim_img_files:
                                claim_img = PIL.Image.open(claim_img_file)
                                description = get_claim_image_description(
                                    claim_img)
                                descriptions.append(description)
                            st.session_state.image_descriptions = descriptions

                else:
                    st.session_state.image_descriptions = []

        if "sessionId" in st.session_state:
            # if "agent" not in st.session_state:
            #     print('Creating new agent')
            #     st.session_state.agent = FraudDetectionAgent(
            #         claim_report=claim_text, claim_image=claim_img)

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            # st.text(f'Session ID: {st.session_state.sessionId}')

            if prompt := st.chat_input("Hi! I am here to help you with your claim."):
                # Display user message in chat message container

                # Add user message to chat history
                st.session_state.messages.append(
                    {"role": "user", "content": prompt})

                try:
                    with st.spinner("Thinking..."):
                        # Display assistant response in chat message container
                        image_descriptions = []
                        if "image_descriptions" in st.session_state:
                            image_descriptions = st.session_state.image_descriptions
                        if "is_new_session" not in st.session_state:
                            st.session_state.is_new_session = True

                        with st.chat_message("assistant"):
                            response = st.write_stream(agent.invoke_agent(
                                st.session_state.sessionId, prompt, st.session_state.is_new_session, image_descriptions))

                            # Add assistant response to chat history
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response})
                        st.session_state.is_new_session = False

                except Exception as e:
                    st.error(
                        f"Sorry, I'm having trouble connecting to the agent - {e}")
