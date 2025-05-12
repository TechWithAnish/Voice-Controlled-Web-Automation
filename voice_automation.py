import time
import re
import os
import datetime
import webbrowser
import requests
import json
from dotenv import load_dotenv
import pyttsx3
import speech_recognition as sr
from fuzzywuzzy import fuzz
from openai import OpenAI
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Load environment variables
load_dotenv()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

# Initialize DeepSeek client
client = OpenAI(
    api_key=deepseek_api_key,
    base_url="https://api.deepseek.com/v1"
)

# Initialize text-to-speech
engine = pyttsx3.init()

# Initialize ChromeDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(service=service, options=options)

# Chat history for DeepSeek
chat_history = [
    {
        "role": "system",
        "content": "You are a voice-controlled assistant that can perform web automation tasks (e.g., open websites, search, scroll, click links), system tasks (e.g., tell time, fetch weather), and generate text (e.g., cover letters, emails). For each user input, determine if it's a command or a general query. If it's a command, return a JSON object with 'action' and 'value' (e.g., {'action': 'open', 'value': 'google.com'}). If it's a query, return a natural language response. Maintain context for follow-up questions. Current time: " + datetime.datetime.now().strftime("%H:%M:%S")
    }
]

def speak(response):
    """Speak the given response using pyttsx3."""
    engine.say(response)
    engine.runAndWait()

def get_voice_command():
    """Capture and return voice input as lowercase text."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            print("Recognizing...")
            query = recognizer.recognize_google(audio, language="en-in")
            print(f"User: {query}")
            return query.lower()
        except sr.WaitTimeoutError:
            print("No speech detected within timeout.")
            return ""
        except sr.UnknownValueError:
            speak("Sorry, I didn't understand that.")
            return ""
        except sr.RequestError as e:
            speak("There is a problem with speech recognition.")
            print(f"Speech recognition error: {e}")
            return ""
        except Exception as e:
            speak("There is a problem.")
            print(f"Error: {e}")
            return ""

def ai_response(prompt):
    """Generate a response using DeepSeek."""
    global chat_history
    try:
        chat_history.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="deepseek-chat",  # Updated model name
            messages=chat_history,
            temperature=0.7,
            max_tokens=256,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        answer = response.choices[0].message.content.strip()
        chat_history.append({"role": "assistant", "content": answer})
        # Keep chat history manageable
        if len(chat_history) > 20:
            chat_history = chat_history[:1] + chat_history[-19:]
        return answer
    except Exception as e:
        print(f"DeepSeek error: {e}")
        speak("There is a problem with the AI service.")
        return "Sorry, I couldn't generate a response."

def process_command(command):
    """Processes voice commands or natural language queries."""
    global chat_history

    if not command:
        return

    # Exit commands
    if any(word in command for word in ["exit", "close", "quit", "bye"]):
        speak("Closing the browser. Goodbye!")
        driver.quit()
        service.stop()
        exit()

    # Fuzzy match commands
    commands = [
        ("open", lambda cmd: cmd.startswith("open") or cmd.startswith("go to")),
        ("search for", lambda cmd: "search for" in cmd),
        ("search amazon", lambda cmd: "search amazon" in cmd),
        ("scroll down", lambda cmd: "scroll down" in cmd),
        ("scroll up", lambda cmd: "scroll up" in cmd),
        ("scroll to bottom", lambda cmd: "scroll to bottom" in cmd),
        ("click on", lambda cmd: "click on" in cmd),
        ("go back", lambda cmd: "go back" in cmd),
        ("go forward", lambda cmd: "go forward" in cmd),
        ("refresh", lambda cmd: "refresh" in cmd or "reload" in cmd),
        ("the time", lambda cmd: "the time" in cmd or "tell me time" in cmd),
        ("weather", lambda cmd: "weather" in cmd),
        ("generate", lambda cmd: fuzz.partial_ratio("generate", cmd) > 80 or fuzz.partial_ratio("generator", cmd) > 80),
        ("reset chat", lambda cmd: "reset chat" in cmd)
    ]

    for cmd_name, cmd_check in commands:
        if cmd_check(command):
            if cmd_name == "open":
                website = command.replace("open", "").replace("go to", "").strip()
                if not website.startswith("http"):
                    if "." not in website:
                        website = f"www.{website}.com"
                    website = "https://" + website
                speak(f"Opening {website}")
                driver.get(website)
            elif cmd_name == "search for":
                search_phrase = command.split("search for", 1)[1].strip()
                speak(f"Searching Google for {search_phrase}")
                driver.get(f"https://www.google.com/search?q={search_phrase}")
            elif cmd_name == "search amazon":
                search_query = command.split("search amazon", 1)[1].strip()
                speak(f"Searching Amazon for {search_query}")
                driver.get(f"https://www.amazon.com/s?k={search_query}")
            elif cmd_name == "scroll down":
                match = re.search(r"scroll down (\d+)", command)
                pixels = int(match.group(1)) if match else 300
                speak(f"Scrolling down by {pixels} pixels.")
                driver.execute_script(f"window.scrollBy(0, {pixels});")
            elif cmd_name == "scroll up":
                match = re.search(r"scroll up (\d+)", command)
                pixels = int(match.group(1)) if match else 300
                speak(f"Scrolling up by {pixels} pixels.")
                driver.execute_script(f"window.scrollBy(0, {-pixels});")
            elif cmd_name == "scroll to bottom":
                speak("Scrolling to the bottom of the page.")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            elif cmd_name == "click on":
                element_text = command.split("click on", 1)[1].strip()
                try:
                    speak(f"Clicking on element containing '{element_text}'")
                    element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_text))
                    )
                    element.click()
                except Exception as e:
                    speak("There is a problem finding the element.")
                    print(e)
            elif cmd_name == "go back":
                speak("Going back.")
                driver.back()
            elif cmd_name == "go forward":
                speak("Going forward.")
                driver.forward()
            elif cmd_name == "refresh":
                speak("Refreshing the page.")
                driver.refresh()
            elif cmd_name == "the time":
                strfTime = datetime.datetime.now().strftime("%H:%M:%S")
                speak(f"The time is {strfTime}")
            elif cmd_name == "weather":
                match = re.search(r"weather in (\w+)", command)
                city = match.group(1) if match else None
                if city:
                    try:
                        url = f"https://wttr.in/{city}?format=%C+%t"
                        response = requests.get(url)
                        if response.status_code == 200:
                            weather = response.text.strip()
                            speak(f"The weather in {city} is {weather}.")
                        else:
                            speak("There is a problem fetching the weather.")
                    except Exception as e:
                        speak("There is a problem fetching the weather.")
                        print(e)
                else:
                    speak("Please specify a city for the weather.")
            elif cmd_name == "generate":
                prompt = command.replace("generate", "").replace("generator", "").strip()
                response = ai_response(f"Generate: {prompt}")
                speak(response)
            elif cmd_name == "reset chat":
                chat_history = [
                    {
                        "role": "system",
                        "content": "You are a voice-controlled assistant that can perform web automation tasks (e.g., open websites, search, scroll, click links), system tasks (e.g., tell time, fetch weather), and generate text (e.g., cover letters, emails). For each user input, determine if it's a command or a general query. If it's a command, return a JSON object with 'action' and 'value' (e.g., {'action': 'open', 'value': 'google.com'}). If it's a query, return a natural language response. Maintain context for follow-up questions. Current time: " + datetime.datetime.now().strftime("%H:%M:%S")
                    }
                ]
                speak("Chat history reset.")
            return

    # Handle predefined sites
    sites = [
        ["youtube", "https://www.youtube.com"],
        ["wikipedia", "https://www.wikipedia.com"],
        ["google", "https://www.google.com"],
        ["netflix", "https://netflix.com"],
        ["instagram", "https://instagram.com"],
        ["amazon", "https://www.amazon.in"],
        ["spotify", "https://www.spotify.com"]
    ]
    for site in sites:
        if f"open {site[0]}" in command:
            speak(f"Opening {site[0]}.")
            webbrowser.open(site[1])
            return

    # Natural language processing for unrecognized commands
    response = ai_response(command)
    try:
        # Check if response is a JSON command
        cmd = json.loads(response)
        if isinstance(cmd, dict) and "action" in cmd and "value" in cmd:
            action, value = cmd["action"], cmd["value"]
            if action == "open":
                speak(f"Opening {value}")
                driver.get(f"https://{value}" if not value.startswith("http") else value)
            elif action == "search":
                speak(f"Searching Google for {value}")
                driver.get(f"https://www.google.com/search?q={value}")
            elif action == "say":
                speak(value)
            else:
                speak("There is a problem with the command.")
        else:
            speak(response)
    except json.JSONDecodeError:
        # Response is natural language
        speak(response)

# Greet the user
speak("Hello, I'm your voice-controlled assistant! How can I help you today?")
speak("Try saying 'open Google', 'search for cats', 'weather in Noida', 'generate a cover letter', or anything else!")

# Main loop
while True:
    try:
        command = get_voice_command()
        if command:
            print(f"Processing command: {command}")
            process_command(command)
    except Exception as e:
        print(f"Main loop error: {e}")
        speak("There is a problem. Please try again.")