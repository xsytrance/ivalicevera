#!/usr/bin/env python3
"""
FFT Stat Field Mapper v2 — Using Ed's hypothesis about field layout.

Layout hypothesis:
  identity/flags → job/class/level/exp/bravery/faith → base stats → 
  current battle stats → equipment → abilities bitfield → name

HP/MP appear multiple times: base/max/current/job-adjusted/battle
"""
import struct, pathlib


def find_records(data, filename):
    records = []
    for i in range(len(data) - 12):
        if (data[i+2:i+9] == b'\x11\x11\x11\x11\x11\x11\x11' and
            data[i+9:i+12] == b'\x01\x01\x00'):
            for off in range(i + 70, min(i + 200, len(data) - 3)):
                if data[off:off+4].isalpha():
                    end = off
                    while end < len(data) and data[end] != 0:
                        end += 1
                    name = data[off:end].decode('ascii', errors='replace')
                    if len(name) >= 3:
                        stat_start = i + 12
                        stat_data = data[stat_start:off]
                        u16 = list(struct.unpack_from(f'<{len(stat_data)//2}H', stat_data, 0))
                        records.append({
                            'file': filename, 'name': name,
                            'marker': f"{data[i]:02x}{data[i+1]:02x}",
                            'stats': u16, 'stat_bytes': len(stat_data),
                        })
                        break
    return records


def main():
    base = pathlib.Path('/home/xsyvps/fft-saves/tactics')
    all_records = []
    
    for f in sorted(base.rglob('*.sav')):
        data = f.read_bytes()
        rel = str(f.relative_to(base))
        all_records.extend(find_records(data, rel))

    # Focus on Ghost (marker 4123) — 30 occurrences across all saves
    ghost_4123 = [r for r in all_records if r['name'] == 'Ghost' and r['marker'] == '4123']
    
    print(f"=== GHOST (marker 4123) — {len(ghost_4123)} records ===\n")
    print(f"Stat block size: {ghost_4123[0]['stat_bytes']} bytes ({len(ghost_4123[0]['stats'])} uint16)\n")
    
    # Ed's rules for identifying fields:
    # Level: small, 1-99/100
    # EXP: small, 0-99 (wait, FFT EXP goes higher... but "small" relative to HP)
    # HP/MP: larger, 0-999
    # STR/AGI/VIT/INT/MND: medium, 0-255
    # PA/MA/Speed: smaller
    # Move/Jump: very small, 0-10
    # Bravery/Faith: 0-100
    
    # Let's look at Ghost's stat block and classify each field
    # Use the MAIN save values (index where file has 'main')
    main_vals = None
    attack_vals = None
    fturn_vals = None
    world_vals = None
    
    for r in ghost_4123:
        f = r['file']
        if 'en00_main' in f:
            main_vals = r['stats']
        elif 'en00_attack' in f and attack_vals is None:
            attack_vals = r['stats']  # First Ghost in attack
        elif 'en00_fturn' in f and fturn_vals is None:
            fturn_vals = r['stats']
        elif 'en00_world' in f:
            world_vals = r['stats']
    
    stats = main_vals or ghost_4123[0]['stats']
    n = len(stats)
    
    print("Field-by-field classification:\n")
    print(f"{'Off':>4} | {'Main':>6} | {'Atk':>6} | {'FTurn':>6} | {'World':>6} | {'Class':<10} | Candidate")
    print("-" * 85)
    
    for i in range(n):
        v_main = main_vals[i] if main_vals and i < len(main_vals) else '-'
        v_atk = attack_vals[i] if attack_vals and i < len(attack_vals) else '-'
        v_ft = fturn_vals[i] if fturn_vals and i < len(fturn_vals) else '-'
        v_w = world_vals[i] if world_vals and i < len(world_vals) else '-'
        v = stats[i] if i < len(stats) else '-'
        
        # Classify by value range
        if v == 0:
            cls = "ZERO"
        elif 1 <= v <= 7:
            cls = "tiny(1-7)"
        elif 8 <= v <= 20:
            cls = "vsmall"
        elif 21 <= v <= 99:
            cls = "small(L?)"
        elif 100 <= v <= 300:
            cls = "medium"
        elif 301 <= v <= 999:
            cls = "large(HP?)"
        elif 1000 <= v <= 9999:
            cls = "xlarge"
        else:
            cls = "HUGE"
        
        # Candidate identification
        cand = ""
        if 1 <= v <= 99 and isinstance(v_main, int) and v_main == v:
            cand = "Level?"
        elif 100 <= v <= 255:
            cand = "Base stat"
        elif 70 <= v <= 180:
            cand = "HP/MP base?"
        elif 200 <= v <= 300:
            cand = "HP growth?"
        elif i == n - 1 or i == n - 2:
            cand = "Pre-name pad"
        
        m_str = str(v_main) if v_main != '-' else '-'
        a_str = str(v_atk) if v_atk != '-' else '-'
        f_str = str(v_ft) if v_ft != '-' else '-'
        w_str = str(v_w) if v_w != '-' else '-'
        
        print(f"  +{i*2:3d} | {m_str:>6} | {a_str:>6} | {f_str:>6} | {w_str:>6} | {cls:<10} | {cand}")

    # Also analyze the big picture
    print(f"\n\n=== VALUE RANGE ANALYSIS ===")
    print(f"Total fields: {n}")
    print(f"Always zero: {sum(1 for i in range(n) if all(r['stats'][i] == 0 for r in ghost_4123[:5]))}")
    print(f"Non-zero: {sum(1 for i in range(n) if any(r['stats'][i] != 0 for r in ghost_4123[:5]))}")
    
    # Check which fields are CONSTANT across all 30 Ghost records
    constant_fields = []
    varying_fields = []
    for i in range(n):
        vals = set()
        for r in ghost_4123:
            if i < len(r['stats']):
                vals.add(r['stats'][i])
        if len(vals) == 1:
            constant_fields.append((i, vals.pop()))
        else:
            varying_fields.append((i, vals))
    
    print(f"Constant fields: {len(constant_fields)}")
    print(f"Varying fields: {len(varying_fields)}")
    
    print(f"\nConstant fields (these are identity/base stats):")
    for i, v in constant_fields:
        print(f"  +{i*2:3d}: {v}")
    
    print(f"\nVarying fields (these change battle→main):")
    for i, vals in varying_fields:
        main_v = main_vals[i] if main_vals and i < len(main_vals) else '?'
        atk_v = attack_vals[i] if attack_vals and i < len(attack_vals) else '?'
        ft_v = fturn_vals[i] if fturn_vals and i < len(fturn_vals) else '?'
        # Classify range
        classification = ""
        typical_val = main_v if isinstance(main_v, int) else (atk_v if isinstance(atk_v, int) else 0)
        if isinstance(typical_val, int):
            if 1 <= typical_val <= 20:
                classification = "→ Level/Small"
            elif 21 <= typical_val <= 99:
                classification = "→ EXP/Bravery/Faith?"
            elif 100 <= typical_val <= 999:
                classification = "→ HP/MP?"
            else:
                classification = "→ ???"
        print(f"  +{i*2:3d}: main={main_v}, atk={atk_v}, ft={ft_v}  {classification}")


if __name__ == "__main__":
    main()
