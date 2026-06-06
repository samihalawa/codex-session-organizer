---
name: codex-session-organizer
description: Reorganize and rename Codex Desktop/CLI sessions by editing the rollout logs under ~/.codex/sessions. Use when a Codex chat shows under the wrong project (or no project), when a session's working folder is wrong/misspelled, or when the user wants to rename a Codex chat. Triggers: "link codex session to folder", "codex session wrong project", "rename codex chat", "move codex session", "reorganize codex sessions".
---

# Codex Session Organizer

## What it does

The Codex app files each chat under a **Project** based on the `payload.cwd` field
written on the first line (`session_meta`) of its rollout log:

```
~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<uuid>.jsonl
```

The chat **title** is the text of the first user message in that log.

So two operations cover almost every "my session is misfiled / misnamed" request:

- **move**  → rewrite `payload.cwd` to the correct project folder
- **rename** → rewrite the first user message text

A common cause of an *unlinked* session is a malformed cwd (wrong case, missing a
path segment, e.g. `/users/me/PROJECT` instead of `/Users/me/git/PROJECT`) that
resolves to nothing, so the app can't attach it to any real project.

## Usage

`scripts/organize.py` is dependency-free (Python 3, stdlib only).

```bash
# See every session: uuid, cwd, title
python3 scripts/organize.py list

# Re-file a session under the right project folder (id = full uuid or unique prefix)
python3 scripts/organize.py move 019e9739 /Users/samihalawa/git/PROJECTS_AI_TUTORING

# Rename the chat
python3 scripts/organize.py rename 019e9739 "AI tutoring – Expo app"
```

Every mutation writes a `<file>.bak` backup first. The target folder for `move`
must already exist (the script refuses a nonexistent path — that's what causes
unlinked sessions in the first place).

## After editing

Restart the Codex app so it re-indexes the sessions:

```bash
osascript -e 'tell application "Codex" to quit'; sleep 3; open -a Codex
```

(If a "Quit Codex? Active local threads will be interrupted" dialog appears and you
have a running task, click **Cancel** and instead just reload the window.)

## Notes

- Read-only `list` is always safe; run it first to grab the exact uuid and see the
  current cwd/title.
- `move` only changes where the chat is filed; it does not touch history.
- `rename` edits the first user turn only. To undo, restore the `.bak` file.
