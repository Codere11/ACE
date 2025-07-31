import requests

API_KEY = "sk-ac86f23b7a524c8cb0f42b4f62a010b2"
API_URL = "https://api.deepseek.com/v1/chat/completions"

class DeepSeekProvider:
    def __init__(self, model="deepseek-chat"):
        self.model = model

    def get_response(self, messages, temperature=0.7):
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
