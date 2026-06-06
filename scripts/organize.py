#!/usr/bin/env python3
"""Reorganize and rename Codex Desktop/CLI sessions.

The Codex app groups chats under "Projects" by the `payload.cwd` field stored on
the first (session_meta) line of each rollout log:
    ~/.codex/sessions/YYYY/MM/DD/rollout-*-<uuid>.jsonl
The chat title shown in the app is the text of the first user message.

Commands:
    list                          List sessions (id, date, cwd, title).
    move <id> <new_cwd>           Re-file a session under a different project folder.
    rename <id> <new title...>    Change the chat title (first user message).

Matching <id> accepts a full UUID or any unique prefix.
Every mutation writes a <file>.bak backup first. Restart Codex to re-index.
"""
import sys, os, json, glob, shutil

SESS = os.path.expanduser("~/.codex/sessions")


def all_files():
    return sorted(glob.glob(os.path.join(SESS, "**", "rollout-*.jsonl"), recursive=True))


def session_id(path):
    base = os.path.basename(path)
    return base.replace(".jsonl", "").rsplit("-", 5)[-5:] and base.replace(".jsonl", "")[-36:]


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [l for l in f.read().splitlines() if l.strip()]


SKIP_PREFIX = ("#", "<", "{")
SKIP_SUBSTR = ("AGENTS.md", "instructions for", "environment_context",
               "user_instructions", "<system", "developer instructions")


def _is_real_prompt(t):
    s = t.strip()
    if not s:
        return False
    head = s.splitlines()[0]
    if head.startswith(SKIP_PREFIX):
        return False
    if any(x in s[:200] for x in SKIP_SUBSTR):
        return False
    return True


def meta_and_title(path, max_lines=120):
    """Cheap scan: cwd from line 1, title from first genuine user message.
    Reads at most max_lines so huge logs don't stall `list`."""
    cwd, title, uid = "?", "", path[-41:-6]
    with open(path, "r", encoding="utf-8") as f:
        for i, l in enumerate(f):
            if i >= max_lines:
                break
            l = l.strip()
            if not l:
                continue
            try:
                d = json.loads(l)
            except Exception:
                continue
            p = d.get("payload", d)
            if i == 0:
                cwd = p.get("cwd", cwd)
                uid = p.get("id", uid)
                continue
            if p.get("type") == "message" and p.get("role") == "user" and not title:
                for c in p.get("content", []):
                    t = c.get("text", "")
                    if _is_real_prompt(t):
                        title = t.strip().splitlines()[0][:70]
                        break
            if title:
                break
    return uid, cwd, title


def resolve(idfrag):
    hits = [f for f in all_files() if idfrag in os.path.basename(f)]
    if not hits:
        sys.exit(f"No session matching '{idfrag}'")
    if len(hits) > 1:
        sys.exit(f"'{idfrag}' is ambiguous ({len(hits)} matches). Use a longer prefix.")
    return hits[0]


def backup(path):
    shutil.copy2(path, path + ".bak")


def cmd_list():
    for f in all_files():
        uid, cwd, title = meta_and_title(f)
        print(f"{uid}  {cwd}\n    {title or '(no title)'}")


def cmd_move(idfrag, new_cwd):
    new_cwd = os.path.abspath(os.path.expanduser(new_cwd))
    if not os.path.isdir(new_cwd):
        sys.exit(f"Target folder does not exist: {new_cwd}")
    path = resolve(idfrag)
    lines = read_lines(path)
    m = json.loads(lines[0])
    p = m.get("payload", m)
    old = p.get("cwd")
    p["cwd"] = new_cwd
    backup(path)
    lines[0] = json.dumps(m, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"moved {os.path.basename(path)}\n  {old} -> {new_cwd}\nRestart Codex to re-index.")


def cmd_rename(idfrag, new_title):
    path = resolve(idfrag)
    lines = read_lines(path)
    changed = False
    for i, l in enumerate(lines[1:], start=1):
        try:
            d = json.loads(l)
            p = d.get("payload", {})
            if p.get("type") == "message" and p.get("role") == "user":
                for c in p.get("content", []):
                    if _is_real_prompt(c.get("text", "")):
                        c["text"] = new_title
                        lines[i] = json.dumps(d, ensure_ascii=False)
                        changed = True
                        break
            if changed:
                break
        except Exception:
            continue
    if not changed:
        sys.exit("No user message found to rename.")
    backup(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"renamed {os.path.basename(path)} -> {new_title!r}\nRestart Codex to re-index.")


def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__); return
    cmd = a[0]
    if cmd == "list":
        cmd_list()
    elif cmd == "move" and len(a) == 3:
        cmd_move(a[1], a[2])
    elif cmd == "rename" and len(a) >= 3:
        cmd_rename(a[1], " ".join(a[2:]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
