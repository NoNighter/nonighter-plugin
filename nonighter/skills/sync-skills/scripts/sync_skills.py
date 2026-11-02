#!/usr/bin/env python3
"""sync-skills: install the skills and mods a licensed user's plugin is entitled to.

The manifest comes from the MCP tool `skills-provision` (the skill saves that JSON to a file and hands
it here); this script never talks to NoNighter's API itself and holds no credential. It downloads each
package from the presigned S3 URL in the manifest, verifies its sha256, and installs it by its `kind`:

    skill   under <plugin root>/skills/<name>/ — the only place Claude discovers skills on every surface.
            A missing `kind` means skill, as it always has.
    mod     under <plugin root>/mods/<name>/ — a hooks module that changes Claude's own interface. The
            plugin's hooks.json names `../mods/<name>/hooks/register.tsx`, and the plugin ships an empty
            placeholder module there, so an install without the licence still loads clean. Claude reads
            modules when plugins load, before any hook runs, so a mod installed or restored mid-session
            appears only after `/reload-plugins` or in a new session.

Any other kind is refused rather than guessed at: a package installed as the wrong thing is worse than
one not installed, and a kind this script does not know means the plugin is older than the store.

Two folders, two jobs:

    <plugin root>   the working copy. Rebuilt by Claude on every plugin version (and per session in
                    Cowork), so anything installed here can vanish and is simply installed again.
    <data dir>      the durable copy, when the surface has one: the plugin's persistent data folder
                    (`${CLAUDE_PLUGIN_DATA}`, ~/.claude/plugins/data/<plugin>/). Holds the receipt and a
                    cache of the downloaded zips so `restore` can re-copy skills without network. Where
                    it does not exist or cannot be written, the receipt lives inside the plugin root and
                    there is no cache — everything still works, one network round trip more.

Commands (all take --plugin-root and --data-dir; defaults from CLAUDE_PLUGIN_ROOT / CLAUDE_PLUGIN_DATA):
    apply --manifest FILE [--check]   reconcile receipt vs manifest: install / update / keep / remove
    restore                           re-copy receipted skills and mods whose folder vanished, from the zip cache
    status                            JSON: receipt present, age, missing skill and mod folders, what is restorable
    uninstall                         remove everything the receipt lists, then the receipt

Guards:
  - a skill package must carry SKILL.md at its root, or it is not installed
  - a mod package must carry hooks/register.tsx and a build.json whose "version" is the manifest's, and
    no root SKILL.md or .placeholder, or it is not installed
  - a mod is unpacked and checked in a staging folder beside its own, and only a package that passes
    replaces what is there, by a rename. Anything that fails - a broken zip, a wrong version, any error -
    leaves the folder as it was: the working App stays, or the placeholder where there was none
  - a mod is installed only under a name the plugin's hooks.json loads (`../mods/<name>/hooks/register.tsx`);
    any other is refused, because Claude would never load it
  - an item that fails to install keeps its previous receipt entry and cached zip, so nothing is
    recorded that is not on disk; the other items go ahead, and the run exits 1
  - an item whose folder already exists in the plugin and is NOT in the receipt is refused: it is one of
    the plugin's own, and a downloaded package never overwrites a shipped one. The one exception is a
    mod folder holding `.placeholder`: that folder was shipped to be replaced
  - a download whose sha256 differs from the manifest is refused, never retried blindly
  - an item whose `kind` is neither skill nor mod is refused; only an absent `kind` means skill
  - remove touches only folders the receipt lists, and a removed mod leaves the placeholder behind

Stdlib only: runs as `py` on Windows and `python3` elsewhere.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RECEIPT = "sync-skills-receipt.json"
PACKAGES = "packages"
DEFAULT_DATA_DIR = Path.home() / ".claude" / "plugins" / "data" / "nonighter"

# What each kind installs under, and the one file whose presence means "installed". A mod's marker is
# its module, not a SKILL.md: a mod may carry nested skills of its own, but Claude loads it through the
# module hooks.json names, so that file is what has to be there.
KINDS = {
    "skill": {"folder": "skills", "marker": "SKILL.md"},
    "mod": {"folder": "mods", "marker": "hooks/register.tsx"},
}
# The stand-in the plugin ships at mods/<name>/, kept beside this script so it can be put back after a
# mod is removed. The copy shipped under mods/ must stay identical to it.
PLACEHOLDER_SRC = Path(__file__).resolve().parent.parent / "mod-placeholder"
PLACEHOLDER_FLAG = ".placeholder"
# How a mod is named to the user.
MOD_TITLES = {"noni-app": "the NoNighter App"}
# hooks.json names each mod's module at this path; a mod is installable only where one is named.
MOD_MODULE_PREFIX, MOD_MODULE_SUFFIX = "../mods/", "/hooks/register.tsx"


# ----------------------------------------------------------------------------- paths

def resolve_plugin_root(arg: str | None) -> Path:
    root = arg or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not root:
        root = str(Path(__file__).resolve().parents[3])  # <plugin root>/skills/sync-skills/scripts/
    return Path(root)


def resolve_data_dir(arg: str | None, plugin_root: Path) -> Path | None:
    """The durable folder if it is usable, else None (receipt inside the plugin root, no cache)."""
    candidate = arg or os.environ.get("CLAUDE_PLUGIN_DATA") or str(DEFAULT_DATA_DIR)
    p = Path(candidate).expanduser()
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return p
    except OSError:
        return None


def receipt_path(plugin_root: Path, data_dir: Path | None) -> Path:
    return (data_dir if data_dir else plugin_root) / RECEIPT


def load_receipt(plugin_root: Path, data_dir: Path | None) -> dict:
    # A receipt may exist in either place: the durable folder wins, the plugin-root one is a fallback
    # left by a surface without a data dir.
    for p in ([data_dir / RECEIPT] if data_dir else []) + [plugin_root / RECEIPT]:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                pass
    return {"tenant": None, "synced_at": None, "items": {}}


def save_receipt(plugin_root: Path, data_dir: Path | None, tenant: str, items: dict) -> Path:
    p = receipt_path(plugin_root, data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "tenant": tenant,
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": items,  # name -> {name, version, kind, sha256}; never the URLs, they expire
    }, indent=2), encoding="utf-8")
    return p


def kind_of(item: dict) -> str:
    # Only an absent key means skill. A kind that is there but empty, null or not a string is malformed
    # and must reach the refusal, not be installed as a skill by default.
    if "kind" not in item:
        return "skill"
    kind = item["kind"]
    return kind if isinstance(kind, str) else repr(kind)


def registered_mods(plugin_root: Path) -> set[str]:
    """The mod names this plugin's hooks.json loads. A mod named nowhere there would be installed and
    never run, so only these are installed; an unreadable hooks.json means none."""
    try:
        modules = json.loads((plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8")).get("modules", [])
    except (OSError, ValueError, AttributeError):
        return set()
    names = set()
    for m in modules if isinstance(modules, list) else []:
        if isinstance(m, str) and m.startswith(MOD_MODULE_PREFIX) and m.endswith(MOD_MODULE_SUFFIX):
            name = m[len(MOD_MODULE_PREFIX):-len(MOD_MODULE_SUFFIX)]
            if name and "/" not in name:
                names.add(name)
    return names


def item_dir(item: dict, plugin_root: Path) -> Path:
    return plugin_root / KINDS[kind_of(item)]["folder"] / item["name"]


def is_placeholder(dest: Path) -> bool:
    return (dest / PLACEHOLDER_FLAG).exists()


def is_installed(item: dict, plugin_root: Path) -> bool:
    # A mod folder that still holds the placeholder has its marker too - the placeholder is an empty
    # module at the same path - so for a mod the flag file is what tells "shipped" from "installed".
    dest = item_dir(item, plugin_root)
    if not (dest / KINDS[kind_of(item)]["marker"]).exists():
        return False
    return not (kind_of(item) == "mod" and is_placeholder(dest))


def mod_title(item: dict) -> str:
    return MOD_TITLES.get(item["name"], f"the NoNighter mod {item['name']}")


def cached_zip(item: dict, data_dir: Path | None) -> Path | None:
    return (data_dir / PACKAGES / f"{item['name']}-{item['version']}.zip") if data_dir else None


# ----------------------------------------------------------------------------- packages

def download(url: str) -> bytes:
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"download failed: HTTP {e.code} - the download links may have expired (they last "
                         f"about 15 minutes); run the sync again to get fresh ones")
    except urllib.error.URLError as e:
        raise SystemExit(f"download failed: {e.reason}")


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def extract(blob: bytes, dest: Path) -> list[str]:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    root = dest.resolve()
    written = []
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for info in z.infolist():
            out = (dest / info.filename).resolve()
            if root not in out.parents and out != root:  # zip-slip guard
                shutil.rmtree(dest)
                raise SystemExit(f"refusing zip entry outside destination: {info.filename}")
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(info))
            written.append(info.filename)
    return written


def put_placeholder(dest: Path) -> None:
    """Leave the shipped stand-in at a mod's folder, replacing whatever is there.

    hooks.json names the mod's module path, so a folder left empty makes Claude report the whole plugin
    as "failed to load" - harmless, but it reads as broken to someone who only lacks the licence. If the
    stand-in itself is missing from this plugin the folder is still cleared, and that is said.
    """
    if dest.exists():
        shutil.rmtree(dest)
    if PLACEHOLDER_SRC.is_dir():
        shutil.copytree(PLACEHOLDER_SRC, dest)
    else:
        print(f"  warning  no placeholder at {PLACEHOLDER_SRC}; {dest} left empty")


def mod_problem(item: dict, dest: Path, files: list[str]) -> str:
    """Why an extracted package is not a mod this plugin can load, or "" when it is."""
    if KINDS["mod"]["marker"] not in files:
        return "package has no hooks/register.tsx at its root; not a mod"
    if "SKILL.md" in files:
        return "package has a SKILL.md at its root, which makes it a skill, not a mod"
    if PLACEHOLDER_FLAG in files:
        return "package carries a .placeholder file, which would mark it as never installed"
    if "build.json" not in files:
        return "package has no build.json at its root"
    try:
        built = json.loads((dest / "build.json").read_text(encoding="utf-8")).get("version")
    except (ValueError, AttributeError, OSError):
        return "package's build.json is not readable JSON"
    if built != item["version"]:
        # The receipt and the cache are keyed on the manifest's version, so a package that says otherwise
        # would be kept or restored as something it is not.
        return f"package's build.json says version {built!r} but the store says {item['version']!r}"
    return ""


def install_mod(item: dict, blob: bytes, dest: Path) -> Path:
    """Put a mod in place only once it is known good; on any failure leave `dest` as it was.

    The package is unpacked into a staging folder beside `dest` and checked there. Only then does it
    replace `dest`, by two renames: the current folder aside, the staged one in. If the second rename
    fails the first is undone. So an update that turns out bad never touches the App that was working,
    and a first install that fails leaves the placeholder (put back if the folder had gone missing).
    """
    stage = dest.with_name(f".{dest.name}.incoming")
    aside = dest.with_name(f".{dest.name}.previous")
    # A run killed between the two renames leaves the working App aside and nothing in its place: put it
    # back first. Any other leftover is never live and goes.
    if aside.exists() and not dest.exists():
        os.replace(aside, dest)
    for leftover in (stage, aside):
        if leftover.exists():
            shutil.rmtree(leftover)
    try:
        try:
            files = extract(blob, stage)  # its own refusals (zip-slip) are SystemExit and pass through
        except Exception as e:  # a broken zip, a full disk, anything: the same refusal, never a crash
            raise SystemExit(f"package could not be unpacked ({type(e).__name__}: {e})")
        problem = mod_problem(item, stage, files)
        if problem:
            raise SystemExit(problem)
        had = dest.exists()
        if had:
            os.replace(dest, aside)
        try:
            os.replace(stage, dest)
        except OSError:
            if had:
                os.replace(aside, dest)
            raise
    except (SystemExit, Exception) as e:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        if not dest.exists():
            put_placeholder(dest)
        reason = str(e) if isinstance(e, SystemExit) else f"{type(e).__name__}: {e}"
        raise SystemExit(f"{item['name']}: {reason}; not installed, {mod_title(item)} left as it was")
    if aside.exists():
        shutil.rmtree(aside, ignore_errors=True)
    return dest


def install_blob(item: dict, blob: bytes, plugin_root: Path) -> Path:
    dest = item_dir(item, plugin_root)
    if kind_of(item) == "mod":
        return install_mod(item, blob, dest)
    files = extract(blob, dest)
    if "SKILL.md" not in files:
        shutil.rmtree(dest)
        raise SystemExit(f"{item['name']}: package has no SKILL.md at its root; not a skill, not installed")
    return dest


def remove_item(item: dict, plugin_root: Path) -> Path:
    dest = item_dir(item, plugin_root)
    # A registered mod's folder is named by hooks.json and must never be empty: the placeholder goes back.
    if kind_of(item) == "mod" and item["name"] in registered_mods(plugin_root):
        put_placeholder(dest)
    elif dest.exists():
        shutil.rmtree(dest)
    return dest


def missing_items(receipt: dict, plugin_root: Path) -> list[dict]:
    # An item of a kind this plugin does not know, or a mod its hooks.json does not load, can only come
    # from another plugin version's receipt; it is left alone rather than restored where nothing runs it.
    mods = registered_mods(plugin_root)
    return [i for i in receipt["items"].values() if kind_of(i) in KINDS
            and (kind_of(i) != "mod" or i["name"] in mods) and not is_installed(i, plugin_root)]


# ----------------------------------------------------------------------------- commands

def cmd_apply(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    tenant = manifest.get("tenant") or manifest.get("user") or "unknown"
    entries = manifest.get("skills", [])
    receipt = load_receipt(plugin_root, data_dir)

    print(f"plugin root : {plugin_root}")
    print(f"data dir    : {data_dir if data_dir else '(none - no cache on this surface)'}")

    names = [m["name"] for m in entries]
    duplicated = {n for n in names if names.count(n) > 1}
    wanted = {m["name"]: m for m in entries if m["name"] not in duplicated}
    plan, refused = [], []
    carried = {}  # receipt entries left exactly as they were, because what replaces them was refused
    mods = registered_mods(plugin_root)
    for m in entries:
        if m["name"] in duplicated:
            refused.append((m, "listed more than once in the manifest; ambiguous, nothing installed under it"))
    for name, m in wanted.items():
        prev = receipt["items"].get(name)
        if kind_of(m) not in KINDS:
            refused.append((m, f"kind {m.get('kind')!r} is not one this plugin installs ({', '.join(KINDS)}); "
                               f"nothing installed - a newer NoNighter plugin is needed for it"))
            if prev:
                carried[name] = prev
            continue
        if kind_of(m) == "mod" and name not in mods:
            refused.append((m, f"this plugin does not load a mod named {name!r} (it loads: "
                               f"{', '.join(sorted(mods)) or 'none'}); nothing installed - a newer NoNighter "
                               f"plugin is needed for it"))
            if prev:
                carried[name] = prev
            continue
        dest = item_dir(m, plugin_root)
        # The receipt keys items by name alone, so the same name can come back as another kind. That is a
        # different thing in a different folder: the old one is removed, the new one installed fresh.
        same = prev if prev and kind_of(prev) == kind_of(m) else None
        if dest.exists() and not same and not (kind_of(m) == "mod" and is_placeholder(dest)):
            refused.append((m, f"a {kind_of(m)} with this name already ships in the plugin; a downloaded package never overwrites it"))
            if prev:
                carried[name] = prev
            continue
        if prev and not same:
            if kind_of(prev) in KINDS:
                plan.append(("remove", prev, item_dir(prev, plugin_root)))
            else:
                carried[name] = prev
        if same and same["version"] == m["version"] and same["sha256"] == m["sha256"] and is_installed(m, plugin_root):
            plan.append(("keep", m, dest))
        elif same:
            plan.append(("update", m, dest))
        else:
            plan.append(("install", m, dest))
    for name, prev in receipt["items"].items():
        if name not in wanted and name not in duplicated:
            if kind_of(prev) in KINDS:
                plan.append(("remove", prev, item_dir(prev, plugin_root)))
            else:
                carried[name] = prev

    for action, m, dest in plan:
        print(f"  {action:8s} {m['name']}@{m['version']}  -> {dest}")
    for m, why in refused:
        print(f"  REFUSED  {m['name']}@{m.get('version', '?')}  - {why}")
    if a.check:
        print("--check: nothing written")
        return 0

    new_items = dict(carried)
    failed = []
    for action, m, dest in plan:
        if action == "remove":
            remove_item(m, plugin_root)
            continue
        if action != "keep":
            # One item failing never takes the others down, and never records what is not on disk: the
            # receipt keeps the item's previous entry (and the cleanup below its cached zip), so the
            # session hook can still restore the version that worked.
            try:
                blob = download(m["url"])
                got = sha256(blob)
                if got != m["sha256"]:
                    raise SystemExit(f"{m['name']}: sha256 mismatch (manifest {m['sha256'][:12]}, got {got[:12]}); not installed")
                install_blob(m, blob, plugin_root)
            except (SystemExit, Exception) as e:
                why = str(e) if isinstance(e, SystemExit) else f"{m['name']}: {type(e).__name__}: {e}; not installed"
                print(f"  FAILED   {m['name']}@{m['version']}  - {why}")
                failed.append(m["name"])
                prev = receipt["items"].get(m["name"])
                if prev and kind_of(prev) == kind_of(m):
                    new_items[m["name"]] = prev
                continue
            # The cache is written only for a package that installed, so a bad one never stands in for a
            # good one on the next restore.
            cache = cached_zip(m, data_dir)
            if cache:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(blob)
            print(f"  wrote    {m['name']}@{m['version']} -> {dest}")
        new_items[m["name"]] = {k: m[k] for k in ("name", "version", "sha256")} | {"kind": kind_of(m)}

    if data_dir and (data_dir / PACKAGES).exists():  # drop cached zips no longer receipted
        keep = {cached_zip(i, data_dir).name for i in new_items.values()}
        for z in (data_dir / PACKAGES).glob("*.zip"):
            if z.name not in keep:
                z.unlink()

    print(f"receipt     : {save_receipt(plugin_root, data_dir, tenant, new_items)}")
    done = [(act, m) for act, m, _ in plan if act in ("install", "update") and m["name"] not in failed]
    changed = [m["name"] for act, m in done if kind_of(m) == "skill"]
    if changed:
        print(f"NOTE: {', '.join(changed)} installed. Claude lists skills when a session starts, so they appear as "
              f"skills from the NEXT session; in this one, read each skill's SKILL.md directly if it is needed.")
    # Claude reads modules when plugins load, before any hook runs, so a mod changed now - installed,
    # updated or removed - shows its new state only once plugins load again.
    mods_in = [mod_title(m) for act, m in done if kind_of(m) == "mod"]
    mods_out = [mod_title(m) for act, m, _ in plan if act == "remove" and kind_of(m) == "mod"]
    if mods_in:
        print(f"NOTE: {', '.join(mods_in)} installed. Claude loads it when plugins load, so it appears after "
              f"the user types /reload-plugins, or in a new session.")
    if mods_out:
        print(f"NOTE: {', '.join(mods_out)} removed. It stays on screen until the user types /reload-plugins, "
              f"or opens a new session.")
    if failed:
        print(f"FAILED: {', '.join(failed)} not installed; what was there before is unchanged.")
        return 1
    return 0


def cmd_restore(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    receipt = load_receipt(plugin_root, data_dir)
    restored, uncached, reload = [], [], []
    for item in missing_items(receipt, plugin_root):
        z = cached_zip(item, data_dir)
        if z and z.exists():
            blob = z.read_bytes()
            if sha256(blob) == item["sha256"]:
                try:
                    install_blob(item, blob, plugin_root)
                except SystemExit:  # a cached package refused now is as good as not cached
                    uncached.append(item["name"])
                    continue
                restored.append(item["name"])
                if kind_of(item) == "mod":
                    reload.append(item["name"])
                continue
        uncached.append(item["name"])
    # `reload_needed`: mods put back now, which Claude shows only once plugins load again.
    print(json.dumps({"restored": restored, "not_in_cache": uncached, "reload_needed": reload}))
    return 0


def cmd_status(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    receipt = load_receipt(plugin_root, data_dir)
    age_days = None
    if receipt.get("synced_at"):
        try:
            synced = datetime.strptime(receipt["synced_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - synced).days
        except ValueError:
            pass
    missing = missing_items(receipt, plugin_root)
    print(json.dumps({
        "receipt": receipt["tenant"] is not None or bool(receipt["items"]),
        "data_dir": str(data_dir) if data_dir else None,
        "tenant": receipt["tenant"],
        "age_days": age_days,
        "items": len(receipt["items"]),
        "missing_skills": [i["name"] for i in missing if kind_of(i) == "skill"],
        "missing_mods": [i["name"] for i in missing if kind_of(i) == "mod"],
        "restorable": [i["name"] for i in missing if (cached_zip(i, data_dir) or Path("/nonexistent")).exists()],
    }))
    return 0


def cmd_uninstall(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    receipt = load_receipt(plugin_root, data_dir)
    for item in receipt["items"].values():
        if kind_of(item) not in KINDS:
            print(f"  left     {item['name']} - kind {item.get('kind')!r} is not one this plugin knows")
            continue
        dest = remove_item(item, plugin_root)
        print(f"  removed  {item['name']} -> {dest}" + (" (placeholder back)" if kind_of(item) == "mod" else ""))
    if data_dir and (data_dir / PACKAGES).exists():
        shutil.rmtree(data_dir / PACKAGES)
    for p in ([data_dir / RECEIPT] if data_dir else []) + [plugin_root / RECEIPT]:
        if p.exists():
            p.unlink()
    print("uninstalled" if receipt["items"] else "nothing was synced here")
    mods_out = [mod_title(i) for i in receipt["items"].values() if kind_of(i) == "mod"]
    if mods_out:
        print(f"NOTE: {', '.join(mods_out)} removed. It stays on screen until the user types /reload-plugins, "
              f"or opens a new session.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plugin-root", help="default: CLAUDE_PLUGIN_ROOT, else derived from this script's location")
    ap.add_argument("--data-dir", help="default: CLAUDE_PLUGIN_DATA, else ~/.claude/plugins/data/nonighter; unusable => no cache")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("apply"); p.add_argument("--manifest", required=True); p.add_argument("--check", action="store_true"); p.set_defaults(fn=cmd_apply)
    sub.add_parser("restore").set_defaults(fn=cmd_restore)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("uninstall").set_defaults(fn=cmd_uninstall)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
