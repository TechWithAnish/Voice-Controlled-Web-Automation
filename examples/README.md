# Examples (unsupported)

These scripts are kept for reference only. They are **not** part of the
`voice_automation` package, are excluded from packaging, linting, type
checking and CI, and are not covered by tests. Nothing here is maintained.

| File | What it was | Why it is not in the package |
|---|---|---|
| `legacy_voice_automation.py` | The v1.x single-file assistant | Superseded by the `voice_automation` package. Kept so the old behaviour can be compared against the new one. |
| `legacy_monolithic_assistant.py` | An earlier duplicate of the same assistant, written at module scope | A second copy of the same logic that drifted out of step with the first. |
| `legacy_audio_test.py` | Interactive microphone / TTS check | Replaced by `voice-automation --doctor`, which reports the same information plus Chrome, configuration and network checks. |
| `selenium_smoke_check.py` | Three lines that open Google in Chrome | A manual check, not a test. It was named `test_selenium.py`, so `pytest` collected it and launched a real browser. |
| `deepseek_api_probe.py` | A probe against the DeepSeek chat API | The assistant never had an LLM layer; this was left over from an abandoned experiment. It imports `openai`, which the project does not depend on. |
| `pdf_form_filler.py` | Fills a web form from a PDF | Unfinished and unrelated to voice control. It imports `pdfplumber`, which the project does not depend on, and as written it submits a real third-party form when run. |

## If you want to run one

Install the extra dependency it needs first, and read the file before you run
it. `pdf_form_filler.py` in particular performs a live form submission.

```bash
pip install pdfplumber        # pdf_form_filler.py
pip install openai            # deepseek_api_probe.py (also needs an API key)
```
