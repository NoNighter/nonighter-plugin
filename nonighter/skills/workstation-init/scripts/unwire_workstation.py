#!/usr/bin/env python3
"""Remove a workstation's route from its host folder. Never deletes the instance.

Unwiring is the reversible half of uninstall: the marked block comes out of the host CLAUDE.md
and AGENTS.md, the nesting relation is repaired on both sides, and instance.json records that it
is no longer routed. Everything under .nonighter/ stays exactly where it is - months of memory,
records and context cards are not an agent's call to delete, so this script has no code that can.

    py unwire_workstation.py --host "C:/path/to/folder"
    py unwire_workstation.py --host "C:/path/to/folder" --dry-run
    py unwire_workstation.py --host "C:/path/to/folder" --delete-created-claude-md

The last flag applies only to a CLAUDE.md this installer created and the user never edited.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workstation_lib as wl  # noqa: E402
import stamp_lib as sl  # noqa: E402
from init_workstation import WORKSTATION_REL, INSTANCE_FILE, route_markers  # noqa: E402


def strip_block(text, begin, end):
    """Cut out every marked span, and only those. Returns (text, spans removed).

    Two things were wrong with removing only the first. A host file can hold more than one route block
    - `--verify` reports exactly that state - and unwiring then reported success while the host went on
    routing through the block left behind. And the end marker was found with `text.index(end)` from
    position zero, which with two blocks present can return an end belonging to the earlier one; what
    sits between that end and this begin is the user's own text.
    """
    spans = wl.find_marked_spans(text, begin, end)
    if not spans:
        return text, 0
    before, previous_end = text[:spans[0][0]], spans[0][1]
    for start, stop in spans[1:]:
        before += text[previous_end:start]
        previous_end = stop
    after = text[previous_end:]
    joined = before.rstrip() + ("\n\n" + after.lstrip() if after.strip() else "\n")
    return joined, len(spans)


def unwire_file(path, begin, end, dry_run):
    if not path.exists():
        return "absent"
    original = wl.read_text(path) or ""
    stripped, removed = strip_block(original, begin, end)
    if not removed:
        return "no route block found"
    if not dry_run:
        wl.write_text(path, stripped)
    return "route removed" if removed == 1 else "route removed ({} blocks)".format(removed)


def holds_nothing_of_the_user(path, recorded, begin, end):
    """True when everything outside our marked block is still exactly what the installer wrote.

    **The comparison is on the file with our block removed**, against the shell hash recorded at
    creation. Comparing whole files was a data-loss bug: the recorded hash was refreshed by every
    upgrade, so once a block had been rewritten the user's own additions were part of the baseline and
    this returned True for a file full of their text - which was then deleted, with no backup, because
    the upgrade's backup covers `.nonighter/` and not the host folder.

    Exact, so one line the user added keeps their file. Without a recorded hash the answer is no: an
    unverifiable guess is not grounds for deleting somebody's file.
    """
    if not path.exists():
        return False
    return wl.shell_is_untouched(wl.read_text(path) or "", recorded, begin, end)


def repair_nesting(host, instance, dry_run):
    """Take this instance out of the other side's record, in both directions."""
    notes = []
    nested = instance.get("nested") or {}
    me = str(host)

    ancestor = nested.get("ancestor")
    if ancestor:
        state = Path(ancestor) / WORKSTATION_REL / INSTANCE_FILE
        outer = wl.read_json(state)
        if not outer:
            notes.append("could not read the outer instance at {} - its descendant list still "
                         "names this folder".format(state))
        else:
            listed = (outer.setdefault("nested", {})).setdefault("descendants", [])
            if me in listed:
                listed.remove(me)
                if not dry_run:
                    wl.write_json(state, outer)
                notes.append("removed from the descendant list of {}".format(ancestor))
            else:
                notes.append("the outer instance at {} did not list this folder".format(ancestor))

    for child in nested.get("descendants") or []:
        state = Path(child) / WORKSTATION_REL / INSTANCE_FILE
        inner = wl.read_json(state)
        if not inner:
            notes.append("could not read the inner instance at {} - it still names this folder as "
                         "its ancestor".format(state))
            continue
        if (inner.get("nested") or {}).get("ancestor") == me:
            inner.setdefault("nested", {})["ancestor"] = None
            if not dry_run:
                wl.write_json(state, inner)
            notes.append("cleared the ancestor pointer in {}".format(child))
    return notes


def main(argv=None):
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host")
    parser.add_argument("--templates", default=str(here.parent / "templates"))
    parser.add_argument("--delete-created-claude-md", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    host = (Path(args.host) if args.host else wl.default_scope()).resolve()
    manifest = sl.Manifest(Path(args.templates).resolve() / "manifest.json")
    begin, end = route_markers(manifest)

    ws = host / WORKSTATION_REL
    instance = wl.read_json(ws / INSTANCE_FILE) or {}
    name = (instance.get("instance") or {}).get("name")
    print("host folder: {}".format(host))
    print("instance:    {}".format(name or "unnamed - no readable {}".format(INSTANCE_FILE)))
    if not ws.exists():
        print("nothing to unwire: there is no {} here".format(WORKSTATION_REL))
        return 1

    wiring_state = instance.get("host-wiring") or {}
    # Read BEFORE the block is stripped below: the check needs the file as it stands, block included.
    ours_alone = (wiring_state.get("claude-md") == "created"
                  and holds_nothing_of_the_user(host / "CLAUDE.md",
                                                wiring_state.get("claude-md-hash"), begin, end))

    results = {}
    for target in ("CLAUDE.md", "AGENTS.md"):
        results[target] = unwire_file(host / target, begin, end, args.dry_run)
        print("  {:<10} {}".format(target, results[target]))

    deleted = False
    if ours_alone:
        if args.delete_created_claude_md:
            if not args.dry_run:
                wl.make_writable(host / "CLAUDE.md")
                (host / "CLAUDE.md").unlink()
            deleted = True
            print("  CLAUDE.md  deleted - the installer created it and it held nothing else")
        else:
            print("  CLAUDE.md  the installer created it and it now holds nothing of the user's;")
            print("             pass --delete-created-claude-md to remove it, or leave it")

    for note in repair_nesting(host, instance, args.dry_run):
        print("  nesting:   {}".format(note))

    if instance:
        wiring = instance.setdefault("host-wiring", {})
        # Record what happened, not what was attempted. "removed" was written unconditionally for
        # CLAUDE.md, so a file that was absent or never carried a block ended up recorded as one
        # whose route we took out. And the AGENTS.md check compared the exact string "route
        # removed", which stopped matching the moment the message could read "route removed (3
        # blocks)" - so repairing duplicates left the state claiming the host was still routed.
        def outcome(result, previous):
            if str(result).startswith("route removed"):
                return "removed"
            return previous if previous else str(result)
        if deleted:
            wiring["claude-md"] = "deleted"
        else:
            wiring["claude-md"] = outcome(results["CLAUDE.md"], None)
        wiring["agents-md"] = outcome(results["AGENTS.md"], wiring.get("agents-md"))
        wiring["unwired"] = datetime.date.today().isoformat()
        if not args.dry_run:
            wl.write_json(ws / INSTANCE_FILE, instance)

    print("")
    if args.dry_run:
        print("dry run - nothing written.")
        return 0
    print("=== unwired ===")
    print("  No session will load this instance again.")
    print("  Everything it holds is still at {} - memory, records, cards, work notes."
          .format(ws))
    print("  Deleting that folder is the user's call, by hand. This script cannot and does not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
