#!/usr/bin/env python3
"""
FFT Save Parser v2 — End-to-end save file analyzer
Extracts party members, story progress, and game state from FFT PC Remaster save files.

Key facts:
- Ramza Beoulve is ALWAYS in the party (protagonist, unique Squire)
- Story characters (Delita, Agrias, etc.) are present based on story progress
- Player-created characters are stored by name in marker records
- Story progress is at offset 0x38-0x39 in the 40KB main save files
"""
import struct
import os
from pathlib import Path


# ═══════════════════════════════════════════════════════════
# Story character roster — who's available at each story phase
# ═══════════════════════════════════════════════════════════

STORY_PHASE_CHARACTERS = {
    'early': {
        'always_present': ['Ramza Beoulve'],
        'likely_present': ['Delita Heiral'],
        'description': 'Early game — just after character creation. Ramza and Delita are childhood friends.',
        'context': 'The game has just begun. Ramza is a young noble squire. Delita is his commoner foster brother.',
        'available_jobs': {
            'Ramza': ['Squire'],  # Unique Squire skillset
            'Delita': ['Squire'],
        }
    },
    'mid_early': {
        'always_present': ['Ramza Beoulve'],
        'likely_present': ['Delita Heiral', 'Agrias Oaks'],
        'description': 'Corpse Brigade arc — Ramza deserts the Order, meets Agrias.',
        'context': 'Ramza has witnessed corruption in his family and the Church. Agrias is protecting Princess Ovelia.',
        'available_jobs': {
            'Ramza': ['Squire', 'Knight', 'Archer', 'Monk', 'Thief'],
            'Delita': ['Squire', 'Knight'],
            'Agrias': ['Holy Knight'],  # Exclusive job
        }
    },
    'mid': {
        'always_present': ['Ramza Beoulve', 'Agrias Oaks'],
        'likely_present': ['Mustadio Bunansa', 'Rapha Galthena', 'Marach Galthena', 'Delita Heiral'],
        'description': 'War of the Lions — political intrigue and growing party.',
        'context': 'The civil war has begun. Ramza is branded a heretic. The party grows with allies from all walks of life.',
        'available_jobs': {
            'Ramza': ['Squire', 'Knight', 'Archer', 'Monk', 'Thief', 'Dragoon', 'Samurai', 'Ninja'],
            'Agrias': ['Holy Knight'],
            'Mustadio': ['Machinist'],
            'Rapha': ['Black Mage', 'Wizard'],
            'Marach': ['White Mage', 'Priest'],
            'Delita': ['Squire', 'Knight', 'Archer'],
        }
    },
    'mid_late': {
        'always_present': ['Ramza Beoulve', 'Agrias Oaks', 'Count Cidolfus Orlandeau'],
        'likely_present': ['Mustadio Bunansa', 'Rapha Galthena', 'Marach Galthena', 
                          'Meliadoul Tengille', 'Delita Heiral'],
        'description': 'Lucavi conspiracy deepens — Thunder God joins the cause.',
        'context': 'The true threat of the Lucavi demons is becoming clear. Count Orlandeau has joined Ramza\'s side.',
        'available_jobs': {
            'Ramza': ['Squire', 'Knight', 'Archer', 'Monk', 'Thief', 'Dragoon', 'Samurai', 'Ninja', 'Dancer', 'Chemist'],
            'Agrias': ['Holy Knight', 'Knight', 'Squire'],
            'Orlandeau': ['Knight', 'Squire'],
            'Meliadoul': ['Templar', 'Knight'],
            'Mustadio': ['Machinist'],
            'Rapha': ['Black Mage', 'Wizard', 'Time Mage', 'Summoner'],
            'Marach': ['White Mage', 'Priest', 'Black Mage'],
            'Delita': ['Squire', 'Knight', 'Archer', 'Thief'],
        }
    },
    'late': {
        'always_present': ['Ramza Beoulve', 'Alma Beoulve'],
        'likely_present': ['Agrias Oaks', 'Mustadio Bunansa', 'Rapha Galthena', 'Marach Galthena',
                          'Count Cidolfus Orlandeau', 'Meliadoul Tengille'],
        'description': 'Endgame — the final confrontation with the Lucavi.',
        'context': 'The fate of Ivalice hangs in the balance. Ramza faces the Lucavi and his possessed loved ones.',
        'available_jobs': {
            'Ramza': ['Squire', 'Knight', 'Archer', 'Monk', 'Thief', 'Dragoon', 'Samurai', 'Ninja', 
                     'Dancer', 'Chemist', 'Geomancer'],
            'Agrias': ['Holy Knight', 'Knight'],
            'Orlandeau': ['Knight', 'Holy Knight'],
            'Meliadoul': ['Templar', 'Divine Knight'],
            'Alma': ['Squire'],  # Young, similar to Ramza's starting class
        }
    }
}


# ═══════════════════════════════════════════════════════════
# Story progress mapping
# ═══════════════════════════════════════════════════════════

STORY_PROGRESS_MAP = {
    (0x10, 0x09): 'early',        # Just after character creation
    (0x15, 0x18): 'mid',          # War of the Lions has begun
    # TODO: Add more mappings as we get saves from other story points
}


def parse_save(filepath):
    """
    Parse an FFT save file and extract key information.
    
    Works with:
    - 2MB fftsave.bin (complete archive, all party data, extended region)
    - 40KB resume_*_main.sav (game state, story progress, character presence)
    - 1MB+ resume_enbtl_main.sav (battle state, current fight data)
    """
    data = Path(filepath).read_bytes()
    
    result = {
        'filepath': str(filepath),
        'size': len(data),
        'file_type': _detect_file_type(data),
    }
    
    # Extract based on file type
    if result['file_type'] == 'main_save':
        result['story_progress'] = _extract_story_progress(data)
    elif result['file_type'] == 'fftsave_archive':
        # 2MB archive: story progress is NOT at 0x38 (that's Shift-JIS text)
        # We'd need to find it in a different section, or skip it
        result['story_progress'] = {
            'raw_38': data[0x38], 'raw_39': data[0x39],
            'phase': 'unknown', 'note': '2MB archive — use 40KB main saves for story progress',
            'phase_info': {}, 'battle_state': 0, 'checkpoint': 0,
        }
    else:
        result['story_progress'] = None
    
    result['player_characters'] = _extract_player_characters(data)
    result['party_context'] = _determine_party_context(result)
    
    return result


def _detect_file_type(data):
    """Detect what kind of save file this is."""
    if len(data) < 0x50:
        return 'unknown'
    
    # Check for FFTI magic at offset 0x10 (main saves and battle saves)
    magic = data[0x10:0x14]
    if magic == b'FFTI':
        if len(data) == 40516:
            return 'main_save'  # 40KB game state
        else:
            return 'battle_save'  # 1MB+ battle state
    
    # Check for SC magic at offset 0x10 (2MB fftsave archive)
    if magic[:2] == b'SC' and len(data) > 1000000:
        return 'fftsave_archive'
    
    return 'unknown'


def _extract_story_progress(data):
    """Extract story progress from save header."""
    b38, b39 = data[0x38], data[0x39]
    b3b, b3c = data[0x3b], data[0x3c]
    
    # Look up the phase
    phase_key = (b38, b39)
    phase = STORY_PROGRESS_MAP.get(phase_key, 'unknown')
    
    return {
        'raw_38': b38,
        'raw_39': b39,
        'battle_state': b3b,
        'checkpoint': b3c,
        'phase': phase,
        'phase_info': STORY_PHASE_CHARACTERS.get(phase, {}),
    }


def _extract_player_characters(data):
    """
    Extract player-created characters from marker records.
    Each marker: [XX YY] [0x11×7] [tail] [92-byte stat block] [name\0]
    
    Returns list of dicts with name, stats, encoding type.
    """
    characters = []
    seen_names = set()
    
    for i in range(min(len(data) - 140, 0x45000)):
        if data[i+2:i+9] != b'\x11\x11\x11\x11\x11\x11\x11':
            continue
        
        tail = data[i+9:i+12]
        if tail not in [b'\x01\x01\x00', b'\x10\x11\x00']:
            continue
        
        name_start = i + 12 + 92
        name_end = data.find(b'\x00', name_start, min(name_start + 30, len(data)))
        
        if name_end <= name_start:
            continue
        
        try:
            name = data[name_start:name_end].decode('ascii')
            if len(name) < 2 or name in seen_names:
                continue
            seen_names.add(name)
            
            # Extract stats (first 6 u16 values)
            raw_hp = struct.unpack_from('<H', data, i + 12)[0]
            raw_mp = struct.unpack_from('<H', data, i + 14)[0]
            
            # Decode NEW encoding (values shifted << 8)
            if tail == b'\x10\x11\x00':
                hp = raw_hp >> 8
                mp = raw_mp >> 8
                encoding = 'NEW'
            else:
                hp = raw_hp
                mp = raw_mp
                encoding = 'STANDARD'
            
            characters.append({
                'name': name,
                'offset': i,
                'hp': hp,
                'mp': mp,
                'encoding': encoding,
                'marker_id': f'{data[i]:02x}{data[i+1]:02x}',
            })
        except (UnicodeDecodeError, struct.error):
            pass
    
    return characters


def _determine_party_context(result):
    """
    Determine the full party context including story characters.
    Story characters are inferred from story progress since they're
    referenced by ID in the save, not by name.
    """
    chars = result.get('player_characters', [])
    progress = result.get('story_progress', {})
    
    if progress and progress.get('phase'):
        phase = progress['phase']
        phase_info = STORY_PHASE_CHARACTERS.get(phase, {})
    else:
        phase = 'unknown'
        phase_info = {}
    
    return {
        'story_phase': phase,
        'phase_description': phase_info.get('description', 'Unknown'),
        'phase_context': phase_info.get('context', ''),
        'always_present': phase_info.get('always_present', []),
        'likely_present': phase_info.get('likely_present', []),
        'player_characters': [c['name'] for c in chars],
        'full_party_estimate': (
            phase_info.get('always_present', []) + 
            [c['name'] for c in chars]
        ),
    }


def format_report(result):
    """Format parse results into a human-readable report."""
    ctx = result['party_context']
    lines = [
        "═" * 60,
        f"  FFT Save Analysis Report",
        "═" * 60,
        f"  File: {result['filepath']}",
        f"  Size: {result['size']:,} bytes",
        f"  Type: {result['file_type']}",
        "",
    ]
    
    if result.get('story_progress'):
        sp = result['story_progress']
        lines += [
            f"  Story Progress:",
            f"    Phase: {sp.get('phase', 'unknown')}",
        ]
        if 'raw_38' in sp:
            lines.append(f"    Raw: 0x{sp['raw_38']:02x}, 0x{sp['raw_39']:02x}")
        if sp.get('note'):
            lines.append(f"    Note: {sp['note']}")
        if sp.get('phase_info'):
            lines.append(f"    Description: {sp['phase_info'].get('description', 'Unknown')}")
        lines.append("")
    
    lines += [
        f"  Party Context:",
        f"    Always Present (story): {', '.join(ctx['always_present']) or 'N/A'}",
        f"    Likely Present (story): {', '.join(ctx['likely_present']) or 'N/A'}",
        f"    Player Characters: {', '.join(ctx['player_characters']) or 'None'}",
        f"    Full Party Estimate: {', '.join(ctx['full_party_estimate']) or 'N/A'}",
        "",
        f"  Context: {ctx['phase_context']}" if ctx['phase_context'] else "",
        "═" * 60,
    ]
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    
    paths = [Path(p) for p in sys.argv[1:]] if len(sys.argv) > 1 else []
    
    if not paths:
        # Auto-detect save files
        base = Path('/home/xsyvps')
        # Check the best main save from each unique game state
        checked = set()
        for savedir in sorted(base.glob('fft-saves*')):
            if not savedir.is_dir():
                continue
            for f in savedir.rglob('resume_en00_main.sav'):
                data = f.read_bytes()
                if len(data) == 40516:
                    key = (data[0x38], data[0x39])
                    if key not in checked:
                        checked.add(key)
                        paths.append(f)
                    break
        
        # Also add the fftsave archives
        for f in sorted(base.glob('fft-saves*/**/fftsave.bin')):
            paths.append(f)
    
    for p in paths:
        try:
            result = parse_save(p)
            print(format_report(result))
            print()
        except Exception as e:
            print(f"Error parsing {p}: {e}")
            import traceback
            traceback.print_exc()
