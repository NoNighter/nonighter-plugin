# Memory records — index

> One routing line per durable fact this instance holds. Auto-loads every session through `AGENTS.md`; budget ~800 tokens. Written only by the daily pass.

**A line routes; it never asserts.** Name what the record is about and the hook that makes it worth opening. Never state the fact itself — a record earns a staleness banner when it is read, and an index line gets none.

Records live at `memory/records/<slug>.md`. Writing rules: `memory/instructions-memory-maintenance.md` §3.

---

*No records yet — this instance was installed {{INSTALL_DATE}}. The first pass writes the first line here.*
