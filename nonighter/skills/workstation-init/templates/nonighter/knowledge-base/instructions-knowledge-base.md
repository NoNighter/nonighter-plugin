# Instructions — Knowledge Base

> How reference material is kept in this instance: what earns an entry, how one is shaped, and how it is found. Read before adding or revising an entry.

Activity type: **task**. An agent in this folder is writing or revising a reference entry, not doing project work.

## What earns an entry

Durable domain knowledge that a session would otherwise re-derive: a method, a standard, a definition set, a piece of hard-won technique. It earns a place when it is **reusable across scopes** and **stable across months**.

Three things do not belong here. Live state belongs in a memory buffer. A fact about *where something is* belongs in a memory record or a context card. Knowledge about one scope only belongs in that scope's own files.

## Who writes one — propose-first, always

> The same split is stated in `memory/instructions-memory-maintenance.md` §3, on purpose: the daily pass is what catches a rule the user stated in passing, and it has to know that a criterion belongs here rather than in a memory record. One run filed a client-wide criterion into a single project's instructions instead, where the next project for that client could not see it.

**No session writes an entry on its own judgment.** Notice the candidate, propose it in one line, write it only if the user agrees. Where the user says "keep this", that is the same path with the proposal already answered.

The reason is what an entry *is*. Memory records what happened; this records **what to do** — and `index-knowledge-base.md` is loaded at session start, so an entry here is applied to work without being re-examined first. An inference filed as a criterion becomes policy: "this client's DCF is always unlevered" written on a hunch changes numbers in every later model, and nobody goes back to ask where it came from. That is the difference from a memory record, which the daily pass writes unattended because it only reports what already happened.

**What is worth proposing:** something the user has said more than once, or a decision that settled a question which will come back. Not everything true, and not a summary of the session.

**Every entry names its source and its date** — who decided it, or which document it comes from. An uncited criterion is indistinguishable from a guess six months later, and this one will be obeyed.

**When an entry and the user disagree, the user wins**, in that moment. Correct the entry, date the correction, and say what changed. An entry that contradicts what the user just said and stays on the shelf is worse than no entry.

## Shape

One topic per file, named `<topic>.md`, flat until the count justifies a subfolder. Header per `CONVENTIONS.md` §1: H1, then a blockquote saying what the entry covers and when to read it.

Body: whatever structure the topic needs. An entry is written to be *used mid-task*, so lead with the operative content and put the derivation below it.

**Cite the source when the entry rests on one**, with enough detail to re-find it. An uncited claim in a reference file is indistinguishable from a guess six months later.

## Finding an entry

`index-knowledge-base.md` carries one row per entry: topic, path, one line. Add the row in the same edit that creates the entry — an unindexed entry is not findable, and is therefore not knowledge.
