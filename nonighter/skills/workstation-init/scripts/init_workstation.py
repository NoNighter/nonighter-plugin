#!/usr/bin/env python3
"""Install a NoNighter workstation instance into a host folder, from templates/manifest.json.

This is the deterministic half of the skill. The skill interviews - the instance name, the user and
org, which optional systems to enable, what already lives in the folder - and hands the answers here;
this stamps them. The judgment stays with the agent, the stamping does not vary.

What it implements, all of it declared by the manifest rather than known here:

    the folder list, per enabled system          the token registry
    the file list, with each file's owner        the conditional-block contract
    which files are hashed                       the verbatim list
    the host-wiring rules

Modes: install (default), --verify, --uninstall. Upgrade is a procedure, not a script: SKILL.md §7.

Usage:
    init_workstation.py --answers answers.json
    init_workstation.py --show-answer-keys
    init_workstation.py --verify
    init_workstation.py --dry-run --answers answers.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import workstation_lib as wl  # noqa: E402
import stamp_lib as sl  # noqa: E402

WORKSTATION_REL = ".nonighter"
INSTANCE_FILE = "instance.json"

MARKER_RE = re.compile(r"<!--[ 	]*nonighter:[a-z0-9-]+:(start|end)[ 	]*-->")

# Asked in the interview. Everything else in the manifest's registry is derived from these or from
# the machine, and the installer refuses to invent any of them.
ASKED_TOKENS = ["INSTANCE_NAME", "USER_NAME", "ORG_NAME", "USER_FIELD"]

MAX_PATH = 260


def route_markers(manifest) -> tuple:
    """The exact marker strings, read from the template rather than assumed.

    Hardcoding them is how a rename in the template silently turns "refresh the block" into
    "append a second one", leaving two routes in the host CLAUDE.md and no error anywhere.
    """
    text = wl.read_text(manifest.root / "host" / "route-block.md") or ""
    found = MARKER_RE.findall(text)
    spans = [m.group(0) for m in MARKER_RE.finditer(text)]
    if [f for f in found] != ["start", "end"] or len(spans) != 2:
        raise SystemExit("host/route-block.md must carry exactly one nonighter:*:start and one "
                         ":end marker - found {}".format(spans or "none"))
    return spans[0], spans[1]


def derive_prefix(instance_name: str) -> str:
    """A short uppercase slug for the work-list prefix, per the manifest's rule.

    Initials when the name has several words, otherwise the first letters of the single word.
    """
    words = [w for w in re.split(r"[^A-Za-z0-9]+", instance_name) if w]
    if not words:
        return "WS"
    if len(words) > 1:
        return "".join(w[0] for w in words)[:6].upper()
    return words[0][:4].upper()


def find_nesting(host: Path):
    """Other instances above and below, because two routers in one context is the failure that matters.

    Ancestors: every folder from the host up to the drive root. Descendants: one level of subfolders,
    which is what the skill's §1 asks for - deeper than that and an install scans the user's whole
    estate.
    """
    ancestor = None
    for parent in host.parents:
        if (parent / WORKSTATION_REL / "AGENTS.md").exists():
            ancestor = str(parent)
            break
    descendants = []
    try:
        for child in sorted(host.iterdir()):
            if not child.is_dir() or child.name == WORKSTATION_REL or wl.is_link(child):
                continue
            if (child / WORKSTATION_REL / "AGENTS.md").exists():
                descendants.append(str(child))
    except OSError:
        pass
    return ancestor, descendants


def build_values(answers: dict, host: Path, manifest: sl.Manifest) -> dict:
    """The token registry, filled. Asked values from the interview, the rest derived here."""
    # str() first: main() validates through str(), so a non-string value - `"INSTANCE_NAME": 123`
    # in the answers file - passed validation and crashed here on .strip().
    instance_name = str(answers.get("INSTANCE_NAME", "")).strip()
    values = {token: str(answers.get(token, "")).strip() for token in ASKED_TOKENS}
    values.update({
        "INSTANCE_NAME": instance_name,
        # Derived, never asked: an interview that asks for these gets them wrong.
        "INSTANCE_PREFIX": str(answers.get("INSTANCE_PREFIX", "")).strip() or derive_prefix(instance_name),
        "HOST_PATH": str(host),
        "INSTALL_DATE": datetime.date.today().isoformat(),
        "VERSION": manifest.version,
    })
    unknown = [t for t in manifest.tokens if t not in values]
    if unknown:
        raise SystemExit(
            "the manifest declares token(s) this installer does not know how to fill: {}.\n"
            "Add them to build_values, or the stamped files carry them through as literal text."
            .format(", ".join(unknown)))
    return values


def stamp_instance(host: Path, manifest: sl.Manifest, values: dict, enabled: set, dry_run: bool):
    """Create the folders and stamp the files the manifest lists for the enabled systems.

    Returns (stamped hashes, defects). A defect is a leftover token or conditional marker, and it
    fails the install rather than being reported and ignored: a token left in the router is read as
    literal text every session after.
    """
    ws = host / WORKSTATION_REL
    hashes = OrderedDict()
    defects = []

    for folder in manifest.folders(enabled):
        if not dry_run:
            (host / folder).mkdir(parents=True, exist_ok=True)

    for row in manifest.files(enabled):
        template_rel = wl.normalise_rel(row["template"])
        target_rel = wl.normalise_rel(row["target"])
        source = manifest.root / template_rel
        raw = wl.read_text(source)
        if raw is None:
            raise SystemExit("the manifest lists a template that is not on disk: {}\n"
                             "A row with no file is an install crash.".format(template_rel))

        if template_rel in manifest.verbatim:
            # Copied with no substitution: its angle-bracket placeholders are filled in later, by
            # whoever uses it.
            content = raw
        else:
            content = sl.stamp_text(raw, target_rel, values, enabled)
            found = sl.find_leftovers(content)
            if found:
                defects.append("{}: {}".format(target_rel, "; ".join(found)))

        if not dry_run:
            wl.write_text(host / target_rel, content)
        if row.get("hashed"):
            hashes[target_rel] = wl.hash_text(content)

    return hashes, defects


def wire_host(host: Path, manifest: sl.Manifest, values: dict, enabled: set, dry_run: bool) -> dict:
    """Write the route into the host folder's CLAUDE.md, and its AGENTS.md when it has one.

    Anything outside the markers is left alone. The AGENTS.md case exists because a harness reading
    that file instead of CLAUDE.md would otherwise never find the route.
    """
    wiring = {}
    begin, end_marker = route_markers(manifest)
    block_source = manifest.root / "host" / "route-block.md"
    full_source = manifest.root / "host" / "CLAUDE.md"

    for name in ("CLAUDE.md", "AGENTS.md"):
        target = host / name
        exists = target.exists()
        if name == "AGENTS.md" and not exists:
            wiring["agents-md"] = "absent"
            continue

        if not exists:
            content = sl.stamp_text(wl.read_text(full_source) or "", name, values, enabled)
            state = "created"
        else:
            block = sl.stamp_text(wl.read_text(block_source) or "", name, values, enabled)
            existing = wl.read_text(target) or ""
            if begin in existing and end_marker in existing:
                # Every marked span, not just the first. Replacing only the first left any duplicates
                # in place, so a file `--verify` flags for carrying two blocks stayed broken after the
                # thing meant to repair it had run. And the end marker is now searched for AFTER the
                # begin it belongs to: `index(end_marker)` from position zero can return an end that
                # precedes this begin, and the slice between them is the user's own text.
                content, spans = wl.replace_marked_spans(existing, begin, end_marker, block.strip())
                state = "refreshed" if spans < 2 else "refreshed, {} duplicate block(s) removed".format(spans - 1)
            else:
                content = existing.rstrip() + "\n\n" + block.strip() + "\n"
                state = "appended"
        if not dry_run:
            wl.write_text(target, content)
        key = "claude-md" if name == "CLAUDE.md" else "agents-md"
        wiring[key] = state
        # Recorded ONLY when we created the file, and it is the hash of the file with our marked block
        # removed - the shell around it. That combination is the whole fix for a data-loss bug:
        #
        #   Recording it on every write, as "what we last wrote", let a refreshed block fold the user's
        #   own text into the baseline, and the uninstall - which reads this as "the file holds nothing
        #   of theirs" - then deleted a file with their content in it. Recording the WHOLE file only at
        #   creation is safe but useless: the first refresh makes it stale, so the file is never
        #   deletable again, which is what a reviewer flagged in the other direction.
        #
        # Hashing the shell answers the question the uninstall actually asks. The block may be
        # rewritten any number of times without touching it; one line the user adds outside it changes
        # it. And it is not re-recorded afterwards, because creation is the only moment we know for
        # certain that nothing in the file is theirs.
        if state == "created":
            wiring[key + "-hash"] = wl.hash_text(
                wl.shell_without_blocks(content, begin, end_marker))
    return wiring


def write_instance(host: Path, manifest: sl.Manifest, values: dict, enabled: set,
                   hashes, wiring: dict, nesting, dry_run: bool) -> None:
    """The state file, stamped from its own template so its shape stays the manifest's business."""
    ancestor, descendants = nesting
    row = next((f for f in manifest.files(enabled)
                if wl.normalise_rel(f["target"]).endswith(INSTANCE_FILE)), None)
    if row is None:
        raise SystemExit("the manifest does not list {} - the installer cannot record state".format(INSTANCE_FILE))

    raw = wl.read_text(manifest.root / wl.normalise_rel(row["template"])) or "{}"
    instance = json.loads(sl.stamp_text(raw, INSTANCE_FILE, values, enabled))

    systems = instance.setdefault("systems", {})
    # A conditional system this template never listed has to be ADDED here, not skipped: verify
    # reads a missing key as off and then reports that system's own freshly stamped files as
    # "present though its system is off". Only systems that own file rows count - `nested` is a
    # relation between instances, recorded in its own key.
    owns_files = {f.get("system") for f in manifest.files(set(manifest.systems))}
    for system in list(systems) + [s for s in manifest.systems
                                   if s in owns_files and s not in systems]:
        # A system the manifest still declares conditional takes the interview's answer. Anything
        # else is always on - including one that USED to be optional and is not any more, which the
        # template's own default would otherwise leave recorded as off while its files sit there.
        systems[system] = (system in enabled) if system in manifest.systems else True
    # Every asked answer, recorded so a later upgrade can rebuild the same values. Without this, a
    # token added to the template after an instance was installed has nothing to fill it from, and
    # the upgrade stamps it into the file as literal text.
    instance["answers"] = OrderedDict((t, values.get(t, "")) for t in ASKED_TOKENS)
    instance["host-wiring"] = wiring
    instance["nested"] = {"ancestor": ancestor, "descendants": descendants}
    instance["stamped"] = hashes

    if not dry_run:
        wl.write_json(host / WORKSTATION_REL / INSTANCE_FILE, instance)


def record_descendant(ancestor: str, child: Path, dry_run: bool) -> str:
    """Tell the outer instance it now contains an inner one.

    Only the fact is recorded. The ancestor's own AGENTS.md was stamped before this child
    existed, so its text still says nothing about nesting - that is what the returned note
    is for. Flipping its "nested" flag here would make --verify claim a section its files
    do not carry.
    """
    state = Path(ancestor) / WORKSTATION_REL / INSTANCE_FILE
    instance = wl.read_json(state)
    if not instance:
        return "could not read the outer instance at {} - it does not know about this one".format(state)

    nested = instance.setdefault("nested", {"ancestor": None, "descendants": []})
    listed = nested.setdefault("descendants", [])
    entry = str(child)
    if entry in listed:
        return "the outer instance already listed this folder"
    listed.append(entry)
    if not dry_run:
        wl.write_json(state, instance)
    return ("recorded in the outer instance at {}. Its own AGENTS.md predates this child, so it "
            "will not mention it until that instance is upgraded".format(ancestor))


def enable_system(host: Path, manifest, name: str) -> int:
    """Turn on an optional system in an installed instance.

    The skill has been telling users a system can be added later, and until this existed that was a
    promise with nothing behind it: systems were settled at install and there was no way back. The
    flag moves here; the files are delivered by the upgrade path, which already knows how to add a
    file without touching the user's edits and how to treat a router they have changed.
    """
    ws = host / WORKSTATION_REL
    instance = wl.read_json(ws / INSTANCE_FILE)
    if not instance:
        raise SystemExit("no readable {} at {}".format(INSTANCE_FILE, ws))
    if name not in manifest.systems:
        raise SystemExit("this template set has no system called {!r}. It declares: {}".format(
            name, ", ".join(manifest.systems)))
    if name == "nested":
        raise SystemExit("`nested` is not a choice - it is set by the scan for other instances.")

    systems = instance.setdefault("systems", {})
    if systems.get(name):
        print("{} is already on for this instance. Nothing to do.".format(name))
        return 0

    systems[name] = True
    wl.write_json(ws / INSTANCE_FILE, instance)
    print("{} is now on for this instance.".format(name))
    print("")
    print("The files it brings are not there yet. Deliver them by following SKILL.md §7,")
    print("which reads this instance against the bundled template and edits with the user.")
    print("")
    print("The router changes too, because the system's rows live in a conditional block. Where the")
    print("user has edited it, that lands as a conflict to merge with them - not as an overwrite.")
    return 0


def verify(host: Path, manifest: sl.Manifest) -> int:
    """Compare an installed instance against the template set at its own version."""
    ws = host / WORKSTATION_REL
    instance = wl.read_json(ws / INSTANCE_FILE)
    if not instance:
        print("no readable {} in {} - a tree with no state file cannot be verified".format(INSTANCE_FILE, ws))
        return 1

    systems = instance.get("systems", {})
    on = sorted(k for k, v in systems.items() if v)
    off = sorted(k for k, v in systems.items() if not v)
    print("instance: {} (v{})".format(instance.get("instance", {}).get("name"), instance.get("version")))
    print("  systems on:  {}".format(", ".join(on) or "none"))
    print("  systems off: {}".format(", ".join(o for o in off if o != "nested") or "none"))
    if instance.get("version") != manifest.version:
        print("  NOTE: the bundled template set is v{} - upgrade it with SKILL.md §7".format(manifest.version))

    stamped = {wl.normalise_rel(k): str(v).lower()
               for k, v in (instance.get("stamped") or {}).items()}
    missing, edited, pristine = [], [], 0
    for rel, recorded in sorted(stamped.items()):
        target = host / rel
        if not target.exists():
            missing.append(rel)
            continue
        # Hash the way the upgrade does, by suffix, rather than assuming every recorded file is UTF-8
        # text. They agree today because every hashed row happens to be text, but a hashed non-text row
        # would make verify disagree with the upgrade about the same file - or crash on the decode.
        theirs = (wl.hash_file_normalised(target) if wl.is_text_file(target.suffix)
                  else wl.hash_file(target))
        if str(theirs).lower() == recorded:
            pristine += 1
        else:
            edited.append(rel)

    # The files the manifest declares WITHOUT a hash - MEMORY.md, the four registries, the state files.
    # They have no recorded hash by design, so the loop above cannot see them, and an inventory that
    # skips them reports a healthy instance whose memory file has been deleted. They can only ever be
    # present or absent: there is nothing to compare them against.
    unhashed_missing = []
    active = {name for name in manifest.systems if systems.get(name)}
    nesting = instance.get("nested") or {}
    if nesting.get("ancestor") or nesting.get("descendants"):
        active.add("nested")
    for row in manifest.files(active):
        if row.get("hashed", True):
            continue
        rel = wl.normalise_rel(row["target"])
        if rel not in stamped and not (ws.parent / rel).exists():
            unhashed_missing.append(rel)

    print("  {} pristine, {} edited, {} missing".format(
        pristine, len(edited), len(missing) + len(unhashed_missing)))
    for rel in edited:
        print("    edited:  {}".format(rel))
    for rel in missing:
        print("    MISSING: {}".format(rel))
    for rel in sorted(unhashed_missing):
        print("    MISSING: {}  (no hash recorded - the instance writes this one)".format(rel))

    # Check 2 of reference-verify.md: exactly one route block per host file. Two means an install
    # ran twice without recognising its own markers - a bug worth reporting, not just repairing.
    begin, end_marker = route_markers(manifest)
    for name in ("CLAUDE.md", "AGENTS.md"):
        target = host / name
        if not target.exists():
            print("  host {:<10} absent".format(name))
            continue
        text = wl.read_text(target) or ""
        count = text.count(begin)
        if count == 1 and end_marker in text:
            print("  host {:<10} one route block".format(name))
        elif count == 0:
            print("  host {:<10} NO route block - nothing routes into the instance from here"
                  .format(name))
        else:
            print("  host {:<10} {} route blocks - an install ran twice without matching its own "
                  "markers".format(name, count))

    # Nothing should exist for a system the interview switched off.
    off = [s for s in manifest.systems if not systems.get(s)]
    leaked = []
    for row in manifest.files(set(manifest.systems)):
        if row.get("system") in off and (host / wl.normalise_rel(row["target"])).exists():
            leaked.append(wl.normalise_rel(row["target"]))
    for rel in leaked:
        print("  present though its system is off: {}".format(rel))

    # An instance can appear above or below this one long after install.
    ancestor, descendants = find_nesting(host)
    recorded = instance.get("nested") or {}
    if ancestor != recorded.get("ancestor") or sorted(descendants) != sorted(recorded.get("descendants") or []):
        print("  nesting has changed since install:")
        print("    recorded: ancestor {}, descendants {}".format(
            recorded.get("ancestor"), recorded.get("descendants") or []))
        print("    on disk:  ancestor {}, descendants {}".format(ancestor, descendants))

    # Only the files the manifest declares - what the installer actually stamped. Scanning the whole
    # tree made this check cry wolf on a healthy instance, and loudly: on a real folder it reported
    # INSTALL DEFECTS for `memory/archive/2026-09-01_1807-workstation.md`, a file the memory pass wrote,
    # whose crime was quoting the token names while documenting the day's work on tokens. Plus the same
    # file again from inside `backups/`.
    #
    # The claim is "no token survived stamping", so the scope is the stamped files. A token-shaped
    # string in the user's own notes is not a defect, and telling them their install is broken when it
    # is not costs more than the check is worth - they cannot tell a false alarm from a real one.
    # Iterate the declared rows, rather than walking the tree and filtering it down to them. Same
    # result, and it stops the check's cost from tracking something it has nothing to do with: on a real
    # folder the walk visited 97 files to examine 17, and 49 of the 97 were inside `backups/` - three
    # full copies of the instance, which grow with every upgrade.
    leftovers = []
    for row in manifest.files(active):
        rel = wl.normalise_rel(row["target"])
        target = host / rel
        if not wl.is_text_file(target.suffix) or not target.exists():
            continue
        found = sl.find_leftovers(wl.read_text(target) or "")
        if found:
            leftovers.append("{}: {}".format(rel, "; ".join(found)))

    # The host files too, and they had never been checked - not before the narrowing above and not
    # after it. The walk starts at `.nonighter/`, and `host/CLAUDE.md` carries `{{HOST_PATH}}`, so a
    # token surviving into a freshly created host CLAUDE.md went unreported while the line below said
    # there were none.
    #
    # But the scope has to be OUR part of those files, for the same reason the narrowing happened: when
    # the installer only appended a block, the rest of that file is the user's, and a token-shaped
    # string in their own text is not our defect. So: the marked block always, and the whole file only
    # where `host-wiring` records that we created it.
    wiring_state = instance.get("host-wiring") or {}
    for name, key in (("CLAUDE.md", "claude-md"), ("AGENTS.md", "agents-md")):
        text = wl.read_text(host / name)
        if not text:
            continue
        # "We created it" is not the same as "it is still all ours". The template's own host CLAUDE.md
        # invites the user to write outside the block - *"anything written here outside the marked block
        # above is yours"* - so scanning the whole file on the strength of `created` alone brings back
        # the false alarm this whole check was just narrowed to remove, one file over.
        #
        # The exact question is the one the uninstall already asks before it dares delete that file:
        # does anything outside our block differ from what we wrote? Same helper, so the two cannot
        # answer it differently - and they must not, since one would delete the user's text and the
        # other would call it an install defect.
        if (wiring_state.get(key) == "created"
                and wl.shell_is_untouched(text, wiring_state.get(key + "-hash"), begin, end_marker)):
            ours = text
        else:
            spans = wl.find_marked_spans(text, begin, end_marker)
            ours = "\n".join(text[a:b] for a, b in spans)
        found = sl.find_leftovers(ours) if ours else []
        if found:
            leftovers.append("../{}: {}".format(name, "; ".join(found)))

    if leftovers:
        print("  INSTALL DEFECTS - these should never have survived stamping:")
        for line in leftovers:
            print("    {}".format(line))
        return 1

    print("  no leftover tokens or conditional markers")
    return 0 if not missing else 1


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", help="host folder to WRITE into; defaults to what the surface reports")
    parser.add_argument("--host-path", help="the folder's durable path, the one to RECORD. Only needed where --host is a per-session sandbox mount, which is not the path the user will see tomorrow.")
    parser.add_argument("--templates", default=str(here.parent / "templates"))
    parser.add_argument("--answers", help="JSON with the interview's answers")
    parser.add_argument("--show-answer-keys", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--enable", metavar="SYSTEM",
                        help="turn on an optional system in an instance already installed. Flips the "
                             "flag; the upgrade procedure in SKILL.md §7 then delivers the files.")
    parser.add_argument("--dry-run", action="store_true", help="report the plan, write nothing")
    args = parser.parse_args(argv)

    manifest = sl.Manifest(Path(args.templates).resolve() / "manifest.json")

    if args.show_answer_keys:
        print("Asked in the interview:")
        for token in ASKED_TOKENS:
            print("  {:<16} required".format(token))
        print("  {:<16} optional - derived from INSTANCE_NAME when absent".format("INSTANCE_PREFIX"))
        print("Optional systems (list the ones to enable under \"systems\"):")
        for system in manifest.systems:
            if system != "nested":   # not a choice; set by the nesting scan
                print("  {}".format(system))
        print("Derived from the machine, never supplied: HOST_PATH, INSTALL_DATE, VERSION")
        return 0

    host = (Path(args.host) if args.host else wl.default_scope()).resolve()
    if not host.is_dir():
        raise SystemExit("host folder not found: {}".format(host))

    # What gets written into every stamped file is not always the path we write THROUGH. In a Cowork
    # session the folder is mounted at /sessions/<session>/mnt/<folder>, and that session name is
    # gone tomorrow - so recording it puts a dead path in the router, the host CLAUDE.md, every
    # card and every source. Measured on a real install before this check existed.
    record_as = Path(args.host_path).resolve() if args.host_path else host
    if wl.is_ephemeral_path(record_as) and not args.host_path:
        # Before asking a human, look for the durable path in the environment. The surface that
        # mounts the folder usually also names it: the first Cowork install recorded a per-session
        # mount only because the caller passed the path it could SEE instead of letting this script
        # resolve one. Where a durable candidate names the same folder, take it and say so.
        for candidate in wl.candidate_scopes():
            if wl.is_ephemeral_path(candidate):
                continue
            if Path(candidate).name == host.name:
                record_as = Path(candidate)
                print("note: {} is a per-session mount, so recording the durable path the surface "
                      "reports instead: {}".format(host, record_as))
                break

    if wl.is_ephemeral_path(record_as):
        print("")
        print("STOP: {} is a per-session sandbox mount, not a durable folder.".format(record_as))
        print("Stamping it would put a path that dies with this session into the router, the host")
        print("CLAUDE.md, and every source and card - a workstation that works today only.")
        print("")
        print("Ask the user for the folder's real path as they see it on their machine (something")
        print("like C:/Users/<name>/Documents/<folder>), then re-run with:")
        print("    --host \"{}\" --host-path \"<the real path>\"".format(host))
        print("")
        print("Paths visible in this process's environment - if one of these is that folder, it is")
        print("the variable this script should be reading and this stops being a question:")
        for line in wl.path_like_environment():
            print("  {}".format(line))
        return 1

    if args.verify:
        return verify(host, manifest)

    if args.enable:
        return enable_system(host, manifest, args.enable)

    if not args.answers:
        raise SystemExit("no --answers. Run --show-answer-keys for what the interview must settle.")
    answers = wl.read_json(Path(args.answers))
    if answers is None:
        raise SystemExit("answers file not found: {}".format(args.answers))

    missing = [t for t in ASKED_TOKENS if not str(answers.get(t, "")).strip()]
    if missing:
        raise SystemExit("the interview did not settle: {}".format(", ".join(missing)))

    ws = host / WORKSTATION_REL
    if (ws / "AGENTS.md").exists():
        print("an instance already exists at {}".format(ws))
        print("Verify it with --verify, or upgrade it by following SKILL.md §7. This does not overwrite.")
        return 1

    enabled = {s for s in answers.get("systems", []) if s in manifest.systems}
    ancestor, descendants = find_nesting(host)
    if ancestor or descendants:
        enabled.add("nested")

    values = build_values(answers, record_as, manifest)

    deepest = max((len(wl.normalise_rel(f["target"])) for f in manifest.files(enabled)), default=0)
    projected = len(str(host)) + 1 + deepest
    if projected > MAX_PATH - 1:
        print("WARNING: the deepest file lands at about {} characters, past the Windows limit of {}."
              .format(projected, MAX_PATH))
        print("WARNING:   a shorter host folder is the safe fix: {}".format(host))

    print("host folder:   {}".format(host))
    if record_as != host:
        print("recorded as:   {}".format(record_as))
    print("instance:      {} (prefix {})".format(values["INSTANCE_NAME"], values["INSTANCE_PREFIX"]))
    print("systems on:    {}".format(", ".join(sorted(enabled)) or "the always-on three only"))
    print("systems off:   {}".format(
        ", ".join(sorted(set(manifest.systems) - enabled - {"nested"})) or "none"))
    if ancestor:
        print("nested under:  {}".format(ancestor))
    for child in descendants:
        print("contains:      {}".format(child))

    hashes, defects = stamp_instance(host, manifest, values, enabled, args.dry_run)
    if defects:
        print("")
        print("INSTALL DEFECTS - refusing to finish. A token or marker left in a stamped file is read")
        print("as literal text every session after, so this stops here rather than reporting success:")
        for line in defects:
            print("  {}".format(line))
        return 1

    wiring = wire_host(host, manifest, values, enabled, args.dry_run)
    write_instance(host, manifest, values, enabled, hashes, wiring,
                   (ancestor, descendants), args.dry_run)
    note = record_descendant(ancestor, host, args.dry_run) if ancestor else None

    print("")
    if args.dry_run:
        print("dry run - nothing written. {} file(s) would be stamped, {} hashed.".format(
            len(manifest.files(enabled)), len(hashes)))
        return 0

    print("=== instance stamped (template set v{}) ===".format(manifest.version))
    print("  workstation: {}".format(ws))
    print("  host wiring: {}".format(", ".join("{} {}".format(k, v) for k, v in wiring.items()
                                                if not k.endswith("-hash"))))
    print("  hashed:      {} file(s)".format(len(hashes)))
    if note:
        print("  nesting:     {}".format(note))
    print("  Stamped, not verified. Run --verify to check it, and say which you did.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
