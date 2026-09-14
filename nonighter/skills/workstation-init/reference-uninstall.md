# Reference — uninstall

> How an instance is unwired. Read when the user asks to remove, uninstall, or disconnect a workstation.

## 1. What uninstall does

**Uninstall removes the route. It never deletes the instance.**

Removing the route touches only the span between two markers and is reversible in one edit. Deleting `.nonighter/` destroys months of memory, records, context cards and work notes in one unrecoverable step — and an agent is the wrong actor for that decision. The user deletes the folder by hand if they want it gone.

An instance with no route is already silent. Nothing loads it, it costs no tokens, and it sits there readable.

## 2. Procedure

1. **Confirm which instance.** Name the host folder and the instance name back to the user before editing anything. In a nested pair, removing the wrong route is a silent failure — work continues, against the wrong conventions.
2. **Run a final memory pass.** `memory/instructions-memory-maintenance.md`. The buffers hold work that has not been drained into records yet, and after unwiring no session will run the pass again. Skipping this is how the last few days of work are lost.
3. **Remove the marked block** from the host `CLAUDE.md`, and from the host `AGENTS.md` where the block is there too. Delete the markers and everything between them, and **nothing else** — content outside them is the user's.
4. **Clean up an empty host `CLAUDE.md`.** Where the installer created that file and the block was all it ever held, offer to delete it; `host-wiring` in `instance.json` records whether the installer created it or found it. Where the user has written anything of their own in it, leave the file.
5. **Fix the nesting relation.** Where `instance.json` records an ancestor or descendant, remove the reciprocal entry from that other instance's `instance.json` and disable its `nested` conditional block if this was its only relation. A precedence line naming an instance that is no longer routed sends a future session looking for a router that will never load.
6. **Stamp the instance as unwired.** Set `host-wiring` to `removed` and record the date. A later install in the same folder then finds a complete instance with no route and can offer to rewire it rather than restamp over it.

## 3. Report

Tell the user: the route is gone, no session will load this instance again, the folder is at `.nonighter/` and still holds everything, and they can delete it by hand or leave it. Name what the final memory pass wrote.

**Do not offer to delete the folder.** If the user asks you to, that is their call to make explicitly — read what is in it first, say what will be lost, and get a second confirmation.
