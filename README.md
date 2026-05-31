# IvaliceVera

**Final Fantasy Tactics: The Ivalice Chronicles — Save File Analyzer & Character Chat**

IvaliceVera parses FFT PC Remaster save files to extract party composition, story progress, and character data — then feeds it into [MultiVera](https://github.com/xsytrance/multivera) for immersive character chat with Ramza, Delita, Agrias, and the whole party.

## What It Does

- **Parse FFT save files** — upload a save, get story progress + party members
- **Auto-create MultiVera projects** — characters, commits, and story context from a save
- **Character chat** — talk to Ramza or any party member, story-locked to the save's point in the game
- **FFT lore KB** — full character profiles, relationships, story beats

## Quick Start

```bash
# Install dependencies
pip install fastapi sqlalchemy python-multipart uvicorn

# Run the server
python ivalicevera_app.py
```

API docs at `http://localhost:8787/docs`

## API Endpoints

### Save File Upload
```
POST /api/save/upload          — Upload & parse a save file
POST /api/save/create-project  — Upload save → create full MultiVera project
```

### FFT Lore
```
GET /api/lore/characters              — List all FFT characters
GET /api/lore/characters/{slug}       — Get character profile (e.g., ramza)
GET /api/lore/commits                 — List story commits
GET /api/lore/commits?phase=early     — Filter by story phase
```

### MultiVera (inherited)
```
GET    /api/projects                              — List projects
POST   /api/projects                              — Create project
GET    /api/projects/{id}                         — Get project
DELETE /api/projects/{id}                         — Delete project

GET    /api/projects/{id}/characters              — List characters
POST   /api/projects/{id}/characters              — Create character
POST   /api/projects/{id}/characters/extract      — Extract character from text (AI)
GET    /api/characters/{id}                       — Get character profile
PUT    /api/characters/{id}                       — Update character
DELETE /api/characters/{id}                       — Delete character

GET    /api/characters/{id}/commits               — List commits
POST   /api/characters/{id}/commits               — Create commit
GET    /api/commits/{id}                          — Get commit
PUT    /api/commits/{id}                          — Update commit
DELETE /api/commits/{id}                          — Delete commit

POST   /api/chat                                  — Chat with a character
GET    /api/conversations                         — List conversations
GET    /api/conversations/{id}                    — Get conversation
DELETE /api/conversations/{id}                    — Delete conversation
```

## How Character Chat Works

1. Upload a save file → story phase detected (early/mid/late)
2. Characters created from FFT lore KB (Ramza always present)
3. Story commits created from save progress
4. Chat with any character — they know only what they should know at that point
5. Ramza won't spoil the Lucavi plot if you're chatting in Chapter 1

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
| `ivalicevera_app.py` | FastAPI server — save upload, project creation, lore endpoints |
| `save_parser.py` | FFT save file parser — extracts party, story progress, characters |
| `lore_kb.py` | FFT character database + story commits |
| `multivera_integration.py` | Builds MultiVera projects from save data |
| `FFT_LORE_KB.md` | FFT lore knowledge base |
| `FFT_REVERSE_ENGINEERING.md` | Complete save format documentation |
| `ghost_*.py` | Ghost analysis utilities |
| `fft_*_finder.py` | Analysis scripts (job, ability, overlay, etc.) |

## Dependencies

- Python 3.11+
- fastapi, sqlalchemy, python-multipart, uvicorn
- [MultiVera](https://github.com/xsytrance/multivera) (backend/ directory)
- [FF16Tools](https://github.com/Nenkai/FF16Tools) (for initial PNG extraction)

## License

MIT
