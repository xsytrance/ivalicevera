#!/usr/bin/env python3
"""
FFT Character Stat Mapper v3 — Correct 92-byte (46 uint16) blocks.
Cross-reference Ghost+Xsy+Argath+Ares to identify stat fields.
"""
import struct, pathlib


def extract_named_records(filepath):
    """Extract all character records with 92-byte stat blocks."""
    data = filepath.read_bytes()
    fname = str(filepath.relative_to(filepath.parent.parent))
    records = []
    
    for i in range(len(data) - 12):
        if not (data[i+2:i+9] == b'\x11\x11\x11\x11\x11\x11\x11' and
                data[i+9:i+12] == b'\x01\x01\x00'):
            continue
        
        marker = f"{data[i]:02x}{data[i+1]:02x}"
        stats_start = i + 12
        
        # Look for name at stat_start + 92 (the consistent block size)
        for expected_len in [92, 93, 94]:
            name_off = stats_start + expected_len
            if name_off >= len(data):
                continue
            # Read null-terminated string
            end = name_off
            while end < len(data) and 0x20 <= data[end] < 0x7f:
                end += 1
            if end > name_off and end - name_off >= 3:
                name = data[name_off:end].decode('ascii')
                if end < len(data) and data[end] == 0:
                    stat_data = data[stats_start:name_off]
                    u16_count = len(stat_data) // 2
                    u16_vals = list(struct.unpack_from(f'<{u16_count}H', stat_data, 0))
                    records.append({
                        'file': fname,
                        'marker': marker,
                        'name': name,
                        'stats': u16_vals,
                        'n_fields': u16_count,
                        'offset': i,
                    })
                    break
    
    return records


def main():
    base = pathlib.Path('/home/xsyvps/fft-saves/tactics')
    
    all_records = []
    for f in sorted(base.rglob('*.sav')):
        all_records.extend(extract_named_records(f))
    
    # Also get enhanced
    fftsave = base / 'enhanced' / 'fftsave.bin'
    if fftsave.exists():
        all_records.extend(extract_named_records(fftsave))
    
    print(f"Total records: {len(all_records)}\n")
    
    # Deduplicate: for each unique (file, name, marker), keep only one
    seen = set()
    unique = []
    for r in all_records:
        key = (r['file'], r['name'], r['marker'])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    print(f"Unique records: {len(unique)}\n")
    
    # Group by name
    by_name = {}
    for r in unique:
        by_name.setdefault(r['name'], []).append(r)
    
    # Print all unique characters and their stats
    for name, recs in sorted(by_name.items()):
        print(f"\n{'='*70}")
        print(f"  {name} ({len(recs)} saves)")
        print(f"{'='*70}")
        
        for r in recs:
            print(f"\n  File: {r['file']}")
            print(f"  Offset: 0x{r['offset']:x}, Marker: {r['marker']}, Fields: {r['n_fields']}")
            print(f"  Stats ({r['n_fields']} uint16):")
            for j, v in enumerate(r['stats']):
                # Classify
                cls = ""
                if v == 0:
                    cls = "(zero)"
                elif 1 <= v <= 20:
                    cls = "(tiny)"
                elif 21 <= v <= 99:
                    cls = "(small)"
                elif 100 <= v <= 300:
                    cls = "(medium)"
                elif 301 <= v <= 999:
                    cls = "(large)"
                else:
                    cls = "(HUGE)"
                print(f"    u16_{j:02d} (+{j*2:3d}): {v:>6d}  {cls}")
    
    # CROSS-CHARACTER COMPARISON: Ghost vs Xsy vs Argath vs Ares
    # (using the first occurrence of each)
    print(f"\n\n{'='*70}")
    print("  CROSS-CHARISON: Ghost vs Xsy vs Argath vs Ares")
    print(f"{'='*70}\n")
    
    ref = {}
    for r in unique:
        name = r['name']
        if name not in ref:
            ref[name] = r
    
    names = sorted(ref.keys())
    max_fields = max(r['n_fields'] for r in ref.values())
    
    header = f"  {'Field':>6}"
    for n in names:
        header += f"  {n:>8}"
    print(header)
    print(f"  {'-'*6}{'-'*8*len(names)}")
    
    for j in range(max_fields):
        row = f"  u16_{j:02d}"
        has_val = False
        for n in names:
            r = ref[n]
            if j < len(r['stats']):
                v = r['stats'][j]
                row += f"  {v:>8}"
                if v != 0:
                    has_val = True
            else:
                row += f"  {'---':>8}"
        if has_val:
            # Add classification
            vals = []
            for n in names:
                r = ref[n]
                if j < len(r['stats']):
                    vals.append(r['stats'][j])
            
            # Check if all same
            if len(set(vals)) == 1:
                row += "  (SAME)"
            else:
                # Check ratios
                nonzero = [v for v in vals if v != 0]
                if nonzero:
                    ratio = max(nonzero) / min(nonzero) if min(nonzero) > 0 else 0
                    if ratio > 10:
                        row += f"  (ratio {ratio:.0f}:1)"
            
            print(row)


if __name__ == "__main__":
    main()
