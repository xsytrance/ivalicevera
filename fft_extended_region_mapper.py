#!/usr/bin/env python3
"""
FFT Extended Region Mapper
Maps the 0x31000-0x45000 region structure: character names, stat blocks, and post-name metadata.
Run on an enhanced/fftsave.bin file.
"""
import struct
import sys
from pathlib import Path

def load_default():
    paths = [
        '/home/xsyvps/fft-savesnew1/tactics/enhanced-new1/fftsave.bin',
        '/home/xsyvps/fft-saves5/tactics/enhanced-1139/fftsave.bin',
    ]
    for p in paths:
        if Path(p).exists():
            return Path(p).read_bytes()
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).read_bytes()
    print("Usage: python fft_extended_region_mapper.py [fftsave.bin]")
    sys.exit(1)

data = load_default()
START = 0x31000
END = 0x45000

print(f"File size: {len(data):,} bytes")
print(f"Scanning 0x{START:x}-0x{END:x} ({END-START:,} bytes)\n")

# Find all character names
names_to_find = [b'OWL', b'Xsy', b'Ghost', b'Ares', b'Argath', b'Snow']
print("=== Character name blocks ===\n")

for name in names_to_find:
    # Search with null terminator
    search_name = name + b'\x00'
    pos = START
    occurrences = []
    while pos < END:
        idx = data.find(search_name, pos, END)
        if idx == -1:
            break
        occurrences.append(idx)
        pos = idx + 1
    
    if not occurrences:
        print(f"{name.decode()}: NOT FOUND in extended region\n")
        continue
    
    for off in occurrences:
        # Determine the full name pattern (may have extra string after null)
        name_end = off + len(search_name)
        # Check if there's a second string right after
        extra_str = b""
        if name_end < END and data[name_end] != 0:
            extra_end = data.find(b'\x00', name_end, name_end + 20)
            if extra_end > 0:
                extra_str = data[name_end:extra_end]
                name_end = extra_end + 1
        
        full_name = search_name + extra_str + b'\x00' if extra_str else search_name
        
        # Find end of zero padding after name
        zero_end = name_end
        while zero_end < END and data[zero_end] == 0:
            zero_end += 1
        
        # Read post-name metadata bytes (up to 16 non-zero bytes)
        post_meta = data[zero_end:zero_end+16]
        
        # Read pre-name stat block (40 u16 = 80 bytes before name)
        pre_start = off - 80
        if pre_start < 0:
            pre_start = 0
        pre = data[pre_start:off]
        pre_u16 = [struct.unpack_from('<H', pre, i*2)[0] for i in range(len(pre)//2)]
        
        print(f"{name.decode()} at 0x{off:x}:")
        print(f"  Full name pattern: {full_name!r}")
        print(f"  Post-name meta at 0x{zero_end:x}: {post_meta.hex(' ')}")
        print(f"    u8:  {list(post_meta)}")
        print(f"  Pre-name stat block (u16): {pre_u16}")
        
        # Check for mirror pattern in pre-name block
        half = len(pre_u16) // 2
        mirror_match = all(pre_u16[i] == pre_u16[i + half] for i in range(half))
        print(f"  Mirror pattern (first half == second half): {mirror_match}")
        print()

# Map non-zero block distribution
print("\n=== Non-zero block distribution ===")
region = data[START:END]
total = len(region)
zeros = sum(1 for b in region if b == 0)
ffs = sum(1 for b in region if b == 0xFF)
print(f"Total: {total:,} | 0x00: {zeros:,} ({zeros/total*100:.1f}%) | 0xFF: {ffs:,} ({ffs/total*100:.1f}%)")
