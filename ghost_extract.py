#!/usr/bin/env python3
"""Ed's script: extract ALL uint16 values after marker, find names, output CSV."""
from pathlib import Path
import struct
import csv
from collections import defaultdict

ROOT = Path("/home/xsyvps/fft-saves/tactics")

# Marker pattern: XX YY 11 11 11 11 11 11 11 01 01 00
FIXED_TAIL = bytes([0x11] * 7 + [0x01, 0x01, 0x00])
MARKER_LEN = 12
U16_COUNT = 80  # Extract more than needed


def read_cstring(data, start, max_len=64):
    end = data.find(b"\x00", start, start + max_len)
    if end == -1:
        return None
    raw = data[start:end]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("shift_jis")
        except UnicodeDecodeError:
            return raw.hex()


def find_records(data):
    records = []
    for i in range(0, len(data) - MARKER_LEN):
        if data[i+2:i+12] == FIXED_TAIL:
            marker = data[i:i+12]
            stats_start = i + MARKER_LEN
            needed = U16_COUNT * 2
            if stats_start + needed > len(data):
                continue
            vals = list(struct.unpack_from("<" + "H" * U16_COUNT, data, stats_start))
            # Find name after the uint16 area
            possible_names = []
            for off in range(stats_start + 20, min(stats_start + 300, len(data))):
                name = read_cstring(data, off)
                if name and name.isprintable() and 2 <= len(name) <= 24:
                    if all(c not in name for c in "\r\n\t"):
                        possible_names.append((off, name))
                        break
            records.append({
                "offset": i,
                "marker": marker.hex(" "),
                "prefix_xy": marker[:2].hex(" "),
                "values": vals,
                "name_guess": possible_names[0][1] if possible_names else "",
                "name_offset": possible_names[0][0] if possible_names else None,
            })
    return records


all_rows = []
for path in sorted(ROOT.rglob("*.sav")):
    data = path.read_bytes()
    for rec in find_records(data):
        all_rows.append({
            "file": str(path.relative_to(ROOT)),
            "offset_hex": hex(rec["offset"]),
            "marker": rec["marker"],
            "prefix_xy": rec["prefix_xy"],
            "name_guess": rec["name_guess"],
            **{f"u16_{i:02d}": v for i, v in enumerate(rec["values"][:U16_COUNT])},
        })

# Filter Ghost records
ghost_rows = [
    r for r in all_rows
    if r["name_guess"].lower() == "ghost"
    or "ghost" in r["name_guess"].lower()
    or r["prefix_xy"] == "41 23"
]

out = ROOT / "ghost_u16_compare.csv"
with out.open("w", newline="") as f:
    fieldnames = list(ghost_rows[0].keys()) if ghost_rows else list(all_rows[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(ghost_rows)

print(f"Total records found: {len(all_rows)}")
print(f"Ghost-like records found: {len(ghost_rows)}")
print(f"Wrote: {out}\n")

for r in ghost_rows:
    vals = [r[f"u16_{i:02d}"] for i in range(30)]
    print(r["file"][-25:], r["offset_hex"], r["name_guess"], vals)

# Also dump ALL non-Ghost records for comparison
print(f"\n=== ALL NON-GHOST RECORDS ===\n")
for r in all_rows:
    if r not in ghost_rows and r["name_guess"]:
        vals = [r[f"u16_{i:02d}"] for i in range(44)]
        print(r["file"][-25:], r["offset_hex"], r["name_guess"], r["prefix_xy"], vals[:20])
