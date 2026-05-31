#!/usr/bin/env python3
"""Diff Ghost stat blocks between original saves and new save (slot 4 vs slot 5)."""
import struct, pathlib

def extract_ghost(filepath):
    """Extract Ghost's stat block from a .sav file."""
    data = filepath.read_bytes()
    for i in range(len(data) - 12):
        if not (data[i+2:i+9] == b'\x11\x11\x11\x11\x11\x11\x11' and
                data[i+9:i+12] == b'\x01\x01\x00'):
            continue
        
        marker = f"{data[i]:02x}{data[i+1]:02x}"
        stats_start = i + 12
        
        # Try name at offset +92 (consistent block size)
        for block_len in [92, 93]:
            name_off = stats_start + block_len
            if name_off >= len(data):
                continue
            # Check for null-terminated name
            end = name_off
            while end < len(data) and 0x20 <= data[end] < 0x7f:
                end += 1
            if end > name_off and end - name_off >= 3 and end - name_off <= 24:
                name = data[name_off:end].decode('ascii')
                if name == "Ghost":
                    stat_data = data[stats_start:name_off]
                    u16_count = len(stat_data) // 2
                    u16_vals = list(struct.unpack_from(f'<{u16_count}H', stat_data, 0))
                    return {
                        'name': name,
                        'marker': marker,
                        'offset': i,
                        'n_fields': u16_count,
                        'stats': u16_vals,
                    }
    return None


def diff_saves(old_dir, new_dir):
    """Compare Ghost between two save directories."""
    
    # Use main saves for cleanest comparison
    old_main = old_dir / 'autoenhanced' / 'resume_en00_main.sav'
    new_main = new_dir / 'auto3' / 'resume_en00_main.sav'
    
    # Fallback: try slot 01 main saves
    if not old_main.exists():
        old_main = old_dir / 'autoenhanced' / 'resume_en01_main.sav'
    if not new_main.exists():
        new_main = new_dir / 'auto3' / 'resume_en01_main.sav'
    
    print(f"Old: {old_main}")
    print(f"New: {new_main}\n")
    
    ghost_old = extract_ghost(old_main) if old_main.exists() else None
    ghost_new = extract_ghost(new_main) if new_main.exists() else None
    
    # Also try attack saves
    old_atk = old_dir / 'autoenhanced' / 'resume_en00_attack.sav'
    new_atk = new_dir / 'auto3' / 'resume_en00_attack.sav'
    
    if not ghost_old:
        ghost_old = extract_ghost(old_atk) if old_atk.exists() else None
    if not ghost_new:
        ghost_new = extract_ghost(new_atk) if new_atk.exists() else None
    
    if not ghost_old:
        print("ERROR: Could not find Ghost in old saves!")
        return
    if not ghost_new:
        print("ERROR: Could not find Ghost in new saves!")
        return
    
    print(f"Old Ghost: marker={ghost_old['marker']}, offset=0x{ghost_old['offset']:x}, fields={ghost_old['n_fields']}")
    print(f"New Ghost: marker={ghost_new['marker']}, offset=0x{ghost_new['offset']:x}, fields={ghost_new['n_fields']}")
    print()
    
    # Diff
    max_fields = max(ghost_old['n_fields'], ghost_new['n_fields'])
    changes = []
    
    print(f"{'Field':>6} | {'Old':>8} | {'New':>8} | {'Delta':>8} | {'Notes'}")
    print("-" * 60)
    
    for i in range(max_fields):
        v_old = ghost_old['stats'][i] if i < ghost_old['n_fields'] else 0
        v_new = ghost_new['stats'][i] if i < ghost_new['n_fields'] else 0
        
        if v_old != v_new:
            delta = v_new - v_old
            changes.append((i, v_old, v_new, delta))
            print(f"  u16_{i:02d} | {v_old:>8} | {v_new:>8} | {delta:>+8} | *** CHANGED ***")
    
    if not changes:
        print("\nNo differences found! Trying attack saves...")
        
        # Try all files
        for old_file in old_dir.rglob('*.sav'):
            new_file = new_dir / old_file.relative_to(old_dir).replace('autoenhanced', 'auto3')
            if not new_file.exists():
                new_file = new_dir / old_file.relative_to(old_dir)
            
            g_old = extract_ghost(old_file)
            g_new = extract_ghost(new_file) if new_file.exists() else None
            
            if g_old and g_new:
                print(f"\n--- {old_file.name} ---")
                for i in range(max(g_old['n_fields'], g_new['n_fields'])):
                    v_o = g_old['stats'][i] if i < g_old['n_fields'] else 0
                    v_n = g_new['stats'][i] if i < g_new['n_fields'] else 0
                    if v_o != v_n:
                        print(f"  u16_{i:02d}: {v_o} → {v_n}  (delta={v_n-v_o})")
    else:
        print(f"\n=== SUMMARY: {len(changes)} field(s) changed ===")
        for i, v_old, v_new, delta in changes:
            print(f"  u16_{i:02d} ({i*2} bytes): {v_old} → {v_new} (delta {delta})")


if __name__ == "__main__":
    old = pathlib.Path('/home/xsyvps/fft-saves/tactics')
    new = pathlib.Path('/home/xsyvps/fft-saves2/tactics')
    diff_saves(old, new)
