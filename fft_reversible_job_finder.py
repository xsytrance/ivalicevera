#!/usr/bin/env python3
"""
FFT Reversible Job Offset Finder
Finds bytes that change from Job A → Job B → Job A (reversible).
Usage: python fft_reversible_job_finder.py <save_before> <save_archer> <save_after>
"""
import struct
import sys
from pathlib import Path

def load_paths():
    if len(sys.argv) >= 4:
        return [Path(p) for p in sys.argv[1:4]]
    # Default paths based on our file structure
    base = Path('/home/xsyvps/fft-job-saves')
    return [
        base / '01_owl_squire_before' / 'enhanced' / 'fftsave.bin',
        base / '02_owl_archer' / 'enhanced' / 'fftsave.bin',
        base / '03_owl_squire_after' / 'enhanced' / 'fftsave.bin',
    ]

paths = load_paths()
labels = ['SQUIRE_BEFORE', 'ARCHER', 'SQUIRE_AFTER']

# Verify files exist
for p in paths:
    if not p.exists():
        print(f"WARNING: {p} not found")
        print("Usage: python fft_reversible_job_finder.py <save_before.bin> <save_archer.bin> <save_after.bin>")
        sys.exit(1)

datas = [p.read_bytes() for p in paths]
sizes = [len(d) for d in datas]
limit = min(sizes)

print(f"Reversible Job Offset Finder")
print(f"=" * 60)
print(f"  A (Squire before): {paths[0]} ({sizes[0]:,} bytes)")
print(f"  B (Archer):        {paths[1]} ({sizes[1]:,} bytes)")
print(f"  C (Squire after):  {paths[2]} ({sizes[2]:,} bytes)")
print(f"  Comparing: 0x00000-0x{limit:x} ({limit:,} bytes)")
print()

# Focus region: 0x31000-0x45000
SCAN_START = 0x31000
SCAN_END = min(0x45000, limit)

print(f"Focused scan region: 0x{SCAN_START:x}-0x{SCAN_END:x}")
print()

# --- u8 reversible candidates ---
print("=== Reversible u8 candidates (A==C, B≠A, values ≤ 128) ===")
u8_candidates = []
for off in range(SCAN_START, SCAN_END):
    av, bv, cv = datas[0][off], datas[1][off], datas[2][off]
    if av == cv and av != bv and av <= 128 and bv <= 128:
        u8_candidates.append((off, av, bv, cv))

if u8_candidates:
    for off, av, bv, cv in u8_candidates:
        # Try to identify which character this might be near
        context = ""
        for name_off, name, region_start in [
            (0x318a8, 'Xsy', 0x31800),
            (0x31b00, 'Ghost', 0x31a00),
            (0x31d58, 'Ares', 0x31d00),
            (0x32910, 'OWL', 0x32800),
            (0x31fb0, 'Snow', 0x31f00),
        ]:
            if abs(off - name_off) < 200:
                context = f" [near {name} at 0x{name_off:x}, rel={off-name_off:+d}]"
                break
        print(f"  0x{off:06x}: {av:3d} → {bv:3d} → {cv:3d}{context}")
else:
    print("  None found")

print()

# --- u16 reversible candidates ---
print("=== Reversible u16 candidates (A==C, B≠A, values ≤ 512) ===")
u16_candidates = []
for off in range(SCAN_START, SCAN_END - 1):
    av = struct.unpack_from('<H', datas[0], off)[0]
    bv = struct.unpack_from('<H', datas[1], off)[0]
    cv = struct.unpack_from('<H', datas[2], off)[0]
    if av == cv and av != bv and av <= 512 and bv <= 512:
        u16_candidates.append((off, av, bv, cv))

if u16_candidates:
    for off, av, bv, cv in u16_candidates:
        context = ""
        for name_off, name in [
            (0x318a8, 'Xsy'), (0x31b00, 'Ghost'), (0x31d58, 'Ares'),
            (0x32910, 'OWL'), (0x31fb0, 'Snow'),
        ]:
            if abs(off - name_off) < 200:
                context = f" [near {name} at 0x{name_off:x}, rel={off-name_off:+d}]"
                break
        print(f"  0x{off:06x}: {av:3d} → {bv:3d} → {cv:3d}{context}")
else:
    print("  None found")

print()

# --- Also check the whole file for u8 candidates ---
print("=== Whole-file reversible u8 candidates (A==C, B≠A, values ≤ 128) ===")
whole_u8 = []
for off in range(limit):
    av, bv, cv = datas[0][off], datas[1][off], datas[2][off]
    if av == cv and av != bv and av <= 128 and bv <= 128:
        whole_u8.append((off, av, bv, cv))

print(f"  Found {len(whole_u8)} candidates across entire file")
for off, av, bv, cv in whole_u8[:50]:
    section = ""
    if 0x31000 <= off < 0x45000:
        section = " [EXTENDED REGION]"
    elif 0x27000 <= off < 0x31000:
        section = " [base records region]"
    print(f"    0x{off:06x}: {av:3d} → {bv:3d} → {cv:3d}{section}")

if len(whole_u8) > 50:
    print(f"    ... ({len(whole_u8) - 50} more)")
