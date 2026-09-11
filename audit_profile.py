#!/usr/bin/env python3
"""Score a GitHub profile against a mechanical rubric, and report what only the owner can fix.

Modes
  (default)      owner mode: mechanical checks (Class A) on the working-tree README plus the
                 owner-only report (Class B: pins vs slate, identity fields, social previews,
                 stubs) and workflow liveness. Needs a token that can see the owner's repos.
  --public       Class A only, phrased for a public surface: rows are identified by their
                 position in the tools table, never by a private repository name.
  --user LOGIN   audit another user's public profile with the third-party subset of Class A.
  --calibrate    score the exemplar profiles, write calibration.json with the threshold T_mech.
  --markdown P   write the scorecard to P (default: stdout). --json P writes the full report.

Exit code = number of Class A criticals (0 = clean). API failures exit 2.
Standard library only; Python >= 3.11. Prints no HTTP bodies, headers or URLs.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = "https://api.github.com"
BLOCKS = ("contact", "tools", "activity", "releases")
EXEMPLARS = ("simonw", "DenverCoder1")
THRESHOLD_FLOOR = 80
PLACEHOLDER = re.compile(r"TBD|lorem ipsum|No activity tracked|\[placeholder\]|\bTODO\b", re.I)
ANTIPATTERN = re.compile(r"komarev\.com|profile-views|visitor-badge|readme-typing-svg|github-readme-stats|streak-stats|github-profile-trophy|capsule-render", re.I)
LINK = re.compile(r"\]\((https?://[^)\s]+|mailto:[^)\s]+)\)")
NUMBER = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+%|\b\d{5,}\b")
BLOCK = re.compile(r"<!-- (\w+):start -->(.*?)<!-- \1:end -->", re.S)
ASOF = re.compile(r"\*as of (\d{4}-\d{2}-\d{2})\*")


def die(code: int, msg: str) -> None:
    print(f"audit_profile: {msg}")
    sys.exit(code)


def token() -> str:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        die(2, "no token: set GITHUB_TOKEN or log in with gh")
    return ""


class GitHub:
    def __init__(self, tok: str) -> None:
        self.headers = {"Authorization": "bearer " + tok, "Accept": "application/vnd.github+json",
                        "Content-Type": "application/json", "User-Agent": "profile-audit"}

    def _open(self, req: urllib.request.Request):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as exc:
            return exc.code, None
        except Exception as exc:  # noqa: BLE001
            die(2, f"network {type(exc).__name__}")
        return 0, None

    def graphql(self, query: str, variables: dict) -> dict:
        body = json.dumps({"query": query, "variables": variables}).encode()
        status, data = self._open(urllib.request.Request(API + "/graphql", data=body, headers=self.headers))
        if status != 200 or not data or not data.get("data"):
            die(2, f"graphql failed ({status})")
        return data["data"]

    def rest(self, path: str):
        return self._open(urllib.request.Request(API + path, headers=self.headers))


USER_QUERY = """
query($l:String!,$full:Boolean!){ user(login:$l){
  name bio company location websiteUrl socialAccounts(first:4){ totalCount }
  pinnedItems(first:6){ totalCount nodes{ ... on Repository {
    name description isFork isPrivate pushedAt usesCustomOpenGraphImage
    licenseInfo{ spdxId } repositoryTopics(first:1){ totalCount } releases{ totalCount }
    readme:object(expression:"HEAD:README.md"){ ... on Blob { byteSize } }
    defaultBranchRef{ target{ ... on Commit { history{ totalCount } } } } } } }
  contributionsCollection{ restrictedContributionsCount }
  repositories(first:100, isFork:false, privacy:PUBLIC, ownerAffiliations:OWNER) @include(if:$full){ totalCount nodes{
    name description readme:object(expression:"HEAD:README.md"){ ... on Blob { byteSize } }
    defaultBranchRef{ target{ ... on Commit { history{ totalCount } } } } } }
  forks:repositories(first:1, isFork:true, ownerAffiliations:OWNER) @include(if:$full){ totalCount } } }"""


def fetch_user(gh: GitHub, login: str, full: bool) -> dict:
    user = gh.graphql(USER_QUERY, {"l": login, "full": full})["user"]
    user.setdefault("repositories", {"totalCount": 0, "nodes": []})
    user.setdefault("forks", {"totalCount": 0})
    return user


def fetch_readme(gh: GitHub, login: str) -> str:
    status, data = gh.rest(f"/repos/{login}/{login}/readme")
    if status != 200 or not data:
        return ""
    return base64.b64decode(data.get("content", "")).decode("utf-8", "replace")


def repo_info(node: dict) -> dict:
    return {
        "name": node["name"], "description": (node.get("description") or "").strip(),
        "license": (node.get("licenseInfo") or {}).get("spdxId"),
        "topics": (node.get("repositoryTopics") or {}).get("totalCount", 0),
        "releases": (node.get("releases") or {}).get("totalCount", 0),
        "readme_bytes": (node.get("readme") or {}).get("byteSize", 0) or 0,
        "commits": (((node.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}).get("totalCount", 0),
        "og_image": bool(node.get("usesCustomOpenGraphImage")),
        "is_fork": bool(node.get("isFork")), "pushed": (node.get("pushedAt") or "")[:10],
    }


def eligible(info: dict) -> bool:
    return bool(info["description"]) and info["readme_bytes"] >= 2048 and (info["releases"] >= 1 or info["commits"] >= 10)


def tools_rows(readme: str) -> list[tuple[int, str]]:
    m = re.search(r"<!-- tools:start -->(.*?)<!-- tools:end -->", readme, re.S)
    if not m:
        return []
    rows = [ln for ln in m.group(1).splitlines() if ln.startswith("|")]
    return [(i, ln) for i, ln in enumerate(rows[2:], start=1)]  # skip header + separator


def strip_blocks(readme: str, names=("tools", "activity", "releases")) -> str:
    out = readme
    for n in names:
        out = re.sub(rf"<!-- {n}:start -->.*?<!-- {n}:end -->", "", out, flags=re.S)
    return out


def audit(gh: GitHub, login: str, readme: str, cfg: dict | None, public_mode: bool, third_party: bool) -> dict:
    user = fetch_user(gh, login, full=not third_party)
    pins = [repo_info(n) for n in user["pinnedItems"]["nodes"]]
    criticals: list[str] = []
    weighted: list[tuple[str, float, float]] = []  # (label, earned, weight)
    notes: list[str] = []
    lines = readme.splitlines()

    # ---- Class A criticals -------------------------------------------------
    head = "\n".join(lines[:25])
    contacts = [u for u in LINK.findall(head) if "github.com" not in u]
    if not contacts:
        criticals.append("No contact link in the first 25 lines of the README.")

    own_links = re.findall(rf"https://github\.com/{re.escape(login)}/([A-Za-z0-9_.-]+)", readme)
    rows = tools_rows(readme)
    checked: set[str] = set()
    for repo in own_links:
        if repo in checked or repo == login:
            continue
        checked.add(repo)
        status, data = gh.rest(f"/repos/{login}/{repo}")
        where = next((f"row {i} of the tools table" for i, ln in rows if f"/{repo})" in ln), "outside the tools table")
        if status == 200 and data and data.get("private"):
            criticals.append(f"Link target at {where} is private." if public_mode else f"Link target at {where} is private ({repo}).")
        elif status == 404:
            criticals.append(f"Link target at {where} is not public." if public_mode else f"Link target at {where} does not exist for this token ({repo}); fix profile.toml or the README.")
        elif status != 200:
            criticals.append(f"Link target at {where} returned an unexpected status.")

    if any(f"<!-- {n}:start -->" in readme or f"<!-- {n}:end -->" in readme for n in BLOCKS):
        for n in BLOCKS:
            s, e = readme.count(f"<!-- {n}:start -->"), readme.count(f"<!-- {n}:end -->")
            if s != 1 or e != 1 or readme.find(f"<!-- {n}:start -->") > readme.find(f"<!-- {n}:end -->"):
                criticals.append(f"Marker pair for block '{n}' is missing or unpaired.")

    if PLACEHOLDER.search(readme):
        criticals.append("Placeholder text found in the README.")
    if ANTIPATTERN.search(readme):
        criticals.append("Anti-pattern widget or counter referenced in the README.")
    for p in pins:
        if not p["description"]:
            criticals.append("A pinned repository has no description." if public_mode else f"Pinned repository without description: {p['name']}.")
    if not third_party:
        prose = strip_blocks(readme)
        prose_rows = [ln for ln in prose.splitlines() if not (ln.startswith("|") and "github.com" in ln)]
        stray = [ln.strip()[:60] for ln in prose_rows if NUMBER.search(ln)]
        if stray:
            criticals.append(f"Number outside an R-NUM row: {stray[0]!r}")

    # ---- weighted items ------------------------------------------------------
    if pins:
        weighted.append(("pinned repos with a description", 3 * sum(bool(p["description"]) for p in pins) / len(pins), 3))
        weighted.append(("pinned repos with a license", 1 * sum(bool(p["license"]) for p in pins) / len(pins), 1))
        weighted.append(("pinned repos with a topic", 1 * sum(p["topics"] > 0 for p in pins) / len(pins), 1))
    if cfg and not third_party:
        slate = cfg.get("pins", {}).get("slate", [])
        by_name = {repo_info(n)["name"]: repo_info(n) for n in user["repositories"]["nodes"]}
        by_name.update({p["name"]: p for p in pins})
        elig = [eligible(by_name[s]) for s in slate if s in by_name]
        if elig:
            weighted.append(("pin slate eligible (description, README >= 2 KB, release or >= 10 commits)", 2 * sum(elig) / len(elig), 2))
    elif pins:
        weighted.append(("pinned repos eligible (description, README >= 2 KB, release or >= 10 commits)", 2 * sum(eligible(p) for p in pins) / len(pins), 2))
    n_lines = len(lines)
    weighted.append(("README length 40-120 lines", 1.0 if 40 <= n_lines <= 120 else 0.0, 1))
    weighted.append(("bio set", 1.0 if (user.get("bio") or "").strip() else 0.0, 1))
    weighted.append(("location set", 1.0 if user.get("location") else 0.0, 1))
    weighted.append(("website set", 1.0 if user.get("websiteUrl") else 0.0, 1))

    liveness: dict = {}
    if not third_party:
        status, wf = gh.rest(f"/repos/{login}/{login}/actions/workflows/profile.yml")
        if status == 200 and wf:
            liveness["state"] = wf.get("state")
            status, runs = gh.rest(f"/repos/{login}/{login}/actions/workflows/profile.yml/runs?status=success&per_page=1")
            last = (runs or {}).get("workflow_runs") or []
            if last:
                when = dt.datetime.fromisoformat(last[0]["updated_at"].replace("Z", "+00:00"))
                age = (dt.datetime.now(dt.UTC) - when).days
                liveness["last_success_days_ago"] = age
                m = ASOF.search(readme)
                if m:
                    asof = dt.date.fromisoformat(m.group(1))
                    weighted.append(("activity as-of within 30 days of the last successful run", 1.0 if (when.date() - asof).days <= 30 else 0.0, 1))
                if age > 30:
                    criticals.append(f"Last successful workflow run was {age} days ago.")
            if wf.get("state") != "active":
                criticals.append(f"Workflow state is '{wf.get('state')}'; re-arm with: gh workflow enable profile.yml")
        else:
            liveness["state"] = "not deployed"

    earned = sum(e for _, e, _ in weighted)
    total = sum(w for _, _, w in weighted)
    score = round(100 * earned / total) if total else 0

    # ---- Class B (owner only, never public) ---------------------------------
    owner_items: list[str] = []
    if cfg and not public_mode and not third_party:
        slate = cfg.get("pins", {}).get("slate", [])
        pinned_names = [p["name"] for p in pins]
        if pinned_names != slate:
            owner_items.append(f"Pins differ from the slate. Pinned now: {pinned_names or 'none'}. Slate: {slate}. Apply at github.com/{login} -> Customize your pins (no API exists).")
        if not (user.get("bio") or "").strip():
            owner_items.append("Bio is empty (Settings -> Public profile).")
        if not user.get("websiteUrl"):
            owner_items.append("Website field is empty; the README's contact URL is a good value (Settings -> Public profile).")
        if user["socialAccounts"]["totalCount"] == 0:
            owner_items.append("No social account linked (Settings -> Public profile -> Social accounts).")
        no_og = [p["name"] for p in pins if not p["og_image"]]
        if no_og:
            owner_items.append(f"Pinned repos without a social preview image (repo Settings -> Social preview, 1280x640): {no_og}.")
        stubs = [repo_info(n)["name"] for n in user["repositories"]["nodes"] if repo_info(n)["readme_bytes"] < 200 and repo_info(n)["commits"] <= 1 and repo_info(n)["name"] != login]
        if stubs:
            owner_items.append(f"Empty public stub repos (make private or archive): {stubs}.")
        if user["forks"]["totalCount"] > 0:
            owner_items.append(f"{user['forks']['totalCount']} public forks on the Repositories tab; see forks-audit.tsv for the zero-ahead list (deletion is permanent).")
        # An owner-scoped token can see everything, so restrictedContributionsCount is not a
        # reliable sharing signal here. The daily build runs under the job token and renders the
        # private-share clause only when sharing is on, so read that instead.
        activity_block = re.search(r"<!-- activity:start -->(.*?)<!-- activity:end -->", readme, re.S)
        if activity_block and activity_block.group(1).strip() and "in private repos" not in activity_block.group(1):
            owner_items.append("The activity block carries no private-repo share: private contribution counts look hidden (Settings -> Public profile -> Contributions & activity).")

    return {"login": login, "audited_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "score": score, "criticals": criticals, "weighted": [{"item": l, "earned": round(e, 2), "weight": w} for l, e, w in weighted],
            "owner_items": owner_items, "liveness": liveness, "pins": [p["name"] for p in pins],
            "readme_lines": n_lines, "notes": notes}


def load_threshold() -> tuple[int | None, str]:
    p = ROOT / "calibration.json"
    if not p.exists():
        return None, "calibration.json missing; run: python audit_profile.py --calibrate"
    data = json.loads(p.read_text(encoding="utf-8"))
    return int(data["t_mech"]), f"calibrated {data['calibrated_on']}"


def terminal_state(rep: dict, threshold: int | None) -> str:
    if rep["criticals"]:
        return f"NOT DONE — {len(rep['criticals'])} critical"
    if threshold is not None and rep["score"] < threshold:
        return f"NOT DONE — score {rep['score']} below threshold {threshold}"
    if rep["owner_items"]:
        return f"READY-FOR-OWNER — {len(rep['owner_items'])} items"
    return "DONE"


def to_markdown(rep: dict, threshold: int | None, note: str, public_mode: bool) -> str:
    out = [f"## Profile audit — {rep['audited_at'][:10]}" + (" (public data)" if public_mode else ""), ""]
    thr = f" / threshold {threshold}" if threshold is not None else ""
    out.append(f"**Mechanical score:** {rep['score']}{thr} · **Criticals:** {len(rep['criticals'])} · {note}")
    out.append("")
    if rep["criticals"]:
        out.append("**Fix first:**")
        out += [f"- {c}" for c in rep["criticals"]]
        out.append("")
    out.append("| Weighted item | Earned | Weight |")
    out.append("|---|---|---|")
    out += [f"| {w['item']} | {w['earned']} | {w['weight']} |" for w in rep["weighted"]]
    if rep["liveness"]:
        out.append("")
        out.append(f"Workflow: {rep['liveness']}")
    if rep["owner_items"] and not public_mode:
        out.append("")
        out.append("**Owner items (minutes each unless noted; not published anywhere):**")
        out += [f"{i}. {item}" for i, item in enumerate(rep["owner_items"], start=1)]
    out.append("")
    out.append(f"**State:** {terminal_state(rep, threshold)}")
    return "\n".join(out) + "\n"


def calibrate(gh: GitHub) -> dict:
    scores = {}
    for ex in EXEMPLARS:
        rep = audit(gh, ex, fetch_readme(gh, ex), None, public_mode=True, third_party=True)
        scores[ex] = {"score": rep["score"], "criticals": len(rep["criticals"]), "pins": rep["pins"], "readme_lines": rep["readme_lines"]}
    t = max(THRESHOLD_FLOOR, math.floor(min(s["score"] for s in scores.values())))
    data = {"t_mech": t, "calibrated_on": dt.date.today().isoformat(), "floor": THRESHOLD_FLOOR, "exemplars": scores}
    (ROOT / "calibration.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--public", action="store_true")
    ap.add_argument("--user")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--markdown")
    ap.add_argument("--json")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy code page
    except Exception:  # noqa: BLE001
        pass
    gh = GitHub(token())

    if args.calibrate:
        data = calibrate(gh)
        print(json.dumps(data, indent=2))
        return

    cfg = tomllib.loads((ROOT / "profile.toml").read_text(encoding="utf-8")) if (ROOT / "profile.toml").exists() else None
    if args.user:
        login, readme, third = args.user, fetch_readme(gh, args.user), True
    else:
        login = (cfg or {}).get("owner", {}).get("login") or die(2, "profile.toml missing owner.login")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        third = False
    rep = audit(gh, login, readme, cfg, public_mode=args.public or third, third_party=third)
    threshold, note = load_threshold()
    md = to_markdown(rep, threshold, note, public_mode=args.public or third)
    if args.markdown:
        Path(args.markdown).write_text(md, encoding="utf-8")
    else:
        print(md)
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    sys.exit(len(rep["criticals"]))


if __name__ == "__main__":
    main()
