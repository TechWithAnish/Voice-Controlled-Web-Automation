# Standard library imports
import time
import re
import os
import datetime
import webbrowser
import requests
import json
import sys
import logging
from typing import Dict, List, Optional, Tuple

# Third-party package imports
from dotenv import load_dotenv
import pyttsx3
import speech_recognition as sr
from fuzzywuzzy import fuzz

# Selenium imports for browser automation
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    WebDriverException
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_automation.log'),
        logging.StreamHandler()
    ]
)

class VoiceAutomationAssistant:
    """Main class for voice-controlled web automation assistant."""
    
    def __init__(self):
        """Initialize the voice automation assistant."""
        self.driver = None
        self.engine = None
        self.recognizer = None
        self.setup_components()
        
        # Predefined websites for quick access
        self.quick_sites = {
            "youtube": "https://www.youtube.com",
            "wikipedia": "https://www.wikipedia.com", 
            "google": "https://www.google.com",
            "netflix": "https://netflix.com",
            "instagram": "https://instagram.com",
            "amazon": "https://www.amazon.com",
            "spotify": "https://www.spotify.com",
            "facebook": "https://www.facebook.com",
            "twitter": "https://www.twitter.com",
            "github": "https://www.github.com",
            "stackoverflow": "https://stackoverflow.com",
            "reddit": "https://www.reddit.com"
        }
        
        # Command patterns for better matching
        self.command_patterns = {
            'open': [
                r'open\s+(.+)',
                r'go\s+to\s+(.+)',
                r'navigate\s+to\s+(.+)',
                r'visit\s+(.+)'
            ],
            'search': [
                r'search\s+for\s+(.+)',
                r'google\s+(.+)',
                r'look\s+up\s+(.+)',
                r'find\s+(.+)'
            ],
            'search_amazon': [
                r'search\s+amazon\s+(.+)',
                r'amazon\s+(.+)',
                r'buy\s+(.+)'
            ],
            'scroll_down': [
                r'scroll\s+down(?:\s+(\d+))?',
                r'page\s+down(?:\s+(\d+))?'
            ],
            'scroll_up': [
                r'scroll\s+up(?:\s+(\d+))?',
                r'page\s+up(?:\s+(\d+))?'
            ],
            'click': [
                r'click\s+on\s+(.+)',
                r'click\s+(.+)',
                r'press\s+(.+)'
            ]
        }

    def setup_components(self):
        """Initialize all required components."""
        try:
            # Initialize text-to-speech engine
            self.engine = pyttsx3.init()
            self.configure_tts()
            
            # Initialize speech recognizer
            self.recognizer = sr.Recognizer()
            
            # Initialize browser
            self.setup_browser()
            
            logging.info("All components initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up components: {e}")
            self.speak("There was a problem initializing the assistant.")
            sys.exit(1)

    def configure_tts(self):
        """Configure text-to-speech settings."""
        try:
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to set a female voice if available
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
            # Set speech rate and volume
            self.engine.setProperty('rate', 180)  # Speed of speech
            self.engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
            
        except Exception as e:
            logging.warning(f"Could not configure TTS settings: {e}")

    def setup_browser(self):
        """Initialize and configure the Chrome browser."""
        try:
            service = Service(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            
            # Chrome options for better performance and compatibility
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--disable-extensions')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.maximize_window()
            
            logging.info("Browser initialized successfully")
            
        except Exception as e:
            logging.error(f"Error setting up browser: {e}")
            raise

    def speak(self, text: str):
        """Speak the given text using pyttsx3."""
        try:
            print(f"Assistant: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logging.error(f"TTS error: {e}")
            print(f"Assistant: {text}")  # Fallback to text output

    def get_voice_command(self) -> str:
        """Capture and return voice input as lowercase text."""
        try:
            with sr.Microphone() as source:
                print("🎤 Listening...")
                self.recognizer.pause_threshold = 1
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Listen for audio input
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=10)
                print("🔄 Recognizing...")
                
                # Recognize speech using Google API
                query = self.recognizer.recognize_google(audio, language="en-US")
                print(f"👤 User: {query}")
                return query.lower().strip()
                
        except sr.WaitTimeoutError:
            print("⏰ No speech detected within timeout.")
            return ""
        except sr.UnknownValueError:
            self.speak("Sorry, I didn't understand that. Please try again.")
            return ""
        except sr.RequestError as e:
            self.speak("There is a problem with speech recognition.")
            logging.error(f"Speech recognition error: {e}")
            return ""
        except Exception as e:
            self.speak("There is a problem.")
            logging.error(f"Voice command error: {e}")
            return ""

    def normalize_url(self, url: str) -> str:
        """Normalize and validate URL format."""
        url = url.strip()
        
        # Check if it's a quick site
        if url in self.quick_sites:
            return self.quick_sites[url]
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            # Add .com if no domain extension present
            if '.' not in url:
                url = f"www.{url}.com"
            url = f"https://{url}"
        
        return url

    def open_website(self, website: str):
        """Open a website in the browser."""
        try:
            url = self.normalize_url(website)
            self.speak(f"Opening {website}")
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            
        except WebDriverException as e:
            self.speak(f"There was a problem opening {website}")
            logging.error(f"Error opening website {website}: {e}")

    def search_google(self, query: str):
        """Perform a Google search."""
        try:
            self.speak(f"Searching Google for {query}")
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(2)
            
        except Exception as e:
            self.speak("There was a problem with the Google search")
            logging.error(f"Google search error: {e}")

    def search_amazon(self, query: str):
        """Perform an Amazon search."""
        try:
            self.speak(f"Searching Amazon for {query}")
            search_url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(2)
            
        except Exception as e:
            self.speak("There was a problem with the Amazon search")
            logging.error(f"Amazon search error: {e}")

    def scroll_page(self, direction: str, pixels: int = 300):
        """Scroll the page in the specified direction."""
        try:
            if direction == "down":
                self.speak(f"Scrolling down by {pixels} pixels")
                self.driver.execute_script(f"window.scrollBy(0, {pixels});")
            elif direction == "up":
                self.speak(f"Scrolling up by {pixels} pixels")
                self.driver.execute_script(f"window.scrollBy(0, -{pixels});")
            elif direction == "bottom":
                self.speak("Scrolling to the bottom of the page")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            elif direction == "top":
                self.speak("Scrolling to the top of the page")
                self.driver.execute_script("window.scrollTo(0, 0);")
                
        except Exception as e:
            self.speak("There was a problem scrolling")
            logging.error(f"Scroll error: {e}")

    def click_element(self, element_text: str):
        """Click on an element containing the specified text."""
        try:
            self.speak(f"Looking for element containing '{element_text}'")
            
            # Try different strategies to find the element
            strategies = [
                (By.PARTIAL_LINK_TEXT, element_text),
                (By.LINK_TEXT, element_text),
                (By.XPATH, f"//*[contains(text(), '{element_text}')]"),
                (By.XPATH, f"//button[contains(text(), '{element_text}')]"),
                (By.XPATH, f"//input[@value='{element_text}']"),
                (By.XPATH, f"//*[@title='{element_text}']")
            ]
            
            element = None
            for by, value in strategies:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, value))
                    )
                    break
                except TimeoutException:
                    continue
            
            if element:
                element.click()
                self.speak(f"Clicked on {element_text}")
            else:
                self.speak(f"Could not find element containing '{element_text}'")
                
        except Exception as e:
            self.speak("There was a problem clicking the element")
            logging.error(f"Click error: {e}")

    def navigate_browser(self, action: str):
        """Navigate browser (back, forward, refresh)."""
        try:
            if action == "back":
                self.speak("Going back")
                self.driver.back()
            elif action == "forward":
                self.speak("Going forward")
                self.driver.forward()
            elif action == "refresh":
                self.speak("Refreshing the page")
                self.driver.refresh()
            time.sleep(1)
            
        except Exception as e:
            self.speak(f"There was a problem with browser navigation")
            logging.error(f"Navigation error: {e}")

    def get_current_time(self):
        """Get and speak the current time."""
        try:
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            self.speak(f"The current time is {current_time}")
            
        except Exception as e:
            self.speak("There was a problem getting the time")
            logging.error(f"Time error: {e}")

    def get_weather(self, city: str):
        """Get weather information for a specified city."""
        try:
            self.speak(f"Getting weather information for {city}")
            url = f"https://wttr.in/{city}?format=%C+%t"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                weather = response.text.strip()
                self.speak(f"The weather in {city} is {weather}")
            else:
                self.speak("Could not fetch weather information")
                
        except requests.RequestException as e:
            self.speak("There was a problem fetching the weather")
            logging.error(f"Weather error: {e}")

    def match_command_pattern(self, command: str) -> Tuple[str, Optional[str]]:
        """Match command against predefined patterns."""
        for cmd_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    return cmd_type, match.group(1) if match.groups() else None
        return None, None

    def process_command(self, command: str):
        """Process voice commands using pattern matching."""
        if not command:
            return

        command = command.strip().lower()
        
        # Exit commands
        exit_commands = ["exit", "close", "quit", "bye", "goodbye", "stop"]
        if any(word in command for word in exit_commands):
            self.speak("Closing the browser. Goodbye!")
            self.cleanup()
            return

        # Time commands
        if any(phrase in command for phrase in ["time", "what time", "current time"]):
            self.get_current_time()
            return

        # Weather commands
        weather_match = re.search(r"weather\s+(?:in\s+)?(\w+)", command)
        if weather_match:
            city = weather_match.group(1)
            self.get_weather(city)
            return

        # Browser navigation commands
        if "go back" in command or "back" in command:
            self.navigate_browser("back")
            return
        elif "go forward" in command or "forward" in command:
            self.navigate_browser("forward")
            return
        elif "refresh" in command or "reload" in command:
            self.navigate_browser("refresh")
            return

        # Scroll commands
        if "scroll to bottom" in command or "bottom" in command:
            self.scroll_page("bottom")
            return
        elif "scroll to top" in command or "top" in command:
            self.scroll_page("top")
            return

        # Pattern-based command matching
        cmd_type, value = self.match_command_pattern(command)
        
        if cmd_type == "open" and value:
            self.open_website(value)
        elif cmd_type == "search" and value:
            self.search_google(value)
        elif cmd_type == "search_amazon" and value:
            self.search_amazon(value)
        elif cmd_type == "scroll_down":
            pixels = int(value) if value and value.isdigit() else 300
            self.scroll_page("down", pixels)
        elif cmd_type == "scroll_up":
            pixels = int(value) if value and value.isdigit() else 300
            self.scroll_page("up", pixels)
        elif cmd_type == "click" and value:
            self.click_element(value)
        else:
            # Fuzzy matching for close commands
            best_match = None
            best_score = 0
            
            for site in self.quick_sites.keys():
                if site in command:
                    self.open_website(site)
                    return
            
            # If no exact match, try fuzzy matching
            for cmd in ["open google", "search", "scroll down", "go back"]:
                score = fuzz.partial_ratio(cmd, command)
                if score > best_score and score > 70:
                    best_score = score
                    best_match = cmd
            
            if best_match:
                self.speak(f"Did you mean {best_match}? Please try again with clearer pronunciation.")
            else:
                self.speak("I didn't understand that command. Please try again.")

    def cleanup(self):
        """Clean up resources before exit."""
        try:
            if self.driver:
                self.driver.quit()
            if self.engine:
                self.engine.stop()
            logging.info("Cleanup completed successfully")
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        finally:
            sys.exit(0)

    def run(self):
        """Main loop for the voice automation assistant."""
        # Welcome message
        welcome_msg = (
            "Hello! I'm your voice-controlled assistant. "
            "I can help you browse the web, search Google or Amazon, "
            "check the weather and time, and much more. "
            "Try saying 'open Google', 'search for cats', or 'weather in New York'."
        )
        self.speak(welcome_msg)
        
        # Main command loop
        while True:
            try:
                command = self.get_voice_command()
                if command:
                    print(f"🔄 Processing: {command}")
                    self.process_command(command)
                    
            except KeyboardInterrupt:
                self.speak("Stopping assistant...")
                break
            except Exception as e:
                self.speak("There was a problem. Please try again.")
                logging.error(f"Main loop error: {e}")
        
        self.cleanup()


def main():
    """Main function to start the voice automation assistant."""
    try:
        assistant = VoiceAutomationAssistant()
        assistant.run()
    except Exception as e:
        logging.error(f"Failed to start assistant: {e}")
        print("Failed to start the assistant. Please check the logs for details.")


if __name__ == "__main__":
    main()