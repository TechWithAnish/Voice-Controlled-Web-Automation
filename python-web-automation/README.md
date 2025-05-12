# Python Web Automation

This project is a Python-based web automation tool that utilizes voice commands to perform various tasks in web browsers. It currently supports automation in the Chrome browser but can be modified to support other browsers as well.

## Project Structure

```
python-web-automation
├── src
│   ├── AI_webautomation.py  # Main logic for web automation
│   └── __init__.py          # Marks the directory as a Python package
├── requirements.txt          # Lists project dependencies
└── README.md                 # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd python-web-automation
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the main script:
   ```
   python src/AI_webautomation.py
   ```

2. Follow the voice prompts to perform actions such as:
   - Opening Google or Amazon
   - Searching for items on Amazon
   - Scrolling through pages
   - Accessing Wikipedia

## Future Enhancements

- Support for additional web browsers (e.g., Firefox, Edge) by modifying the web driver initialization in `AI_webautomation.py`.
- Improved voice recognition accuracy and response handling.
- Additional web automation features based on user feedback.

## Dependencies

- `selenium`
- `pyttsx3`
- `speech_recognition`
- `webdriver_manager` (for managing browser drivers)

## License

This project is licensed under the MIT License. See the LICENSE file for more details.