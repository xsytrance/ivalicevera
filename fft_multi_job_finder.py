#!/usr/bin/env python3
"""
FFT Multi-Job Candidate Finder
Finds bytes that vary across multiple job saves.
Usage: python fft_multi_job_finder.py <save_files...>
"""
import struct
import sys
from pathlib import Path

def load_args():
    if len(sys.argv) >= 3:
        # Expect: script.py <label1>:<file1> <label2>:<file2> ...
        saves = {}
        for arg in sys.argv[1:]:
            label, path = arg.split(':', 1)
            saves[label] = Path(path).read_bytes()
        return saves
    # Default: search for a standard pattern
    base = Path('/home/xsyvps/fft-job-saves')
    labels = ['squire', 'archer', 'knight', 'monk', 'white_mage', 'chemist']
    saves = {}
    for label in labels:
        p = base / f'owl_{label}' / 'enhanced' / 'fftsave.bin'
        if p.exists():
            saves[label] = p.read_bytes()
    
    if len(saves) < 3:
        print("Usage: python fft_multi_job_finder.py <label1>:<file1.bin> <label2>:<file2.bin> ...")
        print("  or organize saves as: /home/xsyvps/fft-job-saves/owl_<job>/enhanced/fftsave.bin")
        sys.exit(1)
    
    return saves

saves = load_args()
limit = min(len(data) for data in saves.values())

print(f"Multi-Job Candidate Finder")
print(f"=" * 60)
for label, data in saves.items():
    print(f"  {label}: {len(data):,} bytes")
print(f"  Scanning: 0x00000-0x{limit:x}")
print()

# Check that all saves are the same size
sizes = set(len(data) for data in saves.values())
if len(sizes) > 1:
    print(f"WARNING: files have different sizes: {sizes}")

SCAN_START = 0x31000
SCAN_END = min(0x45000, limit)

# u8 candidates: small values, 3+ unique values across jobs
print("=== u8 multi-job candidates (small values, 3+ unique) ===")
u8_candidates = []
for off in range(SCAN_START, SCAN_END):
    vals = {label: data[off] for label, data in saves.items()}
    unique = set(vals.values())
    if len(unique) >= 3 and all(0 <= v <= 128 for v in unique):
        u8_candidates.append((off, vals))

if u8_candidates:
    print(f"  Found {len(u8_candidates)} candidates in extended region:")
    for off, vals in u8_candidates:
        context = ""
        for name_off, name in [
            (0x318a8, 'Xsy'), (0x31b00, 'Ghost'), (0x31d58, 'Ares'),
            (0x32910, 'OWL'), (0x31fb0, 'Snow'),
        ]:
            if abs(off - name_off) < 200:
                context = f" [near {name}, rel={off-name_off:+d}]"
                break
        
        val_str = " | ".join(f"{l:>10s}: {v:3d}" for l, v in vals.items())
        print(f"    0x{off:06x}: {val_str}{context}")
else:
    print("  None found — need more job saves or different values")

print()

# u16 candidates
print("=== u16 multi-job candidates (3+ unique, all ≤ 512) ===")
u16_candidates = []
for off in range(SCAN_START, SCAN_END - 1):
    vals = {}
    for label, data in saves.items():
        vals[label] = struct.unpack_from('<H', data, off)[0]
    unique = set(vals.values())
    if len(unique) >= 3 and all(0 <= v <= 512 for v in unique):
        u16_candidates.append((off, vals))

if u16_candidates:
    print(f"  Found {len(u16_candidates)} candidates:")
    for off, vals in u16_candidates:
        context = ""
        for name_off, name in [
            (0x318a8, 'Xsy'), (0x31b00, 'Ghost'), (0x31d58, 'Ares'),
            (0x32910, 'OWL'), (0x31fb0, 'Snow'),
        ]:
            if abs(off - name_off) < 200:
                context = f" [near {name}, rel={off-name_off:+d}]"
                break
        
        val_str = " | ".join(f"{l:>10s}: {v:3d}" for l, v in vals.items())
        print(f"    0x{off:06x}: {val_str}{context}")
else:
    print("  None found")

print()

# Compact enum pattern detection
print("=== Looking for compact enum pattern (0,1,2,3,4,5) or (0x10,0x11,0x12...) ===")
for off in range(SCAN_START, SCAN_END):
    vals_list = [data[off] for data in saves.values()]
    unique = sorted(set(vals_list))
    if len(unique) >= 3:
        # Check sequential pattern 0,1,2,3...
        if unique == list(range(unique[0], unique[0] + len(unique))):
            val_str = " | ".join(f"{l}: {v}" for l, v in saves.items())
            print(f"  SEQUENTIAL u8 at 0x{off:06x}: values={unique}")
        # Check 0x10, 0x11, 0x12... pattern
        if all(v >= 0x10 and v <= 0x20 for v in unique) and len(unique) >= 3:
            sorted_unique = sorted(unique)
            if sorted_unique == list(range(sorted_unique[0], sorted_unique[0] + len(sorted_unique))):
                val_str = " | ".join(f"{l}: 0x{v:02x}" for l, v in saves.items())
                print(f"  HEX SEQUENTIAL u8 at 0x{off:06x}: values={[hex(v) for v in sorted_unique]}")
