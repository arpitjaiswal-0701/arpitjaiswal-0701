# I'm Arpit Jaiswal.

I sell enterprise software, and I build the tooling that takes the paperwork out of selling: CRM updates, meeting prep, contact research, inbox triage. Everything I build shows you the change before it writes it, and never invents a fact.

<!-- contact:start -->
[LinkedIn](https://www.linkedin.com/in/arpit-jaiswal-0701)
<!-- contact:end -->

### Three rules everything here follows

- **Rules first.** If a script can do the job, a script does it. The model drafts and reviews; it never holds the pen on the final bytes.
- **You see every write before it lands.** Anything that touches a system of record shows the exact change and waits for a yes. A bad day for the model is a declined prompt, not a corrupted record.
- **No invented facts.** A name, number or date appears only when the evidence does. Enforced in code, not in a prompt.

### Tools I've built

Built for my own desk, one user in production: me. Public ones are MIT-licensed; the ones that touch my employer's systems stay private.

<!-- tools:start -->
| Tool | What it does | Proof |
|---|---|---|
| **Autopsy** *(private)* | Cause-of-death report for any deal, dead or alive. Pulls the full record out of Dynamics 365 read-only, compiles a sourced intel document with the CRM link on every line, and proposes gated edits to the deal folder. Nothing is written until you type apply. |  |
| **Dynamics sync** *(private)* | Turns the meetings on your Outlook calendar into Dynamics 365 activity records. Shows every record before it writes; never invents what happened in the room. |  |
| **Ghosthand** *(private)* | Drives weekly account-hygiene updates into a Power BI report with a Power Apps write-back panel and no API, through watched, human-gated browser actions. |  |
| [**vibe-clone**](https://github.com/arpitjaiswal-0701/vibe-clone) | Turns a design reference into a new, visually verified artifact in that design language. |  |
| [**/sales plan**](https://github.com/arpitjaiswal-0701/sales-plan-skill) | One command runs six research agents and fills an account business-plan deck. | 6 agents, one populated deck |
| [**attendee-harvester**](https://github.com/arpitjaiswal-0701/attendee-harvester) | Pulls a full event attendee list from Swapcard by intercepting its own API calls. Resumable, validated, Excel out. |  |
| [**Dead Reels Society**](https://github.com/arpitjaiswal-0701/dead-reels) | Turns the Instagram reels you hoard into a local, searchable knowledge base: transcripts, OCR, triage. | 100% local; installs nothing on its own |
<!-- tools:end -->

<!-- activity:start -->
**Active on 23 of the last 90 days:** 157 commits, issues and reviews across 6 repositories (77% of them in private repos). *as of 2026-09-22*
<!-- activity:end -->

<!-- releases:start -->
### Latest tagged versions

- [v0.1.0](https://github.com/arpitjaiswal-0701/dead-reels/releases/tag/v0.1.0) · [dead-reels](https://github.com/arpitjaiswal-0701/dead-reels) · 2026-09-11
- [v1.0.0](https://github.com/arpitjaiswal-0701/arpitjaiswal-0701/releases/tag/v1.0.0) · [arpitjaiswal-0701](https://github.com/arpitjaiswal-0701/arpitjaiswal-0701) · 2026-09-11
- [v1.0.0](https://github.com/arpitjaiswal-0701/vibe-clone/releases/tag/v1.0.0) · [vibe-clone](https://github.com/arpitjaiswal-0701/vibe-clone) · 2026-07-27
- [v1.0.0](https://github.com/arpitjaiswal-0701/sales-plan-skill/releases/tag/v1.0.0) · [sales-plan-skill](https://github.com/arpitjaiswal-0701/sales-plan-skill) · 2026-07-27
- [v1.0.0](https://github.com/arpitjaiswal-0701/inbox-zero-engine/releases/tag/v1.0.0) · [inbox-zero-engine](https://github.com/arpitjaiswal-0701/inbox-zero-engine) · 2026-07-27
- [v1.0.0](https://github.com/arpitjaiswal-0701/attendee-harvester/releases/tag/v1.0.0) · [attendee-harvester](https://github.com/arpitjaiswal-0701/attendee-harvester) · 2026-07-27
<!-- releases:end -->

### Also running, privately

Two more sit behind the same rules: zero-cost contact enrichment with SMTP-level verification and no invented addresses, and a local agent control plane with scheduled routines, a watchdog and backups. Happy to walk through any of it. LinkedIn is above.

### How I work

- Claude Code skills are the unit of automation. Each one is a prompt, the scripts it calls, and a README that states its limits.
- Deterministic first. If a rule can express the task, it becomes a script, not an agent.
- Adversarial review before anything outward-facing. A fresh reviewer attacks the draft; then it ships.
- Measured, not vibes. Audits run on real logs, and the numbers decide what changes.

---

<sub>Rebuilt daily by <a href="build_readme.py">build_readme.py</a>; committed only when something changed. Rubric: <a href="audit_profile.py">audit_profile.py</a>.</sub>
