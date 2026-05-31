#!/usr/bin/env python3
"""FFT stat field mapper — cross-reference character records across saves."""
import struct, pathlib, json
from collections import defaultdict


def find_all_records(data, filename):
    """Find all character records in a save file."""
    records = []
    for i in range(len(data) - 12):
        if (data[i+2:i+9] == b'\x11\x11\x11\x11\x11\x11\x11' and
            data[i+9:i+12] == b'\x01\x01\x00'):
            for off in range(i + 70, min(i + 130, len(data) - 3)):
                if data[off:off+4].isalpha():
                    end = off
                    while end < len(data) and data[end] != 0:
                        end += 1
                    name = data[off:end].decode('ascii', errors='replace')
                    if len(name) >= 3:
                        marker_bytes = f"{data[i]:02x}{data[i+1]:02x}"
                        stat_start = i + 12
                        stat_end = off
                        stat_data = data[stat_start:stat_end]
                        u16_count = len(stat_data) // 2
                        u16_vals = list(struct.unpack_from(f'<{u16_count}H', stat_data, 0))
                        records.append({
                            'file': filename,
                            'name': name,
                            'marker': marker_bytes,
                            'stats': u16_vals,
                            'stat_len': u16_count,
                        })
                        break
    return records


def main():
    all_records = []
    base = pathlib.Path('/home/xsyvps/fft-saves/tactics')

    for sav_file in sorted(base.rglob('*.sav')):
        data = sav_file.read_bytes()
        rel = str(sav_file.relative_to(base))
        records = find_all_records(data, rel)
        all_records.extend(records)

    # Also check fftsave.bin
    fftsave = base / 'enhanced' / 'fftsave.bin'
    if fftsave.exists():
        data = fftsave.read_bytes()
        records = find_all_records(data, 'enhanced/fftsave.bin')
        all_records.extend(records)

    print(f"Total records found: {len(all_records)}")

    # Group by (name, marker)
    by_key = defaultdict(list)
    for r in all_records:
        by_key[(r['name'], r['marker'])].append(r)

    print(f"Unique name+marker combos: {len(by_key)}\n")

    # For each unique character, compare stat blocks
    for (name, marker), records in sorted(by_key.items()):
        print(f"\n{'='*60}")
        print(f"  {name} (marker {marker}) — {len(records)} occurrence(s)")
        print(f"{'='*60}")

        stat_lens = set(r['stat_len'] for r in records)
        if len(stat_lens) != 1:
            print(f"  WARNING: Different stat block sizes: {stat_lens}")
            for r in records:
                print(f"    {r['file']}: {r['stat_len']} fields")
                print(f"    First 16: {r['stats'][:16]}")
            continue

        stat_len = stat_lens.pop()

        # Show all values side by side
        header = f"  {'Field':>6}"
        for r in records:
            short = r['file'].split('/')[-1][:15]
            header += f"  {short:>12}"
        print(header)
        print(f"  {'-'*6}{'-'*13*len(records)}")

        for j in range(stat_len):
            vals = [r['stats'][j] for r in records]
            unique_vals = set(vals)
            diff_marker = " ***" if len(unique_vals) > 1 else ""
            line = f"  +{j*2:4d}:"
            for v in vals:
                line += f"  {v:>12d}"
            line += diff_marker
            # Only print if there's something interesting (non-zero or differs)
            if any(v != 0 for v in vals) or len(unique_vals) > 1:
                print(line)

    # Now do cross-character comparison within same file
    print(f"\n\n{'='*60}")
    print("  CROSS-CHARACTER COMPARISON (same file, same offsets)")
    print(f"{'='*60}")

    # Group records by file
    by_file = defaultdict(list)
    for r in all_records:
        by_file[r['file']].append(r)

    for filename, records in sorted(by_file.items()):
        if len(records) < 2:
            continue
        print(f"\n  --- {filename} ---")
        # Find min stat_len
        min_len = min(r['stat_len'] for r in records)
        for j in range(min_len):
            vals = [(r['name'], r['stats'][j]) for r in records]
            unique = set(v for _, v in vals)
            if len(unique) > 1 and any(v != 0 for v in unique):
                line = f"    +{j*2:4d}:"
                for name, v in vals:
                    line += f"  {name:>10s}={v:>5d}"
                print(line)


if __name__ == "__main__":
    main()
