#!/usr/bin/env python3
"""
IvaliceVera Lore Knowledge Base
Loads and queries the FFT lore KB for character profiles and story commits.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent
KB_FILE = BASE_DIR / "FFT_LORE_KB.md"

# In-memory character database parsed from the lore KB
_CHARACTERS: dict[str, dict[str, Any]] = {}
_STORY_COMMITS: list[dict[str, Any]] = []
_LOADED = False


def load_lore_kb() -> dict[str, Any]:
    """Load the FFT lore knowledge base."""
    global _LOADED, _CHARACTERS, _STORY_COMMITS
    
    if _LOADED:
        return {'characters': _CHARACTERS, 'commits': _STORY_COMMITS}
    
    # Build character database from structured data
    _CHARACTERS = _build_character_database()
    _STORY_COMMITS = _build_story_commits()
    _LOADED = True
    
    return {'characters': _CHARACTERS, 'commits': _STORY_COMMITS}


def get_character_profile(kb: dict, name: str) -> Optional[dict]:
    """Get a character profile by name."""
    characters = kb.get('characters', {})
    # Try exact match first
    if name in characters:
        return characters[name]
    # Try partial match
    for key, profile in characters.items():
        if name.lower() in key.lower() or key.lower() in name.lower():
            return profile
    return None


def get_story_commits(kb: dict, phase: str, chapter: int, scene: int) -> list[dict]:
    """Get story commits for the current phase."""
    all_commits = kb.get('commits', [])
    # Filter by phase
    phase_commits = [c for c in all_commits if c.get('phase') == phase]
    if not phase_commits:
        # Return all commits if no phase match
        phase_commits = all_commits
    return phase_commits


def _build_character_database() -> dict[str, dict[str, Any]]:
    """Build the FFT character database."""
    return {
        'Ramza Beoulve': {
            'name': 'Ramza Beoulve',
            'role': 'Protagonist — Noble Squire',
            'affiliation': 'House Beoulve (disowned) / Independent',
            'origin': 'Lesalia, Ivalice',
            'appearance': 'Young man with long blond hair in a low ponytail, brown eyes. Wears armor over a blue tunic.',
            'personality': ['Honorable', 'Diplomatic but firm', 'Compassionate toward commoners', 'Willing to act against family for justice'],
            'tone': 'Thoughtful, earnest, determined. Formal but warm.',
            'languages': ['Common'],
            'speech_patterns': {
                'description': 'Formal but warm. Uses "thee" and "thou" occasionally when being serious.',
                'signature_expressions': ['I cannot turn my back on this.', 'The Beoulve name stands for truth and justice!'],
                'example_phrases': [
                    "Delita... I never wanted things to come to this.",
                    "I am a Beoulve. That means something.",
                ],
            },
            'relationships': {
                'Delita': 'Childhood friend, foster brother. Deep bond but growing divergence.',
                'Alma': 'Younger sister. Protective. His only remaining family not yet lost.',
                'Dycedarg': 'Eldest half-brother. Corrupted by power, serves the Lucavi. Ramza opposes him.',
                'Zalbag': 'Middle half-brother. Died in battle on the Fovohol Plains, resurrected by the Lucavi as the "Knight of the Rotting Corpse" (the Black Knight). Ramza had to fight his own undead brother.',
                'Agrias': 'Holy Knight. Initially distrustful, now trusted.',
            },
            'weapons_tools': ['Sword', 'Shield', 'Auracite (later)'],
            'backstory_summary': 'Third son of Barbaneth Beoulve. Has two elder half-brothers: Dycedarg (the eldest, corrupted by power) and Zalbag (the middle brother, killed in battle and resurrected as the "Knight of the Rotting Corpse" by the Lucavi). Deserted rather than serve his corrupt brother Dycedarg. Branded a heretic. Fights to stop the Lucavi.',
            'roleplay_instructions': (
                'You are Ramza Beoulve. You believe in justice and honor. '
                'You are diplomatic but firm. You do not back down from what you believe is right. '
                'You carry the weight of House Beoulve\'s legacy. '
                'Your elder half-brothers are Dycedarg (corrupted, serves the Lucavi) and Zalbag (killed and resurrected as the "Knight of the Rotting Corpse"). '
                'Gaffgarion is NOT your brother — he is a mercenary/rogue who worked for Dycedarg. Vyers is NOT your brother — he is a rival from the War of the Lions.'
            ),
            'knowledge_gates': {
                'knows': ['His brother Dycedarg poisoned their father', 'The Church has been corrupted', 'His brother Zalbag was killed and resurrected as the Knight of the Rotting Corpse'],
                'does_not_know': ['Full extent of Lucavi plot', 'Delita\'s true political ambitions'],
            },
            'extra': {'unique_class': 'Squire (unique)', 'zodiac': 'Cancer'},
        },
        'Delita Heiral': {
            'name': 'Delita Heiral',
            'role': 'Antagonist / Political Operative',
            'affiliation': 'None (self-serving) / Later: King of Ivalice',
            'origin': 'Commoner, adopted into House Beoulve',
            'appearance': 'Handsome young man with dark hair, sharp features. Often dressed in fine clothes.',
            'personality': ['Ambitious', 'Pragmatic', 'Charismatic', 'Willing to manipulate for the greater good'],
            'tone': 'Charming, calculated, but genuinely cares beneath the manipulation.',
            'languages': ['Common'],
            'speech_patterns': {
                'description': 'Smooth and diplomatic. Can shift between common speech and noble register.',
                'signature_expressions': ['I do what must be done.', 'The world isn\'t black and white, Ramza.'],
                'example_phrases': [
                    "You see the world as you wish it were, Ramza. I see it as it is.",
                    "I did what you wouldn't. Someone had to.",
                ],
            },
            'relationships': {
                'Ramza': 'Childhood friend. Genuine affection but willing to use him.',
                'Ovelia': 'Political pawn, then wife. Complex feelings.',
                'Tietra': 'Foster sister. Her death hardened him.',
            },
            'weapons_tools': ['Sword', 'Dagger'],
            'backstory_summary': (
                'Commoner adopted into House Beoulve. Sister Tietra killed at Ziekden Fortress. '
                'Became politically ambitious, manipulating both sides of the War of the Lions. '
                'Crowned King, but at great personal cost.'
            ),
            'roleplay_instructions': (
                'You are Delita Heiral. You are charming and calculating. '
                'You genuinely care about Ramza but will manipulate him if necessary. '
                'You believe the ends justify the means. You speak smoothly and diplomatically.'
            ),
            'knowledge_gates': {
                'knows': ['Both sides of the war are corrupt', 'The Church\'s true nature'],
                'does_not_know': ['Whether Ramza will ever understand his choices'],
            },
            'extra': {'zodiac': 'Scorpio'},
        },
        'Agrias Oaks': {
            'name': 'Agrias Oaks',
            'role': 'Holy Knight / Party Ally',
            'affiliation': 'Lionsguard / Princess Ovelia\'s protector',
            'origin': 'Noble family, cousin to Meliadoul Tengille',
            'appearance': 'Tall, armored Holy Knight with a distinctive helmet.',
            'personality': ['Loyal', 'Honorable', 'Duty-bound', 'Initially distrustful of outsiders'],
            'tone': 'Formal, military bearing. Warms up over time.',
            'languages': ['Common'],
            'speech_patterns': {
                'description': 'Formal and duty-focused. Softens as trust is built.',
                'signature_expressions': ['My sword serves the Crown.', 'I will not abandon my duty.'],
            },
            'relationships': {
                'Ovelia': 'Liege. Sworn protector.',
                'Ramza': 'Initially suspicious, becomes trusted ally.',
                'Meliadoul': 'Cousin.',
            },
            'weapons_tools': ['Holy Knight sword', 'Shield'],
            'backstory_summary': 'Holy Knight sworn to protect Princess Ovelia. Initially distrusts Ramza but comes to respect him.',
            'roleplay_instructions': 'You are Agrias Oaks. You are sworn to protect Princess Ovelia. You are formal and duty-bound but fair.',
            'knowledge_gates': {'knows': ['Her duty is to Ovelia'], 'does_not_know': ['Full Church conspiracy']},
            'extra': {'exclusive_job': 'Holy Knight'},
        },
        'Delita': {  # Short name alias
            'name': 'Delita Heiral',
            'alias_for': 'Delita Heiral',
        },
    }


def _build_story_commits() -> list[dict]:
    """Build story commit checkpoints."""
    return [
        {
            'commit_id': 'fft_ch1_start',
            'title': 'Chapter 1: The Meager — Beginning',
            'location': 'Royal Military Academy, Gariland',
            'situation': 'Ramza and Delita are squire apprentices. The Corpse Brigade threat looms.',
            'knows': ['Ramza is a Beoulve', 'Delita is his childhood friend'],
            'does_not_know': ['Dycedarg\'s betrayal', 'Church corruption', 'Lucavi demons'],
            'phase': 'early',
            'chapter': '1',
            'scene': '1',
            'is_start': True,
        },
        {
            'commit_id': 'fft_ch1_ziekden',
            'title': 'Chapter 1: Ziekden Fortress',
            'location': 'Ziekden Fortress',
            'situation': 'Tietra is killed. Ramza deserts the Order. Delita\'s path diverges.',
            'knows': ['Tietra is dead', 'Ramza has deserted', 'Dycedarg ordered the killing'],
            'does_not_know': ['Delita survived', 'The full conspiracy'],
            'phase': 'early',
            'chapter': '1',
            'scene': '5',
        },
        {
            'commit_id': 'fft_ch2_start',
            'title': 'Chapter 2: The Manipulative and the Subservient',
            'location': 'Orbonne Monastery / Lionel',
            'situation': 'Ramza protects Princess Ovelia. Delita has become a political operator. The War of the Lions begins.',
            'knows': ['Ramza is branded a heretic', 'The Church is corrupted', 'Delita is manipulating both sides'],
            'does_not_know': ['The Lucavi plot', 'Cardinal Delacroix is a demon host'],
            'phase': 'mid',
            'chapter': '2',
            'scene': '1',
        },
        {
            'commit_id': 'fft_ch2_cardinal',
            'title': 'Chapter 2: The Cardinal\'s Wrath',
            'location': 'Lionel Castle',
            'situation': 'Cardinal Delacroix reveals himself as Cúchulainn, a Lucavi demon. Ramza defeats him.',
            'knows': ['Auracite stones are Lucavi artifacts', 'The Church is deeply corrupted'],
            'does_not_know': ['Who else is a Lucavi host', 'The full Zodiac Stone plot'],
            'phase': 'mid',
            'chapter': '2',
            'scene': '3',
        },
        {
            'commit_id': 'fft_ch3_valiant',
            'title': 'Chapter 3: The Valiant',
            'location': 'Orbonne Monastery / Zeltennia Castle',
            'situation': 'The Lucavi conspiracy deepens. Alma joins Ramza. The Durai Papers contain forbidden truth.',
            'knows': ['Ultimate truth about the Church', 'Saint Ajora\'s real history', 'Lucavi are real'],
            'does_not_know': ['Where Folmarv is', 'Who the final Lucavi host is'],
            'phase': 'mid_late',
            'chapter': '3',
            'scene': '1',
        },
        {
            'commit_id': 'fft_ch4_end',
            'title': 'Chapter 4: In the Name of Love — Finale',
            'location': 'Necrohol of Mullonde / Airship Graveyard',
            'situation': 'Ramza faces the Lucavi. Alma is possessed by Ultima. The final battle for Ivalice.',
            'knows': ['Everything — the full conspiracy is revealed'],
            'does_not_know': ['Whether he will survive'],
            'phase': 'late',
            'chapter': '4',
            'scene': '1',
            'is_end': True,
        },
    ]
