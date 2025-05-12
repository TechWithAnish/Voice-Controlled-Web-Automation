# test_deepseek_model.py
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)
try:
    response = client.chat.completions.create(
        model="deepseek-chat",  # Try different model names
        messages=[{"role": "user", "content": "Hello, world!"}]
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")