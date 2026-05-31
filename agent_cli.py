#!/usr/bin/env python3
"""
IvaliceVera Agent CLI — test and use the app directly from the terminal.

Usage:
    python agent_cli.py test-all          # Run full test suite
    python agent_cli.py parse <file>      # Parse a save file
    python agent_cli.py upload <file>     # Upload + parse via API
    python agent_cli.py create-project <file>  # Full pipeline: save → project
    python agent_cli.py list-projects      # List all projects
    python agent_cli.py chat <project_id> <char_slug> <message>
    python agent_cli.py characters <project_id>
    python agent_cli.py lore <slug>
    python agent_cli.py projects
    python agent_cli.py status            # Full system status
"""
import sys
import json
import urllib.request
import urllib.error
import os
from pathlib import Path

BASE = os.environ.get("IVALICEVERA_URL", "http://localhost:8787")

def api(method, path, data=None, files=None):
    """Make an API call and return parsed JSON."""
    url = f"{BASE}{path}"
    try:
        if files:
            # Multipart upload
            boundary = "----IvB0und4ry"
            body = b""
            for key, (filename, content, ctype) in files.items():
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode()
                body += f"Content-Type: {ctype}\r\n\r\n".encode()
                body += content
                body += b"\r\n"
            body += f"--{boundary}--\r\n".encode()
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        elif data:
            req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                         method=method, headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(url, method=method)

        resp = urllib.request.urlopen(req, timeout=60)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": True, "status": e.code, "detail": body}
    except Exception as e:
        return {"error": True, "detail": str(e)}


def status():
    """Full system status check."""
    print("═══ IvaliceVera System Status ═══\n")

    h = api("GET", "/api/health")
    print(f"Backend:     {'✅ ' + h.get('status', '?') if 'error' not in h else '❌ ' + h.get('detail', '?')}")

    try:
        resp = urllib.request.urlopen(f"{BASE}/", timeout=5)
        print(f"Frontend:    ✅ Serving ({len(resp.read())} bytes)")
    except Exception as e:
        print(f"Frontend:    ❌ {e}")

    chars = api("GET", "/api/lore/characters")
    print(f"Lore KB:     ✅ {len(chars.get('characters', []))} characters" if "error" not in chars else f"Lore KB:     ❌ {chars.get('detail')}")

    projects = api("GET", "/api/projects")
    print(f"Projects:    {'✅ ' + str(len(projects)) + ' projects' if isinstance(projects, list) else '❌ ' + str(projects)}")

    # Check Ollama
    ollama = api("GET", "/api/chat/health")
    if "error" not in ollama and ollama.get("success"):
        models = ollama.get("data", {}).get("available_models", [])
        print(f"Ollama:      ✅ {ollama.get('data', {}).get('default_model', '?')} ({len(models)} models)")
    else:
        print(f"Ollama:      ⚠️  Unavailable ({ollama.get('message', ollama.get('detail', '?'))})")

    return h, chars, projects, ollama


def parse_save(filepath):
    """Parse a save file directly (no API needed)."""
    sys.path.insert(0, str(Path(__file__).parent))
    from save_parser import parse_save, format_report
    result = parse_save(filepath)
    print(format_report(result))
    return result


def upload_save(filepath):
    """Upload a save file to the API."""
    with open(filepath, "rb") as f:
        data = f.read()
    result = api("POST", "/api/save/upload", files={
        "file": (os.path.basename(filepath), data, "application/octet-stream")
    })
    print(json.dumps(result, indent=2))
    return result


def create_project(filepath, name=None):
    """Full pipeline: upload save → create project with characters + commits."""
    with open(filepath, "rb") as f:
        data = f.read()
    filename = os.path.basename(filepath)
    if not name:
        name = f"FFT — {filename}"

    result = api("POST", "/api/save/create-project", files={
        "file": (filename, data, "application/octet-stream"),
        "project_name": (None, name, "text/plain"),
    })
    # The form field needs to be multipart too
    # Let me redo this properly
    boundary = "----IvB0und4ry"
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
    ).encode() + data + (
        f'\r\n--{boundary}\r\n'
        f'Content-Disposition: form-data; name="project_name"\r\n\r\n'
        f'{name}\r\n'
        f'--{boundary}--\r\n'
    ).encode()

    url = f"{BASE}/api/save/create-project"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2))
    return result


def list_projects():
    """List all projects."""
    projects = api("GET", "/api/projects")
    if isinstance(projects, list):
        for p in projects:
            print(f"  [{p['id']}] {p['name']} — {p.get('description', '')[:60]}")
            print(f"       chars: {p.get('character_count', '?')}, commits: {p.get('commit_count', '?')}, sources: {len(p.get('sources', []))}")
    else:
        print(projects)
    return projects


def list_characters(project_id):
    """List characters in a project."""
    chars = api("GET", f"/api/projects/{project_id}/characters")
    if isinstance(chars, list):
        for c in chars:
            print(f"  [{c['id']}] {c['name']} ({c['slug']}) — {c.get('role', '')}")
    else:
        print(chars)
    return chars


def chat(project_id, char_slug, message, mode="story-locked"):
    """Send a chat message to a character."""
    # First find the character
    chars = api("GET", f"/api/projects/{project_id}/characters")
    char = None
    if isinstance(chars, list):
        for c in chars:
            if c["slug"] == char_slug:
                char = c
                break

    if not char:
        print(f"Character '{char_slug}' not found. Available:")
        if isinstance(chars, list):
            for c in chars:
                print(f"  - {c['slug']}")
        return None

    # Get commits for the character
    commits = api("GET", f"/api/characters/{char['id']}/commits")
    commit_id = commits[0]["id"] if isinstance(commits, list) and commits else None

    result = api("POST", "/api/chat", data={
        "project_id": project_id,
        "character_ids": [char["id"]],
        "commit_id": commit_id,
        "mode": mode,
        "message": message,
    })
    if "error" not in result:
        msg = result.get("message", {})
        print(f"\n{char['name']}:")
        print(f"  {msg.get('content', result)}")
    else:
        print(f"Chat error: {result}")
    return result


def get_lore(slug):
    """Get a character's lore profile."""
    result = api("GET", f"/api/lore/characters/{slug}")
    print(json.dumps(result, indent=2))
    return result


def test_all():
    """Run comprehensive tests."""
    print("═══ IvaliceVera Test Suite ═══\n")

    # 1. Backend health
    print("1. Backend Health")
    h = api("GET", "/api/health")
    print(f"   {'✅' if h.get('status') == 'ok' else '❌'} {h}")

    # 2. Lore KB
    print("\n2. Lore KB")
    chars = api("GET", "/api/lore/characters")
    clist = chars.get("characters", [])
    print(f"   ✅ {len(clist)} characters" if clist else f"   ❌ {chars}")
    for c in clist[:3]:
        print(f"      - {c['name']} ({c['slug']})")

    # 3. Parse a real save file
    print("\n3. Save Parsing")
    save_files = []
    for base in ["/home/xsyvps/fft-saves"]:
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.endswith(".bin") or f.endswith(".sav"):
                    save_files.append(os.path.join(root, f))
            if save_files:
                break
        if save_files:
            break

    if save_files:
        sf = save_files[0]
        print(f"   Testing with: {sf}")
        r = upload_save(sf)
        pcs = r.get("player_characters", [])
        print(f"   ✅ Found {len(pcs)} player characters: {[c['name'] for c in pcs]}")
        sp = r.get("story_progress", {})
        print(f"   Story phase: {sp.get('phase', 'unknown')} (raw: 0x{sp.get('raw_38', 0):02x}, 0x{sp.get('raw_39', 0):02x})")
    else:
        print("   ⚠️  No save files found")

    # 4. Create a test project
    print("\n4. Project Creation")
    if save_files:
        r = create_project(save_files[0], "Test FFT Project")
        if r.get("success"):
            pid = r["project_id"]
            print(f"   ✅ Project #{pid} created with {r['characters_created']} chars, {r['commits_created']} commits")

            # 5. List project
            print("\n5. Project Listing")
            list_projects()

            # 6. List characters
            print(f"\n6. Characters in Project #{pid}")
            list_characters(pid)

            # 7. Get lore
            print("\n7. Lore Character")
            get_lore("ramza_beoulve")
        else:
            print(f"   ❌ {r}")

    # 8. Ollama check
    print("\n8. Ollama LLM")
    o = api("GET", "/api/chat/health")
    if o.get("success"):
        m = o.get("data", {})
        print(f"   ✅ {m.get('default_model', '?')} — {len(m.get('available_models', []))} models")
    else:
        print(f"   ⚠️  Unreachable: {o.get('message', '?')}")

    print("\n═══ Tests Complete ═══")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "test-all":
        test_all()
    elif cmd == "status":
        status()
    elif cmd == "parse" and len(args) > 1:
        parse_save(args[1])
    elif cmd == "upload" and len(args) > 1:
        upload_save(args[1])
    elif cmd == "create-project" and len(args) > 1:
        create_project(args[1], args[2] if len(args) > 2 else None)
    elif cmd == "projects":
        list_projects()
    elif cmd == "characters" and len(args) > 1:
        list_characters(args[1])
    elif cmd == "chat" and len(args) >= 4:
        chat(args[1], args[2], " ".join(args[3:]))
    elif cmd == "lore" and len(args) > 1:
        get_lore(args[1])
    else:
        print(__doc__)
        sys.exit(1)
