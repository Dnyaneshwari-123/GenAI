import os
import requests
from dotenv import load_dotenv

load_dotenv()


class LLM:

    def __init__(self, provider=None):

        self.provider = provider or os.getenv("LLM_PROVIDER", "groq")

        if self.provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

        elif self.provider == "gemini":
            self.api_key = os.getenv("GEMINI_API_KEY")
            self.model = os.getenv("GEMINI_MODEL")

        else:
            raise ValueError("Invalid provider")

        if not self.api_key or not self.model:
            raise ValueError("API key or model is missing")

    def ask(self, system_prompt, user_prompt):

        try:
            if self.provider == "groq":
                return self.ask_groq(system_prompt, user_prompt)
            else:
                return self.ask_gemini(system_prompt, user_prompt)
        except (requests.exceptions.RequestException, KeyError, IndexError) as error:
            raise RuntimeError("LLM call failed: " + str(error))

    def ask_groq(self, system_prompt, user_prompt):

        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }

        response = requests.post(
            url, headers=headers, json=data, timeout=60
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Groq error " + str(response.status_code) + ": " + response.text[:300]
            )

        return response.json()["choices"][0]["message"]["content"]

    def ask_gemini(self, system_prompt, user_prompt):

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + self.model + ":generateContent"
        )

        headers = {
            "x-goog-api-key": self.api_key
        }

        data = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ]
        }

        response = requests.post(
            url, headers=headers, json=data, timeout=60
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Gemini error " + str(response.status_code) + ": " + response.text[:300]
            )

        return response.json()["candidates"][0]["content"]["parts"][0]["text"]