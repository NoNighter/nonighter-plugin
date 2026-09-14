# Instructions — Context

> How this instance describes the material it reads from: the index hierarchy, the cards beneath it, the tag dimensions that make them searchable, and the daily conformance run that keeps it true. Read before adding a source, writing a card, or running the check.

Activity type: **task (recurring, daily)**. An agent in this file is describing material or running the conformance check. Retrieval *through* the system needs only `index-context.md`.

## 1. What this system buys, and the one rule that shapes it

A described corpus the agent reads **instead of** walking an estate, bounded at every step:

```
index-context.md  →  index-<source>.md, where one exists  →  a card  →  the file itself
```

**Everything this system writes lives inside `.nonighter/context/`. Nothing is ever written into a described folder.** That single rule is why there is no authorization step, no writability probe, and no wording constraint about being read by a stranger: no colleague ever sees these files, so there is nothing to ask permission for and no reader to write around. A card may name this instance, its paths and its user freely.

The cost of that rule, stated so nobody reaches for it as an improvement: **the descriptions do not accumulate as something the company owns.** Every person who maps the same library describes it again. That was chosen deliberately over the alternative — cards written into shared folders, where two people's sync clients can produce conflict copies of one card, and a card owned by another instance can only be reported on, never corrected.

**Every layer is a shortlist.** Open the file before relying on anything an index or a card says about it.

## 2. The layers

| Layer | Lives | Holds | Written by |
|---|---|---|---|
| **Master index** | `context/index-context.md` | every source, what each is for, and where to go next — a card, or a lower index | the run |
| **Lower index** | `context/index-<source-slug>.md` | the same shape, for one source that outgrew its rows in the master | the run |
| **Card** | `context/cards/<source-slug>/card-<item-slug>.md` | one file or folder worth more than a line: what it is, where it sits, its tags | the run drafts; a human confirms |

**The master index is the first direction, not a routing table.** It says what each source is and what a session would come to it for, in enough detail to choose without opening anything. A source with few described items keeps its rows in the master. A source with many gets `index-<source-slug>.md` and one master row pointing there. **Split on size, never on category** — the only reason a lower index exists is that its rows no longer belong in a file meant to be read whole.

**Cards are flat inside their source's folder**, named for the item, with the item's real location recorded inside as `path:`. Deep material earns a longer card name, never a deeper card path — this instance already sits inside a user's folder, and a mirrored tree is how a path length becomes a Windows failure.

**Cards are authoritative; the indexes are derived and disposable.** A wrong index is regenerated, so it costs one pass. A card a human has confirmed is never regenerated.

## 3. Tags — named dimensions, free values

A card carries dimensions, not a bag of words, because a dimension is what makes a question answerable: *what models do we have for this client* is two dimensions, and a flat tag list can only be scanned. The dimensions and the values in use: `context/tag-dimensions.md`, which is the authority for what a tag means and the only place a new dimension is added.

Values are free text and grow with the material. **Reuse a value that already exists in `tag-dimensions.md` rather than coining a synonym** — a vocabulary holding both `valuation` and `valuations` answers neither query.

The card block, its keys, and the tag syntax: `CONVENTIONS.md` §4.

## 4. Selecting a source — scan shallow, then propose

Naming every folder by hand is right for a curated library and wrong for a home folder, which can hold fifty top-level entries of which six carry content worth reading. So:

1. **Walk directory names only**, depth one to two, **reading no file contents**.
2. **Drop everything on the exclusion list** (§6) before proposing anything.
3. **Propose the candidates** with the reason each looks relevant, and say how many were dropped and why.
4. **The user cuts the list.** Do not argue for a folder they cut.
5. **Map only what survives** (§5).

**The names-only pass is pre-consent, and it stays names-only.** It is what makes consent informed without reading anything sensitive in order to obtain it. Reading contents happens after the user has chosen the folder, never before.

## 5. Mapping a source — this is where contents get read

The names-only pass produces a description built out of folder names. It reads plausibly and is worth little: it gets a session to an *area* and leaves the last step — which file — as a walk through the tree, which is the thing this system exists to remove. So mapping goes through the material.

1. **Register the source** through `register_sources.py`, never by editing `sources.json`.
2. **Walk it to the registered depth and read what is there** — file names, and enough of the contents of anything that looks reusable to say truthfully what it holds. A spreadsheet's sheet names and header rows; a document's title and first screen; a folder's own readme where it has one.
3. **Write a card for every item worth more than a line.** Reusable material earns one: past client work, a model or a deck that would be a starting point again, a price book, a playbook, a dataset. Routine and closed material earns an index line and no card.
4. **Set `provenance` to `inferred from contents, unconfirmed`** on everything drafted. You inferred it; a confirmation is a human act, and marking your own inference confirmed is how a wrong description becomes permanent.
5. **Generate the index rows**, and split a source into its own lower index once its rows outgrow the master.

**Measure one source before quoting the next.** Reading contents across a large library is the expensive part of this system, and the cost is not knowable in advance from the folder count. Map one, say what it took, and let the user decide whether the next is worth it.

**Say it will take a while before starting, not after.** A run that goes silent through a large mapping has left the user no way to stop something they did not know had started.

## 6. Five exclusions, hard-coded

Not offered as choices. The scan never proposes them regardless of what the user might approve.

- **Credential and state paths** — `.ssh`, `.aws`, `.claude*`, `.gnupg`, `AppData`, `NTUSER.dat`, and any live token file. A mapper pointed at a home folder walks straight into secrets.
- **Legacy reparse points** — `Application Data`, `My Documents`, `Local Settings`, `Recent`, `Cookies`. Windows compatibility junctions that loop back on themselves, so a recursive scan does not terminate.
- **Download-manager and temp locations** — browser download staging, `Temp`, package caches. Content there is transient by definition.
- **The instance itself.** `.nonighter/` is never mapped, or the run writes cards describing its own cards.
- **A folder carrying its own `CLAUDE.md` or `AGENTS.md`** is described, but its card carries **what is in the folder and nothing about how to work in it**: contents, purpose, what the material is for, plus a line naming its own instruction file as the authority. What to edit, what to copy first, what its conventions are — all of that is theirs, and a card that restates them is a second router. Describing where things are was never the conflict; describing how to work there is.

## 7. Class precedence resolves the overlap

`sources.json` carries a class per source — `company-shared` for a shared library the user selected, `host-local` for content inside `{{HOST_PATH}}`. **Since 0.6.0 the two behave identically**: both are described by cards inside the instance, and the write boundary that used to separate them is gone. The class is kept because it says where the material came from, which is worth knowing when a path stops resolving.

A host folder commonly *contains* the company libraries, so a naive local scan would swallow the whole company estate and re-describe it as local content. Two rules settle it:

- A subtree already covered by a `company-shared` source is **never** mapped as `host-local`.
- A subtree governed by a nearer instance is mapped by **neither**. `instance.json` records the relation; the nearer instance owns its subtree.

## 8. Existing work is adopted in place, never moved

Where the host folder already holds a real project, a scope inside the instance takes ownership **by reference**: `projects/<project>/` carries the instructions and the memory, and records the absolute path to the materials where they already sit.

Relocate no user file. Moving content breaks the shortcuts, sync links and other tools built around the old path, and buys only tidiness. The value of this system is the description layer, not the location.

## 9. The daily run is a conformance check, not a crawl

Four checks, then one regeneration.

1. Has a folder or file appeared under a selected source that no card and no index row covers?
2. Has a described item's content moved since its card was written?
3. Has a card aged past its stale threshold, or does its `path:` no longer resolve?
4. Does a card carry a tag value `tag-dimensions.md` does not list — a synonym coined instead of reused?

Then regenerate the affected indexes, and write the run report to `context/runs/YYYY-MM-DD-context-run.md`.

**Nothing authoritative is machine-written.** A card whose `provenance` reads `inferred from contents, unconfirmed` may be rewritten by the run at will. Once it reads `confirmed by <role>, <date>` the run **never overwrites it** — it reports a conflict and stops there.

**Gate on material change, never on modified-date.** On a synced estate, sync touches and autosave change files constantly without changing content, and Office files gain injected `customXml` on sync, so whole-file comparison never matches across library folders. Hash the **content payload** and act only when the payload moved or the file is new. A run keyed on modified-date re-reads the entire selection every night.

## 10. No mounts

The index holds absolute paths to libraries already on the machine. A junction per instance would read as a local subfolder, but each one adds another path the sync client walks, multiplied by every instance the user holds.

Absolute paths also degrade gracefully: on a machine where a library is absent, the index stays a readable list of what exists and where it would be, rather than a broken directory.

## 11. Procedure and exit

Adding a source: register it in `sources.json` with its class and mapping depth → scan or name → the user cuts → map through the contents → write cards → regenerate the indexes.

A run is complete when every check has been made, every affected index is regenerated, every conflict is reported rather than resolved, and the run report is written. **Nothing this run does reaches outside `.nonighter/`**, so the whole of it is unattended: the confirmation this system used to need was for writes into other people's folders, and there are none.
