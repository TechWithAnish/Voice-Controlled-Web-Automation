# Voice-Controlled Web Automation

A Python-based voice assistant that automates web browsing and performs system tasks using natural speech commands. Control your browser hands-free with voice commands to open websites, search Google/Amazon, navigate pages, check weather, and more.

## ✨ Features

### 🌐 Web Automation
- **Website Navigation**: Open any website with voice commands
- **Smart Search**: Search Google or Amazon using natural language
- **Page Control**: Scroll, click elements, navigate browser history
- **Quick Sites**: Instant access to popular websites (YouTube, GitHub, etc.)

### 🎯 System Tasks
- **Time & Weather**: Get current time and weather for any city
- **Browser Control**: Back, forward, refresh, and window management
- **Smart Element Detection**: Click on page elements using natural descriptions

### 🗣️ Voice Features
- **Natural Language Processing**: Understand conversational commands
- **Fuzzy Matching**: Tolerates mispronunciations and variations
- **Audio Feedback**: Clear spoken responses for all actions
- **Error Handling**: Graceful error recovery with helpful messages

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**: Required for all functionality
- **Chrome Browser**: Used for web automation
- **Microphone**: For voice input (built-in or external)
- **Internet Connection**: Required for speech recognition and weather

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/voice-web-automation.git
   cd voice-web-automation
   ```

2. **Create Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Test Your Setup**:
   ```bash
   python test_speech.py
   ```
   This will verify your microphone, speech recognition, and text-to-speech functionality.

### Usage

1. **Start the Assistant**:
   ```bash
   python voice_automation.py
   ```

2. **Try These Commands**:
   ```
   🌐 Web Navigation:
   - "open google"
   - "go to youtube"
   - "visit github"
   
   🔍 Search:
   - "search for python tutorials"
   - "google machine learning"
   - "amazon wireless headphones"
   
   📄 Page Control:
   - "scroll down 500"
   - "click on sign in"
   - "go back"
   - "refresh page"
   
   ℹ️ Information:
   - "what time is it"
   - "weather in London"
   
   🚪 Exit:
   - "quit" or "bye"
   ```

## 📋 Command Reference

### Website Navigation
| Command | Action | Example |
|---------|--------|---------|
| `open [site]` | Open website | "open wikipedia" |
| `go to [url]` | Navigate to URL | "go to example.com" |
| `visit [site]` | Visit website | "visit stackoverflow" |

### Search Commands
| Command | Action | Example |
|---------|--------|---------|
| `search for [query]` | Google search | "search for AI tutorials" |
| `google [query]` | Google search | "google python docs" |
| `amazon [query]` | Amazon search | "amazon bluetooth speaker" |

### Page Control
| Command | Action | Example |
|---------|--------|---------|
| `scroll down [pixels]` | Scroll down | "scroll down 300" |
| `scroll up [pixels]` | Scroll up | "scroll up 200" |
| `scroll to bottom` | Scroll to bottom | "scroll to bottom" |
| `click on [element]` | Click element | "click on login" |

### Browser Navigation
| Command | Action |
|---------|--------|
| `go back` | Browser back |
| `go forward` | Browser forward |
| `refresh` | Reload page |

### System Information
| Command | Action | Example |
|---------|--------|---------|
| `what time` | Current time | "what time is it" |
| `weather in [city]` | Weather info | "weather in Paris" |

## 🔧 Configuration

### Customizing Quick Sites
Edit the `quick_sites` dictionary in `voice_automation.py`:

```python
self.quick_sites = {
    "youtube": "https://www.youtube.com",
    "mysite": "https://example.com",  # Add custom sites
    # ... more sites
}
```

### Adjusting Speech Settings
Modify TTS settings in the `configure_tts()` method:

```python
self.engine.setProperty('rate', 180)     # Speech speed
self.engine.setProperty('volume', 0.9)   # Volume level
```

### Adding Custom Commands
Extend the `command_patterns` dictionary to add new command types:

```python
self.command_patterns = {
    'your_command': [
        r'your\s+pattern\s+(.+)',
        r'alternative\s+pattern\s+(.+)'
    ]
}
```

## 🛠️ Troubleshooting

### Common Issues

**Speech Recognition Not Working**:
```bash
# Test your setup
python test_speech.py

# Check microphone permissions in system settings
# Ensure internet connection for Google Speech API
```

**Browser Not Opening**:
```bash
# Update ChromeDriver
pip install webdriver-manager --upgrade

# Ensure Chrome browser is installed and updated
```

**TTS Not Working**:
```bash
# Check audio output devices
# Try different TTS engines
# Verify pyttsx3 installation
```

### Debug Mode
Enable detailed logging by modifying the logging level:

```python
logging.basicConfig(level=logging.DEBUG)
```

### Performance Optimization
- Close unnecessary browser tabs
- Use `--headless` Chrome option for background operation
- Adjust timeout values for slower connections

## 📁 Project Structure

```
voice-web-automation/
├── voice_automation.py    # Main assistant class
├── test_speech.py         # Audio testing utility
├── requirements.txt       # Python dependencies
├── README.md             # Documentation
└── voice_automation.log  # Runtime logs
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints for new functions
- Include error handling for external API calls
- Update documentation for new features

## 🐛 Known Issues

- Speech recognition may struggle with heavy accents
- Chrome updates can occasionally break WebDriver compatibility
- Weather API has rate limiting (rarely encountered)

## 🔮 Future Enhancements

- [ ] Support for Firefox and Edge browsers
- [ ] Custom wake word detection
- [ ] Voice command macro recording
- [ ] Integration with calendar and email
- [ ] Offline speech recognition option
- [ ] Mobile app companion

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Selenium](https://selenium.dev) for web automation
- Uses [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) for voice input
- Weather data from [wttr.in](https://wttr.in) API
- Text-to-speech powered by [pyttsx3](https://pypi.org/project/pyttsx3/)

## 📞 Support

If you encounter any issues or have questions:

1. Check the [troubleshooting section](#-troubleshooting)
2. Run `python test_speech.py` to diagnose audio issues
3. Check the `voice_automation.log` file for detailed error information
4. Open an issue on GitHub with your system details and error logs

---

**Made with ❤️ for hands-free web browsing**