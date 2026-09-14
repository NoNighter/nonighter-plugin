# Reference — the initial context mapping

> The install-time mapping: the shallow scan, the proposal, and the first cards. Read when context is one of the enabled systems. The ongoing conformance run is the instance's own job and is specified in the stamped `context/instructions-context.md`.

## 1. Scan the host folder shallow, then propose

Run this during the install interview, so the user cuts the list once.

1. **Walk directory names only**, depth one to two inside the host folder. **Read no file contents.** The cheap pass is what makes consent informed without reading anything sensitive to obtain it.
2. **Drop every exclusion** (§2) before proposing anything.
3. **Build the outside list too** (§1a). What sits outside the host folder is invisible to the walk, and it is often where the real material is.
4. **Propose the survivors**, each with the reason it looks relevant, and say plainly how many entries you dropped and why. A home folder can hold fifty top-level entries of which six carry content worth reading; a proposal that does not admit the ratio reads as if the whole folder is in scope.
5. **The user cuts the list.** Do not argue for a folder they cut.
6. **Deep-map only the survivors** (§4).

## 1a. The outside candidates, and why they are offered rather than typed

**A folder this session cannot reach cannot be mapped, so reachability is not a check applied after the answer — it is what makes something a candidate at all.** Asking *"where is it?"* into an empty field invites a path that is real on the user's disk and unreadable from here, and the failure then arrives after they have answered. Offering what is already reachable inverts that: ticking a folder is the complete answer, and there is nothing left to get wrong.

Build the list from three places, cheapest first:

- **The folders this session can already read.** Its own connected and additional working directories, named in its environment. These are the strongest candidates: reachable by definition, and already chosen once by the user when they connected them.
- **The cloud-library roots beside the host's own.** A user with one synced company library usually has more than one, and a sibling library root is a folder, not a guess.
- **The other filesystem roots.** One cheap listing — `Get-PSDrive -PSProvider FileSystem` on Windows, the mount table elsewhere. A mapped network drive or a second disk shows up here and nowhere else.

Then, before offering any of it: **drop the host folder itself, every §2 exclusion, and every root you cannot actually read.** A candidate that fails on selection is worse than one never shown.

**The menu holds four options; a detected list can be longer.** Put the strongest candidates in the menu and **name the remainder in the line under the question**, where there is room — nothing detected goes unmentioned, and the user can ask for one by name. Never silently truncate the list to fit.

**Typing a path is the exception, and it is Other.** For a folder nothing detected, one line under the question says so. Validate what they typed through `register_sources.py` (§4), which refuses a path that does not exist, is a file, or sits inside the instance — and if it is real but unreachable, ask them to connect it and pick it up after. **No option ever reads "choose Other and type the path".** An option that instructs the user to select a different option is not an answer, and the third option is already Other; a tester met exactly that and the honest-looking pick returned nothing.

## 2. Five exclusions, hard-coded

Never propose these, whatever the user might approve.

- **Credential and state paths** — `.ssh`, `.aws`, `.claude*`, `.gnupg`, `AppData`, `NTUSER.dat`, and any live token file. A mapper pointed at a home folder walks straight into secrets, and a token file at a folder's top level is a real thing that happens.
- **Legacy reparse points** — `Application Data`, `My Documents`, `Local Settings`, `Recent`, `Cookies`. These are Windows compatibility junctions that loop back on themselves, so a recursive scan does not terminate.
- **Download-manager and temp locations** — download staging, `Temp`, package caches.
- **The instance itself.** `.nonighter/` is never mapped, or the run writes cards describing its own cards.
- **A folder governed by a nearer instance.** Its own instance owns its subtree (§3).

### A folder with its own instruction file is described, not excluded

This used to sit in the list above as "do not describe it", and it was too strong. **Describing where
things are was never the conflict; describing how to work there is.** A folder carrying its own
`CLAUDE.md` or `AGENTS.md` gets a card that **carries contents, not guidance**: what is in the folder,
what the material is for, and a line naming its own instruction file as the authority. Not what to
edit, not what to copy first, not its conventions — those are theirs, and a card that restates them is
the second router this rule exists to prevent.

A session that finds the folder through the index then knows what is in it and is sent to their file
before acting, which is strictly more useful than not knowing the folder exists.

**Nothing is written inside such a folder** — which is true of every folder, so it is not a limit
peculiar to this case.

## 3. Class precedence

A host folder commonly *contains* the company libraries, so a naive local scan swallows the whole company estate and re-describes it as local content. Two rules settle it:

- A subtree already covered by a `company-shared` source is **never** mapped as `host-local`.
- A subtree governed by a nearer instance is mapped by **neither**.

Apply both before proposing, not after.

## 4. Map a source — the layers, and where they live

**Everything this system writes lives inside `.nonighter/context/`.** No file is placed in a described
folder, whoever owns it. What that removes: the writability probe, the authorization to write into a
shared library, the record of that authorization, and the constraint that a card be readable by a
colleague who has installed nothing. What it costs: the descriptions never accumulate as a company
asset — every person who maps the same library describes it again. Decided 2026-09-08, against the
alternative of writing a card in place wherever the folder allowed it.

Three layers, top down:

| Layer | Path | Holds |
|---|---|---|
| Master index | `context/index-context.md` | every source, what each is for, where to go next |
| Lower index | `context/index-<source-slug>.md` | one source's rows, once they outgrow the master |
| Card | `context/cards/<source-slug>/card-<slug>.md` | one item worth more than an index line |

**Register first, through `scripts/register_sources.py`, never by editing `sources.json`.** It validates
each folder before recording it (a path that does not exist, is a file, or sits inside the instance is
refused out loud), derives the class, flags a cloud-sync placeholder, and writes one fixed set of keys.
A source inside the host folder carries **both** path forms: `path` absolute, so a reader that knows
nothing of this convention still resolves it, and `relative-to-host`, which is what this system
resolves through because it is the only form that survives the same folder being reached by a
different absolute path. Hand-written rows drift in their key names, and the conformance run that
reads the file back then finds nothing where it looks. `--check` re-validates what is recorded.

**Then read the material, not just the folder names.** The shallow pass in §1 is names-only because it
runs before consent; once the user has chosen a folder, mapping goes through what is in it — file
names, and enough of the contents of anything reusable to say truthfully what it holds. A description
assembled out of folder names reads plausibly and gets a session as far as an *area*, leaving the last
step — which file — as a walk through the tree. That walk is the thing this system exists to remove,
and leaving it in place is what a tester called the system looking thin.

**Write a card for what is worth returning to**, an index line for the rest: past client work, a model
or deck that would be a starting point again, a price book, a playbook, a dataset. Set every card's
`provenance` to `inferred from contents, unconfirmed` — you inferred it, a confirmation is a human
act, and marking your own inference confirmed is how a wrong description becomes permanent.

**Tag along the three dimensions** — `for`, `work`, `kind` — and add each new value to
`context/tag-dimensions.md` in the same pass. Reuse a listed value rather than coining a synonym; a
vocabulary holding both `valuation` and `valuations` answers neither query. The card block and its
keys: the stamped `CONVENTIONS.md` §4.

**Split on size, never on category.** A source keeps its rows in the master index until they no longer
belong in a file meant to be read whole; then it gets `index-<source-slug>.md` and one master row
pointing there.

## 5. Report the cost

Say how many folders you walked, how many cards you wrote, and how much of the material you actually
read. **Measure one source before quoting the second** — reading contents is the expensive part and
the cost is not knowable in advance from a folder count. If a source is going to be expensive, say so
before starting it and let the user decide whether it goes in at all.
