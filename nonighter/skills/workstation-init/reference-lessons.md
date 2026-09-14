# Reference — the runs behind the rules

> Why each rule in `SKILL.md` exists: the install, upgrade or unwire that produced it. **For whoever
> maintains this skill.** A run does not read this; it reads the rule. Keep it that way — a lesson
> written into `SKILL.md` competes for the run's attention with the rule it explains, and twice its
> own wording has leaked into what the user was shown.

Each entry: the rule as it stands, then what happened.

## How you ask

**Always the harness's question mechanism, never a rendered widget.** Twice in Cowork a rendered HTML
widget returned only its choice answers; every typed field arrived blank. Both times the lost answers
were the identity ones, and the user, who had typed them, was asked again.

**Never prose for something that needs an answer.** The rule above used to sit at the *end* of the
interview section, 150 lines below the steps that use it, with an escape clause ("if the harness has
no mechanism, ask in conversation"). A run reached for the clause and asked the identity answers and
the watch's coverage as chat text. The rule was present, correct, and positioned where it could not act.

**A menu is for enumerable choices; identity is a text field.** A run offered a picker of professions
and no way to write, asking the user to recognise themselves in three guesses. A later run, trying to
honour both "use the mechanism" and "ask it open", produced a menu whose second option read *"I'd
rather type it — use Other"*: two rules obeyed literally, one nonsensical question.

**Never a menu of guesses about the user.** A run proposed "Meridian Capital" as the instance name for
a folder called `Cliente Andes`, because a project inside was named after Meridian. Another built the
watch's coverage from the folder — *"Meridian y comparables directos"* — offered it as the only option,
wrote it into `coverage.md`, then reported the watch could not run without a ticker.

**State facts; do not narrate the process.** The skill said, in bold, *"The memory pass is registered
without asking"*, with a rule under it not to say so to the user. The run copied the bold line into the
question header: *"(la de memoria diaria se registra siempre, sin preguntar)"*. A rule not to say X,
placed under a heading that says X, loses.

**Inside the question: what it does, what it costs, that it is reversible.** The reversibility note was
first written as something to say *after* a decline. Said then it costs a round trip and reads as not
accepting the no. The watch was first described as *"reads the outside world for the names you follow
and leaves what moved in a file"* — the mechanism, which the user cannot price; rewritten as what lands
in the file.

**Batch; one question per decision.** A measured install took over ten minutes; the scripts took under
a second of it. Seven questions were asked one after another. One run asked "is there another folder
outside this one?", got yes, then spent two more turns on which and where. Another re-asked the
folder's name in prose after the user had typed it.

**But collapsing that into one text field was the wrong repair, and it shipped.** The correction to
the run above became *ask both halves in the same text field*, which produced an option reading
**"Yes, there is — here's where / Choose Other and type the folder and its path"** with Other already
sitting beneath it as the third option. A tester picked the option that answered the question and it
carried no path. Two things to keep from it: **the enemy was never the second question — it was the
second *round*, and the mechanism takes several questions at once**; and **a step that needs a path
should offer the folders it can already reach**, because a tick is an answer and a typed path is a
thing that can be wrong. §1a of `reference-context.md` now specifies that list. Batching is not a
reason to fold two answers into one field.

**Labels say what happens.** Three runs named the foreign-folder option instead of saying its effect —
*"adopt it pointing at its own file"*, *"llevar seguimiento del trabajo ahí"*, *"Registrar sin tocar
reglas"* — and one put the destructive option in the picker one keystroke under the recommended one.

**Set the workstation up on its own.** A run mixed "what is your org called" with "how many projection
years" into one wall of questions for a user who had asked for a model.

## Host folder and surfaces

**Confirm the folder; the plan is the one confirmation.** An instance installed one folder up is a
wrong answer that takes months to notice. A run announced it was confirming the folder and proceeded
as if it had.

**Cowork mounts are ephemeral.** A real install stamped `/sessions/<name>/mnt/<folder>` into the router,
the host `CLAUDE.md`, and every source — a dead path by the next day. The scripts now refuse it.

**Python, not PowerShell.** Cowork runs tools in a Linux sandbox. On Windows, `python` and `python3`
are Store stubs whose message explains nothing.

## Interview content

**Context is the only system asked as a system.** Tools and the knowledge base were once asked too;
both cost a folder until used, and the first thing ever recorded in the tools registry was this
plugin's own connector, which every client reaches. Asking a user to predict a need that costs nothing
was one more round trip in an interview that had too many.

**Both halves of the context question in one round.** Two runs proved that splitting it drops one
half: one asked which folders inside and never about outside; the other the reverse.

**Ask about outside even when nothing suggests it.** What is outside the host folder is invisible to
the scan, so an unasked question always answers no. And "is there a shared library" narrows the
answer to that category — a user may mean a network drive or another client's folder.

**Reachability after the answer.** A run said "I cannot register it" and moved on, leaving the user
holding a pending item they did not ask for.

**Memory and improvement are not offered; the watch is.** The first design asked about all three,
then about the last two, then only about the watch - each step reversing the one before. The argument
that settled it was already in the client-facing delivery document, written by Toto: the watch
produces something visible, the other two do not, *which is exactly why they get disabled* - their
failure is silent, nothing breaks, the instance just decays until someone concludes it was oversold.
"Nothing breaks without it" had been used as the reason improvement was the least essential; it is
the reason it cannot be a question, because a person cannot price a no to something whose absence is
invisible. The watch has a real cost (coverage, daily external reads) and a visible product, so it is
the one that is a genuine choice. The improvement pass was also nearly made mandatory for the wrong
reason - a naming confusion with the maintenance *skill*, which a person triggers and is not a task.
**Coverage at install, as a starter.** Left to a later working session it never gets filled; the watch
sits registered and silent. The whole universe is not askable five minutes in. A derived sector menu
was proposed and not taken: `USER_FIELD` is already the user's words, and names cannot be menued.

**Write what they said, or nothing.** An install got one name and no sector, wrote the name with
*"(pendiente — confirmar ticker/identificador exacto)"* beside it and the sector as *"(pendiente:
confirmar con Victoria)"*, and finished. The watch's first run read the placeholders, correctly refused
to pick a universe, and wrote a run file asking for the two things the install could have asked while
the user was sitting there.

## Stamping and reporting

**Say what will take a while.** A run went silent through the whole context mapping — minutes with
nothing on screen — which is how a user learns not to ask for things.

**The plan includes the prefix.** It goes on every work item the instance ever numbers and is the one
thing in the plan nobody notices is missing.

**Report what is on disk.** A run reported an instance "set up with tracking for Cierre Mensual and
Valuación Meridian" when neither scope folder existed — both were context sources and nothing else.

**Name the folder, not the concept.** A `03 Company General Context/` from an older template and a
`context/` system are not the same thing; "the context system is empty" read against the wrong one
told the user something untrue.

## First working state

**One file again in 0.6.0 — `operating-manual.md`, unhashed, and there is no `preferences.md`.**
Until 0.5.0 they were one file, **hashed**, and the install *instructed* the run to write in it. Every
instance in real use reported the manual edited and took a merge conflict on every later improvement.
The four instance-written registries were unhashed in the same change, for the same reason. Splitting
the file fixed it, and a tester then read the two as one thing done twice (`workstation-init` QA `#6`).

**Read the fix, not the shape: the conflicts came from the hash, not from the two purposes sharing a
file.** 0.6.0 merges them back and drops the hash instead, so the same failure cannot return — an
unhashed file is never compared and never overwritten. **The price is the other half of that trade,
and it is real: an improvement to the defaults no longer reaches an instance already installed.** A
client set up today keeps today's wording until somebody edits their file by hand, and nothing tells
them a better default exists. That was accepted knowingly. Do not "restore" the split by citing the
0.5.0 lesson above — it describes a hashed file, which this no longer is.

**A scope is a piece of work, not a folder.** An install created one scope per repository; every one
had to be removed.

**Recurring work is a task.** A monthly close was filed under `projects/` beside a deal that ends.

**The foreign-`CLAUDE.md` "leave it" option must not promise a note when context is off.** It said *"I
note the folder exists and has its own rules"* — the note is a card under `context/cards/`, which only
exists with context on. A user who had just declined context was promised it anyway.

**Read the foreign file to them before touching it.** The one that produced this rule said *"this repo
has its own rules, do not touch them"*.

## Scheduled tasks

**Pointer, not copy.** The first hand-built memory task carried absolute paths and a restated
procedure; the template moved and the task did not.

**Forbid deletion in the prompt.** An unattended run has nobody to authorize one.

**Run once by hand.** A first unattended run stalled on a permission prompt nobody was there to answer.

**Cowork has scheduled tasks; they cannot reach a workstation.** The obvious reason ("Cowork has no
scheduled tasks") was asserted and was false. They run in the cloud and the documentation says they
"can't be tied to a folder on your computer". The split is local versus cloud, not Cowork versus Code.

**No time-of-run guard.** One was written into a real task's prompt and removed: the pass reads from
the previous cut-off forward whatever the clock says, and the guard restated a rule the procedure
already carried, in a per-instance file where it would drift.

**Installer cannot deliver a task.** A task lives in the harness's configuration plus a schedule the
app holds, both outside the folder the user pointed at. "Ships with your workstation" was promised in
the delivery document and produced a hand-built task; now the template ships the procedure and
registration is a step of the install.

## Upgrade and unwire

**Resolve a file the user edited in the session that found it.** The mechanism that used to leave a
second copy beside theirs is gone: users do not open them, and no one came back for them.

**An orphan is a migration.** A retired-file sweep would have deleted `MEMORY.md` in a dry run on a
copy of a real instance.

**The unwire comparison is on the shell, not the whole file.** Refreshing the whole-file hash on every
upgrade folded the user's own text into the baseline; a review reproduction deleted a user's `CLAUDE.md`
with their text in it, unrecoverable because the backup covered `.nonighter/` only. "Has this changed
since we wrote it?" and "does this hold anything of theirs?" are two questions.

**Backups include the host files.** Until they did, the only files an upgrade rewrites outside
`.nonighter/` had no net under them.

## Versions

**Content changed means the version changed; a number is used once.** Template 0.2.2 was published
twice with different content — bumped, reverted, reused. And the plugin's own version was bumped twice
inside one unmerged branch, spending a number nobody could install. The two numbers behave oppositely:
the template stamp moves with content because upgrades compare hashes against it; the plugin number is
only the marketplace's update signal.

**A version whose job is to say "something changed" was the thing nobody changed** — the template
stamp, `plugin.json`, `marketplace.json`, each at least once. Five instances in one week.
