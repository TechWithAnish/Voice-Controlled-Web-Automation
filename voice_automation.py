import time
import re
import os
import datetime
import webbrowser
import requests
from dotenv import load_dotenv
import pyttsx3
import speech_recognition as sr
import openai
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize text-to-speech
engine = pyttsx3.init()

# Initialize ChromeDriver
service = Service(ChromeDriverManager().install())
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(service=service, options=options)

# Chat history for OpenAI
chat_history = ""

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
        audio = recognizer.listen(source, timeout=5)
    try:
        print("Recognizing...")
        query = recognizer.recognize_google(audio, language="en-in")
        print(f"User: {query}")
        return query.lower()
    except sr.UnknownValueError:
        speak("Sorry, I didn't understand that.")
        return ""
    except sr.RequestError:
        speak("Sorry, I'm unable to process your request at the moment.")
        return ""
    except Exception as e:
        speak("An error occurred while listening.")
        print(e)
        return ""

def ai_response(prompt):
    """Generate a response using OpenAI."""
    global chat_history
    try:
        chat_history += f"Anish: {prompt}\nAssistant: "
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=chat_history,
            temperature=0.7,
            max_tokens=256,
            top_p=Processes voice commands for web automation, system tasks, and AI queries."""
    global chat_history

    if not command:
        return

    # Exit commands
    if any(word in command for word in ["exit", "close", "quit", "bye"]):
        speak("Closing the browser. Goodbye!")
        driver.quit()
        service.stop()
        exit()

    # Open website
    if command.startswith("open") or command.startswith("go to"):
        website = command.replace("open", "").replace("go to", "").strip()
        if not website.startswith("http"):
            if "." not in website:
                website = f"www.{website}.com"
            website = "https://" + website
        speak(f"Opening {website}")
        driver.get(website)
        return

    # Search commands
    if "search for" in command:
        search_phrase = command.split("search for", 1)[1].strip()
        speak(f"Searching Google for {search_phrase}")
        driver.get(f"https://www.google.com/search?q={search_phrase}")
        return

    if "search amazon" in command:
        search_query = command.split("search amazon", 1)[1].strip()
        speak(f"Searching Amazon for {search_query}")
        driver.get(f"https://www.amazon.com/s?k={search_query}")
        return

    # Scroll commands
    if "scroll down" in command:
        match = re.search(r"scroll down (\d+)", command)
        pixels = int(match.group(1)) if match else 300
        speak(f"Scrolling down by {pixels} pixels.")
        driver.execute_script(f"window.scrollBy(0, {pixels});")
        return

    if "scroll up" in command:
        match = re.search(r"scroll up (\d+)", command)
        pixels = int(match.group(1)) if match else 300
        speak(f"Scrolling up by {pixels} pixels.")
        driver.execute_script(f"window.scrollBy(0, {-pixels});")
        return

    if "scroll to bottom" in command:
        speak("Scrolling to the bottom of the page.")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        return

    # Click commands
    if "click on" in command:
        element_text = command.split("click on", 1)[1].strip()
        try:
            speak(f"Clicking on element containing '{element_text}'")
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_text))
            )
            element.click()
        except Exception as e:
            speak(f"Could not find an element with text '{element_text}'.")
            print(e)
        return

    # Browser navigation
    if "go back" in command:
        speak("Going back.")
        driver.back()
        return

    if "go forward" in command:
        speak("Going forward.")
        driver.forward()
        return

    if "refresh" in command or "reload" in command:
        speak("Refreshing the page.")
        driver.refresh()
        return

    # System commands
    if "the time" in command:
        strfTime = datetime.datetime.now().strftime("%H:%M:%S")
        speak(f"The time is {strfTime}")
        return

    if "weather" in command:
        speak("Please tell me the city name.")
        city = get_voice_command()
        if city:
            try:
                url = f"https://wttr.in/{city}?format=%C+%t"
                response = requests.get(url)
                if response.status_code == 200:
                    weather = response.text.strip()
                    speak(f"The weather in {city} is {weather}.")
                else:
                    speak("Sorry, I couldn't fetch the weather.")
            except Exception as e:
                speak("An error occurred while fetching the weather.")
                print(e)
        return

    # Open predefined sites
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

    # AI query
    if "using artificial intelligence" in command or "generate" in command:
        prompt = command.replace("using artificial intelligence", "").replace("generate", "").strip()
        response = ai_response(prompt)
        speak(response)
        return

    # Reset chat
    if "reset chat" in command:
        chat_history = ""
        speak("Chat history reset.")
        return

    # Default
    speak("I'm sorry, I didn't understand that command.")

# Greet the user
speak("Hello, I'm your voice-controlled assistant! How can I help you today?")
speak("Try saying 'open Google', 'search for cats', 'scroll down', 'tell me the time', 'weather in London', or 'generate a resignation email'.")

# Main loop
while True:
    command = get_voice_command()
    if command:
        process_command(command)