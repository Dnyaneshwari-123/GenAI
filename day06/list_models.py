import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

response = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": "Bearer " + os.getenv("GROQ_API_KEY")},
    timeout=30,
)
for model in response.json()["data"]:
    print(model["id"])