import base64
from io import BytesIO
import json
import os
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
import PIL
from PIL.Image import Image
from datetime import datetime
from dotenv import load_dotenv
from websearch import reverse_image_search

load_dotenv()

AGENT_ID = os.environ.get("AGENT_ID", "CKLEWQHZC5")
AGENT_ALIAS_ID = os.environ.get("AGENT_ALIAS_ID", "QGW4VRNITE")


def get_claim_image_description(claim_image: Image) -> str:
    """
    Processes an insurance claim image and returns a detailed description.

    This function resizes the input image to a maximum of 1024x1024 pixels while maintaining the aspect ratio,
    converts the image to a base64-encoded string, and sends it to an AI model for detailed description.
    The description focuses on objects, environment, and the state of objects in the image, providing intelligent
    guesses on how the objects got to their current state.

    Args:
        claim_image (Image): A PIL.Image object representing the insurance claim image.

    Returns:
        str: A detailed description of the image provided by the AI model.
    """

    # Resize the image to a max of 1024x1024, maintaining the aspect ratio
    claim_image.thumbnail((1024, 1024), PIL.Image.LANCZOS)

    # Create a BytesIO object to hold the image data

    image_bytes_io = BytesIO()

    # Save the PIL.Image object to the BytesIO object
    claim_image.save(image_bytes_io, format='JPEG')

    # Get the image bytes from the BytesIO object
    image_bytes = image_bytes_io.getvalue()

    # Encode the image bytes as a base64 string
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')

    # Prepare the request body with the image and prompt
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,  # Adjust as needed
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": encoded_image
                        }
                    },
                    {
                        "type": "text",
                        "text": "You are inspecting photos submitted for insurance claims. Describe the image in detail. Focus on objects, environment and the state of objects in the image. Provide intelligent guesses on how the objects in the image got to the state they are in. Do not mention anything about speculating or privacy, only provide a professional description."
                    }
                ]
            }
        ]
    }

    bedrock_runtime = boto3.client('bedrock-runtime')
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    response = bedrock_runtime.invoke_model(
        body=json.dumps(request_body),
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )

    response_body = json.loads(response['body'].read())
    image_description = response_body['content'][0]['text']
    print(f'Image description: {image_description}')

    return image_description


def perform_image_search(claim_image: Image, filename: str) -> str:

    # Do similarity check
    df_search = reverse_image_search(
        claim_image, filename=filename, sim_thresh=0.95)

    df_search = df_search.sort_values(by='csim', ascending=False)

    search_augment = ""

    return search_augment


class FraudDetectionAgent:

    def __init__(self, claim_report: str):
        self.agents_runtime_client = boto3.client('bedrock-agent-runtime')

        self.claim_report = claim_report

    def augment_prompt(self, prompt, claim_image_descriptions: List[str]):
        """
        Build the prompt attributes for the agent.
        """

        prompt = f"Here is the response from the user: {prompt}"

        print('Claim report that was initially submitted:', self.claim_report)

        prompt += f"Claim report that was initially submitted: {self.claim_report}\n"

        current_datetime = datetime.now().strftime("%d %b %Y %H:%M:%S")

        prompt += f"The current date/time is: {current_datetime}\n"

        if len(claim_image_descriptions) > 0:
            prompt += "The user uploaded photos as part of the claim. The descriptions of the photos are as follows:\n"
            for claim_image_description in claim_image_descriptions:
                prompt += f"<ImageDescription>{claim_image_description}</ImageDescription>\n"

        return prompt

    def process_string(self, input_string: str):
        """
        Process the input string and return the question.
        """

        strings_to_remove = [("<question>", "</question>"),
                             ("<sources>", "</sources>")]

        for start_tag, end_tag in strings_to_remove:
            if start_tag in input_string and end_tag in input_string:
                start_index = input_string.index(start_tag) + len(start_tag)
                end_index = input_string.index(end_tag)
                input_string = input_string[start_index:end_index]

        input_string = input_string.replace("<<REDACTED>>", "")

        return input_string

    def invoke_agent(self, session_id, prompt, is_new_session: bool, claim_image_descriptions: List[str] = []):
        """
        Sends a prompt for the agent to process and respond to.

        :param agent_id: The unique identifier of the agent to use.
        :param agent_alias_id: The alias of the agent to use.
        :param session_id: The unique identifier of the session. Use the same value across requests
                           to continue the same conversation.
        :param prompt: The prompt that you want Claude to complete.
        :return: Inference response from the model.
        """

        try:
            if is_new_session:
                prompt = self.augment_prompt(prompt, claim_image_descriptions)

            print(f"Sending prompt: {prompt}")
            response = self.agents_runtime_client.invoke_agent(
                agentId=AGENT_ID,
                agentAliasId=AGENT_ALIAS_ID,
                sessionId=session_id,
                memoryId=session_id,
                inputText=prompt,
                enableTrace=False
            )

            print(f"Response: {response}")

            for event in response.get("completion"):
                print(event)
                chunk = event["chunk"]
                yield self.process_string(chunk["bytes"].decode())
                # completion = completion + chunk["bytes"].decode()

        except ClientError as e:
            print(f"Couldn't invoke agent. {e}")
            raise
