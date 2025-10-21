# Language Codes Reference for cc-hooks

cc-hooks uses **ISO 639-1** language codes (2-letter codes) for TTS providers.

## Common Language Codes

| Language   | Code | Example Usage   |
| ---------- | ---- | --------------- |
| English    | `en` | `--language=en` |
| Japanese   | `ja` | `--language=ja` |
| Indonesian | `id` | `--language=id` |
| Spanish    | `es` | `--language=es` |
| French     | `fr` | `--language=fr` |
| German     | `de` | `--language=de` |
| Italian    | `it` | `--language=it` |
| Portuguese | `pt` | `--language=pt` |
| Russian    | `ru` | `--language=ru` |
| Chinese    | `zh` | `--language=zh` |
| Korean     | `ko` | `--language=ko` |
| Arabic     | `ar` | `--language=ar` |
| Hindi      | `hi` | `--language=hi` |
| Dutch      | `nl` | `--language=nl` |
| Polish     | `pl` | `--language=pl` |
| Turkish    | `tr` | `--language=tr` |
| Vietnamese | `vi` | `--language=vi` |
| Thai       | `th` | `--language=th` |

## Common Mistakes

⚠️ **Do not use country codes (ISO 3166-1)!**

| Wrong (Country Code)  | Correct (Language Code) | Language |
| --------------------- | ----------------------- | -------- |
| `jp` (Japan)          | `ja` (Japanese)         | Japanese |
| `cn` (China)          | `zh` (Chinese)          | Chinese  |
| `kr` (Korea)          | `ko` (Korean)           | Korean   |
| `uk` (United Kingdom) | `en` (English)          | English  |

## Provider-Specific Notes

### GTTS (Google TTS)

- Strictly validates language codes
- Raises `ValueError` for invalid codes
- Falls back to next provider on error
- See full list: https://gtts.readthedocs.io/en/latest/module.html#languages-gtts-lang

### ElevenLabs

- Supports all major languages
- Uses language code for voice optimization
- More flexible than GTTS

### Prerecorded

- Language code is ignored
- Always uses pre-recorded English audio files
- Serves as fallback when other providers fail

## Checking Language Support

You can test if a language code works with GTTS:

```python
#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["gtts"]
# ///

from gtts import gTTS

try:
    tts = gTTS(text="Test", lang="ja")
    print("✅ Language code 'ja' is supported")
except ValueError as e:
    print(f"❌ Error: {e}")
```

## Status Line Behavior

⚠️ **Known UX Issue**: The status line shows the _configured_ provider, not which provider actually
succeeded.

Example:

```bash
cld --language=jp  # Wrong code
# Status line shows: "Google TTS (JP)"
# Actual audio: Prerecorded (GTTS failed, fell back to prerecorded)
```

This happens because:

1. Status line reads from session configuration
2. Provider fallback happens at runtime
3. Status line doesn't track runtime failures

**Workaround**: Use correct language codes to ensure your intended provider works.

## Full List of ISO 639-1 Codes

For a complete list of ISO 639-1 language codes, see:

- https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
- https://www.loc.gov/standards/iso639-2/php/code_list.php
