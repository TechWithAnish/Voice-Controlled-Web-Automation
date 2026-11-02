import time
import re
import pyttsx3
import speech_recognition as sr
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Initialize and start the ChromeDriver service using webdriver_manager for automatic driver handling
service = Service(ChromeDriverManager().install())
service.start()

# Create a new instance of the Chrome WebDriver with SSL error handling
options = webdriver.ChromeOptions()
options.add_argument('--ignore-certificate-errors')
driver = webdriver.Chrome(service=service, options=options)

def speak(response):
    """Uses pyttsx3 to speak out any given response."""
    engine = pyttsx3.init()
    engine.say(response)
    engine.runAndWait()

def get_voice_command():
    """Captures user's voice input using the microphone and returns the recognized text in lowercase."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1
        audio = recognizer.listen(source)
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

def process_command(command):
    """Parses the user's command and maps it to browser automation functions."""
    if not command:
        return
    
    # Exit commands: if the command contains "exit", "close", or "quit".
    if any(word in command for word in ["exit", "close", "quit"]):
        speak("Closing the browser. Goodbye!")
        driver.quit()
        service.stop()
        exit()

    # Open website: detect commands starting with "open" or "go to"
    if command.startswith("open") or command.startswith("go to"):
        website = command.replace("open", "").replace("go to", "").strip()
        if not website.startswith("http"):
            if "." not in website:
                website = f"www.{website}.com"
            website = "https://" + website
        speak(f"Opening {website}")
        driver.get(website)
        return

    # Search commands: recognizes phrases like "search for <query>".
    if "search for" in command:
        search_phrase = command.split("search for", 1)[1].strip()
        speak(f"Searching Google for {search_phrase}")
        driver.get(f"https://www.google.com/search?q={search_phrase}")
        return

    # Scroll commands: look for "scroll down" or "scroll up".
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

    # Click commands: expects "click on <element text>"
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

    # Browser navigation: go back, go forward, refresh/reload.
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

    # If no known pattern was detected.
    speak("I'm sorry, I didn't understand that command.")

# Greet the user and provide instructions.
speak("Hello! How can I assist you with your browser today?")
speak("You can say things like 'open Google', 'search for cats', 'scroll down', 'click on a link', 'go back', 'refresh', or 'exit'.")

# Main program loop: continuously listen for voice commands and process them.
while True:
    command = get_voice_command()
    if command:
        process_command(command)
