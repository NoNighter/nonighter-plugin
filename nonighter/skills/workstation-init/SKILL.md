---
name: workstation-init
description: |
  Install a scoped NoNighter workstation into a folder as a self-contained `.nonighter/` subfolder —
  a router, memory system, authoring conventions, and the work folders an agent routes into — then
  verify, upgrade, or unwire it. Use when the user asks to "init a NoNighter workstation", "set up a
  workstation here", "install the workstation in this folder", "make this folder agent-ready", "give
  this project its own memory", "check my workstation", "upgrade the workstation", or "remove the
  workstation" — even if they don't say "skill". Also use when the user asks for NoNighter's help with
  work in a folder that has no workstation yet — they invoke another NoNighter skill, or they name
  NoNighter — and offer it rather than installing: answer what they actually asked first, put
  the offer at the end of that same turn, and take the answers from them.
  Needs Python on the machine (`py` on Windows, `python3` elsewhere).
---

# Skill — workstation-init

**Template-set version: 0.6.0.** Stamped into `instance.json` at install and compared on every upgrade.

> Installs and maintains one `.nonighter/` instance in a host folder. §0 interpreter and host folder;
> §1 mode; §2–§5 install; §6 report; §7 upgrade; §8 unwire; §9 later sessions. The scripts, the
> layout and the design decisions: `reference-implementation.md`. Why each rule below exists — the
> runs that produced it: `reference-lessons.md`, for whoever maintains this skill, not for a run.

## Three rules that govern everything

**The scripts stamp; you do not.** Every folder, file, token, conditional block and hash comes from
`templates/manifest.json` and is written by `scripts/`. A tree written by hand cannot be upgraded.
The one exception is a scope folder (§5): scopes are not in the manifest.

**The installer only adds.** It never edits the user's files except inside the marked block in the
host `CLAUDE.md` / `AGENTS.md`, and nothing in this skill deletes `.nonighter/`.

**Every answer comes from the user.** Their name, their organization, their field, what they follow,
what a folder is for — you never infer these from the folder's contents and present them as known.
A candidate read off the disk is offered as exactly that, with its source named.

## How you ask — read before the first question

**Always through the harness's own question mechanism** — the built-in prompt with options and a
text field — never a rendered widget, and never prose in the chat for something that needs an answer.
A typed answer still goes through the mechanism: *open* describes the answer field, not the channel.
Prose is for what the user does not have to answer.

**A menu is for a real choice between things you can enumerate.** Anything only the user knows — the
identity answers, a folder's purpose, the watch's coverage — is a text field, prompted with an example
in their terms. Never a menu of guesses about them, and never a menu item whose content is "use the
text field".

**Inside the question, not around it:** one line of what the thing does *for them*, what saying yes
costs, and that it can be changed later. A user who cannot price a yes assumes the worst.

**Labels say what happens; the body says why you are asking.** Recommended option first. An option
that edits somebody else's file is not a click — mention it in a sentence and let them ask.

**State facts; do not narrate your process.** Say what runs and what it does. Never explain that
something was not offered, not asked, or decided for them.

**Batch.** The mechanism takes several questions at once, so the whole interview in §2 is **two rounds,
not one question per turn**: identity and name together, then context, the watch and its
coverage together. A follow-up belongs in the round that raised it; never re-ask what was answered;
never ask what is on disk. Every extra round is a person waiting.

**Set the workstation up on its own.** When it is a prerequisite you discovered, finish it, say so in
a line, and let the skill they actually invoked run its own interview afterwards.

## 0. The interpreter, and the host folder

**`<py>` means: pick the interpreter and verify it.** Try `py` on Windows and `python3` elsewhere;
if that is absent, try `python`. Run `<py> --version` and check it printed a version — on Windows a
Store stub answers *"Python was not found"* instead, and that is not an installed Python. If no
candidate prints a version, tell the user Python is missing and stop.

**Confirm the host folder before anything is written.** Pass `--host "<path>"` when the user names
one; otherwise the scripts resolve it from `CLAUDE_CODE_WORKSPACE_HOST_PATHS`, then
`CLAUDE_PROJECT_DIR` — never from the current directory. Every script prints the folder it resolved
as its first line. Name it in the first thing you say. The plan in §3 is the one confirmation; do not
add a separate one for the folder, and never announce a confirmation you did not wait for.

**In Cowork the reachable folder is a mount** at `/sessions/<name>/mnt/<folder>`, gone tomorrow.
Ask the user for the folder's real path on their machine and pass both: `--host` is where to write,
`--host-path` what to record. The installer refuses an ephemeral path. Only connected folders are
reachable: ask them to connect one rather than registering a path you cannot see.

## 1. Pick the mode

| What you find | Mode |
|---|---|
| The user asked to remove or uninstall | **Unwire** — §8, `reference-uninstall.md` |
| No `.nonighter/` in the host folder | **Install** — §2 |
| `.nonighter/instance.json` older than the version above | **Upgrade** — §7 |
| `.nonighter/instance.json` at the current version | **Verify** — `--verify`, `reference-verify.md` |
| `.nonighter/` with no readable `instance.json` | **Stop**, report, ask. Nothing can be done safely over it |

The SessionStart hook already reports installed / not installed. Trust it; run `--verify` when the
user asks or before an upgrade. `init_workstation.py` refuses to overwrite an existing instance.

## 2. Install — interview

Five things, in **two rounds** (see *Batch* above). Nothing is stamped until all five are settled —
including the watch's coverage, which is complete before the plan is shown, not after.

1. **The instance name** (`Home`, `Acme Deal`). The script derives the work-list prefix; say it back.
2. **The user, the org, and their field** — *"financial analyst, valuations for private-equity
   clients"*. The field goes into the operating manual and sets how every later session talks to them.
   Text fields, all three.
3. **The context system** — the one optional system asked here. *"So I know where your material is
   without hunting for it every time."* It is the only system that does work at install: it scans the
   folders the user names and writes a description of each, and that is the slow part of an install —
   say so before they answer.

   Where they take it, **two questions in the same round, every candidate already tickable**: the
   folders inside this one that survived the shallow scan, and the folders *outside* it that you can
   already read — both built for you by `reference-context.md` §1. Ask the outside half even when
   nothing suggests it: what is outside is invisible to the scan.

   **Offer folders, not a blank field.** An outside folder you cannot reach cannot be mapped at all,
   so the folders this session already reaches are the honest list — and ticking one is the whole
   answer. **No option ever says to use the text field**; that is the rule in *How you ask*, and this
   step is where it was broken once. Typing a path stays the route for a folder nothing detected:
   name it in one line under the question, where there is room, and check you can read what they
   typed before recording it. Each question carries an option that takes nothing, so a user with
   nothing to add is not forced to invent an answer.

   A folder they name that you cannot reach is **never silently dropped** — ask them to connect it,
   say why, and pick it up after. Never drop a folder they named without saying so.
4. **What runs on a schedule.** Three procedures ship as files; the harness holds the schedule (§5).

   **Two run without being offered, and are stated as facts** — one line each, what it does for them:
   - the daily **memory pass** — *"it is what lets a session pick up where the last one left off"*
   - the weekly **improvement pass** — *"a short list of the things that cost you time more than once,
     and what to change about each; it proposes, it changes nothing on its own"*

   Neither is a choice: their absence is invisible, so a no cannot be priced by the person asked.

   **The watch is the one question**, yes or no. Say what lands in the file, not what the task is
   called, and that it does not delay the install: *"what happened to the companies you follow — deals,
   results, rating changes, management moves — each with its source and date. A quiet day says so in
   one line."* A yes adds `watch` to the answers' `systems` list.
   **Coverage is asked in the same round when they take the watch**: a text field, two or three names
   and a sector, enough for a useful first run. If the answer lacks either half, ask for it in the same
   round — the user is right there. Write into `watch/coverage.md` exactly what they said, or nothing:
   never a placeholder, never a guess from the folder's contents. The watch does not run while the file
   is empty or holds placeholders instead of answers; it says what is missing instead of choosing.
5. **What already lives in the host folder.** List it. Real work is adopted by reference in §5. A
   subfolder with its own `CLAUDE.md` / `AGENTS.md` is not a candidate — it is its own question (§5).

The installer knows which answers this template set needs; ask it rather than trusting the list:

```bash
<py> "<plugin>/skills/workstation-init/scripts/init_workstation.py" --show-answer-keys
```

## 3. Install — stamp

Write the answers as JSON to the session scratchpad, with the file tools. `systems` lists only what
the user took — `context` from step 3, `watch` from step 4 — and is `[]` when they took neither:

```json
{
  "INSTANCE_NAME": "Acme Deal",
  "USER_NAME": "Jane Client",
  "ORG_NAME": "Acme Capital",
  "USER_FIELD": "financial analyst, valuations for private-equity clients",
  "systems": ["context"]
}
```

**Show the plan and get a yes — all of it, the derived prefix included:**

```bash
<py> ".../scripts/init_workstation.py" --host "<host>" --answers "<scratch>/answers.json" --dry-run
```

Then, once they have agreed, the same command without `--dry-run`:

```bash
<py> ".../scripts/init_workstation.py" --host "<host>" --answers "<scratch>/answers.json"
```

It creates the folders for the enabled systems, stamps each file the
manifest lists, refuses to finish if a `{{TOKEN}}` or `<!-- if: -->` marker survives, records a hash
for every `hashed` file under `stamped` in `instance.json`, wires the host `CLAUDE.md` (and
`AGENTS.md` where one exists), and records any nesting relation. **A MAX_PATH warning means offer a
shorter host folder. INSTALL DEFECTS means nothing completed — report the files.**

Where context is on, register the folders the user named **through the script**, from a JSON array
of `{"label", "path"}` in the scratchpad, and relay every refusal it prints:

```bash
<py> ".../scripts/register_sources.py" --host "<host>" --sources "<scratch>/sources.json"
```

Then the initial mapping: `reference-context.md`. Say how long before starting it.

## 4. Install — verify

Stamping is not verification:

```bash
<py> ".../scripts/init_workstation.py" --host "<host>" --verify
```

Report what it prints — pristine / edited / missing, leftover tokens — per `reference-verify.md`.

## 5. Install — first working state

**`operating-manual.md` §2.** Ask for one paragraph — what work this folder holds, who it is for,
what a finished piece looks like — and write it into the manual's *What this folder is for*. There is
no second file: the manual is the user's, unhashed, written once at install and never rewritten by an
upgrade, so writing in it costs nothing and a preference the user states later goes in its §5.

**Adopt existing work by reference.** For each real piece of work in the host folder, create its scope
from `templates/scope/` — the instructions file carries the boundary and the activity type, the memory
file the Status block — pointing at the materials where they sit. Relocate nothing. This is the one
place you write a template file by hand: a scope is not in the manifest. Follow the template's shape.

Classify first, `CONVENTIONS.md` §2: recurring work is a task, not a project. And a scope is a piece
of work, not a folder — one initiative may span a repository, a library folder and a ticket list.
Create `initiatives/`, `projects/`, `tasks/` only when a scope goes into them.

**A subfolder with its own agent instructions** already tells an agent how to work in it; a scope
here too is two rule sets for one folder. Ask, with the first two as options and the third as a
sentence — it edits a file that may be the team's:

| Option | What happens | Label |
|---|---|---|
| **Leave it** (recommended) | No scope, nothing written there. It gets a card in `context/cards/` only where context is on — with it off the option is simply *"leave it alone"*. Either way nothing is written inside the folder | *"I track nothing in it"* |
| **Adopt, deferring** | A scope whose instructions name the folder's own file as the authority | *"I track the work; its rules still govern"* |
| **Reconcile** | Their rules move here and the folder's file goes. Read it to them and keep a copy first | not in the picker |

**The recurring tasks.** The instance holds what to do; the harness holds when. Register each through
the harness's scheduled-task mechanism, with a prompt that names this instance's absolute path and
says to read the procedure and follow it — a pointer, never a copy:

| Procedure | Cadence | Register |
|---|---|---|
| `memory/instructions-memory-maintenance.md` | daily | always |
| `improvement/instructions-improvement-pass.md` | weekly | always |
| `watch/instructions-market-watch.md` | weekdays | if they took it, once coverage is filled |

The memory task's prompt also forbids deletion (an unattended run has nobody to authorize one — it
proposes instead) and names every transcript store that resolves inside the host folder. A local task
needs the app open; a missed slot fires one catch-up run. **Run each once by hand with the user
present**: approvals granted in that run are stored on the task, and a first unattended run stalls
on a prompt otherwise. Not offered in Cowork: cloud tasks cannot reach a folder on the user's disk.

## 6. Report

The host folder, the instance name, systems on and off, what was written outside `.nonighter/`, any
nesting, how many sources were mapped — and that **the session must be restarted**, because the
plugin's SessionStart hook is what loads the workstation.

**Report what the scripts printed and what is on disk, never what you infer.** Verified only if §4
ran. Name folders, not concepts. Then read `.nonighter/AGENTS.md`, say setup is done in a line, and
hand over to whatever the user originally asked for.

## 7. Upgrade

The user has weeks of work in the instance and the template has moved on. There is no upgrade script:
read what is on their disk against what this template says, and make the edits with them.

`instance.json` names the version the instance is on and `templates/manifest.json` names this one.
Equal versions: say so and stop.

1. **Back up the instance.** Copy `.nonighter/` to a folder outside it, tell the user where it is,
   and delete the copy once they confirm the result. The instance carries no backup folder of its
   own.
2. **Sort the files by whether the user has touched them.** `instance.json` records a hash for every
   file the manifest marks `hashed: true`. Where it still matches, that file is untouched and this
   version's copy replaces it whole. Where it differs, the file is theirs and step 3 applies. The
   contract is in `reference-verify.md` §1.
3. **In a file that is theirs, work in edits and never in replacements.** This is the whole safety
   property: change what this version changes, leave the rest where it is, and their additions
   survive because you never went near them. Read their file against the template file that now
   governs it — filling the template's tokens from the answers in `instance.json`, since unfilled
   every stamped value reads as a difference — and sort what you find three ways:
   - **The template says something theirs does not** — this version added it. Add it.
   - **Both say the same thing in different words** — this version reworded it. Take the template's.
   - **Theirs says something the template does not** — they wrote it, or this version dropped it.
     Anything naming their work, their folders, their people or how they work is theirs.
4. **Read the folder names on disk against the folders the manifest declares.**
5. **Show the plan before touching anything.** One line per file: the difference, and what you will
   do about it. One line per folder that does not match: what is on disk, what the manifest now
   expects, and where their work currently sits.
6. **Apply it, moving folders one at a time with their yes** — contents across, then the empty husk
   removed. Two folders where the user had one is an unfinished upgrade. A file the manifest marks
   `hashed: false` is theirs from install: offer the change and take their answer.
7. **Record, report, then verify.** Write the new version into `instance.json` and re-record
   `stamped` to this version’s pristine hashes, or the next upgrade reads every file you
   replaced as edited — `reference-verify.md` §3. Say what you edited and what you moved, file
   by file. Then `init_workstation.py --host "<host>" --verify`.

**Where a line could be theirs or could be wording this version dropped, it is theirs.** Keep it, and
say you kept it. Stale wording costs a sentence; their deleted paragraph costs the thing this product
exists to protect.

**A rename announces itself nowhere, which is why step 4 exists.** The manifest
declares no work-scope folder — those exist only once their first real item arrives — so when one is
renamed there is nothing on disk to notice: the user's scopes sit under a name the template dropped,
the router looks for a name that is not there, and the memory structure check passes over a scope
root it cannot find. An instance can strand every scope it holds and still report clean. Comparing
the names on disk to the manifest is the one thing that surfaces it.

**`MEMORY.md`, `memory/` and the work folders are the user's record**: add, never rewrite. Where the
template contradicts them, theirs stands and you say so. Resolve everything in the session that
raised it. A decision beyond you: change nothing, and name the single thing you need answered.

## 8. Unwire

Removes the route; **never deletes the instance.** `reference-uninstall.md` carries the confirmation
and the final memory pass, both before the script:

```bash
<py> ".../scripts/unwire_workstation.py" --host "<host>"     # --dry-run first
```

It strips the marked block from the host `CLAUDE.md` / `AGENTS.md`, repairs nesting on both sides, and
stamps `host-wiring` removed. A `CLAUDE.md` the installer created is deletable only when the file
*with our block removed* still matches what was recorded at creation, and only with
`--delete-created-claude-md`. If the user wants `.nonighter/` gone, that is theirs to do by hand after
you have told them what is in it.

## 9. Telling the user where they stand

For any later session where they ask. `instance.json` holds it; say it in their terms — *"I keep
track of where your material is"*, not *"context is on"*. What is on, as what it does for them; what
is off, that it can be turned on (`init_workstation.py --enable <system>`, then an upgrade), and what
that costs. Turning the watch on later means asking for coverage then, the same text field as §2.

## Reference

- `templates/manifest.json` — the machine contract. Read before changing anything about the template.
- `reference-implementation.md` — layout, upgrade design, Windows traps. Read before changing scripts.
- `reference-verify.md`, `reference-context.md`, `reference-uninstall.md` — per mode.
- `reference-lessons.md` — the runs behind each rule above. For maintainers.
- `scripts/init_workstation.py` — `--show-answer-keys`, `--dry-run`, `--verify`, `--enable <system>`.
  `unwire_workstation.py`. `register_sources.py` — `--sources`, `--check`, `--list`.
  `stamp_lib.py`, `workstation_lib.py` — shared by all of them.

## Limits

- **The template ships with the plugin.** `tools/sync-authoring-copy.py` carries the authoring copy
  into `templates/` at release; every published version is tagged `template-<version>`. It does not
  run by itself.
- **This skill instantiates the template; it does not edit it.** A client edition changes the template
  and the manifest, never the scripts.
- **The plugin hook is the only thing that loads the context.** Without the plugin the workstation is
  files and a `CLAUDE.md` block.
- **A manifest row naming an undeclared system fails at load**, by design.
