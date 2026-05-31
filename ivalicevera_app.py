#!/usr/bin/env python3
"""
IvaliceVera Backend — FastAPI server extending MultiVera for FFT save file integration.

Provides:
- Save file upload and parsing
- Automatic project/character/commit creation from save data
- Character chat with story-locked knowledge gating
- FFT lore RAG

Usage:
    python backend.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ── Paths ────────────────────────────────────────────────────────────────────
IVALICEVERA_DIR = Path(__file__).resolve().parent
MULTIVERA_DIR = IVALICEVERA_DIR.parent / "multivera"
sys.path.insert(0, str(IVALICEVERA_DIR))
sys.path.insert(0, str(MULTIVERA_DIR))

# ── MultiVera imports ────────────────────────────────────────────────────────
from backend.database import Base, get_db as mv_get_db
from backend.models import Project, Character, Commit, Conversation
from backend.schemas import (
    ProjectCreate, ProjectOut,
    CharacterCreate, CharacterOut,
    CommitCreate, CommitOut,
    ChatRequest, ChatResponse, ConversationMessage,
)
from backend.routers import projects, characters, commits, chat, ingestion, export as export_router

# ── IvaliceVera imports ──────────────────────────────────────────────────────
from save_parser import parse_save
from lore_kb import load_lore_kb, get_character_profile, get_story_commits
from multivera_integration import build_multivera_project

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = IVALICEVERA_DIR / "ivalicevera.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)

# Create tables
Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="IvaliceVera",
    description="Final Fantasy Tactics save analyzer & character chat",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include MultiVera routers ────────────────────────────────────────────────
app.include_router(projects.router, prefix="/api")
app.include_router(characters.router, prefix="/api")
app.include_router(commits.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(export_router.router, prefix="/api")


# ── FFT Save Upload & Parse ──────────────────────────────────────────────────

@app.post("/api/save/upload")
async def upload_save(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload an FFT save file (.png, .sav, or .bin).
    
    Parses the save and returns extracted data:
    - Story progress (chapter/scene)
    - Party members (story + player characters)
    - Save metadata
    """
    # Save uploaded file to temp
    suffix = Path(file.filename or "save.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse the save
        result = parse_save(tmp_path)
        
        return {
            "success": True,
            "filename": file.filename,
            "file_size": len(content),
            "story_progress": result.get("story_progress"),
            "player_characters": result.get("player_characters", []),
            "party_context": result.get("party_context"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse save: {str(e)}")
    finally:
        os.unlink(tmp_path)


@app.post("/api/save/create-project")
async def create_project_from_save(
    file: UploadFile = File(...),
    project_name: str = Form("Final Fantasy Tactics"),
    db: Session = Depends(get_db),
):
    """
    Upload an FFT save file and automatically create a MultiVera project
    with characters and story commits.
    """
    # Save uploaded file to temp
    suffix = Path(file.filename or "save.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Build the MultiVera project from save data
        data = build_multivera_project(tmp_path)
        
        # 1. Create project in database
        project = Project(
            name=project_name,
            description=data["project"]["description"],
            sources=data["project"]["sources"],
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # 2. Create characters
        char_map = {}  # slug -> id
        for char_data in data["characters"]:
            char = Character(
                project_id=project.id,
                slug=char_data["slug"],
                name=char_data["name"],
                role=char_data.get("role"),
                affiliation=char_data.get("affiliation"),
                origin=char_data.get("origin"),
                appearance=char_data.get("appearance"),
                personality=char_data.get("personality", []),
                tone=char_data.get("tone"),
                languages=char_data.get("languages", []),
                speech_patterns=char_data.get("speech_patterns", {}),
                relationships=char_data.get("relationships", {}),
                notable_quotes=char_data.get("notable_quotes", []),
                weapons_tools=char_data.get("weapons_tools", []),
                backstory_summary=char_data.get("backstory_summary"),
                roleplay_instructions=char_data.get("roleplay_instructions"),
                knowledge_gates=char_data.get("knowledge_gates", {}),
                is_player=char_data.get("is_player", False),
                is_active=char_data.get("is_active", True),
                extra=char_data.get("extra", {}),
            )
            db.add(char)
            db.commit()
            db.refresh(char)
            char_map[char.slug] = char.id
        
        # 3. Create commits
        for commit_data in data["commits"]:
            # Find the character for this commit (default to Ramza)
            char_slug = commit_data.get("character_slug", "ramza")
            char_id = char_map.get(char_slug)
            
            commit = Commit(
                project_id=project.id,
                character_id=char_id,
                commit_id=commit_data["commit_id"],
                title=commit_data.get("title"),
                location=commit_data.get("location"),
                situation=commit_data.get("situation"),
                knows=commit_data.get("knows", []),
                does_not_know=commit_data.get("does_not_know", []),
                chapter=commit_data.get("chapter"),
                scene=commit_data.get("scene"),
                order_index=commit_data.get("order_index", 0),
                is_start=commit_data.get("is_start", False),
                is_end=commit_data.get("is_end", False),
                extra=commit_data.get("extra", {}),
            )
            db.add(commit)
        
        db.commit()
        
        return {
            "success": True,
            "project_id": project.id,
            "project_name": project.name,
            "characters_created": len(char_map),
            "commits_created": len(data["commits"]),
            "character_slugs": list(char_map.keys()),
            "story_phase": data["save_data"]["story_progress"]["phase"],
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")
    finally:
        os.unlink(tmp_path)


# ── FFT Lore KB Endpoint ─────────────────────────────────────────────────────

@app.get("/api/lore/characters")
def list_lore_characters():
    """List all characters in the FFT lore KB."""
    kb = load_lore_kb()
    chars = []
    for name, profile in kb.get("characters", {}).items():
        if "alias_for" not in profile:
            chars.append({
                "name": profile["name"],
                "slug": profile["name"].lower().replace(" ", "_"),
                "role": profile.get("role", ""),
                "affiliation": profile.get("affiliation", ""),
            })
    return {"characters": chars}


@app.get("/api/lore/characters/{slug}")
def get_lore_character(slug: str):
    """Get a specific character's full profile from the lore KB."""
    kb = load_lore_kb()
    profile = get_character_profile(kb, slug.replace("_", " "))
    if not profile or "alias_for" in profile:
        raise HTTPException(status_code=404, detail="Character not found")
    return profile


@app.get("/api/lore/commits")
def list_lore_commits(phase: Optional[str] = None):
    """List story commits from the lore KB, optionally filtered by phase."""
    kb = load_lore_kb()
    commits = kb.get("commits", [])
    if phase:
        commits = [c for c in commits if c.get("phase") == phase]
    return {"commits": commits}


# ── Health Check ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ivalicevera"}


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8787))
    print(f"Starting IvaliceVera on port {port}")
    print(f"API docs: http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
