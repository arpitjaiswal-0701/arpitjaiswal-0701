# I'm Arpit Jaiswal.

I sell enterprise software, and I build the tooling that takes the paperwork out of selling: CRM updates, meeting prep, contact research, inbox triage. Everything I build shows you the change before it writes it, and never invents a fact.

<!-- contact:start -->
[LinkedIn](https://www.linkedin.com/in/arpit-jaiswal-0701)
<!-- contact:end -->

### Three rules everything here follows

- **Rules first.** If a script can do the job, a script does it. The model drafts and reviews; it never holds the pen on the final bytes.
- **You see every write before it lands.** Anything that touches a system of record shows the exact change and waits for a yes. A bad day for the model is a declined prompt, not a corrupted record.
- **No invented facts.** A name, number or date appears only when the evidence does. Enforced in code, not in a prompt.

### Tools I've published

Built for my own desk, MIT-licensed, one user in production: me.

<!-- tools:start -->
| Tool | What it does | Proof |
|---|---|---|
| [**Dead Reels Society**](https://github.com/arpitjaiswal-0701/dead-reels) | Turns the Instagram reels you hoard into a local, searchable knowledge base: transcripts, OCR, triage. | 100% local; installs nothing on its own |
| [**Inbox Zero Engine**](https://github.com/arpitjaiswal-0701/inbox-zero-engine) | Rules-first Gmail cleanup. Native filters do the work; the model only drafts the rules. | 62,275 inbox threads to ~2,000 in one session (Jul 2026) |
| [**/sales plan**](https://github.com/arpitjaiswal-0701/sales-plan-skill) | One command runs six research agents and fills an account business-plan deck. | 6 agents, one populated deck |
| [**attendee-harvester**](https://github.com/arpitjaiswal-0701/attendee-harvester) | Pulls a full event attendee list from Swapcard by intercepting its own API calls. Resumable, validated, Excel out. |  |
| [**vibe-clone**](https://github.com/arpitjaiswal-0701/vibe-clone) | Turns a design reference into a new, visually verified artifact in that design language. |  |
<!-- tools:end -->

<!-- activity:start -->
**Active on 27 of the last 90 days:** 151 commits, issues and reviews across 6 repositories (77% of them in private repos). *as of 2026-09-11*
<!-- activity:end -->

<!-- releases:start -->
<!-- releases:end -->

### Why most of it stays private

The systems I lean on most touch my employer's CRM and customer data, so their code stays private: a calendar-to-CRM activity sync that shows every record before it lands; a browser-driven write-back for a reporting app that has no API; zero-cost contact enrichment with SMTP-level verification and no invented addresses; and a local agent control plane with scheduled routines, a watchdog and backups. Happy to walk through any of them. LinkedIn is above.

### How I work

- Claude Code skills are the unit of automation. Each one is a prompt, the scripts it calls, and a README that states its limits.
- Deterministic first. If a rule can express the task, it becomes a script, not an agent.
- Adversarial review before anything outward-facing. A fresh reviewer attacks the draft; then it ships.
- Measured, not vibes. Audits run on real logs, and the numbers decide what changes.

---

<sub>Rebuilt daily by <a href="build_readme.py">build_readme.py</a>; committed only when something changed. Rubric: <a href="audit_profile.py">audit_profile.py</a>.</sub>
