# Voice-Controlled Web Automation

Drive a real browser by speaking. Say *"open youtube"*, *"search for python
tutorials"*, *"click on sign in"*, *"scroll down 400"* — the assistant hears
the command, performs it, and tells you what it did.

Works with **Chrome, Edge, Brave and Firefox**. By default it uses whichever
one you already have installed; no driver download or setup is needed.

[![CI](https://github.com/TechWithAnish/Voice-Controlled-Web-Automation/actions/workflows/ci.yml/badge.svg)](https://github.com/TechWithAnish/Voice-Controlled-Web-Automation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Browsers](https://img.shields.io/badge/browsers-Chrome%20%7C%20Edge%20%7C%20Brave%20%7C%20Firefox-blue)](#install)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Install

Requires Python 3.10 or newer and one of Chrome, Edge, Brave or Firefox. The
matching driver is downloaded automatically on first run by Selenium Manager.

```bash
git clone https://github.com/TechWithAnish/Voice-Controlled-Web-Automation.git
cd Voice-Controlled-Web-Automation

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

For microphone input, add the audio backend:

```bash
pip install -e ".[mic]"
```

That installs `sounddevice`, which ships prebuilt wheels with PortAudio
bundled — no compiler, and it works on every Python 3 version.

<details>
<summary>Using PyAudio instead</summary>

PyAudio also works and takes priority when both are installed:

```bash
pip install -e ".[mic-pyaudio]"
```

It is a C extension, so pip compiles it from source whenever PyPI has no
wheel for your Python version. That needs Microsoft Visual C++ Build Tools on
Windows, `brew install portaudio` on macOS, or `portaudio19-dev` on Debian.
`sounddevice` avoids all of that, which is why it is the default.
</details>

Neither is needed to try the assistant: `--text` drives the same pipeline
from the keyboard.

## Check your setup

```bash
voice-automation --doctor
```

Each check reports a remedy if it fails:

```
Voice automation pre-flight checks
----------------------------------------------
[PASS] Python version: 3.12.4 on Windows AMD64
[PASS] Configuration: valid (overrides: none)
[PASS] Browser: using Microsoft Edge (C:\Program Files\Microsoft\Edge\Application\msedge.exe); installed: Microsoft Edge, Brave
[PASS] Microphone: sounddevice, 3 device(s), default: Microphone Array
[PASS] Text to speech: 2 voice(s): Microsoft Zira, Microsoft David
[PASS] Network: reached google.com (HTTP 200)
----------------------------------------------
All checks passed.
```

## Run

```bash
voice-automation                       # listen on the microphone
voice-automation --text                # type commands instead of speaking
voice-automation --browser brave       # pick a browser
voice-automation --command "open youtube" --command "scroll down 400"
voice-automation --headless --no-speech
```

`python -m voice_automation` works identically.

| Flag | Effect |
|---|---|
| `--doctor` | Run pre-flight checks and exit |
| `--text` | Read typed commands from stdin instead of the microphone |
| `--command TEXT` | Run one command and exit; repeatable, implies `--text` |
| `--browser` | `auto` (default), `chrome`, `edge`, `brave` or `firefox` |
| `--headless` | Run without a visible window |
| `--no-speech` | Print responses instead of speaking them |
| `--search-engine` | `google` (default), `duckduckgo` or `bing` |
| `--log-level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `--log-file PATH` | Write rotating logs to `PATH` |

Exit codes: `0` normal, `1` runtime failure, `2` invalid configuration.

## Commands

The assistant tolerates filler ("please open youtube", "can you go back"),
spoken punctuation ("example dot com slash docs") and spoken numbers
("scroll down two hundred").

### Navigation

| Say | Action |
|---|---|
| `open youtube` / `go to example.com` / `visit github` | Open a site |
| `youtube` | A known site name on its own opens it |
| `go back` / `go forward` / `refresh` | Browser history |
| `where am i` | Read out the current page |

### Search

| Say | Action |
|---|---|
| `search for python tutorials` | Web search |
| `google machine learning` / `look up tide times` | Web search |
| `search amazon for headphones` / `buy milk` | Amazon |
| `search youtube for jazz` / `play lo-fi on youtube` | YouTube |
| `search wikipedia for turing` / `who is ada lovelace` | Wikipedia |

### Page control

| Say | Action |
|---|---|
| `click on sign in` / `press submit` | Click a link, button or control |
| `scroll down` / `scroll down 400` / `scroll down two hundred` | Scroll |
| `scroll up` / `scroll to top` / `scroll to bottom` | Scroll |

### Information and control

| Say | Action |
|---|---|
| `what time is it` / `what is the date` | Clock and calendar |
| `weather in london` | Current conditions |
| `help` | List examples |
| `exit` / `quit` / `close the browser` | Shut down |

Anything unrecognised is answered with the closest known command rather than
guessed at.

## Configuration

Every setting is optional. Copy [`.env.example`](.env.example) to `.env`, or
export the variables directly. No API keys are needed: speech recognition
uses Google's free endpoint and weather comes from
[wttr.in](https://wttr.in).

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| `VA_BROWSER` | `auto` | `chrome`, `edge`, `brave`, `firefox`, or `auto` |
| `VA_BROWSER_BINARY` | auto | Path to the browser, if discovery misses it |
| `VA_DRIVER_PATH` | auto | Pin a driver instead of letting Selenium fetch one |
| `VA_HEADLESS` | `false` | Run without a window |
| `VA_PAGE_LOAD_TIMEOUT` | `30` | Seconds before a page load is abandoned |
| `VA_ELEMENT_TIMEOUT` | `8` | Seconds spent looking for an element to click |
| `VA_SCROLL_STEP` | `400` | Default scroll distance in pixels |
| `VA_DISABLE_SANDBOX` | `false` | Add `--no-sandbox`; needed in containers only |
| `VA_SPEECH_LANGUAGE` | `en-US` | Recognition language, e.g. `en-IN` |
| `VA_MICROPHONE_INDEX` | default | Input device index, as listed by `--doctor` |
| `VA_LISTEN_TIMEOUT` | `8` | Seconds of silence before giving up on a turn |
| `VA_AMBIENT_CALIBRATION` | `1` | Seconds of noise calibration |
| `VA_RECALIBRATE_EVERY` | `25` | Commands between re-calibrations (`0` = once) |
| `VA_ENERGY_THRESHOLD` | auto | Fixed microphone sensitivity for noisy rooms |
| `VA_TTS_ENABLED` | `true` | Speak responses |
| `VA_TTS_RATE` / `VA_TTS_VOLUME` / `VA_TTS_VOICE` | `180` / `0.9` / auto | Voice tuning |
| `VA_SEARCH_ENGINE` | `google` | `google`, `duckduckgo` or `bing` |
| `VA_DEFAULT_WEATHER_CITY` | unset | Used when you say "weather" with no city |
| `VA_LOG_LEVEL` | `INFO` | Logging verbosity |
| `VA_LOG_FILE` | unset | Enable rotating file logging |
| `VA_MAX_CONSECUTIVE_FAILURES` | `5` | Failures tolerated before stopping |

An invalid value fails at start-up and names the variable, rather than
surfacing later as a confusing browser error.

## How it works

```
microphone ──► speech/listener ──► commands/parser ──► assistant ──► browser/controller ──► browser
                                        (pure)            │
                                                          ├──► services/weather
                                                          └──► speech/tts ──► speaker
```

| Module | Responsibility |
|---|---|
| `config` | Typed settings, validated at start-up |
| `commands` | Utterance to intent. No I/O, so it is exhaustively testable |
| `browser` | Browser discovery, plus a small safe action surface over Selenium |
| `speech` | Microphone capture and speech output, behind protocols |
| `services` | Outbound HTTP (weather) |
| `assistant` | Orchestration, failure handling and shutdown |
| `cli` | Arguments, logging, signals, exit codes |

Each layer depends only on the ones below it, and every collaborator is
injected, so the command loop can be tested end to end with fakes.

### Adding a command

1. Add a member to `Intent` in `commands/models.py`.
2. Add an anchored pattern to `RULES` in `commands/parser.py`. Order matters:
   specific rules go above general ones.
3. Add a `_do_<intent>` method to `VoiceAssistant`.
4. Add a parser case and a loop case to the tests.

## Development

```bash
pip install -r requirements-dev.txt
pre-commit install          # optional

pytest                      # 352 tests, no browser or microphone needed
pytest --cov --cov-report=term-missing
pytest -m browser           # opt-in: drives a real browser against a local page
ruff check .
mypy
```

The default suite fakes every external collaborator, so it runs offline in
about two seconds. CI runs it on Python 3.10 through 3.13 on Linux and
Windows. The `browser` marker selects a small set of integration tests that
launch a real browser; they are deselected by default.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `No audio input backend is installed` | Run `pip install -e ".[mic]"`. Use `--text` meanwhile. |
| PyAudio fails to build with "Visual C++ 14.0 or greater is required" | No prebuilt wheel exists for your Python version. Use `pip install -e ".[mic]"` instead — `sounddevice` needs no compiler. |
| Wrong microphone is used | Run `--doctor` to list devices, then set `VA_MICROPHONE_INDEX`. |
| Nothing is heard in a noisy room | Set `VA_ENERGY_THRESHOLD` to a fixed value such as `300`, or raise `VA_AMBIENT_CALIBRATION`. |
| `No supported browser was found` | Install Chrome, Edge, Brave or Firefox, or point `VA_BROWSER_BINARY` at an executable. |
| `<browser> is not installed` | `VA_BROWSER` names one you do not have. Run `--doctor` to see what is installed. |
| Driver download fails | Set `VA_DRIVER_PATH` to a driver you downloaded yourself, matching your browser version. |
| Responses are printed, not spoken | No speech engine. On Linux install `espeak-ng`; on Windows check SAPI5 voices. |
| A command does the wrong thing | Run with `--text` and `--log-level DEBUG`: the log records the intent each utterance matched. |
| Recognition struggles with your accent | Set `VA_SPEECH_LANGUAGE`, for example `en-IN` or `en-GB`. |

## Privacy

Audio is sent to Google's speech recognition service for transcription; that
is how the `SpeechRecognition` package's free endpoint works. Weather queries
go to wttr.in. Nothing else leaves your machine, and no transcript is stored
unless you enable file logging with `VA_LOG_FILE`.

## Limitations

- Recognition needs an internet connection; there is no offline mode.
- Clicking matches visible text, labels and titles. It cannot target an
  element that has no accessible text.
- One tab. There is no tab or window management.

## Project layout

```
.
├── src/voice_automation/     # the package
│   ├── assistant.py          # orchestration
│   ├── cli.py                # entry point
│   ├── config.py             # settings
│   ├── diagnostics.py        # --doctor
│   ├── logging_setup.py
│   ├── urls.py               # URL safety and search templates
│   ├── browser/              # discovery, Selenium wrapper, XPath escaping
│   ├── commands/             # intent parsing
│   ├── services/             # weather
│   └── speech/               # microphone backends and text-to-speech
├── tests/                    # 352 offline tests
│   └── integration/          # opt-in live-browser tests (pytest -m browser)
├── examples/                 # unsupported legacy scripts
└── .github/workflows/ci.yml
```

## Contributing

1. Fork and branch from `main`.
2. `pip install -r requirements-dev.txt`.
3. Keep `ruff check .`, `mypy` and `pytest` green; new behaviour needs a test.
4. Note user-visible changes in `CHANGELOG.md`.
5. Open a pull request.

## Licence

MIT — see [LICENSE](LICENSE).

Built with [Selenium](https://selenium.dev),
[SpeechRecognition](https://pypi.org/project/SpeechRecognition/),
[pyttsx3](https://pypi.org/project/pyttsx3/),
[RapidFuzz](https://pypi.org/project/rapidfuzz/) and
[wttr.in](https://wttr.in).
