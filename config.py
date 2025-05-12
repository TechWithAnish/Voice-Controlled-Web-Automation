# config.py
from dotenv import load_dotenv
import os

load_dotenv()
apikey = os.getenv("OPENAI_API_KEY")