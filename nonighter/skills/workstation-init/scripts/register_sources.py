#!/usr/bin/env python3
"""Register the folders the user names as context sources, and re-check the ones already registered.

Two jobs, both of which the model should not be doing by hand:

**One fixed shape for `context/sources.json`.** The context system's instructions name what a source
carries - its class, its write permission, its mapping depth, its confirmation - but not what the
keys are called. Left to prose, two sessions write two different key names into the same file, and
the conformance run that reads it back finds neither. The schema lives here instead.

**Validation before recording.** A path that does not exist, is a file, or sits inside the instance
itself is refused out loud rather than recorded. A silently broken reference is worse than a missing
one: nothing will ever say why the context came back empty.

    py register_sources.py --host "<host>" --sources "<scratch>/sources.json"
    py register_sources.py --host "<host>" --check
    py register_sources.py --host "<host>" --list

Input is a JSON array (or `{"sources": [...]}`) of objects carrying at least `path`. Optional per
source: `label`, `class`, `depth`. Anything not given is derived and reported.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import unicodedata
import uuid
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workstation_lib as wl  # noqa: E402
from init_workstation import WORKSTATION_REL, INSTANCE_FILE  # noqa: E402

SOURCES_REL = "context/sources.json"
CLASSES = ("company-shared", "host-local")
DEFAULT_DEPTH = 2
MAX_DEPTH = 3


def is_cloud_placeholder(path: Path) -> bool:
    """A cloud-sync placeholder (OneDrive Files-On-Demand) rather than a plain folder?

    Worth telling the user when they register a reference folder: a placeholder lists its files but
    the bytes may not be on the machine, so reading one needs the sync client online. The tell is the
    reparse-point flag with no link target - a real junction resolves elsewhere.
    """
    try:
        attrs = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    if not attrs & wl.FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    try:
        return path.resolve() == path.absolute()
    except OSError:
        return False


def slugify(text: str) -> str:
    """A slug that is safe as a folder name anywhere.

    Accents are folded to ASCII first: `isalnum()` considers them alphanumeric, so a plain filter kept
    them and produced `valuacion-meridian-2026` beside `valuación-meridian-2026` for the same folder -
    one from the scope naming, one from here. A slug names a folder (`context/cards/<slug>/`) and is
    matched as text, so two spellings of it are two folders and a lookup that misses.
    """
    folded = unicodedata.normalize("NFKD", text.lower())
    ascii_only = "".join(c for c in folded if not unicodedata.combining(c))
    slug = "".join(c if c.isalnum() and ord(c) < 128 else "-" for c in ascii_only).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "source"


def resolve_recorded(host, source):
    """The folder a recorded row points at, resolved for THIS session.

    The host-relative form wins where there is one: it is the only one that resolves on a surface
    that reaches the same folder by a different absolute path. `path` is the fallback, and is what a
    reader outside this system uses.
    """
    rel = source.get("relative-to-host")
    if rel:
        return (host if rel == "." else host / rel).resolve()
    raw = str(source.get("path", ""))
    if source.get("base") == "host" and raw and not Path(raw).is_absolute():
        return (host / raw).resolve()          # rows written before `relative-to-host` existed
    return Path(raw)


def validate(item, host: Path, ws: Path, durable: Path):
    """One input record to (source, note) - source is None when it must not be recorded."""
    raw = str(item.get("path", "")).strip()
    label = str(item.get("label", "")).strip()
    if not raw:
        return None, "no path given, skipped: {!r}".format(label or item)

    candidate = Path(raw)
    if not candidate.exists():
        return None, "does not exist, NOT registered: {}".format(raw)
    if not candidate.is_dir():
        return None, "is a file, not a folder, NOT registered: {}".format(raw)

    resolved = candidate.resolve()
    if resolved == ws or ws in resolved.parents:
        return None, ("is inside the instance itself, NOT registered: {} - mapping the workstation "
                      "produces cards describing its own cards".format(resolved))

    host_local = resolved == host or host in resolved.parents
    declared = item.get("class")
    if declared and declared not in CLASSES:
        return None, "unknown class {!r}, NOT registered: {}".format(declared, resolved)
    source_class = declared or ("host-local" if host_local else "company-shared")

    depth = item.get("depth", DEFAULT_DEPTH)
    try:
        depth = max(1, min(MAX_DEPTH, int(depth)))
    except (TypeError, ValueError):
        depth = DEFAULT_DEPTH

    # No writability probe, and no choice of where a description goes: since 0.6.0 every card this
    # system writes lives inside the instance, at context/cards/<slug>/, and nothing is ever written
    # into a described folder. That removed four recorded fields along with the probe - writable,
    # writable-basis, descriptor-home and descriptor-writes-confirmed - because each existed to
    # manage a write that no longer happens. It also removed the probe's own failure mode: it
    # created a file to find out, and a probe it could not delete left litter in the user's folder.

    # A folder inside the host is recorded RELATIVE to it, and that is not tidiness: in a Cowork
    # session the same folder is reached through /sessions/<session>/mnt/..., so an absolute path
    # recorded there is dead by the next morning. A relative path resolves on every surface.
    # Anything outside the host has no relative form, so it is absolute - and an ephemeral absolute
    # path is refused rather than written, because a source nobody can resolve is worse than a
    # source that was never registered.
    if host_local:
        rel = resolved.relative_to(host).as_posix() if resolved != host else "."
        # BOTH forms, on purpose. `path` stays a durable absolute one so anything reading this file
        # without knowing our conventions still resolves it - the authoring kit's own verifier does
        # exactly that, and a relative-only row made it warn on every source. `relative-to-host` is
        # what WE resolve through, because it is the only form that survives a surface where the same
        # folder is reached by a different absolute path.
        recorded_path, base, relative = str(durable / rel if rel != "." else durable), "host", rel
    elif wl.is_ephemeral_path(resolved):
        # Reached through this session's mount. The durable path is derivable when the host folder is
        # reached the same way and its own durable path is known, and deriving it is the difference
        # between recording the folder and abandoning it - a run left a shared library one folder up
        # as a pending item for exactly this reason.
        translated = wl.durable_equivalent(resolved, host, durable)
        if translated is None:
            return None, ("is only reachable through this session's mount and its real path cannot be "
                          "derived, NOT registered: {} - ask the user for the folder's path as they "
                          "see it on their machine, and pass it in the row".format(resolved))
        recorded_path, base, relative = str(translated), "absolute", None
    else:
        recorded_path, base, relative = str(resolved), "absolute", None

    cloud = is_cloud_placeholder(resolved)
    source = OrderedDict([
        ("slug", slugify(label or resolved.name)),
        ("label", label or resolved.name),
        ("path", recorded_path),
        ("base", base),
        ("relative-to-host", relative),
        ("class", source_class),
        ("depth", depth),
        ("cloud-placeholder", cloud),
        ("cards-home", "instance"),
        ("registered", datetime.date.today().isoformat()),
    ])
    note = ("registered {} [{}] depth {}; cards go to .nonighter/context/cards/{}/ - nothing is written "
            "inside the folder itself").format(source["label"], source_class, depth,
                                               source["slug"])
    if cloud:
        note += ("\n    WARNING: cloud-sync placeholder - it lists its files but the bytes may not be "
                 "on this machine, so reading them needs the sync client online")
    return source, note


def load_file(host: Path):
    path = host / WORKSTATION_REL / SOURCES_REL
    data = wl.read_json(path)
    if data is None:
        raise SystemExit(
            "no {} at {}. Either the context system is off for this instance, or the install did not "
            "finish - check with init_workstation.py --verify.".format(SOURCES_REL, path))
    data.setdefault("sources", [])
    return path, data


def register(host: Path, ws: Path, durable: Path, input_path: Path, dry_run: bool) -> int:
    items = wl.read_json(input_path)
    if items is None:
        raise SystemExit("input file not found: {}".format(input_path))
    if isinstance(items, dict):
        items = items.get("sources", [])
    if not isinstance(items, list):
        raise SystemExit("input must be a JSON array of sources, or an object with a `sources` array")

    path, data = load_file(host)
    existing = {resolve_recorded(host, s): s for s in data["sources"]}
    added, refused = 0, 0

    for item in items:
        source, note = validate(item, host, ws, durable)
        print("  {}".format(note))
        if source is None:
            refused += 1
            continue
        previous = existing.get(resolve_recorded(host, source))
        if previous:
            source["registered"] = previous.get("registered", source["registered"])
            source["slug"] = previous.get("slug", source["slug"])   # the slug is an address; keep it
            data["sources"][data["sources"].index(previous)] = source
            print("    (already registered - updated in place, confirmation kept)")
        else:
            # The slug is a key and a folder name - `context/cards/<slug>/` - and two sources can
            # easily derive the same one: two folders both called `Documents`, or the same label given
            # twice. Colliding means one source's cards land in the other's folder, which nothing
            # downstream can detect because both rows look well-formed. Suffix instead, and say so.
            taken = {s.get("slug") for s in data["sources"]}
            if source["slug"] in taken:
                stem, n = source["slug"], 2
                while "{}-{}".format(stem, n) in taken:
                    n += 1
                source["slug"] = "{}-{}".format(stem, n)
                print("    slug '{}' was taken by another source - registered as '{}'"
                      .format(stem, source["slug"]))
            data["sources"].append(source)
            added += 1

    if not dry_run:
        wl.write_json(path, data)
    print("")
    print("{} added, {} refused, {} registered in total{}".format(
        added, refused, len(data["sources"]), " (dry run - nothing written)" if dry_run else ""))
    if refused:
        print("Relay the refusals to the user. A folder they named and did not get is something they "
              "need to hear about, not a silent omission.")
    return 1 if refused else 0


def check(host: Path) -> int:
    """The mechanical half of the conformance run: does every recorded source still resolve?"""
    path, data = load_file(host)
    if not data["sources"]:
        print("no sources registered - the context system is installed and empty")
        return 0

    problems = 0
    for source in data["sources"]:
        target = resolve_recorded(host, source)
        state = []
        if not target.exists():
            state.append("ABSENT on this machine")
            problems += 1
        elif not target.is_dir():
            state.append("NOT A FOLDER any more")
            problems += 1
        elif is_cloud_placeholder(target) and not source.get("cloud-placeholder"):
            state.append("has become a cloud placeholder since it was registered")
        print("  {:<28} {:<14} {}".format(source.get("slug", "?"), source.get("class", "?"),
                                          "; ".join(state) or "ok"))

    print("")
    print("{} source(s), {} problem(s)".format(len(data["sources"]), problems))
    if problems:
        print("Report an absent source as absent - do NOT delete the row. A library missing on this "
              "machine is normal: a different machine, the sync client offline, a VPN not connected.")
    return 1 if problems else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", help="host folder to READ through")
    parser.add_argument("--host-path", help="the host folder's durable path, the one recorded "
                        "against. Defaults to what the instance already recorded, which is right "
                        "unless the folder moved.")
    parser.add_argument("--sources", help="JSON with the folders to register")
    parser.add_argument("--check", action="store_true", help="re-validate what is already recorded")
    parser.add_argument("--list", action="store_true", help="print the recorded sources as JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    host = (Path(args.host) if args.host else wl.default_scope()).resolve()
    ws = (host / WORKSTATION_REL).resolve()
    # --list is meant to be read by a program, so its stdout carries JSON and nothing else. Every
    # other mode prints the resolved host folder first, because that is the line the skill reads
    # back to the user before anything is written.
    print("host folder: {}".format(host), file=sys.stderr if args.list else sys.stdout)

    instance = wl.read_json(ws / INSTANCE_FILE) or {}
    durable = Path(args.host_path) if args.host_path else Path(
        ((instance.get("instance") or {}).get("host")) or host)
    if durable != host and not args.list:
        print("recorded against: {}".format(durable))
    if not (ws / INSTANCE_FILE).exists():
        raise SystemExit("no instance at {} - nothing to register sources against".format(ws))

    if args.list:
        _, data = load_file(host)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    if args.check:
        return check(host)
    if not args.sources:
        raise SystemExit("nothing to do: pass --sources, --check or --list")
    return register(host, ws, durable, Path(args.sources), args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
