#!/usr/bin/env python3
"""
FFT Ability/JP Bitfield Finder
Compares saves before/after learning one ability to find bitfield patterns.
Usage: python fft_ability_finder.py <before.bin> <after.bin>
"""
import struct
import sys
from pathlib import Path

def load_paths():
    if len(sys.argv) >= 3:
        return Path(sys.argv[1]), Path(sys.argv[2])
    base = Path('/home/xsyvps/fft-ability-saves')
    return (
        base / 'before_ability' / 'enhanced' / 'fftsave.bin',
        base / 'after_ability' / 'enhanced' / 'fftsave.bin',
    )

before_path, after_path = load_paths()

if not before_path.exists() or not after_path.exists():
    print(f"Files not found.")
    print("Usage: python fft_ability_finder.py <before.bin> <after.bin>")
    sys.exit(1)

before = before_path.read_bytes()
after = after_path.read_bytes()
limit = min(len(before), len(after))

print(f"Ability/JP Bitfield Finder")
print(f"Before: {before_path} ({len(before):,} bytes)")
print(f"After:  {after_path} ({len(after):,} bytes)")
print()

SCAN_START = 0x31000
SCAN_END = min(0x45000, limit)

# Byte-level diff
print("=== Byte-level diff (0x31000-0x45000) ===")
diffs = []
for off in range(SCAN_START, SCAN_END):
    if before[off] != after[off]:
        diffs.append((off, before[off], after[off]))

print(f"  Found {len(diffs)} changed bytes")

# Group consecutive diffs
if diffs:
    groups = []
    start = diffs[0][0]
    end = diffs[0][0]
    for off, _, _ in diffs[1:]:
        if off == end + 1:
            end = off
        else:
            groups.append((start, end + 1))
            start = off
            end = off
    groups.append((start, end + 1))
    
    print(f"  In {len(groups)} groups:")
    for s, e in groups:
        size = e - s
        hex_before = before[s:min(s+16, e)].hex(' ')
        hex_after = after[s:min(s+16, e)].hex(' ')
        print(f"    0x{s:06x}-0x{e:06x} ({size}B):")
        print(f"      Before: {hex_before}")
        print(f"      After:  {hex_after}")
        
        # Check for bitfield pattern (single bit flip)
        for off in range(s, min(s + 16, e)):
            bval = before[off]
            aval = after[off]
            xor = bval ^ aval
            # Check if exactly one bit changed
            if xor != 0 and (xor & (xor - 1)) == 0:
                bit_pos = xor.bit_length() - 1
                print(f"      0x{off:06x}: {bval:02x} → {aval:02x} xor={xor:02x} (SINGLE BIT {bit_pos} flipped)")
            elif xor != 0:
                # Multi-bit change — could be JP value
                delta = aval - bval
                print(f"      0x{off:06x}: {bval:02x} → {aval:02x} xor={xor:02x} (Δ={delta})")

# XOR diff for bitfield detection
print("\n=== XOR analysis (bitfield detection) ===")
xor_data = bytes(b ^ a for b, a in zip(before[SCAN_START:SCAN_END], after[SCAN_START:SCAN_END]))

# Find runs of XOR bytes with single bits set
print("Single-bit XOR patterns (learned ability bits):")
for i in range(len(xor_data)):
    xor = xor_data[i]
    if xor != 0 and (xor & (xor - 1)) == 0:
        bit = xor.bit_length() - 1
        abs_off = SCAN_START + i
        print(f"  0x{abs_off:06x}: bit {bit} flipped ({before[abs_off]:02x} → {after[abs_off]:02x})")

# Find multi-byte changes (JP values, etc.)
print("\nMulti-byte changes (JP-related):")
for off in range(SCAN_START, SCAN_END - 1):
    bval = struct.unpack_from('<H', before, off)[0]
    aval = struct.unpack_from('<H', after, off)[0]
    if bval != aval:
        xor = bval ^ aval
        delta = aval - bval
        # Check if this could be JP spent (decrease)
        if 0 < bval <= 999 and delta < 0:
            print(f"  0x{off:06x}: JP? {bval} → {aval} (Δ={delta})")
        # Check if this could be an ability bitfield change
        if xor != 0 and xor > 0xFF:
            print(f"  0x{off:06x}: multi-byte change {bval} → {aval} (xor=0x{xor:04x}, Δ={delta})")
