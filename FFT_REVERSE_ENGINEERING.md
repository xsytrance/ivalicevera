# FFT PC Remaster — Save File Reverse Engineering
## Complete Documentation
### May 2026 — OWL & Ed

---

## Table of Contents
1. [Background & Motivation](#1-background--motivation)
2. [Tools & Environment](#2-tools--environment)
3. [Save File Container Format](#3-save-file-container-format)
4. [Inner Binary Format — Discovery Process](#4-inner-binary-format--discovery-process)
5. [Character Record Structure](#5-character-record-structure)
6. [Cross-Character Analysis](#6-cross-character-analysis)
7. [Equipment Storage](#7-equipment-storage)
8. [Two Encoding Types](#8-two-encoding-types)
9. [Scripts & Reproduction](#9-scripts--reproduction)
10. [Open Questions & Next Steps](#10-open-questions--next-steps)
11. [Lessons Learned](#11-lessons-learned)

---

## 1. Background & Motivation

**Goal:** Parse Final Fantasy Tactics PC Remaster ("The Ivalice Chronicles") save files to extract character stats, party composition, inventory, and story progress — for integration with MultiVera (a character chat/analysis platform).

**Why:** No public documentation exists for the PC Remaster's save format. The community (FFHacktics, Nenkai) has documented the PNG container wrapper and the old PSX/PSP save formats, but the PC Remaster uses a completely different internal binary format.

**Starting point:** Three sets of save files from the user's Windows machine (Winport), extracted using FF16Tools:
- `autoenhanced/` — autosave files (17 files across 3 slots)
- `enhanced/` — manual save (1 file, the complete game state archive)
- `system/` — settings (256-byte fixed file)

---

## 2. Tools & Environment

### Required Software
- **FF16Tools** (Nenkai): https://github.com/Nenkai/FF16Tools
  - CLI or GUI version
  - Command: `FF16Tools.CLI unpack -g fft "save.png" "output_folder"`
  - Handles PNG → XOR decrypt → zlib decompress → raw binary

### Save File Locations (Windows)
```
C:\Users\<user>\Documents\My Games\FINAL FANTASY TACTICS\Steam\<steam_id>\
```
- `autoenhanced.png` — autosave (extracted to multiple .sav files)
- `enhanced.png` — manual save (extracted to `fftsave.bin`)
- `system.png` — settings (extracted to `settings.sav`)

### Transfer to Linux VPS
```powershell
scp -r output\autoenhanced\ xsyvps@100.65.108.84:/home/xsyvps/fft-saves/tactics/
```

### Python Environment
Any Python 3.11+ with standard library only (struct, pathlib, re, collections). No external dependencies needed.

---

## 3. Save File Container Format

**Outer wrapper:** PNG image with custom chunk.

**Steps to unwrap:**
1. Parse PNG chunks, find custom chunk with ID `ffTo`
2. Extract chunk data (encrypted + compressed)
3. XOR decrypt with 64-bit key: `0xF3F80FE5F1FC4F3`
4. Prepend zlib header `0x78 0xF9` (indicates fdict flag)
5. Decompress with zlib using FF16Tools' 32KB custom dictionary (`CompressDict.ZlibDict`)

**Result:** Raw `.sav` files containing the game state.

**Source:** FF16Tools C# source at `FF16Tools.Files/Save/`:
- `FaithSaveFile.cs` — container reading/writing
- `CompressDict.cs` — 32KB zlib preset dictionary

**Note:** We did NOT have to reimplement this — FF16Tools handled it. The challenge was parsing the inner binary after extraction.

---

## 4. Inner Binary Format — Discovery Process

### 4.1 Early Assumptions (WRONG)

Initially we assumed the inner format might be XML-based (like the PSX version) or contain clear text. It does not. It's a proprietary binary format.

### 4.2 File Types

| File | Size | Content |
|------|------|---------|
| `*_main.sav` | ~40 KB | Story progress + all character data |
| `*_world.sav` | ~40 KB | World map state |
| `*_attack.sav` | ~1.1 MB | Battle state + character positions |
| `*_fturn.sav` | ~1.1 MB | Turn-based combat state |
| `fftsave.bin` | ~2 MB | Complete game state archive (all slots) |
| `settings.sav` | 256 B | Audio, display, key bindings |

### 4.3 Header Structure (first 0x30 bytes)

```
Offset  Size  Notes
0x00    4     Type ID (always 0x10 = 16)
0x04    4     CRC32 checksum
0x08    4     Always 0x10
0x0C    4     Zero
0x10    4     Magic: "FFTI" (ASCII)
0x14    4     Number of files/entries
0x18    4     Number of entries
0x1C    4     Metadata size
0x20    4     Offset to data section
0x24    4     Offset to data section (duplicate?)
0x28    4     Offset to data section (duplicate?)
0x2C    4     Field 0x5d = chapter/scene?
```

### 4.4 The Breakthrough — Finding Character Records

**Approach 1 (FAILED):** Search for XML tags, readable strings near structured data. Found the `SC` magic at offset 0x160 in main saves, but this appeared to be a different container format, not character data.

**Approach 2 (FAILED):** Try to find zlib-compressed data blocks within the .sav files. The inner format is NOT further compressed.

**Approach 3 (SUCCEEDED):** Systematic byte-pattern search.

Key insight: All character records share a common 12-byte **marker pattern**:
```
Byte 0-1:   XX YY       (character/unit identifier, varies)
Byte 2-8:   11 11 11 11 11 11 11  (7 identical bytes of 0x11)
Byte 9-11:  01 01 00  OR  10 11 00  (tail — see encoding types below)
```

This pattern appears at multiple offsets in every `.sav` file. Each instance is followed by a block of uint16 LE values (the stat block), then a null-terminated ASCII name string.

### 4.5 Marker Tail Variants

| Tail Bytes | Encoding | Characters | Notes |
|------------|----------|------------|-------|
| `01 01 00` | STANDARD | Ghost, Xsy, Ares | Normal uint16 values |
| `10 11 00` | NEW | OWL | Values are ×256 (<< 8 shifted) |

The cause of the encoding difference is unknown. It may depend on:
- How the character was created (story vs. custom)
- The order/timing of creation
- Some flag in the marker's first two bytes

### 4.6 Header-First Name-First Discovery

For each marker found at offset `M`:
```
M+0  to M+11:  12-byte marker
M+12 to M+103: 92-byte stat block (46 × uint16 LE)
M+104+:        Null-terminated ASCII name
```

The stat block is always **exactly 92 bytes** (for STANDARD encoding) or **93 bytes** (for NEW encoding) between the marker and the name string.

---

## 5. Character Record Structure

### 5.1 Complete Layout

```
┌─────────────────────────────────────────────────────────┐
│ 12-byte Marker                                          │
│   [XX YY] [0x11 × 7] [01 01 00 | 10 11 00]            │
├─────────────────────────────────────────────────────────┤
│ 92-byte Stat Block (46 × uint16 LE)                     │
│   Fields u16_00 through u16_45                          │
│   — Identity / base stats / derived stats / padding     │
├─────────────────────────────────────────────────────────┤
│ Null-terminated ASCII Name                              │
│   e.g. "Ghost\0", "Ares\0", "OWL\0"                   │
├─────────────────────────────────────────────────────────┤
│ Padding to alignment (variable)                         │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Confirmed Field Properties

| Fields | Value | Classification |
|--------|-------|----------------|
| u16_12 | Always 128 (0x80) | Structural constant (all 4 chars) |
| u16_35 | Always 128 (0x80) | Structural constant (mirror of u16_12) |
| u16_18 | Always 0 | UNUSED |
| u16_20-22 | Always 0 | UNUSED (padding) |
| u16_43-45 | Always 0 | UNUSED (padding) |
| u16_27-42 | = u16_03-18 | Mirror/copy — base stats vs. displayed/current stats |
| u16_00 | 57-202 | Max HP or HP-related (gender-correlated) |
| u16_01 | 62-119 | MP-related |
| u16_23 | 249-802 | EXP or Gil (large, increases over time) |
| u16_17 | 129-171 | Unit ID or job class identifier |

### 5.3 Character Roster (this save file)

Characters are stored across 3 battle slots. Each slot has its own copy of Ghost plus one unique character:

| Slot | Marker 4123 (Ghost) | Unique Character | Marker |
|------|---------------------|------------------|--------|
| 1 | ✓ | Ares (male Squire) | 4231 |
| 2 | ✓ | Xsy (custom) | 2211 |
| 3 | ✓ | OWL (female Squire) | 0011 (NEW) |

Plus `fftsave.bin` contains 3 copies of each slot's data.

---

## 6. Cross-Character Analysis

### 6.1 Why It Matters

By comparing the same field across different characters with known properties (gender, class, level), we can deduce field meaning from value ranges and gender differences.

### 6.2 Known Character Properties

| Character | Gender | Class | Level | Notes |
|-----------|--------|-------|-------|-------|
| Ares | Male | Squire | 1 | Story character, clean data |
| OWL | Female | Squire | 1 | Newly created, NEW encoding (shifted) |
| Ghost | Unknown | Custom | Low | Player-created sprite, tiny stats |
| Xsy | Unknown | Custom | Low | Player-created, medium stats |

### 6.3 Gender Correlation

FFT has known gender stat modifiers. Male characters have ~15% higher HP/MP than females at the same level:

| Field | Ares (M) | OWL (F) | Ratio M/F | Likely Stat |
|-------|----------|---------|-----------|-------------|
| u16_00 | 202 | 176* | 1.15 | Max HP |
| u16_03 | 135 | 117* | 1.15 | PA or Speed |
| u16_04 | 197 | 171* | 1.15 | VIT or HP growth |

*OWL unshifted values (÷256)

This confirms u16_00 is HP-related and u16_03/u16_04 are primary stats with gender modifiers.

### 6.4 Ghost Anomaly

Ghost's values don't follow the gender pattern:
- u16_00 = 57 (much lower than Ares' 202 and Xsy's 109)
- u16_03 = 328 (much HIGHER than Ares' 135)

This suggests Ghost is a different unit type (sprite/monster) with different stat calculations, or Ghost is at a different level/in a different job.

---

## 7. Equipment Storage

### 7.1 Key Finding: Equipment is NOT in the Character Record

When Ghost had crossbow + shield equipped, then removed both:
- Ghost's 92-byte stat block: **NO CHANGES**
- Other regions of the main save: **CHANGED** (item IDs → 0xFFFF)

### 7.2 Equipment Location

Equipment data is stored in a **separate inventory table** within the main save file, around offsets `0x0130-0x015F`. Item IDs (uint16) are stored there, NOT in the character's stat block.

When items are removed, their IDs become `0xFFFF` (empty slot sentinel value).

### 7.3 Item IDs Observed
```
Before (equipped):          After (removed):
1009 (0x03F1)              65535 (0xFFFF)
1156 (0x0484)              65535 (0xFFFF)
161  (0x00A1)              65535 (0xFFFF)
836  (0x0344)              65535 (0xFFFF)
842  (0x034A)              65535 (0xFFFF)
1016 (0x03F8)              65535 (0xFFFF)
1000 (0x03E8)              65535 (0xFFFF)
1004 (0x03EC)              65535 (0xFFFF)
830  (0x033E)              65535 (0xFFFF)
1018 (0x03FA)              65535 (0xFFFF)
1008 (0x03F0)              65535 (0xFFFF)
```

These are in the 160-1156 range, consistent with FFT item ID tables.

---

## 8. Two Encoding Types

### 8.1 Discovery

Created a new Female Squire named "OWL." Her character record uses the same marker pattern but with a DIFFERENT tail:

- STANDARD: `tail = 01 01 00` → values are normal uint16
- NEW: `tail = 10 11 00` → values are shifted left 8 bits (×256)

### 8.2 Evidence

OWL's raw u16_00 = 45312 = 0xB000. Dividing by 256: 0xB0 = 176. This matches Ares' u16_00 = 202 with the expected female modifier (176/202 ≈ 0.87, consistent with FFT gender scaling).

### 8.3 All Fields Affected

EVERY uint16 field in OWL's stat block is shifted. It's not specific to one field — the entire record uses a different storage format.

### 8.4 Possible Causes

- **Order of creation:** OWL was created AFTER Ghost and Xsy. The game may have switched encoding schemes mid-playthrough.
- **Marker prefix:** OWL's marker is `0011` vs. Ghost's `4123` and Xsy's `2211`. The HIGH byte (0x00 vs 0x41/0x22) may indicate encoding type.
- **Character type:** OWL is a "real" story-class character (Squire), while Ghost/Xsy might use a different internal class.

### 8.5 How to Handle Both Encodings

```python
def decode_value(raw_u16, marker_prefix_byte):
    if marker_prefix_byte < 0x08:  # NEW encoding (OWL: 0x00)
        return raw_u16 >> 8         # Divide by 256
    else:                          # STANDARD encoding (Ares: 0x42, Ghost: 0x41)
        return raw_u16             # Use as-is
```

---

## 9. Scripts & Reproduction

### 9.1 Script Inventory

All scripts are in `/home/xsyvps/projects/ivalicevera/`:

| Script | Purpose |
|--------|---------|
| `fft_save_analyzer.py` | Extract characters, party roster, settings from .sav files |
| `fft_stat_mapper.py` | Cross-compare ALL character records across ALL saves |
| `fft_field_mapper_v2.py` | Classify fields by value range (HP-like, level-like, etc.) |
| `fft_final_mapper.py` | Side-by-side comparison of all 4 characters |
| `fft_final_analysis.py` | Comprehensive cross-reference with gender analysis |
| `fft_save_parser.py` | PNG container parser (XOR + zlib, from earlier reverse engineering) |
| `ghost_extract.py` | Extract first 80 uint16 values from Ghost records → CSV |
| `ghost_correlate.py` | Correlation pass on Ghost CSV — identify constant vs. changing fields |
| `ghost_diff.py` | Diff Ghost between before/after save pairs |

### 9.2 How to Reproduce This Research

**Prerequisites:**
1. FFT PC Remaster save files (autoenhanced.png, enhanced.png, system.png)
2. FF16Tools (Nenkai) to extract PNG → raw .sav files
3. Python 3.11+

**Step 1: Extract saves**
```bash
FF16Tools.CLI unpack -g fft "autoenhanced.png" "autoenhanced_out/"
FF16Tools.CLI unpack -g fft "enhanced.png" "enhanced_out/"
FF16Tools.CLI unpack -g fft "system.png" "system_out/"
```

**Step 2: Find all character markers**
```python
import struct, pathlib

def find_markers(data):
    for i in range(len(data) - 12):
        if data[i+2:i+9] == b'\x11\x11\x11\x11\x11\x11\x11':
            tail = data[i+9:i+12]
            if tail in [b'\x01\x01\x00', b'\x10\x11\x00']:
                marker = f"{data[i]:02x}{data[i+1]:02x}"
                tail_type = "STANDARD" if tail == b'\x01\x01\x00' else "NEW"
                # Scan for name after stat block
                for bl in range(50, 150):
                    no = i + 12 + bl
                    if data[no:no+3].isalpha() and data[no:data.find(b'\\x00',no)].isascii():
                        name = data[no:data.find(b'\\x00',no)].decode()
                        if len(name) >= 3:
                            stats = list(struct.unpack_from(f'<{bl//2}H', data, i+12))
                            yield marker, tail_type, name, i, stats
                            break

for f in pathlib.Path('path/to/saves').rglob('*.sav'):
    for marker, tail, name, off, stats in find_markers(f.read_bytes()):
        print(f"{f.name}: {name} marker={marker} tail={tail} off=0x{off:x}")
```

**Step 3: Cross-compare characters**
```python
# Compare u16_00 (likely Max HP) across all characters
# Compare u16_12 (always 128 — structural flag)
# Compare fields that match exactly (constants) vs. those that differ (stats)
# Use gender differences to confirm HP/MP-related fields
```

**Step 4: Controlled diffs for field identification**
```python
# Save before making a single change in-game
# Save after making the change
# Diff the binary to find which bytes changed
# Map those byte offsets to field positions

# Test matrix:
# - Take damage → u16_XX = current HP
# - Cast spell → u16_XX = current MP
# - Gain EXP without leveling → u16_XX = EXP
# - Level up once → u16_XX = level, others = stat growth
# - Equip one item → equipment table (separate from stat block)
```

---

## 10. Open Questions & Next Steps

### 10.1 Definitively Unmapped Fields

The following fields are NOT yet confirmed with controlled tests:

- **Level** — which u16? (likely 1-99 or 1-100 range)
- **EXP** — u16_23 is a candidate (249-802 range)
- **Bravery** — should be 0-100
- **Faith** — should be 0-100
- **Job/Class ID** — small integer, u16_17 is a candidate (129-171)
- **Unit ID** — unique per character sprite
- **Current HP** — separate from Max HP (u16_00)
- **Current MP** — separate from Max MP
- **Move** — typically 3-5
- **Jump** — typically 2-4
- **C-EV** — evade percentage

### 10.2 Planned Controlled Tests

| Test | Method | What We Learn |
|------|--------|---------------|
| HP damage | Take damage in battle, save, diff | Current HP field |
| MP use | Cast spell, save, diff | Current MP field |
| EXP gain | Win battle without leveling, diff | EXP field |
| Level up | Gain enough EXP to level once | Level field + stat growth pattern |
| Equip weapon | Equip one item, diff | Equipment table structure |
| Change job | Use job change item/ability | Job class ID field |
| Brave/Faith | Trigger Brave/Faith change event | Brave/Faith fields |

### 10.3 The NEW Encoding Mystery

Why does OWL's record use shifted values? Open hypotheses:
1. Marker prefix byte indicates encoding (0x00-0x07 = NEW, 0x08+ = STANDARD)
2. Late-created characters use a different format
3. The game upgraded its save format and old characters kept the old format

**Test:** Create another new character. If they also use NEW encoding, hypothesis 1 or 2 is supported. If they use STANDARD, hypothesis 3 (or something else) is at play.

### 10.4 Equipment Table

Located around `0x0130-0x015F` in main saves. Structure unknown:
- Are slots fixed-position (slot 1 always at offset X)?
- Or is it a linked list / dynamic array?
- How are equipped vs. unequipped items distinguished? (0xFFFF = empty)

### 10.5 Abilities

Learned abilities are NOT in the 92-byte stat block. They're likely in:
- A separate bitfield/blob elsewhere in the file
- The equipment table region
- A completely different section

**Test:** Have a character learn exactly ONE new ability. Diff before/after. Find the changed bit(s).

---

## 11. Lessons Learned

### 11.1 What Worked

1. **FF16Tools was essential.** Without it, we couldn't get past the PNG/XOR/zlib wrapper. Nenkai's reverse engineering of the container format saved us days of work.

2. **Cross-character comparison is powerful.** By comparing 4 characters with different genders and classes, we could deduce field meanings from ratios and patterns.

3. **Controlled save diffs work.** Changing ONE thing in-game and diffing the binary is the most reliable way to map fields. The equipment test proved this even though the result was unexpected.

4. **File naming matters.** The `autoenhanced/` files (autosaves) contain the same data structure as `enhanced/` (manual saves) but split across many files. The `enhanced/fftsave.bin` is the complete archive — easier to work with.

### 11.2 What Didn't Work

1. **Autosave files were misleading.** We spent time analyzing `autoenhanced/` files which have the same structure but are split across 17 files. The single `fftsave.bin` was cleaner.

2. **Assuming one encoding.** Discovering OWL's NEW encoding mid-research meant re-checking assumptions. Always verify that ALL records use the same format.

3. **Equipment in stat block assumption.** Equipment is stored in a SEPARATE table, not in the character's 92-byte block. Don't assume all character data is in one place.

### 11.3 General Reverse Engineering Advice

1. **Start with the container format.** Get extraction working first. FF16Tools handled this for FFT.

2. **Find repeating patterns.** The `0x11×7` marker was the key. Search for ANY byte that repeats 5+ times — it's likely a struct delimiter.

3. **Use controlled experiments.** One change, one save, one diff. Patient binary diffing beats guessing.

4. **Save EVERYTHING.** Keep before/after pairs with notes about what changed. You'll need them later.

5. **Expect multiple encodings/versions.** Games evolve. Save formats change. Characters created at different times may use different internal formats.

6. **Gender differences are your friend.** In FFT, male/female stat modifiers create predictable ratios. Use them to identify HP/MP/stat fields.

7. **Zero fields are structure.** Fields that are ALWAYS zero across all characters and saves are padding or unused. Map them once and ignore them.

---

## Appendix A: File Checksums (for verification)

### enhanced-1139 (before OWL)
- Size: 2,007,816 bytes
- MD5: (compute with `md5sum fftsave.bin`)
- CRC32 at offset 0x04: 0x87FD509F

### enhanced-1143 (after OWL)
- Size: 2,007,816 bytes
- CRC32 at offset 0x04: 0x0CB068DF

---

## Appendix B: Magic Numbers

| Constant | Value | Meaning |
|----------|-------|---------|
| File magic | `FFTI` at offset 0x11 | Save file identifier |
| Marker body | `0x11` × 7 | Character record delimiter |
| Standard tail | `0x01 0x01 0x00` | Normal encoding |
| New tail | `0x10 0x11 0x00` | Shifted encoding (÷256) |
| Empty item | `0xFFFF` | Unequipped/empty slot sentinel |
| XOR key | `0xF3F80FE5F1FC4F3` | PNG container decryption |
| Struct constant | `128` (0x80) | u16_12 and u16_35, all records |
| Stat block size | `92` bytes | Between marker and name |

---

## Appendix C: Controlled Test Plan & Build Log

See `TEST_PLAN.md` for the complete controlled experiment sequence.

### Field Status (as of May 30, 2026)

| Field | Status | Notes |
|-------|--------|-------|
| u16_12, u16_35 | ✅ CONFIRMED | Always 128 — structural constant |
| u16_18, u16_20-22, u16_43-45 | ✅ CONFIRMED | Always 0 — unused padding |
| u16_27-42 | ✅ CONFIRMED | Mirror of u16_03-18 |
| u16_00 | 🟡 LIKELY | Max HP (gender ratio 1.15:1 matches FFT) |
| u16_01 | 🟡 LIKELY | MP-related |
| u16_02 | 🟡 LIKELY | STR or growth rate |
| u16_17 | 🟡 LIKELY | Unit/Job ID |
| u16_23 | 🟡 LIKELY | EXP or Gil |
| Current HP | 🔴 UNKNOWN | Need controlled damage test |
| Current MP | 🔴 UNKNOWN | Need controlled MP use test |
| Level | 🔴 UNKNOWN | Need level-up test |
| Bravery | 🔴 UNKNOWN | Need 0-100 range identification |
| Faith | 🔴 UNKNOWN | Need 0-100 range identification |
| Equipment slots | 🔴 UNKNOWN | Separate table, need equip test |
| Abilities | 🔴 UNKNOWN | Not in stat block, separate section |
| Job Class ID | 🔴 UNKNOWN | Need job change test |
| Move/Jump | 🔴 UNKNOWN | Need to find tiny values (2-5 range) |

### Build Log

#### May 30, 2026 — Initial Discovery
- Found character marker pattern: `XX YY 0x11×7 [01 01 00 | 10 11 00]`
- Identified 46-uint16 stat block structure
- Cross-referenced 4 characters (Ares, Ghost, Xsy, OWL)
- Discovered two encoding types (STANDARD and NEW/shifted)
- Found equipment in separate table (not in stat block)
- Created initial field mapping with gender analysis

#### Controlled Test 1: Equipment Removal (Ghost)
- **Date:** May 30, 2026
- **Method:** Removed crossbow + shield from Ghost, saved in new slot
- **Result:** Ghost's 92-byte stat block unchanged. Equipment changes at offsets 0x0130-0x015F (item IDs → 0xFFFF)
- **Learned:** Equipment stored in separate table. 0xFFFF = empty slot sentinel.

#### Controlled Test 2: New Character Creation (OWL)
- **Date:** May 30, 2026
- **Method:** Created Female Squire named "OWL", saved in new slot
- **Result:** OWL uses NEW encoding (all values << 8). Marker tail = `10 11 00` vs standard `01 01 00`
- **Learned:** Game uses multiple encoding types within same save file.


#### Controlled Test 3: Battle + Level Up (Xsy)
- **Date:** May 30, 2026
- **Method:** Entered battle with OWL and Xsy in party. Xsy leveled up. Saved after battle.
- **Result:** Xsy gained: HP+31, MP+45, StatA+16, StatD+8. 8 fields total changed (4 mirrored).
- **Learned:**
  - **u16_00 = MAX HP** (gender-correlated: male=202, female=177, grows +31 on level up)
  - **u16_01 = MAX MP** (grows +45 on level up)
  - **u16_04 and u16_07** = primary stats that grow on level up (+16 and +8 respectively)
  - **u16_23 and u16_24** = HP/MP related fields (same deltas as u16_00/u16_01)
  - Xsy is NOT a Squire (HP=109 vs Ares'=202 at L1). Different class.
  - Snow does NOT have a character record (only appears as a name string in a different section)
  - Ghost shows 2 records in the enhanced save (markers 4122 and 4123) — different slots/states

### Updated Field Mapping (post-Test 1)

| Offset | Field | Confidence | Evidence |
|--------|-------|------------|----------|
| u16_00 | **Max HP** | ✅ CONFIRMED | Gender ratio 1.15:1, grows +31 on level up |
| u16_01 | **Max MP** | ✅ CONFIRMED | Grows +45 on level up |
| u16_04 | **Primary stat A** | 🟡 LIKELY | Grows +16 on level up (STR? VIT?) |
| u16_07 | **Secondary stat D** | 🟡 LIKELY | Grows +8 on level up (AGI? INT? SPD?) |
| u16_23 | **HP-related** | 🟡 LIKELY | Same delta as u16_00 on level up (current HP? HP growth?) |
| u16_24 | **MP-related** | 🟡 LIKELY | Same delta as u16_01 on level up (current MP? MP growth?) |
| u16_12 | Structural flag | ✅ CONFIRMED | Always 128 |
| u16_35 | Structural flag | ✅ CONFIRMED | Always 128 (mirror) |
| u16_27-42 | Mirror block | ✅ CONFIRMED | = u16_03-18 |
| u16_18,20-22,43-45 | Unused | ✅ CONFIRMED | Always 0 |

### Still Unknown Fields
- u16_02, u16_03, u16_05, u16_06, u16_08-11, u16_13-17, u16_19, u16_25, u16_26
- These did NOT change on level up, so they're either:
  - Very small growth (0 for this level)
  - Derived/computed from other stats
  - Non-stat data (unit ID, job ID, brave, faith, move, jump, etc.)

#### Next Tests (pending):
- HP damage test, MP use test, level up test, equipment equip test, job change test
- See TEST_PLAN.md for detailed procedures.

---

## Appendix D: FFT Save Editor Feature Wishlist

Based on what we know, a save editor would need to:

1. **Read/Write PNG container** (XOR + zlib with custom dict) — use FF16Tools
2. **Find character records** via marker pattern `ffTo` chunk
3. **Decode stat blocks** (check marker prefix for encoding type)
4. **Map 46 fields** per character (documented above)
5. **Handle equipment table** (separate from character records)
6. **Update CRC32 checksum** after modifications
7. **Repack into PNG** with proper chunk structure

---

---

## Appendix E: Job Change Analysis — Critical Discovery

### Test 4: Job Change Squire → Archer (May 30, 2026)
- **Method:** Changed OWL's job from Squire to Archer via the job menu. Saved in slot 7.
- **Data extracted:** All 3 PNG types — `enhanced.png` (manual save), `autoenhanced.png` (17 autosave files), `system.png` (settings.sav)
- **Expected Archer stats (in-game display):** HP=42, MP=9, Bravery=62, Faith=66, JP=117

### KEY FINDING: Job Data is NOT in the Character Record

The character stat block (92 bytes, 46× uint16) does NOT change when you change jobs.

Comparing the Squire (slot 4, `enhanced-1143`) and Archer (slot 7, `enhanced-new1`) enhanced saves:

1. **OWL's character record is IDENTICAL** between Squire and Archer saves:
   - Marker at 0x28bcb, ID=0011, tail=101100 (NEW encoding)
   - Stats: `[45312, 32000, 34816, 29952, 43776, 29184, 40704, 27664, ...]` (>>8: 177, 125, 136, 117, 171, 114, 159, 108)
   - Zero diffs in the character record region (0x28000-0x2A000)

2. **Archer display stats (HP=42, MP=9) are NOT found anywhere in the file:**
   - Searched for 42 and 9 as consecutive uint16 LE: NOT FOUND
   - Searched for shifted values (10752, 2304): NOT FOUND
   - Searched for "Archer" string (ASCII and UTF-16LE): NOT FOUND
   - Searched for Archer stats as individual bytes near OWL region: NOT FOUND
   - Confirmed across all 20 files (1 enhanced, 17 autosave, 1 settings, 1 baseline)

3. **Two encoding types confirmed:**
   - STANDARD encoding (tail `01 01 00`): values are raw (e.g., `[42, 47, 159, ...]`)
   - NEW encoding (tail `10 11 00`): values are shifted left 8 bits (raw >> 8 = real value)
   - The NEW encoding is used for all persistent character records in this save
   - The STANDARD encoding appears mainly in battle overlay records and some NPCs

4. **What DOES change between saves:**
   - 7,559 byte diffs across the file
   - Large blocks of `0xFF` and `0x0101` patterns where Squire save has zeros
   - These diffs are in the 0x31000-0x45000 range — far from character records
   - This region contains: character names ("Xsy", "Ghost", "Ares") in Shift-JIS, equipment data, ability data, etc.
   - The new blocks are likely: **unlocked abilities for Archer job, new equipment permissions, JP-related data**

5. **HP=42 record exists but is NOT OWL:**
   - A STANDARD encoding record at offset 0x7f4 (ID=1111, different from OWL's 0011) has HP=42
   - This is likely a generic NPC or enemy unit template, not OWL

### GAME ENGINE ARCHITECTURE (Revised Understanding)

The game stores BASE STATS in the character record (innate to the unit). Display stats (what you see on screen) are calculated at runtime:

```
display_stat = base_stat × job_multiplier + equipment_bonus + status_modifier
```

When you change jobs:
- The character record (base stats) stays the SAME
- A JOB ID field somewhere tells the engine which multiplier table to use
- The engine reads base stats + job ID → calculates display HP/MP/etc.

**Implication for our parser:** We need to find where the JOB ID is stored, AND we need the game's job multiplier tables to calculate display stats. The raw values in the character record are BASE stats, not display stats.

### What We Still Need to Find
1. **Job ID field location** — searched all files near OWL, haven't found it yet
2. **Job multiplier tables** — likely in game data files, not in saves
3. **The 0x31000 region structure** — contains the new Archer-related data but format is unknown

*Doc version 1.1 — May 30, 2026*
*Author: OWL (AI assistant) & Ed (King Elf Ed)*
*Repository: github.com/xsytrance/ivalicevera*

#### Controlled Test 3: Mid-Battle Autosave (Mandalia Plains)
- **Date:** May 30, 2026
- **Method:** Entered battle with OWL+Xsy+Ghost. Both OWL and Xsy took damage. Saved via autosave (not manual save).
- **Data:** 17 autosave files across 3 slots (en00, en01, en02, enbtl, enwm)
- **Key findings:**
  - Autosave contains BOTH marker types for OWL:
    - `marker=0011` (93B block) = **resting/base stats** (unchanged from baseline — same as manual save)
    - `marker=0021` (94B block) = **battle overlay** (almost all zeros, only u16_1=1 and u16_24=1 nonzero)
  - The `en02_attack.sav` file has BOTH records: 0011 (full stats, unchanged) AND 0021 (zeros)
  - The battle overlay (0021) appears to use a DIFFERENT encoding — values are tiny (0-1) not shifted
  - Ghost's autosave record (marker 4123) in `en00_attack.sav` shows: `[161, 83, 225, 67, 154, 159, 176, 192, 108, 160]` — same as baseline
  - Xsy's autosave record in `en00_attack.sav` shows post-level-up values: `[140, 107, 180, 157, 161, 159, 187, 131, ...]` — confirms level-up changes
  - Xsy's OLD slot 3 record (in `en02_attack.sav`) still shows pre-level-up values: `[109, 62, 180, 157, 145, ...]`
  - **Implication:** The autosave keeps OLD copies of records AND new copies. The slot 3 record wasn't updated when Xsy leveled up; instead a new slot 4 record was created.
  - Snow exists as a name string at file offset 0xac40 but has NO character record (marker-based)
  - Argath's marker changed from 2111 (baseline) to 3111 (mid-battle) — different encoding or state

### Battle Record Structure (NEW DISCOVERY)
The autosave contains TWO types of character records:
1. **Base stats record** (marker 0011/4123/etc, 92-93B): Unchanged resting stats (HP_max, MP_max, etc.)
2. **Battle overlay record** (marker 0021, 94B): Active battle state — HP_current, MP_current, status effects, position, etc.

The battle overlay uses DIFFERENT marker prefixes:
- OWL: base=0011, battle=0021
- Ghost: base=4123 (4122 in slot 1), battle=unknown
- The battle record's u16_1=1 and u16_24=1 might be current HP/MP fractions or status flags

### Updated Understanding
The game maintains TWO parallel character records:
- **Persistent record** (updated on level up, equipment change, etc.)
- **Battle overlay record** (created/updated during combat, tracks current HP/MP/status)

This is why we couldn't find current HP/MP in the persistent record — they're in the battle overlay!

