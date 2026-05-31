# FFT Save Mapping — Controlled Test Plan
## Build Log: Field Identification via In-Game Experiments

### Characters Available
| Name | Gender | Class | Level | Marker | Encoding | Notes |
|------|--------|-------|-------|--------|----------|-------|
| Ares | Male | Squire | 1 | 4231 | STANDARD | Story character, clean baseline |
| OWL | Female | Squire | 1 | 0011 | NEW (÷256) | Newly created, shifted values |
| Ghost | Unknown | Custom | Low | 4123 | STANDARD | Player sprite, anomalous stats |
| Xsy | Unknown | Custom | Low | 2211 | STANDARD | Player character |

### Fields Still Unmapped
| Field | Candidates | How to Confirm |
|-------|-----------|----------------|
| Level | u16_17? (129-171) | Level up once, field +1 |
| EXP | u16_23? (249-802) | Win battle, field increases |
| Current HP | unknown | Take damage, field decreases |
| Current MP | unknown | Cast spell, field decreases |
| Bravery | unknown | 0-100 range, find via event |
| Faith | unknown | 0-100 range, find via event |
| Job ID | u16_17? | Change job, field changes |
| Move | unknown | Very small (3-5) |
| Jump | unknown | Very small (2-4) |
| Equipment slots | separate table | Equip item, diff table |

### Test Sequence (minimize saves, maximize data)

#### TEST 1: Level Up + EXP (do these together)
**Why:** Leveling up changes multiple fields at once — level, stats, possibly EXP resets.
**Steps:**
1. Save current state as "baseline" (already have: enhanced-1143)
2. Enter any battle with OWL
3. Win the battle (gain EXP)
4. If OWL levels up → save as "test1_levelup"
5. If not → repeat until level up
6. Diff: find which field changed by +1 (level), which fields increased (stats), which field reset (EXP)

#### TEST 2: HP Damage
**Why:** Isolates current HP field.
**Steps:**
1. Start from baseline
2. Enter battle with OWL
3. Let OWL take damage (don't heal)
4. Save as "test2_damaged"
5. Diff from baseline: decreased field = current HP

#### TEST 3: MP Use
**Why:** Isolates current MP field.
**Steps:**
1. Start from baseline
2. Enter battle with OWL
3. Cast any MP-using ability
4. Save as "test3_usedmp"
5. Diff from baseline: decreased field = current MP

#### TEST 4: Equipment
**Why:** Map equipment slot positions in the separate table.
**Steps:**
1. Start from baseline
2. Equip ONE specific item on OWL (note which slot: weapon/armor/etc)
3. Save as "test4_equipped"
4. Diff from baseline: changed fields in equipment table = slot positions

#### TEST 5: Job Change (if possible)
**Why:** Identify job/class ID field.
**Steps:**
1. Start from baseline
2. Change OWL's job (if job change is available)
3. Save as "test5_newjob"
4. Diff from baseline: changed stat block field = job ID

### Save Naming Convention
- `enhanced-XXXX` — manual save number from FFT
- Copy to VPS as: `/home/xsyvps/fft-saves/test_NAME/`
- Always keep the baseline (enhanced-1143) for comparison

### Diff Process (automated)
For each test:
1. Extract enhanced.png → fftsave.bin
2. Copy to VPS
3. Run `ghost_diff.py` (adapted for OWL) to diff stat blocks
4. Run full binary diff for equipment table changes
5. Record results in this document
