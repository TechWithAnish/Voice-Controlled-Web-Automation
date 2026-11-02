# Migrating from 1.x

## What changed at a glance

| 1.x | 2.0 |
|---|---|
| `python voice_automation.py` | `voice-automation` (after `pip install -e .`) |
| `python test_speech.py` | `voice-automation --doctor` |
| `pip install -r requirements.txt` | same command, now resolves through `pyproject.toml` |
| Edit `voice_automation.py` to change settings | `VA_*` environment variables or `.env` |
| `DEEPSEEK_API_KEY` in `.env` | removed — it was never used by any code |
| Always wrote `voice_automation.log` next to the process | no log file unless `VA_LOG_FILE` is set |
| `voice_automation.py`, `AI_webautomation.py`, `formfiller.py`, `test_selenium.py`, `test_deepseek_model.py` | moved to `examples/`, unsupported |

Nothing you could say to 1.x has been removed. Several phrases that used to
do the wrong thing now do the right one — see `CHANGELOG.md`.

## Upgrading

```bash
git pull
pip install -e .          # replaces: pip install -r requirements.txt
voice-automation --doctor
voice-automation
```

If you had a `.env`, the `DEEPSEEK_API_KEY` line in it is now ignored and can
be deleted. Copy `.env.example` over it for the full list of real settings.

## Where your old customisations go

**Custom sites.** You used to edit the `quick_sites` dictionary inside
`voice_automation.py`. It now lives in `src/voice_automation/urls.py` as
`QUICK_SITES`, with the same shape:

```python
QUICK_SITES = {
    "youtube": "https://www.youtube.com",
    "intranet": "https://intranet.example.com",   # add yours here
}
```

**Speech rate and volume.** These were literals in `configure_tts()`. Set
`VA_TTS_RATE` and `VA_TTS_VOLUME` instead — no code change.

**New commands.** Previously a new entry in `command_patterns` plus a branch
in the `if`/`elif` chain in `process_command`. Now: an `Intent` member, an
anchored rule in `RULES`, and a `_do_<intent>` method. The README has a
worked example.

## Cleaning up a working copy that still has the 1.x files

If you are upgrading an existing clone in place rather than pulling the
branch, two files from 1.x are superseded and should be removed, since the
package now owns that code:

```bash
git rm voice_automation.py test_speech.py
git add -A
git commit -m "Restructure into an installable package"
```

`voice_automation.log` is now covered by `.gitignore`; delete it if it is
still sitting in your working copy. If it was ever committed, remove it from
tracking with `git rm --cached voice_automation.log`.

The `.idea/` directory is no longer tracked either — PyCharm settings are
per-developer. Your local copy is untouched; git simply stops following it.
