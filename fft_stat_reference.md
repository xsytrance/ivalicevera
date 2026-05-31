# FFT PC Remaster Character Stat Block Reference
# Record: 12-byte marker + 92-byte stat block (46 uint16 LE) + name string
# 
# Field layout (Ghost/Xsy/Ares encoding):
#   u16_00: Current HP? (varies battle/rest)
#   u16_01: Base stat 1 (constant)
#   u16_02: Base stat 2 (constant)
#   u16_03: Current MP? (varies battle/rest)
#   u16_04: Max HP? (varies with level)
#   u16_05-u16_17: Base stats 3-14 (constant)
#   u16_18: UNUSED (always 0)
#   u16_19: Base stat 15 (constant)
#   u16_20-u16_22: UNUSED (always 0)
#   u16_23: EXP? (increases over time)
#   u16_24-u16_25: Base stats 16-17 (constant)
#   u16_26: Gil/Battle count? (accumulates)
#   u16_27-u16_42: Mirror of u16_03-u16_18
#   u16_43-u16_45: UNUSED (always 0)
#
# Argath encoding appears DIFFERENT (byte-pairs/flags, not plain uint16 stats)
# Marker prefix may indicate encoding type
