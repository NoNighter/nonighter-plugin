# Instructions — Memory Maintenance

> How this instance's memory is written: the daily pass that reads the session transcripts and writes every memory file, and the reconciliation with whatever the host harness keeps for this tree. Read in full before touching any memory file.

Activity type: **task (recurring, daily)**. An agent in this file is running the pass or writing a record — never doing project work. This is the **only** file in the instance where harness-specific mechanics are stated, so porting this instance to a different agent harness means rewriting §5 and nothing else.

## 1. Who writes what

| Layer | Path | Written by |
|---|---|---|
| `## Open threads` / `## Settled` | inside each memory file | the session, propose-first |
| the scope-less buffer | `MEMORY.md` | this pass |
| each scope's buffer | `<scope>/memory-<topic>.md` | this pass |
| durable records | `memory/records/<slug>.md` | this pass |
| the records index | `memory/index-memory-records.md` | this pass |
| the verbose log | `memory/archive/YYYY-MM-DD_HHMM-<topic>.md` | this pass |
| per-run reports | `memory/runs/YYYY-MM-DD-memory-pass.md` | this pass |

**Sessions do not checkpoint and do not offer to.** A second writer makes this pass's reconciliation guesswork: the pass cannot tell a fact it derived from the transcript apart from a fact a session asserted, so it cannot tell which one to trust when they disagree.

## 2. The band

**Every buffer: floor ~600 tokens, compress back when it reaches ~2,000** (estimate as words times 1.33). A buffer over the ceiling is drained, not trimmed: the verbose entry goes to `memory/archive/`, the live entry stays, and anything durable becomes a record.

**The shape is checked mechanically, every run.** `python memory/check-memory-structure.py` reports every memory file that misses a required section, duplicates an H2, levels `Settled` wrong, carries a section outside the `CONVENTIONS.md` §4 list, or runs over band. Fix what this pass caused and report the rest. A wrong heading is not cosmetic — it is a section the day plan cannot see, and prose rules with no check behind them are what let a memory system drift in the first place.

**The records index carries its own budget (~800 tokens)** because `AGENTS.md` loads it every session. An index line **routes; it never asserts.** A record earns a staleness banner when it is opened; an index line gets none, so a claim there is an unstamped assertion in every session's context. Write *where the deal files live and the two gotchas*, never *the deal files are on the mapped drive*.

## 3. The record

One file per durable fact, at `memory/records/<slug>.md`. Frontmatter:

```
---
name: <short-kebab-slug>
description: <one line, used to decide relevance during recall>
metadata:
  type: scope | fact
  last-verified: YYYY-MM-DD
---
```

Body: the fact. Link related records with `[[their-slug]]` — link liberally, and a link to a record that does not exist yet is fine, it marks something worth writing.

**A record holds only what does not survive reading the authoritative document.** An address. A supersession. A non-obvious access route. A decision and why. The fact that two documents contradict each other and were deliberately left that way. Restating a document's content creates a second version that drifts silently and suppresses its own correction — a summary already in context removes the reason to open the source.

**Two kinds.** A **scope record** is named for its scope's folder, so coverage is mechanical: a scope whose `memory-<topic>.md` Status says `active` with no matching record is a finding. It carries the address, the file spine, the access route, and what is contested — **never current phase or next actions**, because those move and this file loads unconditionally. A **fact record** takes a free slug for anything belonging to no scope: tool gotchas, environment traps, binding decisions, and rules the user stated in passing — *"this client's models are always unlevered"*, *"invoices go out on the 10th"*. A rule about how work is done *with* the user is theirs and belongs in `operating-manual.md` §5, not here; a rule the *work* must satisfy across more than one job belongs in `knowledge-base/`, where the work will look for it. What lands here is everything else.

**Convert relative dates to absolute** on the way in. A phrase like *last week* is unreadable in three months.

## 4. The pass

Run daily. Each step writes before the next begins, so an interrupted pass leaves a partial but consistent state.

1. **Read the day's transcripts.** Whatever the harness holds for sessions in this tree (§5). Two selection rules, and both are needed:

   - **Select by first message timestamp, not by the file's modified time.** A transcript touched by an unrelated read re-enters the window on modified time and fakes work that never happened.
   - **Also take any transcript whose *last* turn is later than the cut-off of the previous run**, whatever day it started, and read only the turns after that cut-off. A session left open across midnight keeps its first-message timestamp in yesterday, so the first rule alone drops every turn it gained today — and drops them permanently, because tomorrow's pass will not reach back for them either.

   The previous cut-off is named in the last run report; record this run's cut-off in this run's report (step 10). Without it the second rule has nothing to compare against, and a long-running session is either re-read whole every day or lost.

   **The cut-off is the moment reading stopped, never the clock when the pass ends.** Take the timestamp of the newest turn actually read, or the moment step 1 finished - and then hold it, unchanged, through everything that follows. Steps 2 to 11 write for a long time: a measured pass recorded `18:07Z` and finished its report at `18:18Z`, eleven minutes later, while two sessions were still being typed into. Stamping the clock at the end would put those eleven minutes *before* the cut-off, so the next pass would skip turns nobody ever read - and skip them for good, because no later pass reaches back either. It is silent, it scales with how long the pass takes, and the only trace is work that never made it into memory.

   The user does not have to stop working while this runs, and must never be asked to. Turns written after the cut-off belong to the next pass, which is the whole point of recording one. And it reads *turns*, not whole conversations, so a thread left half-finished contributes what it had and the rest arrives tomorrow.
2. **Sort by scope.** Each piece of work belongs to exactly one scope, or to none. Scope-less work goes to `MEMORY.md`.
3. **Write the verbose entry** to `memory/archive/YYYY-MM-DD_HHMM-<topic>.md`: full facts, filenames, IDs, decisions verbatim, numbers. This is the durable copy and it is never compressed.
4. **Write the live entry** to the scope's buffer: a `### YYYY-MM-DD` heading plus tight bullet facts. Past tense, active voice. No adjectives, no connectors, no ceremony. Refresh the Status block — `State:` and `Phase:` only, overwritten, not appended — and update `## Standing facts` when a decision is taken or reversed.
5. **Promote, correct, prune.** A fact that has proved durable becomes a record. A record contradicted by the day's work is corrected in place and its `last-verified` bumped. A record whose subject no longer exists is deleted, and its index line with it.
6. **Reconcile against the harness store** (§5).
7. **Drain any buffer over the band** — archive the old entries, keep the recent tail.
8. **Run `memory/check-memory-structure.py`** and fix or report every STRUCTURE finding.
9. **Regenerate the index** from `memory/records/`, one routing line per record.
10. **Write the run report** to `memory/runs/YYYY-MM-DD-memory-pass.md`: which scopes moved, what was promoted, what was corrected, what the reconcile found, the **read cut-off** this run used - the moment reading stopped, per step 1, not the time the report was written - and anything the transcripts left ambiguous.
11. **Tell the user what changed, in their words.** §7.

**Aging compresses the log; it never rewrites history.** An entry is shortened or archived. It is not edited to say something different from what it said.

## 5. Reconciling with the harness store — the only harness-specific section

The host harness keeps its own memory regardless of this instance. **The instance wins every tie.** A fact the harness learned and the instance lacks is written into `memory/records/`. A fact the instance holds and the harness contradicts is corrected in the harness store. Neither store is deleted; they are made to agree.

Reconcile at step 6 of every pass, and record in the run report which direction each correction went.

**Claude Code.** Its store is keyed to the working directory the session ran in, under the user profile at `.claude/projects/<working-directory-slug>/memory/`, where the slug is the absolute path with its drive-colon and separators replaced by hyphens. Two consequences to handle rather than fight:

- **One instance can have several stores.** A session started in `{{HOST_PATH}}` and a session started in a subfolder of it produce different slugs and therefore different stores. Enumerate every slug that resolves inside `{{HOST_PATH}}` and reconcile against all of them. This is precisely why the instance's own `memory/records/` is authoritative — a store keyed to a path string cannot represent one instance.
- **Transcripts sit beside the store**, under the same slug directory. That is the input to step 1.

**Another harness.** Unknown until one is targeted. Rewrite this section then; nothing else in the instance names a harness.

## 6. Procedure and exit

One pass per day. It is complete when every buffer is inside the band, every live scope has a record, the index has one line per record and no line without a file, the run report is written with its read cut-off, the reconcile direction is recorded for every correction, and the user has been told what changed (§7).

**Propose before deleting a record or a scope buffer.** Everything else in the pass is unattended.

## 7. What to tell the user

**Report the work, not the machinery.** The user owns the work this instance holds; they are not a maintainer of the memory system and did not ask to become one. Four things, a line or two each:

- **What was recorded** — which pieces of work moved, in the names the user uses for them.
- **What is still open** — the threads that need their next move.
- **What needs a decision from them**, and why it is theirs rather than yours.
- **Anything the transcripts left ambiguous**, stated as a question they can answer.

**Leave the vocabulary of this file out of it.** Buffers, bands, slugs, frontmatter, `last-verified`, the reconcile direction, hash counts, filenames of archive entries — these are how the pass works, not what happened. Where an internal detail genuinely changes what the user should do, state the consequence and drop the mechanism: not "the buffer is at 1,840 tokens of a 2,000 ceiling", but nothing at all, because that is the pass's job and not theirs.

**Propose actions; never add them silently.** `## Open threads` is propose-first (§1), so the report is where a new action is put to the user. One line each, and no more than a handful — a list of twenty is a list nobody reads.

**A pass that found nothing says so in one line.** Padding a quiet day with detail teaches the user to skip the report on the day it matters.
