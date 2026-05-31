#!/usr/bin/env python3
"""Analyze Xsy level-up diff to identify stat fields."""
import struct, pathlib

base = pathlib.Path('/home/xsyvps/fft-saves5/tactics/enhanced-1143/fftsave.bin').read_bytes()
new = pathlib.Path('/home/xsyvps/fft-saves6/tactics/enhanced-1244/fftsave.bin').read_bytes()

def get_stats(data, offset):
    return list(struct.unpack_from('<46H', data, offset + 12))

# Xsy: leveled up! (new record at 0x31840 vs baseline at 0x1de88)
# Using baseline slot 3 (0x1de88) vs the NEW slot 4 record (0x31840)
# Actually we should compare same slot. Let me check all 3 baseline slots.
for slot, off in [(1, 0xa4d0), (2, 0x141ac), (3, 0x1de88)]:
    s = get_stats(base, off)
    print(f"Xsy slot {slot} baseline (0x{off:x}): u16_00={s[0]}, u16_01={s[1]}, u16_02={s[2]}, u16_03={s[3]}, u16_04={s[4]}, u16_05={s[5]}, u16_06={s[6]}, u16_07={s[7]}")

# New Xsy at 0x31840
new_xsy = get_stats(new, 0x31840)
print(f"\nXsy NEW slot (0x31840):          u16_00={new_xsy[0]}, u16_01={new_xsy[1]}, u16_02={new_xsy[2]}, u16_03={new_xsy[3]}, u16_04={new_xsy[4]}, u16_05={new_xsy[5]}, u16_06={new_xsy[6]}, u16_07={new_xsy[7]}")

# Compare baseline slot 3 vs new slot 4
base_xsy = get_stats(base, 0x1de88)
print(f"\n=== XSI DIFF (slot 3 baseline → slot 4 new) ===")
for j in range(46):
    vb = base_xsy[j]
    vn = new_xsy[j]
    if vb != vn:
        print(f"  u16_{j:02d}: {vb} → {vn}  (delta {vn-vb})")

# All characters for comparison
print("\n=== ALL L1 SQUIRE VALUES ===")
ares_b = get_stats(base, 0xa980)
owl_b_raw = get_stats(base, 0x28bcb)
owl_b = [v >> 8 for v in owl_b_raw]

print(f"\n{'Field':>6} | {'Ares(M)':>8} | {'OWL(F)':>8} | {'Xsy(?)(base)':>14} | {'Xsy(after)':>12} | Notes")
print("-" * 80)
for j in range(46):
    a = ares_b[j]
    o = owl_b[j]
    x = base_xsy[j]
    xn = new_xsy[j]
    
    # Only show interesting fields
    interesting = (a != 0 or o != 0 or x != 0 or xn != 0)
    if not interesting:
        continue
    
    notes = ""
    if j == 0:
        notes = "HP? Ares(M)=202 > OWL(F)=176 — matches FFT gender mod"
    elif j == 1:
        notes = "MP?"
    elif j == 12:
        notes = "Always 128"
    elif j == 20 or j == 21 or j == 22:
        notes = "Always 0"
    elif j in [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42]:
        mirror_j = j - 24
        notes = f"=u16_{mirror_j:02d} (mirror)"
    
    print(f"  u16_{j:02d} | {a:>8} | {o:>8} | {x:>14} | {xn:>12} | {notes}")

print(f"\n=== CONFIRMED: XSY LEVELED UP ===")
print(f"Comparing baseline slot 3 to new slot 4 (same character, post-battle):")
print(f"  u16_00: {base_xsy[0]} → {new_xsy[0]} (+{new_xsy[0]-base_xsy[0]}) ← MAX HP")
print(f"  u16_01: {base_xsy[1]} → {new_xsy[1]} (+{new_xsy[1]-base_xsy[1]}) ← MAX MP")
print(f"  u16_02: {base_xsy[2]} → {new_xsy[2]} ({new_xsy[2]-base_xsy[2]:+d})  ← STR? (unchanged)")
print(f"  u16_03: {base_xsy[3]} → {new_xsy[3]} ({new_xsy[3]-base_xsy[3]:+d})  ← PA? (unchanged)")
print(f"  u16_04: {base_xsy[4]} → {new_xsy[4]} (+{new_xsy[4]-base_xsy[4]})  ← STAT A (+16)")
print(f"  u16_05: {base_xsy[5]} → {new_xsy[5]} ({new_xsy[5]-base_xsy[5]:+d})  ← STAT B (unchanged)")
print(f"  u16_06: {base_xsy[6]} → {new_xsy[6]} ({new_xsy[6]-base_xsy[6]:+d})  ← STAT C (unchanged)")
print(f"  u16_07: {base_xsy[7]} → {new_xsy[7]} (+{new_xsy[7]-base_xsy[7]})  ← STAT D (+8)")
print(f"  u16_23: {base_xsy[23]} → {new_xsy[23]} (+{new_xsy[23]-base_xsy[23]}) ← HP-RELATED (=u16_00 delta)")
print(f"  u16_24: {base_xsy[24]} → {new_xsy[24]} (+{new_xsy[24]-base_xsy[24]}) ← MP-RELATED (=u16_01 delta)")
