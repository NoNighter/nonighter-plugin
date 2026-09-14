# CONVENTIONS.md

> How work in this instance is classified, and how its instruction and reference files are authored. Read on demand when classifying a piece of work, or creating or revising any `.md` file inside `.nonighter/`.

---

## 1. Header & description — the file's first ten seconds

The H1 and the immediately following blockquote are how a reader (human or agent) decides whether the file is what they need. Both are mandatory.

- **H1 = the filename** for instance-root files (`# AGENTS.md`, `# MEMORY.md`). For topic files, either the filename or a short purpose-title (`# Operating Manual — <name>`). Pick one form per file type and use it consistently.
- **Blockquote description = one sentence, two parts.** What this file *is*, and *when it is read*.
- **Nothing between H1 and blockquote.** No intro paragraph, no "Overview" heading. H1 → blockquote → first real section.
- **Skip "Last updated" footers.** Working files change too often for a date stamp to be reliable; the filesystem timestamp is the source of truth.

## 2. Activity classification — initiative, project, task

Before creating any work folder, decide whether the work earns a scope at all (see *When a scope is created* below), then classify it as one of three types and put it in the matching folder.

| Type | What it is | Home |
|---|---|---|
| **Initiative** | Involves one or more projects and coordinates them; significant enough that its own progress is worth tracking above the projects beneath it. | `initiatives/<initiative>/` |
| **Project** | An organized set of tasks with an end state, an expected deadline, and a significant length of time — a week, weeks, or months. | `projects/<project>/` |
| **Task** | More immediate, a short timeframe (a day or days), and does not fall under the scope of an existing project. | `tasks/<task>/` |

**Declare the type.** Each scope's `instructions-<topic>.md` names its activity type in the scope-boundary line (e.g. *Activity type: task (recurring)*) — the type sets what the file must specify and how the folder is shaped.

**What each must specify.**

- **Initiative** — the projects and processes it coordinates and where each lives; it routes, it does not hold the work.
- **Project** — its end state and the tasks or subfolders that reach it.
- **Task** — the steps and the trigger to run them. A task producing per-run records keeps them under a `runs/` subfolder; a one-shot task can be a single dated file instead of a folder.

**Recurrence is not a type.** A recurring task is a task that states a cadence or trigger in its own instructions.

**A folder is created when its first real item arrives.** `initiatives/`, `projects/` and `tasks/` do not exist until something goes in them.

**No folder here carries a number prefix.** Not `01-`, not `02-`, whatever order feels natural. A number is a promise about position, and it cannot be kept in a tree where a folder appears the day its first item arrives: numbering the folders that exist at install leaves gaps the moment a scope folder is created, and numbering around the ones that do not exist yet starts the visible tree at `04-`. Both were shipped and both were wrong. Name the folder for what it holds and let the alphabet order it.

**Work already in the host folder is adopted where it sits.** Where `{{HOST_PATH}}` already holds a real project, create the scope under `projects/<project>/`, put the instructions and the memory there, and record the absolute path to the materials where they already are. Never relocate a user's files to make the layout tidier — moving content breaks the shortcuts, sync links and tools built around the old path, and the value of the scope is the description, not the location.

### When a scope is created

A scope is earned by continuity, not by topic. Most requests — a question, a lookup, a one-off edit, a deliverable finished in one sitting — create nothing: do the work; the daily pass records it in `MEMORY.md`.

**Create test.** Create a new scope only when all three hold:

1. **Continuity** — the work continues past this session, or recurs on a stated cadence or trigger.
2. **End state** — a done-when can be stated (for a recurring task: a cadence and a per-run output).
3. **Accumulation** — future sessions will need state this one produces: files, decisions, open threads.

**Look for an existing home first.** List the scope folders (`initiatives/`, `projects/`, `tasks/`) and check `memory/index-memory-records.md`. The folder listing is the roster — there is no roster file to maintain. Work that extends an existing scope goes there — a subfolder or an `## Open threads` row, not a sibling scope.

**A returning topic earns the test.** A topic that fails the test today may return. When an untracked topic already appears in `MEMORY.md`'s recent entries and comes up again, or the user repeats the same request a second or third time, apply the create test then — a repeated request is a recurring-task signal.

**Start small, promote when outgrown.** Take the smallest type in the table that fits. A task becomes a project when it acquires an end state weeks out and distinct workstreams; a project becomes an initiative only when it coordinates more than one project. Promotion follows the same create discipline.

**Create clear cases, propose the rest.** When all three conditions clearly hold, create the scope and report it in one line — type, name, home folder, done-when (or cadence) — with the `instructions-<topic>.md` + `memory-<topic>.md` spine (§4, §6). When any condition is uncertain, or the type or home is ambiguous, state that same line as a proposal and create on approval.

## 3. Writing rules — apply to every file in this instance

- **Minimal expression — the first rule.** Say the one thing the section exists to say, then stop. If you can cut words and keep the meaning, cut them. Delete any line that restates the heading, decorates the rule, or does not drive behavior.
- **State what is, never what is not.** Define a file, scope, or rule by what it covers. Do not enumerate what it excludes, contrast it with neighbors, or add "this is not X" disclaimers — the positive statement already draws the boundary. Include an exclusion only when the user explicitly asks for one.
- **Name people by role; address the agent as *you*.** The human directing the work is "the user," the downstream consumer is "the end user," and the agent is addressed in the second person. Never use a proper name, "I," or "me" — those are ambiguous once the file loads into a new context. The binding to a real person lives only in `operating-manual.md` §1.
- **Voice follows where the text lives.** A file *body* commands the agent (second person, a manual). A `description` field is *about* the file (third person, a catalog entry).
- **Each section states only its own content.** Do not forward-explain what another section or file covers. When tempted to explain a neighbor, cross-link by path instead.
- **Point, don't paraphrase.** When a file directs the reader to another file, the pointer is the full entry — never summarize the target's rules alongside it. The reader opens the target anyway, so a summary is pure redundancy and it silently drifts the moment the target changes. Every rule lives in exactly one file; everywhere else, a path.
- **One file, one purpose.** If a file does two things, split it. The retrieval trigger must be obvious from the filename and description alone.
- **Concrete over abstract.** Filenames, paths, IDs, exact commands. Not "the relevant folder" — `projects/<project>/`.
- **Imperative voice for rules.** "Read this file at session start" — not "this file should be read at session start."
- **Tables for lookup, prose for reasoning.** Tables work when the reader is matching a known key to a value. Prose works when the reader needs to understand a rule.
- **No promiscuous auto-loading.** A file enters the auto-load chain only with an explicit purpose and token budget; everything else is on-demand.
- **Cross-link by path, not by name.** `projects/<project>/instructions-<topic>.md`, not "the project's instructions file."
- **This instance writes nothing into a folder it does not own.** Everything it produces lives inside `.nonighter/`. Where a file must nonetheless be written outside — the user asked for it by name, for their own purpose — it has to read correctly for someone who has never installed anything: no reference to `.nonighter/`, to this instance, or to the user's own layout, and any fact it needs from the instance stated in it rather than pointed at. Until 0.6.0 context cards were written into the described folders and this rule was written for them; they are now held in the instance, so it applies to nothing by default.

## 4. Per-file-type structure

### `AGENTS.md` — the instance router

The entry point, reached from the host folder's `CLAUDE.md`. It routes and defers, holding no content of its own. Sections, in order: header → what this system is and its parts → Memory → Session start files → Retrieval map → Operating loop. No task catalog — the instance root has no discrete tasks, so folder routing lives in the retrieval map.

**It is auto-loaded every session, so it carries a budget: ~1,700 tokens with the optional systems off, ~1,900 with all of them on.** Those are measured off a stamped instance, not aspirational — the figure here was ~1,300 for a file that actually weighed ~2,400, which is a budget that catches nothing. Roughly a third of the current file is the retrieval map, and that is the floor: it is the part that stops a session opening the wrong file. Anything added here is paid for in every session of every instance, so a rule that can be read on demand belongs in the file that owns it.

### `CLAUDE.md` — the host folder's entry point

Sits in the host folder, not in the instance, because Claude Code auto-loads `CLAUDE.md` and not `AGENTS.md`. **It is the only file this system writes outside `.nonighter/`.** Three parts and nothing more: a line saying what the folder is, the **marked route block** sending the session to `.nonighter/AGENTS.md`, and whatever the user chooses to add. It carries no routing or procedure of its own — a second copy of the router here is exactly what drifts out of sync.

**Only the span between the two markers belongs to this system.** It is refreshed on upgrade and removed on uninstall; everything outside it is the user's and is never read or altered. Never add a rule outside the block expecting a later session to honour it, and never widen the block to carry one.

### `instructions-<topic>.md` — scope entry point

Tells an agent how to work in one scope. On-demand. An instructions file is a **router, not content**: it drives intentional retrieval and defines procedure. Keep it thin and link-heavy — if any section grows past a screen, that content belongs in a linked file named in the retrieval map.

Six sections, in order (Goals is request-only):

1. **Header + scope boundary.** State what work belongs here and one line of "when an agent is in this folder, it is doing X." Name the **activity type** (§2). The positive scope is the boundary; do not list what falls outside it.
2. **Memory.** Immediately after the header. Use this wording verbatim, changing only the topic slug:

   > `memory-<topic>.md` in this folder holds what just happened here and the current phase. Read it at session start.
   >
   > Do not checkpoint. The daily pass at `memory/instructions-memory-maintenance.md` reads the session transcripts and writes this file, the archive, and the memory records on your behalf. Record decisions and outcomes in the conversation; the pass harvests them.

3. **Goals (request-only).** Include only when the user asks this scope to carry goals. Concrete, verifiable targets; omit the section otherwise.
4. **Retrieval map.** Situation → read these files, in this order, each marked **always-load** or **load-on-demand**. This is where lazy loading is encoded, and where source-of-truth files are referenced together with their handling rules.
5. **Task catalog.** One thin entry per task: trigger, the context it depends on, a one-line description, and a pointer to where the detailed procedure lives. Detail lives in the linked file, not here.
6. **Procedure + iteration.** Order of operations, decision points, and explicit stop conditions. Iteration without exit criteria produces agents that re-check forever.

### `readme-<topic>.md`

Explains a **system** a non-technical human cannot understand from its own materials — code, scripts, config, connectors, unattended jobs. That is what a readme is for, and the only thing it is for.

Write one only when the folder holds materials that are not understandable without a plain-language explanation of what the system is, how it runs, and what breaks it; or when the user asks for one.

**Otherwise, no readme — a hard default, not a preference.** A folder of documents, a project, a task, a reference library: its filenames, its contents, and any `instructions-<topic>.md` already say what it is. A readme there is a second orientation to keep in sync, and the first thing to drift. Do not write one because a folder looks bare or because the contents took work to produce.

When one exists: what the system is and how it is invoked, a table of folder contents with one line each, and the operating detail — setup, run, configure, debug. No live state.

### `index-<topic>.md`

Pure lookup catalog: find a resource by name or topic, get a path. Sortable by the dimension the reader searches on. Path is the key column; description is one line. No prose, no instructions, no commentary.

### `MEMORY.md` / `memory-<topic>.md`

Persistent state, organized **by time, not by topic**. Size-disciplined. **Written only by the daily pass** — sessions do not checkpoint, and no session writes either file except the `## Open threads` / `## Settled` exception below. `MEMORY.md` is the scope-less bucket; each `memory-<topic>.md` is the short-term buffer for one scope.

**The skeleton is fixed.** Every memory file has this shape, in this order. Heading text is literal — the tooling matches on it, so a renamed or re-levelled heading silently drops that section from the day plan.

```markdown
# memory-<topic>.md

> Short-term memory for <scope> — what just happened, where it stands, what is next. Read on demand when this scope is in play.

## Status

- **State:** active | blocked | paused | done
- **Phase:** where the work stands, one line

## Standing facts

- decisions taken and constraints still true until reversed; curated, not appended

## Recent memory

### YYYY-MM-DD — headline naming what happened

- tight bullet facts; filenames, IDs and numbers verbatim

## Open threads

<!-- next-id: XXX-1 -->

### Ready

### Blocked

### Later

## Settled
```

**Sections.** The five above are required and are the whole file. `## To promote` — durable facts staged for a record — is the one permitted addition, and only while it holds something.

| Section | Holds | Written by |
|---|---|---|
| `## Status` | `State:` and `Phase:`, nothing else. Overwritten, never appended | the pass |
| `## Standing facts` | decisions, constraints and scope-specific traps that stay true until reversed. Curated and deleted from, never appended to; ~10 lines. This is what a reader needs before touching the work | the pass |
| `## Recent memory` | the dated log, newest first — the only temporal section | the pass |
| `## Open threads` | `### Ready` / `### Blocked` / `### Later` action tables | sessions, propose-first |
| `## Settled` | the recent tail of closed items. **H2 — never `### Settled` nested under Open threads**, which hides it from the digest | sessions, propose-first |

**Nothing else is a section.** A watchlist, a bug list, a run log, a file index — a second temporal log under another name is the same log twice, and a standing list is not memory. Rules, routing and the scope's file spine go to its `instructions-<topic>.md`; a running list to its own `index-<topic>.md`. A decision or a trap goes in `## Standing facts`. A memory file answers five questions and no others: where does this stand, what is already decided, what just happened, what is next, what is closed.

**No per-file writing guide.** These rules load before any memory file is touched, so a `## How to write this file` section inside one is a copy that drifts.

**Entry shape.** `### YYYY-MM-DD — headline`, headline 20 words or fewer, then bullet facts: past tense, active voice, numbers and filenames verbatim, no paragraphs, ~250 tokens per entry. A recurring task whose real record is a dated brief under `runs/` gets a **one-line pointer per run**, never a restatement.

**Band: floor ~600 tokens, compress when the file reaches ~2,000** (estimate as `words × 1.33`). These are buffers, not stores. The pass drains them — the verbose entry to `memory/archive/YYYY-MM-DD_HHMM-short-topic.md`, durable facts to records, the oldest dated entries out verbatim. **Aging compresses the log; it never rewrites history**, and `## Open threads` / `## Settled` are never trimmed.

**`MEMORY.md`** takes the same skeleton with `## Status` and `## Standing facts` omitted: it is a bucket, not a scope, so it has no state to report and no standing facts of its own — a durable instance-wide fact is a record.

**Staleness between passes is expected.** A scope worked at 14:00 has nothing here until the next pass. That is the trade: the session spends its time on the work, and the record is assembled from the transcript afterward.

**Conformance is mechanical.** `memory/check-memory-structure.py` reports every file that misses a required section, duplicates an H2, levels `Settled` wrong, carries a section outside the table above, or runs over band.

### memory record — one durable fact

One fact that outlives any one session, held at `memory/records/<slug>.md` and routed by `memory/index-memory-records.md`. Two kinds:

- **Scope record** — one per live scope, named for the scope's folder, so coverage is a mechanical check: a folder holding a `memory-<topic>.md` whose `State:` is live, with no matching record, is a finding. Carries the address, the file spine, the non-obvious access route, and what is contested or superseded. **Never current phase or next actions** — those move.
- **Fact record** — free slug, for anything belonging to no scope: tool gotchas, environment traps, binding decisions, the user's own preferences.

Written only by the daily pass. **A record holds only what does not survive reading the authoritative document** — an address, a supersession, an access route, a decision, or the fact that two documents contradict each other and were deliberately left that way. Restating a document's content creates a second version that drifts silently and suppresses its own correction, because a summary already in context removes the reason to open the source.

Frontmatter, index budget, and the reconcile / promote / prune operations: `memory/instructions-memory-maintenance.md`.

### `card-<slug>.md` — context card

One file or folder worth more than an index line, described so an agent can decide whether to open it without opening it. Lives at `context/cards/<source-slug>/card-<slug>.md` — **always inside the instance, never in the folder it describes.** Its subject's real location is a key in the block, not the card's own position.

A card is a **fixed-key block, not prose**, so the indexes above it are assembled mechanically:

```
path: <where it sits, relative to the source root>
holds: <one line — what a reader comes here for>
for: <who or what it serves>
work: <the kind of work it serves>
kind: <what kind of thing it is>
authority: canonical · current · superseded · archive
vintage: YYYY-MM
provenance: inferred from contents, unconfirmed | confirmed by <role>, <date>
read-first:
  - <file> — <why>          (a folder card only)
do-not-modify:
  - <file or subfolder> — <why>
children:
  - <subfolder or file> — <one line>   (a folder card only)
```

`for`, `work` and `kind` are the tag dimensions. Their meaning and the values in use are in `context/tag-dimensions.md`, which is the only place a value is added — **reuse a listed value rather than coining a synonym**, and omit a dimension that does not apply rather than filling it with a placeholder.

**Depth scales with what the material is worth returning to.** Reusable material earns a card: past client work, a model or deck that would be a starting point again, a price book, a playbook, a dataset. Routine and closed material earns an index line and no card of its own. Describing everything equally is how the cost runs away.

**Nothing authoritative is machine-written.** A card whose `provenance` is still `inferred` may be rewritten by the conformance run. Once a human confirms it, the run never overwrites it — it only reports a conflict.

**A card is internal, so it is written for this instance and no one else** — it may name the instance, its paths and its user freely. That is the one thing the old in-place descriptor could not do. Full rules: `context/instructions-context.md`.

### `summary-<slug>.md` — source card

A one-page card fronting a single source — a book, a course, a long video, a report — inside that source's own folder under `knowledge-base/`, beside the full write-up it introduces: the core thesis, the ideas worth remembering, why it matters for the work done here, and its tags. Read before the write-up. Under ~450 words; header per §1; no checklists, no note counts, no date stamps. Rewritten whenever the write-up changes.

It exists because a long write-up is expensive to open just to find out whether it is the right source. Nothing else in the knowledge base rolls up: cross-source themes are drawn at read time, and `index-knowledge-base.md` carries one line per entry.

### `notes-<topic>.md` — record store

Things kept on purpose that have no home elsewhere: to-do lists, captured thoughts, content read or heard worth keeping. On-demand, and **created only when the user explicitly asks** — never auto-scaffolded, never seeded speculatively.

Body organized under H2 headings, one per kind of record. Add a heading when its first record arrives; do not pre-create empty ones. Records earn their place: when one grows into a real artifact or finds a proper home, graduate it there. Notes are the staging area, not the destination.

### `principles-<topic>.md` — scope design principles

The durable design rationale for one scope — the decisions and rules that govern how its work is done, distinct from the day-to-day procedure in `instructions-<topic>.md`. On-demand; added to a scope only once it has accumulated design decisions worth stating once instead of re-deriving each session.

### `## Open threads` / `## Settled` — the work list, inside the memory file

The actionable to-do list for one scope, held as two sections of that scope's `memory-<topic>.md`. `MEMORY.md` carries the scope-less ones.

**Actions are the one exception to "sessions do not write memory."** They are live state the user changes in conversation and cannot wait for the next pass, so a session may edit these two sections — propose-first, always. Everything else in the file belongs to the pass.

**Item granularity.** One item = one sitting with a checkable end. Larger work is a milestone: it stays in the scope's Recent memory or instructions, and Open threads carries only its next slice.

**Columns**, so a digest reads as one table across every scope:

| Column | Content |
|---|---|
| ID | scope prefix + number (`{{INSTANCE_PREFIX}}-3`) |
| Item | the action, imperative |
| Done when | the checkable end state — a file that exists, a number that ties, a message that is sent. One line. Never a restatement of the item. |
| Added | ISO date the row was created. **Set once, never updated** — it is the only field that makes an item's age visible, and age is what forces a stale item back to a decision |
| Autonomy | `auto` · `review` · `user` (`operating-manual.md` §4) |
| Pri | `P0` critical path · `P1` next · `P2` later. Never let everything become P0. |
| Size | `S` under an hour · `M` one sitting · `L` more than one sitting — slice an `L` before picking it up |
| Blocked by | the person, item ID, or input it waits on |

**Each bucket carries only the columns it uses:**

| Bucket | Columns |
|---|---|
| `### Ready` | ID · Item · Done when · Added · Autonomy · Pri · Size |
| `### Blocked` | ID · Item · Done when · Added · Autonomy · Pri · Blocked by |
| `### Later` | ID · Item · Done when · Added · Pri |

There is no `Due` column: a date nobody maintains reads as a deadline nobody set. A real deadline belongs in the Done-when sentence, where it is stated rather than implied.

**Sections, in order:** under `## Open threads` sit `### Ready` (nothing is stopping it) → `### Blocked` (something external stops it; every row names what) → `### Later` (nothing stops it, deferred on purpose). `## Settled` follows as its own H2.

The three answer two questions at once — can this be acted on, and do you intend to soon — so there is no fourth combination to hold. "Only the user can do it" and "a draft is waiting with the user" are **not** buckets: `Autonomy` already carries both.

**Staleness is re-decided, not tolerated.** A `Ready` row whose `Added` date is more than ~30 days old, and a `Blocked` row blocked that long, are surfaced for a decision — keep, defer, or drop. `Later` is exempt: deferring on purpose is a decision, and re-asking about it is not a service.

**`## Settled` is a guard with a lifetime, not an archive.** It exists so anything proposing work can tell an item is already closed before proposing it again, and so a `dropped` decision does not read as an invitation to retry.

- One line per closed item, newest first: **ID · title · outcome · close date**.
- Outcome is one of `done` · `dropped` · `superseded by <ID>`.
- Age rows out past **~30 days or ~10 items, whichever comes first**. Nothing is lost — the memory buffer and `memory/archive/` carry it.
- Work that legitimately returns takes a **new ID** referencing the old one. Never move a row back out of Settled.

**IDs.** Each scope numbers its own items from a declared prefix, so an item is added without touching the instance root. The ID travels with the item between sections; never renumber, never reuse. New items take the next number from the file's `<!-- next-id: {{INSTANCE_PREFIX}}-7 -->` comment, bumped in the same edit.

## 5. Naming schema

One file per type per folder. Instance-root files are CAPS with no topic suffix — the folder context is implicit. Topic-specific files are lowercase with a `-<topic>` suffix.

**Hyphens, never underscores.** Word separators in folder names and `.md` filenames are hyphens. Do not use underscores.

**No spaces anywhere inside `.nonighter/`.** Every path stays safe to commit, script, and move between machines.

**Dates use ISO `YYYY-MM-DD` as a position-encoded prefix.** When a file or folder needs a date, put it at the start of the name and separate it from the rest with a single hyphen (`2026-08-26-kickoff-notes.md`). The first 10 characters identify the date; everything after is the slug. No dots in date segments.

| File type | File name |
|---|---|
| Instance router | `AGENTS.md` |
| Host folder entry point | `../CLAUDE.md` — this system owns only the marked block in it |
| Authoring conventions | `CONVENTIONS.md` |
| Persistent memory — instance | `MEMORY.md` |
| Persistent memory — scope | `memory-<topic>.md` |
| Identity | `operating-manual.md` |
| Instance state | `instance.json` |
| Scope instructions | `instructions-<topic>.md` |
| System explainer | `readme-<topic>.md` |
| Resource index | `index-<topic>.md` |
| Memory record | `memory/records/<slug>.md` |
| Context card | `card-<slug>.md` — in `context/cards/<source-slug>/`, inside the instance |
| Context tag dimensions | `context/tag-dimensions.md` |
| Context source registry | `context/sources.json` |
| Source card | `summary-<slug>.md` — in that source's folder under `knowledge-base/` |
| Record store | `notes-<topic>.md` |
| Design principles | `principles-<topic>.md` |
| Tool rules and access routes | `tools/instructions-tools.md` (the rules) + `tools/index-tools.md` (the registry) |
| Work list | not a file — `## Open threads` / `## Settled` inside a memory file |

## 6. Folder structure

- **`initiatives/<name>/`, `projects/<name>/` and `tasks/<name>/` share the same shape.** Each is a folder, not a loose `.md` file. `instructions-<topic>.md` and `memory-<topic>.md` are the spine. Add `readme-`, `index-`, `principles-` or `notes-` only when earned. Subfolders (`runs/`, `inputs/`, `archive/`) are added when the file count justifies them — not pre-sliced. Folder shape is flexible; the retrieval map in each `instructions-<topic>.md`, not the directory layout, is the authoritative guide to what to read.
- **Stay as flat as possible.** Each level of nesting must answer a distinct organizational question. If a subfolder is the only child of its parent, collapse it.
- **Soft depth target: three levels** inside any numbered folder. Deeper is fine when earned by real content; flag it as a smell when it is not.
- **Encode *stable* metadata in filenames, not in subfolders.** A `2026-08-26-kickoff-notes.md` filename beats a `2026-08-26/` subfolder holding one file. Do not encode mutable attributes (cadence, status, owner) in filenames — those go in the file body, so a change needs no rename.
- **Sibling parallelism.** Folders at the same level should share a similar internal shape. Asymmetry is a smell.
- **No empty placeholder folders.** Create when there is real content to put in.
- **If the folder name does not fit in three words, the folder probably should not exist** — or it is doing two jobs and should be split.

## 7. Anti-patterns

- Generic placeholder files (`misc.md`, `stuff.md`, untouched scaffolds) created speculatively. For kept records the sanctioned home is `notes-<topic>.md`, created only on request.
- Writing a `readme-<topic>.md` for a folder of human-readable material. A readme explains a technical system to a non-technical reader; nothing else earns one (§4). Scaffolding one alongside `instructions-`/`memory-<topic>.md` is the same error twice: the instructions file's header and retrieval map are already the orientation, and the second copy drifts.
- Cross-layer contamination — instructions inside a reference doc, reference material inside an instructions file, memory entries inside a readme.
- A to-do written in both a Status block and its `## Open threads`. Status states where the work stands; Open threads states what to do.
- A fact restated in both an authoritative document and a memory record. The record holds only what the document cannot. A paraphrase drifts the moment the target changes, and worse, it suppresses its own correction: a summary already in context removes the reason to open the source.
- A session writing a memory file, or offering to checkpoint. Every memory file is written by the daily pass; a second writer makes reconciliation guesswork.
- A memory-record index line that asserts instead of routes. The record earns a staleness banner when it is read; the index line gets none, so a claim there is an unstamped assertion in every session's context.
- Storing a rendered day plan. A plan is derived from the memory system when it is asked for; a saved copy is a third version of the same facts and it rots by lunch.
- Any file this system writes outside `.nonighter/`. Context cards are held in the instance; a card written into a described folder is visible to everyone who syncs it and can only be reported on, never corrected, once another instance owns it.
- Relocating the user's existing files to make the instance's layout tidier (§2).
- Two instances' files read in one context. The nearest instance governs its subtree (`AGENTS.md`).
- "Last updated" footers on files that change weekly. The filesystem timestamp is the truth.
- Empty headings. If a section is empty more than once, the section does not belong.
- Cute names (`playbook.md`, `cheatsheet.md`, `the-rules.md`). Discoverable only by readers who already know them. Stick to the schema.
