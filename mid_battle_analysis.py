#!/usr/bin/env python3
"""Analyze mid-battle autosave — focus on OWL and Xsy damage."""
import struct, pathlib

baseline = pathlib.Path('/home/xsyvps/fft-saves5/tactics/enhanced-1143/fftsave.bin').read_bytes()
mid_dir = pathlib.Path('/home/xsyvps/fft-savesx/tactics/auto-x')
after = pathlib.Path('/home/xsyvps/fft-saves6/tactics/enhanced-1244/fftsave.bin').read_bytes()

def find_records(data):
    records = []
    for i in range(len(data) - 12):
        if data[i+2:i+9] != b'\x11\x11\x11\x11\x11\x11\x11':
            continue
        tail = data[i+9:i+12]
        if tail not in [b'\x01\x01\x00', b'\x10\x11\x00']:
            continue
        marker = f"{data[i]:02x}{data[i+1]:02x}"
        tail_type = "STD" if tail == b'\x01\x01\x00' else "NEW"
        for bl in range(70, 120):
            no = i + 12 + bl
            if no >= len(data):
                break
            if 0x20 <= data[no] < 0x7f:
                end = no
                while end < len(data) and 0x20 <= data[end] < 0x7f:
                    end += 1
                if 3 <= end - no <= 24 and end < len(data) and data[end] == 0:
                    name = data[no:end].decode('ascii')
                    stats = list(struct.unpack_from(f'<{bl//2}H', data, i+12))
                    records.append({
                        'marker': marker, 'tail': tail_type, 'name': name,
                        'offset': i, 'block_len': bl, 'stats': stats,
                    })
                    break
    return records

# Baseline characters (slot 1)
base_xsy = [r for r in find_records(baseline) if r['name'] == 'Xsy'][0]
base_owl = [r for r in find_records(baseline) if r['name'] == 'OWL'][0]
base_ghost = [r for r in find_records(baseline) if r['name'] == 'Ghost' and r['marker'] == '4123'][0]

print("=== BASELINE (enhanced-1143) ===")
print(f"Xsy:   marker={base_xsy['marker']} offset=0x{base_xsy['offset']:x} stats={base_xsy['stats'][:10]}")
print(f"OWL:   marker={base_owl['marker']} offset=0x{base_owl['offset']:x} stats={base_owl['stats'][:10]}")
print(f"Ghost: marker={base_ghost['marker']} offset=0x{base_ghost['offset']:x} stats={base_ghost['stats'][:10]}")

# Mid-battle: check ALL files for OWL records
print("\n=== MID-BATTLE OWL RECORDS ===")
owl_mid_all = []
for f in sorted(mid_dir.glob('*.sav')):
    data = f.read_bytes()
    for r in find_records(data):
        if r['name'] == 'OWL':
            raw = r['stats'][:]
            unshifted = [v >> 8 for v in raw] if r['tail'] == 'NEW' else raw
            print(f"  {f.name}: marker={r['marker']} tail={r['tail']} offset=0x{r['offset']:x}")
            print(f"    Raw:     {raw[:15]}")
            print(f"    Unshift: {unshifted[:15]}")
            owl_mid_all.append((f.name, r, unshifted))

# Mid-battle: Xsy records
print("\n=== MID-BATTLE XSY RECORDS ===")
xsy_mid_all = []
for f in sorted(mid_dir.glob('*.sav')):
    data = f.read_bytes()
    for r in find_records(data):
        if r['name'] == 'Xsy':
            print(f"  {f.name}: marker={r['marker']} offset=0x{r['offset']:x} stats={r['stats'][:15]}")
            xsy_mid_all.append((f.name, r))

# The key question: which mid-battle file has current HP data?
# In FFT, the attack save should have battle state
# Let me check the attack save more carefully

print("\n=== DEEP DIVE: resume_en00_attack.sav ===")
atk_data = (mid_dir / 'resume_en00_attack.sav').read_bytes()
atk_recs = find_records(atk_data)
for r in atk_recs:
    print(f"  {r['name']:10s} marker={r['marker']} offset=0x{r['offset']:x} stats={r['stats'][:10]}")

# Diff Xsy baseline vs mid-battle attack
print("\n=== XSY DIFF: baseline vs mid-battle (attack save) ===")
if xsy_mid_all:
    # Use the first Xsy in attack save
    for fname, r in xsy_mid_all:
        if 'attack' in fname:
            mid_stats = r['stats']
            base_stats = base_xsy['stats']
            for j in range(min(len(mid_stats), len(base_stats))):
                vb = base_stats[j]
                vm = mid_stats[j]
                if vb != vm:
                    print(f"  u16_{j:02d}: {vb} → {vm} (delta {vm-vb})")
            break

# Diff OWL baseline vs mid-battle
print("\n=== OWL DIFF: baseline vs mid-battle ===")
if owl_mid_all:
    # baseline OWL stats (unshifted)
    owl_base_unshifted = [v >> 8 for v in base_owl['stats']]
    
    for fname, r, mid_unshifted in owl_mid_all:
        print(f"\n  From {fname} (marker={r['marker']}):")
        changes = []
        for j in range(min(len(mid_unshifted), len(owl_base_unshifted))):
            vb = owl_base_unshifted[j]
            vm = mid_unshifted[j]
            if vb != vm:
                changes.append((j, vb, vm, vm - vb))
        
        if changes:
            for idx, vb, vm, delta in changes:
                print(f"    u16_{idx:02d}: {vb} → {vm} (delta {delta})")
        else:
            print(f"    NO CHANGES")

# Also check: maybe the attack save has a DIFFERENT record layout
# Let me look at the raw bytes around OWL in the attack save
print("\n=== RAW BYTES around OWL in attack save ===")
for f in sorted(mid_dir.glob('*attack*.sav')):
    data = f.read_bytes()
    pos = data.find(b'OWL')
    while pos != -1:
        # Check if there's a marker before this
        for back in range(30, 80, 2):
            m_start = pos - back
            if m_start < 0:
                continue
            if (data[m_start+2:m_start+9] == b'\x11\x11\x11\x11\x11\x11\x11' and
                data[m_start+9:m_start+12] in [b'\x01\x01\x00', b'\x10\x11\x00']):
                marker = f"{data[m_start]:02x}{data[m_start+1]:02x}"
                tail = "STD" if data[m_start+9:m_start+12] == b'\x01\x01\x00' else "NEW"
                block = back - 12
                stats_start = m_start + 12
                stats = list(struct.unpack_from(f'<{block//2}H', data, stats_start))
                unshifted = [v >> 8 for v in stats] if tail == "NEW" else stats
                print(f"  {f.name}: marker={marker} tail={tail} block={block}B stats(unshift)={unshifted[:12]}")
                break
        # Find next OWL
        pos = data.find(b'OWL', pos + 1)

PYEOF