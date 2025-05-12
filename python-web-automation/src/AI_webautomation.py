import time
import pyttsx3
import speech_recognition as sr
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Function to initialize the web driver based on the browser choice
def initialize_driver(browser='chrome'):
    if browser == 'chrome':
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service)
    elif browser == 'firefox':
        service = FirefoxService(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service)
    else:
        raise ValueError("Unsupported browser! Please choose 'chrome' or 'firefox'.")
    return driver

# Create a new instance of the WebDriver
driver = initialize_driver('chrome')  # Change 'chrome' to 'firefox' to use Firefox

# Function to get voice command from the user
def get_voice_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1
        audio = recognizer.listen(source)
    try:
        print("Recognizing...")
        query = recognizer.recognize_google(audio, language='en-in')
        print(f"User: {query}")
        return query.lower()
    except sr.UnknownValueError:
        print("Sorry, I didn't understand that.")
        return ""
    except sr.RequestError:
        print("Sorry, I'm unable to process your request at the moment.")
        return ""

# Function to speak the response
def speak(response):
    engine = pyttsx3.init()
    engine.say(response)
    engine.runAndWait()

# Greet the user
speak("Hello! How can I assist you today?")

# Main program loop
while True:
    command = get_voice_command()
    if command:
        # Open Google
        if "open google" in command:
            speak("Google opened in the browser.")
            driver.get('https://www.google.com')

        # Search on Amazon
        elif "search amazon" in command:
            speak("What would you like to search on Amazon?")
            search_query = get_voice_command()
            speak(f"Searching Amazon for '{search_query}'")
            driver.get(f'https://www.amazon.com/s?k={search_query}')

        # Open Amazon
        elif "open amazon" in command:
            speak("Opening Amazon.")
            driver.get('https://www.amazon.com')

        # Scroll down the page
        elif "scroll down" in command:
            speak("Scrolling down the page.")
            scroll_height = 0
            while scroll_height < 1000:
                scroll_height += 50
                driver.execute_script("window.scrollTo(0, " + str(scroll_height) + ");")
                time.sleep(0.5)

        # Scroll up the page
        elif "scroll up" in command:
            speak("Scrolling up the page.")
            scroll_height = 1000
            while scroll_height > 0:
                scroll_height -= 50
                driver.execute_script("window.scrollTo(0, " + str(scroll_height) + ");")
                time.sleep(0.5)

        # Search for Batman on Wikipedia
        elif "search batman" in command:
            speak("Searching for Batman.")
            driver.get('https://en.wikipedia.org/wiki/Batman')

        # Click on the first link in search results
        elif "click on first link" in command:
            speak("Clicking on the first link.")
            first_link = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="search"]/div[1]/div[1]/div/span[1]/div[1]/div[3]/div/div/div/div/div/div/div/div[2]/div/div/div[1]/h2/a/span')))

            first_link.click()

        # Exit from the browser
        elif "exit from the browser" in command:
            speak("Closing the browser. Goodbye!")
            break

# Close the browser window
driver.quit()