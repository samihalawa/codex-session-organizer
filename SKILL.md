---
name: codex-session-organizer
description: Reorganize and rename Codex Desktop/CLI sessions by editing the rollout logs under ~/.codex/sessions. Use when a Codex chat shows under the wrong project (or no project), when a session's working folder is wrong/misspelled, or when the user wants to rename a Codex chat. Triggers: "link codex session to folder", "codex session wrong project", "rename codex chat", "move codex session", "reorganize codex sessions".
---

# Codex Session Organizer

This skill is fully self-contained. Every command below is inline — it depends on
no other file in this repo. Copy the relevant block, paste it into a terminal, run it.

## What it does

The Codex app files each chat under a **Project** based on the `payload.cwd` field
written on the first line (`session_meta`) of its rollout log:

```
~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl
```

The chat **title** shown in the app is the text of the first genuine user message.

Two operations cover almost every "my session is misfiled / misnamed" request:

- **move**  → rewrite `payload.cwd` to the correct project folder
- **rename** → rewrite the first real user message text

A common cause of an *unlinked* session is a malformed cwd (wrong case, missing a
path segment, e.g. `/users/me/PROJECT` instead of `/Users/me/git/PROJECT`) that
resolves to nothing, so the app can't attach it to any real project.

Every mutation writes a `<file>.bak` backup first. Always run `list` first to grab
the exact uuid and current cwd/title. After editing, restart Codex to re-index.

## 1. List every session (id, cwd, title)

Read-only and always safe. Run this first.

```bash
python3 - <<'PY'
import os, json, glob
SESS = os.path.expanduser("~/.codex/sessions")
SKIP_PREFIX = ("#", "<", "{")
SKIP_SUBSTR = ("AGENTS.md","instructions for","environment_context",
               "user_instructions","<system","developer instructions")
def real(t):
    s=t.strip()
    if not s: return False
    if s.splitlines()[0].startswith(SKIP_PREFIX): return False
    if any(x in s[:200] for x in SKIP_SUBSTR): return False
    return True
for f in sorted(glob.glob(os.path.join(SESS,"**","rollout-*.jsonl"),recursive=True)):
    cwd,title,uid="?","",f[-41:-6]
    with open(f,encoding="utf-8") as fh:
        for i,l in enumerate(fh):
            if i>=120: break
            l=l.strip()
            if not l: continue
            try: d=json.loads(l)
            except: continue
            p=d.get("payload",d)
            if i==0:
                cwd=p.get("cwd",cwd); uid=p.get("id",uid); continue
            if p.get("type")=="message" and p.get("role")=="user" and not title:
                for c in p.get("content",[]):
                    if real(c.get("text","")):
                        title=c["text"].strip().splitlines()[0][:70]; break
            if title: break
    print(f"{uid}  {cwd}\n    {title or '(no title)'}")
PY
```

## 2. Move a session to the right project folder

Set `ID` to a full uuid or any unique prefix (from the list above), and `NEWCWD`
to a folder that **already exists**. The command refuses a nonexistent path — that's
exactly what causes unlinked sessions.

```bash
ID="019e9739"
NEWCWD="/Users/samihalawa/git/PROJECTS_AI_TUTORING"
python3 - "$ID" "$NEWCWD" <<'PY'
import os, sys, json, glob, shutil
idfrag, new = sys.argv[1], os.path.abspath(os.path.expanduser(sys.argv[2]))
if not os.path.isdir(new): sys.exit(f"Target folder does not exist: {new}")
SESS=os.path.expanduser("~/.codex/sessions")
hits=[f for f in glob.glob(os.path.join(SESS,"**","rollout-*.jsonl"),recursive=True) if idfrag in os.path.basename(f)]
if not hits: sys.exit(f"No session matching '{idfrag}'")
if len(hits)>1: sys.exit(f"'{idfrag}' is ambiguous ({len(hits)} matches). Use a longer prefix.")
path=hits[0]
lines=[l for l in open(path,encoding="utf-8").read().splitlines() if l.strip()]
m=json.loads(lines[0]); p=m.get("payload",m); old=p.get("cwd"); p["cwd"]=new
shutil.copy2(path,path+".bak")
lines[0]=json.dumps(m,ensure_ascii=False)
open(path,"w",encoding="utf-8").write("\n".join(lines)+"\n")
print(f"moved {os.path.basename(path)}\n  {old} -> {new}\nRestart Codex to re-index.")
PY
```

## 3. Rename a chat

Rewrites the first real user message only. To undo, restore the `.bak` file.

```bash
ID="019e9739"
NEWTITLE="AI tutoring – Expo app"
python3 - "$ID" "$NEWTITLE" <<'PY'
import os, sys, json, glob, shutil
idfrag, title = sys.argv[1], sys.argv[2]
SESS=os.path.expanduser("~/.codex/sessions")
SKIP_PREFIX=("#","<","{")
SKIP_SUBSTR=("AGENTS.md","instructions for","environment_context","user_instructions","<system","developer instructions")
def real(t):
    s=t.strip()
    if not s: return False
    if s.splitlines()[0].startswith(SKIP_PREFIX): return False
    if any(x in s[:200] for x in SKIP_SUBSTR): return False
    return True
hits=[f for f in glob.glob(os.path.join(SESS,"**","rollout-*.jsonl"),recursive=True) if idfrag in os.path.basename(f)]
if not hits: sys.exit(f"No session matching '{idfrag}'")
if len(hits)>1: sys.exit(f"'{idfrag}' is ambiguous ({len(hits)} matches). Use a longer prefix.")
path=hits[0]
lines=[l for l in open(path,encoding="utf-8").read().splitlines() if l.strip()]
changed=False
for i,l in enumerate(lines[1:],start=1):
    try: d=json.loads(l)
    except: continue
    p=d.get("payload",{})
    if p.get("type")=="message" and p.get("role")=="user":
        for c in p.get("content",[]):
            if real(c.get("text","")):
                c["text"]=title; lines[i]=json.dumps(d,ensure_ascii=False); changed=True; break
    if changed: break
if not changed: sys.exit("No user message found to rename.")
shutil.copy2(path,path+".bak")
open(path,"w",encoding="utf-8").write("\n".join(lines)+"\n")
print(f"renamed {os.path.basename(path)} -> {title!r}\nRestart Codex to re-index.")
PY
```

## 4. Restart Codex so it re-indexes

```bash
osascript -e 'tell application "Codex" to quit'; sleep 3; open -a Codex
```

(If a "Quit Codex? Active local threads will be interrupted" dialog appears and you
have a running task, click **Cancel** and just reload the window instead.)

## Notes

- `list` is read-only — run it first to grab the exact uuid and current cwd/title.
- `move` only changes where the chat is filed; it does not touch history.
- `rename` edits the first user turn only; restore the `.bak` to undo.
- These commands are the whole skill. There is no `scripts/` folder to rely on.
