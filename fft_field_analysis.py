#!/usr/bin/env python3
"""
FFT Character Stat Field Mapper
Maps uint16 stat fields by cross-referencing multiple saves.

KEY FINDINGS (from Ghost character, marker 4123):

VARYING FIELDS (change between main/attack/fturn saves):
  +0:  Current HP? (134 battle / 161 main)
  +6:  Current MP? (29 battle / 67 main)
  +8:  Max HP?    (148 battle / 154 main — level up?)
  +12: Max MP?    (170 battle / 176 main)
  +46: Experience? (904 battle / 931 main)
  +52: Battle count? or secondary EXP?

CONSTANT BASE STATS (same in all 30 occurrences):
  +2:  83   — Base STR or PA?
  +4:  225  — Base VIT or HP growth?
  +10: 159  — Base stat
  +14: 192  — Base stat
  +16: 108  — Base stat
  +18: 160  — Base stat
  +20: 148  — Base stat
  +22: 196  — Base stat
  +24: 128  — Base stat
  +26: 156  — Base stat
  +28: 188  — Base stat
  +30: 159  — Base stat
  +32: 154  — Base stat
  +34: 171  — Base stat
  +38: 113  — Base stat
  +48: 183  — Base stat (between EXP and second block)
  +50: 225  — Base stat (= +4 value, interesting!)
  +56-+84: More base stats (second block, partially mirrors first)

ZERO/UNUSED FIELDS:
  +36, +40, +42, +44, +82: Always 0 — unused padding or rare stats

FIELD COUNT: 44 uint16 values (88 bytes) between marker and name

CHARACTER RECORD LAYOUT:
  Bytes 0-11:   Marker (2-byte ID + 0x11*7 + 0x01 0x01 0x00)
  Bytes 12-99:  Stat block (44 x uint16 LE)
  Bytes 100+:   Name (null-terminated ASCII)
  Padding:      Variable to next record

NOTE: The exact mapping of stat fields to FFT stats (STR, AGI, etc.) requires
saving at known stat values (e.g., level 1 vs level 2 with same equipment)
and diffing the binary. The VARYING fields are almost certainly:
HP_cur, HP_max, MP_cur, MP_max, EXP, and possibly Gil or kill count.
"""

import struct
import pathlib


def analyze_known_fields():
    """Document the known field positions based on cross-save analysis."""
    
    known_mapping = {
        0:  {"name": "HP_current?",   "note": "134 battle / 161 main — decreases in combat"},
        2:  {"name": "stat_base_1",    "note": "83, constant"},
        4:  {"name": "stat_base_2",    "note": "225, constant"},
        6:  {"name": "MP_current?",   "note": "29 battle / 67 main — decreases in combat"},
        8:  {"name": "HP_max?",       "note": "148 battle / 154 main — grows with level"},
        10: {"name": "stat_base_3",    "note": "159, constant"},
        12: {"name": "MP_max?",       "note": "170 battle / 176 main — grows with level"},
        14: {"name": "stat_base_4",    "note": "192, constant"},
        16: {"name": "stat_base_5",    "note": "108, constant"},
        18: {"name": "stat_base_6",    "note": "160, constant"},
        20: {"name": "stat_base_7",    "note": "148, constant"},
        22: {"name": "stat_base_8",    "note": "196, constant"},
        24: {"name": "stat_base_9",    "note": "128, constant"},
        26: {"name": "stat_base_10",   "note": "156, constant"},
        28: {"name": "stat_base_11",   "note": "188, constant"},
        30: {"name": "stat_base_12",   "note": "159, constant (= +10)"},
        32: {"name": "stat_base_13",   "note": "154, constant"},
        34: {"name": "stat_base_14",   "note": "171, constant"},
        36: {"name": "unused_1",       "note": "always 0"},
        38: {"name": "stat_base_15",   "note": "113, constant (maybe C-EV or Luck)"},
        40: {"name": "unused_2",       "note": "always 0"},
        42: {"name": "unused_3",       "note": "always 0"},
        44: {"name": "unused_4",       "note": "always 0"},
        46: {"name": "EXP?",           "note": "904 battle / 931 main — increases over time"},
        48: {"name": "stat_base_16",   "note": "183, constant"},
        50: {"name": "stat_base_17",   "note": "225, constant (= +4)"},
        52: {"name": "battles?",       "note": "579 battle / 617 main — accumulates"},
    }

    print("=== GHOST CHARACTER STAT FIELD MAPPING ===\n")
    print(f"{'Offset':>6} | {'Value':>8} | {'Field':<16} | {'Notes'}")
    print("-" * 75)
    
    # Use Ghost from main save as reference
    ghost_main_vals = [161, 83, 225, 67, 154, 159, 176, 192, 108, 160, 148, 196, 128, 156, 188, 159, 154, 171, 0, 113, 0, 0, 0, 931, 183, 225, 617]
    
    for off, info in sorted(known_mapping.items()):
        val = ghost_main_vals[off//2] if off//2 < len(ghost_main_vals) else "?"
        print(f"  +{off:3d}  | {str(val):>8} | {info['name']:<16} | {info['note']}")

    print()


def compare_characters():
    """Compare Ghost vs Argath to identify field semantics."""
    
    print("=== CROSS-CHARACTER COMPARISON ===\n")
    
    # Values from attack save
    ghost_vals = [134, 83, 225, 29, 148, 159, 170, 192, 108, 160, 148, 196, 128, 156, 188, 159, 154, 171, 0, 113, 0, 0, 0, 904, 183, 225, 579]
    argath_vals = [2560, 7937, 43776, 25600, 33536, 41984, 46336, 43008, 37376, 28160, 34560, 26624, 39424, 29952, 28672, 37632, 50688, 48640, 43264, 25600, 36097, 43776, 25600, 33536, 41984, 46336]
    ares_vals = [202, 119, 59, 135, 197, 114, 128, 110, 139, 179, 148, 118, 145, 194, 150, 124, 178, 129, 0, 103, 0, 0, 0, 802, 269, 559, 135, 197, 114, 128]
    
    max_len = max(len(ghost_vals), len(argath_vals), len(ares_vals))
    
    print(f"{'Field':>6} | {'Ghost':>8} | {'Argath':>8} | {'Ares':>8} | {'Ratio G/A':>10}")
    print("-" * 55)
    
    for i in range(min(20, max_len)):
        g = ghost_vals[i] if i < len(ghost_vals) else "-"
        a = argath_vals[i] if i < len(argath_vals) else "-"
        r = ares_vals[i] if i < len(ares_vals) else "-"
        
        ratio = ""
        if isinstance(g, int) and isinstance(a, int) and a > 0:
            ratio = f"{g/a:.2f}"
        
        print(f"  +{i*2:3d}  | {str(g):>8} | {str(a):>8} | {str(r):>8} | {ratio:>10}")


if __name__ == "__main__":
    analyze_known_fields()
    print()
    compare_characters()
