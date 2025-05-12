# Voice-Controlled Web Automation

A Python-based voice assistant that automates web browsing, performs system tasks, and generates text using the DeepSeek AI API. Speak commands to open websites, search Google/Amazon, scroll pages, check the weather, tell the time, or generate documents like cover letters and resignation emails. The assistant supports natural language inputs and provides spoken error feedback for a seamless user experience.

## Features

- **Web Automation**:
  - Open websites (e.g., "open google", "go to youtube").
  - Search Google or Amazon (e.g., "search for cats", "search amazon headphones").
  - Navigate browser (e.g., "go back", "scroll down 500", "click on login").
- **System Tasks**:
  - Check the time (e.g., "tell me time").
  - Fetch weather (e.g., "weather in Noida").
- **Text Generation**:
  - Generate documents using DeepSeek AI (e.g., "generate cover letter", "write a resignation email").
  - Supports natural language queries (e.g., "I need a thank you note").
- **Natural Language Understanding**:
  - Processes freeform inputs via DeepSeek AI, returning JSON commands or text responses.
  - Maintains conversation context for follow-up questions.
- **Error Handling**:
  - Speaks user-friendly error messages (e.g., "There is a problem.") for API, speech, or browser issues.
  - Logs detailed errors to the terminal.
- **Robust Speech Recognition**:
  - Uses Google Speech API with noise adjustment and 10-second timeouts for reliable voice input.
  - Tolerates misrecognized words (e.g., "generator" as "generate") using fuzzy matching.

## Prerequisites

- **Python**: Version 3.10 or higher.
- **Microphone**: For voice input (built-in or external).
- **Chrome Browser**: For web automation.
- **DeepSeek API Key**: Free tier available at [api.deepseek.com](https://api.deepseek.com).
- **Internet Connection**: Required for API calls and weather fetching.

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/TechWithAnish/Voice-Controlled-Web-Automation.git
   cd Voice-Controlled-Web-Automation
   ```

2. **Set Up a Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   # source venv/bin/activate  # On macOS/Linux
   ```

3. **Install Dependencies**:
   ```bash
   pip install openai python-dotenv fuzzywuzzy python-Levenshtein requests pyttsx3 speechrecognition selenium webdriver-manager
   ```

4. **Configure DeepSeek API Key**:
   - Sign up at [api.deepseek.com](https://api.deepseek.com) and get a free API key.
   - Create a `.env` file in the project root:
     ```
     DEEPSEEK_API_KEY=your-deepseek-api-key
     ```

5. **Verify Microphone**:
   - Ensure your microphone is connected and recognized by Windows (Settings > Privacy > Microphone).
   - Test with a sample script if needed (see `test_speech.py` in the repository).

## Usage

1. **Run the Script**:
   ```bash
   python voice_automation.py
   ```
   - Chrome opens, and the assistant greets you: "Hello, I'm your voice-controlled assistant!..."

2. **Speak Commands**:
   - **Web Automation**:
     - "open google"
     - "search for python tutorials"
     - "scroll down 300"
     - "click on sign in"
   - **System Tasks**:
     - "tell me time"
     - "weather in London"
   - **Text Generation**:
     - "generate cover letter"
     - "write a resignation email"
   - **Natural Language**:
     - "I need a thank you note for a job interview"
     - "what’s the weather like in Delhi?"
   - **Exit**:
     - "quit" or "bye"

3. **Error Handling**:
   - If an error occurs (e.g., API failure, invalid command), the assistant says "There is a problem" or a specific message (e.g., "There is a problem fetching the weather").
   - Check the terminal for detailed error logs.

## Project Structure

```
Voice-Controlled-Web-Automation/
├── voice_automation.py  # Main script
├── .env                # Environment variables (add your DeepSeek API key)
├── README.md           # Project documentation
├── requirements.txt    # List of dependencies
```

## Troubleshooting

- **Speech Recognition Issues**:
  - Ensure microphone permissions are enabled.
  - Test with `test_speech.py`:
    ```bash
    python test_speech.py
    ```
  - Use a high-quality microphone to reduce background noise.
- **DeepSeek API Errors**:
  - Verify API key in `.env`.
  - Check model name in `voice_automation.py` (default: `deepseek-chat`).
  - Test with `test_deepseek_model.py`:
    ```bash
    python test_deepseek_model.py
    ```
- **ChromeDriver Issues**:
  - Ensure Chrome is installed and up-to-date.
  - Update `webdriver-manager`:
    ```bash
    pip install webdriver-manager --upgrade
    ```

## Contributing

Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License

MIT License. See `LICENSE` for details.

## Acknowledgments

- Built with [DeepSeek](https://api.deepseek.com) for free AI text generation.
- Uses [Selenium](https://www.selenium.dev) for web automation and [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) for voice input.
- Developed by Anish for voice-controlled automation.