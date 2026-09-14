# Instructions — Improvement Pass

> The weekly unattended pass that reads how this instance is actually being used and writes proposals for changing it. Read in full before running the pass or writing a proposal file.

Activity type: **task (recurring, weekly)**. An agent in this file is running the pass — never doing project work, and never applying what it proposes.

## 1. The line between this pass and maintenance

**Maintenance asks whether the instance follows its conventions. This pass asks whether the conventions still fit the work.** Structure, naming, headers, cross-references, stale files and token budgets belong to the maintenance pass, which a person triggers and which has `check-memory-structure.py` for the mechanical half. A finding this pass produces is never "this file is off the standard" — it is "the standard costs the user something every week".

Everything here is a proposal. This pass writes one file and changes nothing else: not a memory file, not an instructions file, not a convention. The maintenance pass applies what a person approves.

## 2. What it reads

**The memory pass's run reports, in `memory/runs/`, are the source.** They already distil each day — what moved, what was corrected, what the transcripts left ambiguous — and reading them costs a fraction of re-reading the transcripts, which is the most expensive thing this instance does. Read every report written since this pass last ran; its own last run file names that date.

Then, for context only: `MEMORY.md` and each scope's `## Open threads`, the conventions, and the instructions file of any scope a report named repeatedly.

**Never read the raw transcripts.** If a report is too thin to support a finding, the finding does not exist yet — and that thinness is itself worth proposing about.

## 3. The three things it looks for

- **Friction that recurs.** The same correction, question, or re-explanation appearing in reports from different days. One occurrence is an event; the same one twice is a property of the setup.
- **Work that should be a procedure.** A sequence of steps performed the same way more than twice, from memory each time, with no file that states it.
- **A convention that no longer matches.** A rule the work has quietly stopped obeying, or one that is obeyed at a cost the reports keep mentioning. Where the work and the rule disagree, say which one is wrong; do not assume it is the work.

## 4. The evidence rule

**A proposal names its occurrences, each with a date and the report it came from.** Two on different days is the minimum. A proposal supported by one occurrence is an observation and goes in the run file's *Observed once* list instead, where the next pass can find it and promote it.

State the cost in the terms the reports used — turns spent, work redone, a decision remade. A proposal whose cost cannot be stated is a preference.

## 5. Where it writes

One file per run: `improvement/runs/YYYY-MM-DD-improvement-pass.md`, holding

- the window read, and the date of the previous run
- **Proposals** — each with its occurrences, the cost, and the single change proposed
- **Observed once** — carried for the next pass, not acted on
- **Nothing to propose** is a complete and normal result. Say it in one line and stop; a pass that manufactures a proposal to look productive costs more than a quiet one.

## 6. What it never proposes

Restating a rule the conventions already hold. Tidying that no report mentioned. Anything whose only support is this pass's own opinion of how the instance should look. Adding a system, a scope, or a file that no observed work needs.

And never a proposal about the user's own files — `operating-manual.md`, `MEMORY.md`, their content in the host `CLAUDE.md`. Those are theirs; the reports may describe them, this pass does not. **The manual is on that list as of 0.6.0**, when it stopped being template content and became the user's: its defaults are now theirs to edit, so a proposal to reword one is a proposal about their file.

## 7. Running it unattended

It is registered with the host harness as a weekly task, and the schedule lives there rather than here. The task's prompt does one thing: name this instance's absolute path and say to read this file and follow it.

**Nobody is watching.** So: read, write the one run file, and stop. Do not ask a question — there is no one to answer it, and a pass that stalls on a prompt produces nothing and reports nothing. Where an answer is needed, write the question into the run file as a proposal whose first line is what it needs decided.

If `AGENTS.md` is missing from the path the task names, the instance is gone or moved. Write no run file - there is no instance to write it into - and say so in the task's own output, which is the one place left that somebody will read. Then stop.
