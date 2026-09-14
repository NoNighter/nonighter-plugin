# Instructions — Market and Deal Watch

> The unattended pass that reads the outside world for the names and sectors this user follows, and writes what actually moved. Read in full before running the watch or writing a run file.

Activity type: **task (recurring, weekday)**. An agent in this file is running the watch — reporting what happened, never advising what to do about it.

## 1. Coverage comes from the user, never from inference

**`watch/coverage.md` is the whole definition of what to read for.** It is the user's file: the names, sectors and geographies they follow, and what they explicitly do not want. This pass reads it and obeys it.

**An empty or missing `coverage.md` — or one whose names or sectors are placeholders rather than answers — means the watch does not run.** Write a run file saying what is missing and stop. Guessing coverage from the folder contents, the client names in the memory files, or the sector a model happens to be about produces a plausible report about the wrong universe, which is worse than no report: it reads as though someone chose it.

Coverage changes only when the user changes it. A pass that keeps finding nothing for one name may say so as a note; it does not drop the name.

## 2. What counts as movement

Something that happened, in the window, to something in coverage:

- **Transactions** — announced, closed, withdrawn, repriced. Who, what, how much, and on what date.
- **Market developments** that move the names in coverage, not the market in general.
- **Activity around the names** — filings, guidance, credit ratings, leadership, litigation, capital
  structure.
- **Broker actions, as facts about the broker** — who, on what date, moved what: a target from A to B,
  a rating from X to Y. The movement, its source and its date, and nothing else. Not the broker's
  argument, and never a synthesis of what "the street" thinks - that is an opinion assembled from
  other people's opinions, and it reads as the watch's own.

**A week where nothing moved is a result.** Say it in one line. Padding a quiet week with background reading trains the user to stop opening the file, and the file they stop opening is the one that would have carried the thing that mattered.

## 3. Sourcing rules

**Every item names its source and its date.** An item without both does not go in the file.

**Never state a number the source did not state.** No derived multiples, no implied valuations, no rounding into a different figure. Quote what was published and attribute it.

**Where the sources disagree, say so** and give both, with their dates. Reconciling them is the user's work, and a watch that silently picks one hides the fact that there was a choice.

**If the run has no external reach** — no search or fetch available in the unattended context — write that as the run file's only content. Never fall back to what the model remembers: an unattended report that cannot be told apart from a sourced one is the failure this rule exists to prevent.

## 4. It reports; it does not advise

No recommendation, no target or view of its own, nothing on whether something is cheap, expensive, attractive or risky. A broker's target is reported as that broker's act (§2), never adopted. **Nothing that reads as a suggestion to buy, sell or hold**, for any name, in any wording, including a "what this means" section that arrives at one.

The line is: what happened and who said it, versus what the user should do. The second belongs to the user, who is the licensed professional here, and a watch that crosses it puts its conclusions into their client work under their name.

## 5. Where it writes

One file per date: `watch/runs/YYYY-MM-DD-market-watch.md`. A second run on the same day appends a
`## Run at HH:MM` section to that file rather than creating another. The file holds

- **the window covered, and its end recorded as the point the next run starts from.** A run opens
  where the previous one closed, whatever the clock says; one with no recorded end to start from -
  the first, or one after a run that read nothing - covers the previous five weekdays
- the items, grouped by name or sector as `coverage.md` groups them, each with source and date
- **Nothing moved** where that is the answer
- what could not be read, and why

It writes nothing else — not a memory file, not `coverage.md`, not a scope. The memory pass picks the run files up like any other work.

## 6. Running it unattended

Registered with the host harness as a weekday task; the schedule lives there. The task's prompt names this instance's absolute path and says to read this file and follow it.

**Nobody is watching**, so: read, write the one run file, stop. No questions — there is nobody to answer, and a stalled pass produces nothing and reports nothing.

If `AGENTS.md` is missing from the path the task names, the instance is gone or moved. Write no run file - there is no instance to write it into - and say so in the task's own output, which is the one place left that somebody will read. Then stop.
