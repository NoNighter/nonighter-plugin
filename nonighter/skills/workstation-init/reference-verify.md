# Reference — verify and upgrade

> The hash contract, the verify checks, and the upgrade procedure. Read when `SKILL.md` §1 resolves to Verify or Upgrade.

## 1. The hash contract

`instance.json` records, under `stamped`, a content hash for every file the manifest marks `hashed: true`, keyed by target path. The scripts compute and compare them; you never hash a file by hand.

**The hash is over the normalized content:** line endings to `\n`, trailing whitespace on each line removed, a single trailing newline. Then SHA-256, **lowercase** hex - what `hashlib.sha256(...).hexdigest()` returns. Recorded values are compared case-insensitively so an instance stamped by an older version still verifies. Without normalization an editor that rewrites line endings makes every file look edited, and upgrade then touches nothing — measured, not hypothetical.

Three states, and they decide everything upgrade does:

| State | Meaning | Upgrade does |
|---|---|---|
| hash matches | the user has never edited this file | replace it silently |
| hash differs | the user has edited it | **never overwrite.** Read their file against the template's and edit only what this version changes, with the user — `SKILL.md` §7 step 3 |
| no hash recorded | the user created the file, or the manifest marks it `hashed: false` | never compare it and never overwrite it. A `hashed: false` file the manifest still declares is created once if it is missing — that is how a state file added in a later template version reaches an existing instance — and left alone ever after |

`stamped` records the **pristine template content, not what is on disk** — including for a file the user edited, whose recorded hash moves forward to the newly delivered version once that version has been handed over. That is what makes the next upgrade read a file they edited as theirs again, instead of overwriting it as untouched.

This is what makes an instance safe to upgrade after months of real use. An upgrade that overwrites an edited router destroys work the user cannot recover, so **when in doubt, treat a file as edited.**

## 2. Verify

Seven checks. Report all findings before proposing any repair, and repair only what the user accepts.

**Five of them are already done for you** by `init_workstation.py --verify`. Run it first and read its output; do not redo by hand what it printed.

| # | Check | Who |
|---|---|---|
| 1 | **Inventory.** Every file the manifest lists for an enabled system exists. Nothing exists for a disabled system. | script — prints pristine / edited / missing counts, then each edited and missing file by name, then anything present whose system is off |
| 2 | **Host route.** The marked block is in the host `CLAUDE.md`, and **exactly one** of it. Two blocks means an install ran twice without finding its own markers — a bug worth reporting, not just repairing. | script — per host file: one block, none, or the count |
| 6 | **Nesting.** An instance can appear **above** or below an existing one long after install, and the relation is recorded in only two places. | script — compares the recorded relation against a fresh walk and prints both when they differ. Where a new relation is found, propose recording it in both `instance.json` files and enabling the `nested` block in both routers |
| 7 | **Leftovers.** No stamped file contains `{{` or `<!-- if:`. | script — exits non-zero if any survive |
| 3 | **Memory spine.** `MEMORY.md`, `memory/instructions-memory-maintenance.md`, `memory/index-memory-records.md`, and the `records/`, `archive/`, `runs/` folders exist — the script's inventory covers all of these. Then: every line in the records index has a file behind it, and every record has a line. | script for existence, **you** for the index-to-file correspondence |
| 4 | **Retrieval map.** Every path named in `AGENTS.md` exists **except the work folders**. A router pointing at a folder that was never created is the most common real failure, because it costs a session a wasted read on every miss — but see the exception below, which is not a failure at all. | **you** — the map is prose, not a manifest row |
| 5 | **Sources.** Every path in `context/sources.json` still resolves. Report an absent one as absent — do not delete the row, because a library missing on this machine is normal. | script — `register_sources.py --check` |

**The work folders are the exception to check 4, and it is deliberate.** `initiatives/`, `projects/` and `tasks/` are named in the retrieval map and are **not** created at install. `CONVENTIONS.md` §6 says "no empty placeholder folders — create when there is real content to put in", so an instance that shipped the three empty would be born breaking its own conventions, and empty numbered folders are exactly what invites the dumping ground that rule exists to prevent. The map names where a scope *goes*, not what exists today. A fresh instance with none of the three is conformant; report it as normal, and create one only when a scope actually goes into it.

Also report, without treating it as a fault: which systems are off, and how far each buffer is from its band. Both are the user's decisions, not defects.

## 3. Upgrade

`SKILL.md` §7 carries the procedure. There is no upgrade script: you read the instance against the bundled template and make the edits with the user. What belongs here is the four things that procedure rests on.

1. **The hashes decide which files need judgement, and §1 is the contract.** A file whose hash still matches was never touched, so this version's copy replaces it whole. Only a file whose hash differs is read line by line — and only there can the user lose something.

2. **A token the instance has no answer for stops the upgrade.** The template may declare one added after this instance was installed. Stamping it anyway writes `{{LIKE_THIS}}` into the file as literal text. Ask the user, add it under `answers` in `instance.json`, then continue.

3. **The version and the hashes are recorded at the end, not the start.** `instance.json` takes the new version, and `stamped` takes the **pristine** hash of every hashed file — including the files the user had edited, whose own text stays in place. Recording what is on disk instead makes the next upgrade read their edit as untouched and overwrite it silently. §1 carries why.

4. **An upgrade that cannot read `instance.json` is not an upgrade.** Without the recorded version and hashes there is nothing to compare against. Say so and stop, rather than stamping over the tree.

The backup is step 1 of the procedure, and it covers the host `CLAUDE.md` and `AGENTS.md` as well — the only files outside `.nonighter/` an upgrade rewrites.
