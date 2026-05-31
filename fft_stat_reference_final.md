# FFT PC Remaster — Character Stat Block Reference (FINAL)

## Record Format
- 12-byte marker: XX YY + 0x11*7 + tail
- Tail 01 01 00 = STANDARD encoding (Ghost, Xsy, Ares)
- Tail 10 11 00 = NEW encoding (OWL, values << 8 shifted)
- 92-byte stat block: 46 x uint16 LE
- Null-terminated name string after stat block

## Characters in enhanced-1143
- Ghost (marker 4122/4123) — custom sprite, battle slot 1/2/3
- Xsy (marker 2211) — custom character, battle slot 1/2/3
- Ares (marker 4231) — story character, battle slot 1
- OWL (marker 0011, NEW encoding) — new Female Squire, battle slot 3

## Known Fields (46 uint16 per record)
| Offset | Ares | Ghost | Xsy  | Notes |
|--------|------|-------|------|-------|
| u16_00 | 202  | 57    | 109  | Max HP? (female lower) |
| u16_01 | 119  | 83    | 62   | MP? |
| u16_02 | 59   | 225   | 180  | STR/PA growth? |
| u16_03 | 135  | 328   | 157  | PA? (Ares>Ghost, OWL female lower) |
| u16_04 | 197  | 107   | 145  | VIT? |
| u16_05 | 114  | 159   | 159  | AGI? |
| u16_12 | 128  | (varies) | (varies) | u16_12/u16_35 often 128 — class/record flag |
| u16_23 | 802  | 827   | 249  | EXP or Gil |
| u16_17 | 129  | 171   | 158  | unit/job ID? |
| u16_18 | 0    | 0     | 0    | UNUSED |
| u16_20-22 | 0 | 0    | 0    | UNUSED (padding) |
| u16_27-42 | mirror of u16_03-18 | | | duplicate/base+derived stats |
| u16_43-45 | 0 | 0 | 0 | UNUSED |

## NOT in stat block (stored elsewhere in file):
- Equipment slots (found at 0x0130-0x015F region for inventory)
- Current HP/battle stats
- Learned abilities
- Level (unconfirmed if in stat block)

## Two Encodings Discovered:
1. STANDARD: Normal uint16 values (Ares, Ghost, Xsy)
2. NEW: Values shifted left 8 bits (OWL) — marker tail 10 11 00

## Controlled Tests Still Needed:
1. Take damage → identify HP field
2. Cast spell → identify MP field  
3. Gain EXP → identify EXP field
4. Level up → identify level + growth fields
5. Equip item → confirm equipment in separate table
