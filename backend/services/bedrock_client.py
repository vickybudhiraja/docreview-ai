# backend/services/bedrock_client.py

import os
import boto3
from botocore.config import Config


class BedrockClient:
    def __init__(self):
        aws_region = os.getenv("AWS_DEFAULT_REGION")
        self.model_id = os.getenv("BEDROCK_MODEL_ID")

        if not aws_region:
            raise ValueError("AWS_DEFAULT_REGION is missing in environment")

        if not self.model_id:
            raise ValueError("BEDROCK_MODEL_ID is missing in environment")

        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=aws_region,
            config=Config(read_timeout=3600)
        )

    def converse_text(self, user_text: str, system_text: str | None = None) -> str:
        kwargs = {
            "modelId": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": user_text}]
                }
            ]
        }

        if system_text:
            kwargs["system"] = [{"text": system_text}]

        response = self.client.converse(**kwargs)

        content_list = response["output"]["message"]["content"]

        texts = []
        for item in content_list:
            if "text" in item:
                texts.append(item["text"])

        return "\n".join(texts).strip()