#!/usr/bin/env python3
"""Ed's correlation pass: classify Ghost fields from CSV."""
import csv
from pathlib import Path
from statistics import mean

CSV = Path("/home/xsyvps/fft-saves/tactics/ghost_u16_compare.csv")
rows = list(csv.DictReader(CSV.open()))

u16_cols = [c for c in rows[0] if c.startswith("u16_")]

def vals_for(col):
    return [int(r[col]) for r in rows]

summary = []
for col in u16_cols:
    vals = vals_for(col)
    uniq = sorted(set(vals))
    mn, mx = min(vals), max(vals)
    tags = []
    if len(uniq) == 1:
        tags.append("constant")
    else:
        tags.append("changes")
    if 0 <= mn and mx <= 10:
        tags.append("MOVE/JUMP/SPD-small-candidate")
    if 0 <= mn and mx <= 99:
        tags.append("EXP-or-small-stat-candidate")
    if 1 <= mn and mx <= 100:
        tags.append("LEVEL/BRAVE/FAITH-candidate")
    if 0 <= mn and mx <= 255:
        tags.append("byte-stat-candidate")
    if 50 <= mn and mx <= 999:
        tags.append("HP/MP-candidate")
    if mx > 1000:
        tags.append("ID/flags/bitfield/item-or-pointer-candidate")
    summary.append({
        "field": col, "min": mn, "max": mx,
        "unique_count": len(uniq), "values": uniq[:20],
        "tags": ", ".join(tags)
    })

for s in summary[:80]:
    v_str = str(s['values'][:8])
    print(f"{s['field']:>6} min={s['min']:>5} max={s['max']:>5} uniq={s['unique_count']:>2}  {s['tags']:<50}  {v_str}")
