"""Rewrite the activity block in README.md from live GitHub data.

Writes only between the ACTIVITY_START/ACTIVITY_END markers. If either marker is
missing the script exits non-zero rather than guessing where the block belongs.
"""

import json
import os
import pathlib
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER = "advegaf"
START = "<!-- activity:start -->"
END = "<!-- activity:end -->"
SKIP = {USER, "vita-site"}  # profile repo itself, and a supporting site
ROWS = 5

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"


def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-readme",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def latest_release(repo):
    try:
        rel = api(f"/repos/{USER}/{repo}/releases?per_page=1")
    except urllib.error.HTTPError:
        return None
    return rel[0].get("tag_name") if rel else None


def ago(iso):
    then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - then).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    months = days // 30
    return "1 month ago" if months == 1 else f"{months} months ago"


def build():
    repos = [
        r
        for r in api(f"/users/{USER}/repos?per_page=100&sort=pushed")
        if not r["fork"] and not r["archived"] and r["name"] not in SKIP
    ]
    lines = ["| | | |", "|---|---|---|"]
    for r in repos[:ROWS]:
        name, lang = r["name"], r.get("language") or ""
        tag = latest_release(name)
        version = f"`{tag}` " if tag else ""
        lines.append(
            f"| [{name}](https://github.com/{USER}/{name}) "
            f"| {lang} | {version}updated {ago(r['pushed_at'])} |"
        )
    return "\n".join(lines)


def main():
    text = README.read_text()
    if START not in text or END not in text:
        raise SystemExit(f"markers missing in {README}")
    block = f"{START}\n{build()}\n{END}"
    updated = re.sub(
        re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S
    )
    if updated == text:
        print("no change")
        return
    README.write_text(updated)
    print("updated")


if __name__ == "__main__":
    main()
