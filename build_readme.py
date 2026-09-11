#!/usr/bin/env python3
"""Render the machine blocks of README.md from profile.toml and live GitHub data.

Blocks, each between ``<!-- NAME:start -->`` and ``<!-- NAME:end -->`` in README.md:

  contact   links from [links]; empty values are omitted, never a placeholder
  tools     table of public tools; a row whose repo is not public renders without a link
  activity  contribution summary over the last N days (GitHub's own public counts; the
            private share appears only when the owner shares private contribution counts)
  releases  latest GitHub Releases across public non-fork repos; rendered only when at
            least ``min_distinct_dates`` distinct release dates exist

Exit codes: 0 ok (changed or unchanged), 1 marker pair missing or unpaired,
2 GitHub API failure, 3 configuration error.
Never prints HTTP response bodies, headers or request URLs.
Writes build-report.json (gitignored) for the workflow's commit message and issue step.
Standard library only; Python >= 3.11 (tomllib).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"
CONFIG = ROOT / "profile.toml"
REPORT = ROOT / "build-report.json"
API = "https://api.github.com"
BLOCKS = ("contact", "tools", "activity", "releases")
MARK = re.compile(r"<!-- (\w+):start -->(.*?)<!-- \1:end -->", re.S)
ASOF = re.compile(r"^(.*?)\s*\*as of (\d{4}-\d{2}-\d{2})\*\s*$", re.S)


def die(code: int, msg: str) -> None:
    print(f"build_readme: {msg}")
    sys.exit(code)


def iso(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        die(2, "no token: set GITHUB_TOKEN or log in with gh")
    return ""  # unreachable


class GitHub:
    def __init__(self, tok: str) -> None:
        self.headers = {
            "Authorization": "bearer " + tok,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-builder",
        }

    def graphql(self, query: str, variables: dict) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(API + "/graphql", data=body, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as exc:
            die(2, f"graphql http {exc.code}")
        except Exception as exc:  # noqa: BLE001
            die(2, f"graphql {type(exc).__name__}")
        if not data.get("data"):
            die(2, "graphql returned errors")
        return data["data"]

    def repo_status(self, owner: str, name: str) -> str:
        """'public', 'private' (visible to this token), or 'not-public' (404 to this token)."""
        req = urllib.request.Request(f"{API}/repos/{owner}/{name}", headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
                return "private" if data.get("private") else "public"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return "not-public"
            die(2, f"rest http {exc.code}")
        except Exception as exc:  # noqa: BLE001
            die(2, f"rest {type(exc).__name__}")
        return "not-public"  # unreachable


def replace_block(text: str, name: str, body: str) -> str:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        die(1, f"marker pair for block '{name}' missing or unpaired")
    i = text.index(start) + len(start)
    j = text.index(end)
    inner = body.strip("\n")
    return text[:i] + ("\n" + inner + "\n" if inner else "\n") + text[j:]


def render_contact(cfg: dict) -> str:
    labels = {"linkedin": "LinkedIn", "email": "Email", "website": "Website", "x": "X",
              "mastodon": "Mastodon", "bluesky": "Bluesky"}
    parts = []
    for key, value in (cfg.get("links") or {}).items():
        if not value:
            continue
        href = value
        if key == "email" and not value.startswith("mailto:"):
            href = "mailto:" + value
        parts.append(f"[{labels.get(key, key.title())}]({href})")
    return " · ".join(parts)


def render_tools(cfg: dict, gh: GitHub, owner: str) -> tuple[str, list[dict]]:
    rows = ["| Tool | What it does | Proof |", "|---|---|---|"]
    demoted: list[dict] = []
    for index, tool in enumerate(cfg.get("tools") or [], start=1):
        status = gh.repo_status(owner, tool["repo"])
        if status == "public":
            cell = f"[**{tool['name']}**](https://github.com/{owner}/{tool['repo']})"
        else:
            cell = f"**{tool['name']}**"
            demoted.append({"row": index, "status": status})
        rows.append(f"| {cell} | {tool['what']} | {tool.get('proof', '')} |")
    return "\n".join(rows), demoted


def plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def render_activity(cfg: dict, gh: GitHub, owner: str, old_block: str, today: dt.datetime) -> tuple[str, dict]:
    days = int((cfg.get("activity") or {}).get("window_days", 90))
    frm = today - dt.timedelta(days=days)
    query = """
    query($l:String!,$f:DateTime!,$t:DateTime!){ user(login:$l){ contributionsCollection(from:$f,to:$t){
      restrictedContributionsCount totalRepositoriesWithContributedCommits
      contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount } } } } } }"""
    coll = gh.graphql(query, {"l": owner, "f": iso(frm), "t": iso(today)})["user"]["contributionsCollection"]
    total = coll["contributionCalendar"]["totalContributions"]
    active = sum(1 for w in coll["contributionCalendar"]["weeks"] for d in w["contributionDays"] if d["contributionCount"] > 0)
    repos = coll["totalRepositoriesWithContributedCommits"]
    restricted = coll["restrictedContributionsCount"]

    sentence = (f"**Active on {active} of the last {days} days:** {total} commits, issues and reviews "
                f"across {repos} {plural(repos, 'repository', 'repositories')}")
    if restricted > 0 and total > 0:
        sentence += f" ({round(100 * restricted / total)}% of them in private repos)"
    sentence += "."

    as_of = today.date().isoformat()
    match = ASOF.match(old_block.strip())
    if match and match.group(1).strip() == sentence:
        as_of = match.group(2)  # numbers unchanged: keep the date they last changed
    block = f"{sentence} *as of {as_of}*"
    facts = {"total": total, "active_days": active, "repos": repos, "restricted": restricted,
             "window_days": days, "as_of": as_of}
    return block, facts


def render_releases(cfg: dict, gh: GitHub, owner: str) -> tuple[str, dict]:
    query = """
    query($l:String!){ user(login:$l){ repositories(first:100,isFork:false,privacy:PUBLIC,ownerAffiliations:OWNER){
      nodes{ name releases(last:5){ nodes{ tagName publishedAt isDraft url } } } } } }"""
    nodes = gh.graphql(query, {"l": owner})["user"]["repositories"]["nodes"]
    items = [(r["publishedAt"][:10], n["name"], r["tagName"], r["url"])
             for n in nodes for r in n["releases"]["nodes"] if r["publishedAt"] and not r["isDraft"]]
    items.sort(reverse=True)
    rc = cfg.get("releases") or {}
    items = items[: int(rc.get("max_items", 6))]
    distinct = len({d for d, _, _, _ in items})
    if distinct < int(rc.get("min_distinct_dates", 2)):
        return "", {"rendered": False, "count": len(items), "distinct_dates": distinct}
    lines = ["### Latest tagged versions", ""]
    lines += [f"- [{tag}]({url}) · [{name}](https://github.com/{owner}/{name}) · {date}" for date, name, tag, url in items]
    return "\n".join(lines), {"rendered": True, "count": len(items), "distinct_dates": distinct}


def main() -> None:
    try:
        cfg = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        owner = cfg["owner"]["login"]
    except Exception as exc:  # noqa: BLE001
        die(3, f"profile.toml unreadable: {type(exc).__name__}")
    if not README.exists():
        die(1, "README.md missing")
    text = README.read_text(encoding="utf-8")
    old_blocks = {m.group(1): m.group(2) for m in MARK.finditer(text)}
    for name in BLOCKS:
        if name not in old_blocks:
            die(1, f"marker pair for block '{name}' missing or unpaired")

    gh = GitHub(token())
    now = dt.datetime.now(dt.UTC).replace(microsecond=0)
    contact = render_contact(cfg)
    tools, demoted = render_tools(cfg, gh, owner)
    activity, facts = render_activity(cfg, gh, owner, old_blocks.get("activity", ""), now)
    releases, rel = render_releases(cfg, gh, owner)

    new = text
    for name, body in (("contact", contact), ("tools", tools), ("activity", activity), ("releases", releases)):
        new = replace_block(new, name, body)
    changed = new != text
    if changed:
        README.write_text(new, encoding="utf-8", newline="\n")

    message = f"activity: {facts['total']} on {facts['active_days']}d, {facts['repos']} repos - {facts['as_of']}"
    report = {"built_at": iso(now), "changed": changed, "commit_message": message,
              "activity": facts, "releases": rel, "demoted_rows": demoted}
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"build_readme: {'changed' if changed else 'no change'}; "
          f"activity {facts['total']} on {facts['active_days']}d across {facts['repos']} repos; "
          f"releases {'rendered' if rel['rendered'] else 'gated'} ({rel['count']} items, {rel['distinct_dates']} dates); "
          f"demoted rows {[d['row'] for d in demoted]}")


if __name__ == "__main__":
    main()
