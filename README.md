# Voice-Controlled Web Automation

This project is a Python-based voice-controlled assistant that automates web browsing tasks and performs system operations using voice commands. It integrates **Selenium** for web automation, **SpeechRecognition** for voice input, **pyttsx3** for text-to-speech, **OpenAI** for AI-generated text, and **pdfplumber** for form data extraction.

## Features
- **Voice Recognition**: Converts voice commands to text using Google Speech Recognition.
- **Web Automation**:
  - Open websites (e.g., "open google", "go to youtube.com").
  - Perform Google or Amazon searches (e.g., "search for cats", "search amazon laptop").
  - Scroll pages (e.g., "scroll down 500", "scroll to bottom").
  - Click links (e.g., "click on login").
  - Navigate browser history (e.g., "go back", "refresh").
- **System Commands**:
  - Tell the time (e.g., "the time").
  - Fetch weather for a city (e.g., "weather in London").
- **AI Integration**: Generate text like emails or answers using OpenAI (e.g., "generate a resignation email").
- **Form Filling**: Extract data from PDFs and fill online forms.
- **User-Friendly**: Provides spoken feedback for all actions.

## Requirements
- Python 3.8+
- Chrome browser
- Internet connection (for Google Speech Recognition and OpenAI API)
- Microphone

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/TechWithAnish/Voice-Controlled-Web-Automation.git
   cd Voice-Controlled-Web-Automation
   ```

2. **Set Up a Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up OpenAI API Key**:
   - Copy the `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and add your OpenAI API key:
     ```
     OPENAI_API_KEY=your-api-key-here
     ```

5. **Install ChromeDriver**:
   - The `webdriver-manager` package automatically handles ChromeDriver installation.

## Usage
1. Run the script:
   ```bash
   python voice_automation.py
   ```

2. Follow the spoken prompts and use commands like:
   - "open google"
   - "search for python tutorials"
   - "scroll down 300"
   - "click on sign in"
   - "tell me the time"
   - "weather in New York"
   - "generate a thank you email"
   - "exit"

3. To fill a form:
   - Update `formfiller.py` with the target form URL, PDF path, and field mappings.
   - Run:
     ```bash
     python formfiller.py
     ```

## Example Commands
| Command                     | Action                                    |
|-----------------------------|-------------------------------------------|
| "open youtube"              | Opens YouTube in the browser              |
| "search for machine learning" | Searches Google for "machine learning"   |
| "scroll to bottom"          | Scrolls to the bottom of the page         |
| "weather in Tokyo"          | Fetches weather for Tokyo                 |
| "generate a resignation email" | Generates a resignation email using OpenAI |

## Project Structure
```
Voice-Controlled-Web-Automation/
├── voice_automation.py  # Main script for voice-controlled web automation
├── formfiller.py        # Script for PDF-based form filling
├── .env                # Environment variables (API keys)
├── requirements.txt     # Python dependencies
├── .gitignore           # Git ignore file
├── README.md            # Project documentation
```

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m "Add feature"`).
4. Push to the branch (`git push origin feature-name`).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements
- [Selenium](https://www.selenium.dev/) for web automation.
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) for voice input.
- [pyttsx3](https://pypi.org/project/pyttsx3/) for text-to-speech.
- [OpenAI](https://openai.com/) for AI text generation.
- [pdfplumber](https://github.com/jsvine/pdfplumber) for PDF parsing.

## Disclaimer
This project is provided as-is without any warranty. Use at your own risk. Ensure you have a valid OpenAI API key and comply with its usage policies.