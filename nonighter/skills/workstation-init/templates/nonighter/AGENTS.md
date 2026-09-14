# AGENTS.md

> Entry point for the workstation at `{{HOST_PATH}}`, auto-loaded every session through the host folder's `CLAUDE.md`. It names what to read and the loop to follow; it holds no role detail, project history, or folder prose of its own. This instance is **{{INSTANCE_NAME}}**, and its work belongs to **{{ORG_NAME}}**.

**What this is.** A set of files that let a session start where the last one stopped, instead of being briefed again. Its parts:

- **Retrieval** — this file, plus one folder per piece of work holding that work's own instructions and memory.
- **Memory** — what was decided, what happened, and what is still open. Written by a daily pass, never by a session.
- **Conventions** — how every file here is written, and where a new piece of work goes.
- **Identity** — who the user is, what this folder is for, and how they want work done.
- **Tools** — how anything outside the filesystem is reached, and what has already been reached.
- **Knowledge base** — criteria that apply to more than one job.
<!-- if:context -->
- **Context** — what material exists and where it sits, indexed so a session never walks the folder tree.
<!-- /if:context -->
<!-- if:watch -->
- **Watch** — what moved in the outside world for the names the user follows.
<!-- /if:watch -->

Two run on a schedule without being asked: the **daily memory pass**, and a **weekly improvement pass** that only ever proposes.

Every path below is relative to `.nonighter/` unless it starts with `../`, which means the host folder.
<!-- if:nested -->

**Precedence.** Another instance sits in this folder's line — see `nested` in `instance.json`. **The nearest instance governs its subtree:** when a session starts in a folder that has a `.nonighter/` below this one, that instance's files are the ones to read and these are not. Never merge two instances' conventions, memory, or retrieval maps in one context.
<!-- /if:nested -->

## Memory

**You do not write memory, and you do not checkpoint** — not mid-session, not at the end, and do not offer to. The daily pass reads the session transcripts and writes every memory file on your behalf; record decisions and outcomes in the conversation and the pass harvests them. Four layers, and a fact lives in exactly one: `## Open threads` / `## Settled` inside a memory file — the one place a session edits, propose-first · the rest of `memory-<topic>.md`, a buffer the pass drains · `memory/records/`, the stable facts · `memory/archive/`, the verbose log — the pass writes all three. **Never touch Status, Standing facts, or Recent memory.** File shapes: `CONVENTIONS.md` §4.

Read a scope's `memory-<topic>.md` on entering it; `MEMORY.md` is the scope-less bucket.

## Session start files

Load before any task, in order: **1.** `operating-manual.md` — who the user is, what this folder is for, how work is done here, and any preference they have stated. **2.** `MEMORY.md` — recent scope-less work. **3.** `memory/index-memory-records.md` — the durable facts this instance holds.
<!-- if:context -->
**4.** `context/index-context.md` — what material exists and where. Carrying it costs less than a session walking a folder tree for a document that was already described.
<!-- /if:context -->
**5.** `knowledge-base/index-knowledge-base.md` — criteria that apply to more than one job. Carried from the start rather than read on demand, because a criterion nobody looks up is a criterion that does not apply: a session building a model does not think of itself as needing "general domain knowledge", which is exactly when the house rule it should be following sits unread.

## Retrieval map

Load only what the task needs.

| Situation | Read |
|---|---|
| Initiative, project, or task work | `initiatives/` · `projects/` · `tasks/` → that scope's `instructions-<topic>.md` + `memory-<topic>.md` |
| What to do next inside a scope | that scope's `memory-<topic>.md` → `## Open threads` |
| Work that executes outside this folder — a shared library, a client folder, a mailbox | the owning scope's `memory-<topic>.md` **here**. The work list lives in the instance, never only where the work runs; one body of work never splits across two scopes |
| Deciding whether work earns a new scope, classifying it, or placing it | `CONVENTIONS.md` §2 — the create test and the three activity types with their homes. Read before creating any work folder |
| Creating or editing **any** instruction file, reference file, or folder | `CONVENTIONS.md` — **mandatory**, every time |
| Writing or reconciling a memory record, or running the daily pass | `memory/instructions-memory-maintenance.md` — **mandatory** before touching any memory file; also the only home of harness-specific memory mechanics |
| Running the weekly improvement pass, or writing a proposal it produced | `improvement/instructions-improvement-pass.md` — it proposes only; the maintenance pass applies what a person approves |
<!-- if:watch -->
| Running the market and deal watch, or changing what it reads for | `watch/instructions-market-watch.md` → `watch/coverage.md`, which is the user's and the only definition of coverage |
<!-- /if:watch -->
<!-- if:context -->
| Where a document, model, or folder lives — inside this host folder or in a shared library | `context/index-context.md` → the lower index it names, where there is one → the card → the file. Never walk the estate. To search by what the material is *for* rather than where it sits: `context/tag-dimensions.md` |
| Adding, removing, or re-scoping a context source, or running the conformance check | `context/instructions-context.md` |
<!-- /if:context -->
| Any connector, script, or scheduled job — or batch tool work over more than ~5 similar items | `tools/instructions-tools.md` — the execution-route rule, **mandatory** before any such call — then `tools/index-tools.md` for the route to the system |
| General domain knowledge held for reuse | `knowledge-base/index-knowledge-base.md` |
| Checking, upgrading, or removing this instance | the `workstation-init` skill — explicit trigger only |

Within a scope folder, read the instructions file at **both** the folder root and the active subfolder. A recurring task states its cadence and trigger in its own instructions; per-run records go under `runs/`.

## Operating loop: source context → perform → verify

**Source context.** Work is organized into scopes — initiatives (`initiatives/`), projects (`projects/`), tasks (`tasks/`): one folder per effort holding its instructions and accumulated memory, so any session entering it continues where the last left off. Locate the task via the retrieval map. If no scope fits, work scope-less — most requests earn no scope. Work that continues past this session, recurs, or leaves state future sessions will need is the signal to read `CONVENTIONS.md` §2 and follow its create discipline.

**Perform.** Work inside the relevant scope folder; it is the source of truth. Update it with notes, decisions, and progress. A file sits at a scope's top level only if it spans many sessions, applies to the whole scope, or is in active use — completed working files go to `archive/`, single-task files to a dedicated subfolder. No loose temp artifacts at a scope root.

**This instance governs `{{HOST_PATH}}` and nothing above it.** Work in the host folder freely. Reaching outside it — a shared library, another user's folder, a system path — is reading, not writing, unless the user names the destination. Outbound actions (send, publish, push) are confirm-first, including from a script: a script prepares and prints, and the outbound step goes through the confirm-first tool.

**Verify before returning.** Output meets the stated goal. Numerical and factual claims are correct — verify programmatically where possible. Referenced files exist. Surface assumptions and uncertainties rather than burying them.
