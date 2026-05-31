#!/usr/bin/env python3
"""
IvaliceVera — FFT Save → MultiVera Integration

Loads FFT save files and creates/updates MultiVera projects with:
- Character profiles from FFT lore KB
- Story commits from save file progress
- Party composition from save analysis

Key facts:
- Ramza Beoulve is ALWAYS in the party (protagonist, unique Squire)
- Story characters are inferred from story progress phase
- Player-created characters are detected from marker records in the save
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directories to path for imports
_ivalicevera_dir = Path(__file__).resolve().parent
_multivera_dir = _ivalicevera_dir.parent / "multivera"
sys.path.insert(0, str(_ivalicevera_dir))
sys.path.insert(0, str(_multivera_dir))

from save_parser import parse_save
from lore_kb import load_lore_kb, get_character_profile, get_story_commits


def build_multivera_project(save_path: str) -> dict:
    """
    Parse an FFT save and build a complete MultiVera project.
    
    Returns a dict with project, characters, and commits ready for MultiVera.
    """
    # 1. Parse the save file
    save_data = parse_save(save_path)
    
    # 2. Load FFT lore KB
    kb = load_lore_kb()
    
    # 3. Determine story phase
    phase = save_data['story_progress']['phase']
    chapter = save_data['story_progress'].get('chapter', 1)
    scene = save_data['story_progress'].get('scene', 1)
    
    # 4. Build MultiVera project structure
    project = {
        'name': 'Final Fantasy Tactics',
        'description': 'The Ivalice Chronicles — War of the Lions',
        'universe': 'Ivalice',
        'sources': ['Final Fantasy Tactics (1997)', 'The Ivalice Chronicles (2025)'],
    }
    
    # 5. Build characters from lore KB based on story phase
    party_context = save_data['party_context']
    characters = []
    
    # Always add Ramza (protagonist, always in party)
    ramza = _build_ramza_character(phase, chapter, scene)
    characters.append(ramza)
    
    # Add story characters based on phase
    for char_name in party_context.get('likely_present', []):
        profile = get_character_profile(kb, char_name)
        if profile and 'alias_for' not in profile:
            char = _build_character_from_profile(profile, phase, chapter, scene)
            characters.append(char)
    
    # Add player-created characters from save
    for player_data in save_data['player_characters']:
        player_name = player_data['name'] if isinstance(player_data, dict) else player_data
        player_char = {
            'name': player_name,
            'slug': player_name.lower(),
            'role': 'Player Character',
            'origin': 'Created by the player',
            'personality': ['A custom character created by the player.'],
            'is_player': True,
            'is_active': True,
        }
        characters.append(player_char)
    
    # 6. Build story commits
    commits = get_story_commits(kb, phase, chapter, scene)
    
    return {
        'project': project,
        'characters': characters,
        'commits': commits,
        'save_data': save_data,
    }


def _build_ramza_character(phase: str, chapter: int, scene: int) -> dict:
    """Build Ramza's character profile for the current story phase."""
    
    knows = [
        "He is Ramza Beoulve, third son of House Beoulve",
        "Delita Heiral is his childhood friend",
        "His father Barbaneth was a hero of the Fifty Years' War",
        "He trained at the Royal Military Academy in Gariland",
    ]
    
    does_not_know = [
        "The full extent of the Lucavi demon plot",
        "Cardinal Delacroix's corruption",
        "Dycedarg's betrayal of House Beoulve",
    ]
    
    roleplay = (
        "You are Ramza Beoulve, a young noble squire in the kingdom of Ivalice. "
        "You believe in justice and honor, even when it puts you at odds with your own family. "
        "You have witnessed the corruption of the nobility and the Church firsthand. "
        "Delita is your childhood friend — you trust him deeply, though your paths diverge. "
        "You fight with a sword and have a unique Squire skillset that combines physical and support abilities. "
        "You are diplomatic but firm. You do not back down from what you believe is right."
    )
    
    if phase in ('mid', 'mid_late', 'late'):
        knows.extend([
            "The Corpse Brigade was a peasant revolt caused by post-war poverty",
            "His brother Dycedarg poisoned their father",
            "The Church of Glabados has been corrupted",
        ])
        roleplay += (
            " You have been branded a heretic by the Church. "
            "You carry the weight of House Beoulve's legacy on your shoulders."
        )
    
    return {
        'name': 'Ramza Beoulve',
        'slug': 'ramza',
        'role': 'Protagonist — Noble Squire',
        'affiliation': 'House Beoulve (disowned) / Independent',
        'origin': 'Lesalia, Ivalice',
        'appearance': 'Young man with long blond hair in a low ponytail, brown eyes. Wears armor over a blue tunic.',
        'personality': [
            'Honorable and principled',
            'Diplomatic but firm',
            'Compassionate toward commoners',
            'Willing to act against his own family for justice',
            'Haunted by the violence he has witnessed',
        ],
        'tone': 'Thoughtful, earnest, determined. Speaks with the weight of nobility but the heart of a commoner.',
        'languages': ['Common'],
        'speech_patterns': {
            'description': 'Formal but warm. Uses "thee" and "thou" occasionally when being serious. Direct when angry.',
            'code_switching': None,
            'signature_expressions': [
                'I cannot turn my back on this.',
                'The Beoulve name stands for truth and justice!',
                'There must be another way.',
            ],
            'example_phrases': [
                "Delita... I never wanted things to come to this.",
                "I am a Beoulve. That means something — it has to mean something.",
                "These people didn't choose to be born into poverty. None of us choose the circumstances of our birth.",
            ],
        },
        'relationships': {
            'Delita Heiral': 'Childhood friend, foster brother. Deep bond but growing divergence.',
            'Alma Beoulve': 'Younger sister. Protective of her.',
            'Dycedarg Beoulve': 'Eldest half-brother. Betrayed the family. Hostility.',
            'Agrias Oaks': 'Holy Knight. Initially distrustful, now trusted ally.',
        },
        'weapons_tools': ['Sword', 'Shield', 'Auracite (later)'],
        'backstory_summary': (
            'Third son of Barbaneth Beoulve, hero of the Fifty Years\' War. '
            'Mother was common-born. Witnessed his brother Dycedarg\'s corruption and '
            'chose to desert rather than serve an unjust cause. Now branded a heretic. '
            'Fights to protect the innocent and uncover the truth about Ivalice.'
        ),
        'roleplay_instructions': roleplay,
        'knowledge_gates': {
            'knows': knows,
            'does_not_know': does_not_know,
        },
        'is_player': False,
        'is_active': True,
        'extra': {
            'unique_class': 'Squire (unique skillset, differs from generic Squires)',
            'zodiac': 'Cancer',
        },
    }


def _build_character_from_profile(profile: dict, phase: str, chapter: int, scene: int) -> dict:
    """Build a MultiVera character from a lore KB profile."""
    return {
        'name': profile['name'],
        'slug': profile['name'].lower().replace(' ', '_'),
        'role': profile.get('role', 'Supporting Character'),
        'affiliation': profile.get('affiliation', 'Unknown'),
        'origin': profile.get('origin', 'Ivalice'),
        'appearance': profile.get('appearance', ''),
        'personality': profile.get('personality', []),
        'tone': profile.get('tone', ''),
        'languages': profile.get('languages', ['Common']),
        'speech_patterns': profile.get('speech_patterns', {}),
        'relationships': profile.get('relationships', {}),
        'weapons_tools': profile.get('weapons_tools', []),
        'backstory_summary': profile.get('backstory_summary', ''),
        'roleplay_instructions': profile.get('roleplay_instructions', ''),
        'knowledge_gates': profile.get('knowledge_gates', {'knows': [], 'does_not_know': []}),
        'is_player': False,
        'is_active': True,
        'extra': profile.get('extra', {}),
    }


def create_project_from_save(save_path: str, output_dir: str = None) -> dict:
    """
    Create a full MultiVera project from an FFT save file.
    Outputs JSON files compatible with MultiVera's import format.
    """
    data = build_multivera_project(save_path)
    _output_json(data, output_dir or '.')
    return data


def _output_json(data: dict, output_dir: str):
    """Output project data as JSON files compatible with MultiVera."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # Project
    with open(out / 'project.json', 'w') as f:
        json.dump(data['project'], f, indent=2, ensure_ascii=False)
    
    # Characters
    char_dir = out / 'characters'
    char_dir.mkdir(exist_ok=True)
    for char in data['characters']:
        slug = char['slug']
        with open(char_dir / f'{slug}.json', 'w') as f:
            json.dump(char, f, indent=2, ensure_ascii=False)
    
    # Commits
    commit_dir = out / 'commits'
    commit_dir.mkdir(exist_ok=True)
    for commit in data['commits']:
        commit_id = commit['commit_id']
        with open(commit_dir / f'{commit_id}.json', 'w') as f:
            json.dump(commit, f, indent=2, ensure_ascii=False)
    
    # Full report
    with open(out / 'save_analysis.json', 'w') as f:
        save_data = {k: v for k, v in data['save_data'].items() 
                    if isinstance(v, (dict, list, str, int, float, bool)) or v is None}
        json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Project output to {out}/")
    print(f"  Characters: {len(data['characters'])}")
    print(f"  Commits: {len(data['commits'])}")
    for char in data['characters']:
        print(f"    - {char['name']} ({char.get('role', '')})")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build MultiVera project from FFT save file')
    parser.add_argument('save_file', help='Path to FFT save file')
    parser.add_argument('--output', '-o', default='output', help='Output directory')
    args = parser.parse_args()
    
    result = create_project_from_save(args.save_file, args.output)
    print(f"\nStory phase: {result['save_data']['party_context']['story_phase']}")
    print(f"Player characters: {', '.join(result['save_data']['player_characters']) or 'None'}")
    print(f"Full party: {', '.join(result['save_data']['party_context']['full_party_estimate'])}")
