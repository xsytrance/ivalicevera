# IvaliceVera

**Final Fantasy Tactics: The Ivalice Chronicles — Save File Analyzer & Character Chat**

IvaliceVera parses FFT PC Remaster save files to extract party composition, story progress, and character data — then feeds it into [MultiVera](https://github.com/xsytrance/multivera) for immersive character chat.

## What It Does

- **Parse FFT save files** (`.png` container → extracted `.sav` files via [FF16Tools](https://github.com/Nenkai/FF16Tools))
- **Extract story progress** — chapter/scene detection from save header
- **Identify party members** — both story characters (Ramza, Delita, Agrias...) and player-created characters
- **Build character context** — feeds save data + FFT lore KB into MultiVera for character chat

## Quick Start

```bash
# Parse a save file
python save_parser.py /path/to/fftsave.bin

# Or auto-detect all saves in /home/xsyvps/fft-saves*/
python save_parser.py
```

## Save File Format

See [FFT_REVERSE_ENGINEERING.md](FFT_REVERSE_ENGINEERING.md) for complete format documentation.

Key findings:
- **Story progress**: Offset 0x38-0x39 in 40KB `resume_*_main.sav` files
- **Character records**: 12-byte marker + 92-byte stat block + name string
- **Two encoding types**: STANDARD (raw u16) and NEW (u16 << 8)
- **Extended region**: 0x31000-0x45000 contains per-character metadata

## Project Structure

| File | Purpose |
|------|---------|
| `save_parser.py` | Main save file parser — extracts party, story progress, characters |
| `FFT_LORE_KB.md` | FFT lore knowledge base — story, characters, world |
| `FFT_REVERSE_ENGINEERING.md` | Complete save format documentation |
| `fft_*_finder.py` | Analysis scripts for job ID, abilities, battle overlay, etc. |
| `ghost_*.py` | Ghost character analysis utilities |
| `TEST_PLAN.md` | Controlled test procedures for format discovery |

## MultiVera Integration

IvaliceVera is designed to feed into [MultiVera](https://github.com/xsytrance/multivera) for character chat:

1. Load save → extract party + story progress
2. Look up character profiles from lore KB
3. Generate system prompt with story context
4. Chat with Ramza, Delita, Agrias, or any party member

## Requirements

- Python 3.11+
- FF16Tools (Nenkai) for PNG container extraction
- No other dependencies (stdlib only)

## License

MIT
