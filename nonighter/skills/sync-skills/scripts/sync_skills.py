#!/usr/bin/env python3
"""sync-skills: install the skills a licensed user's plugin is entitled to.

The manifest comes from the MCP tool `skills-provision` (the skill saves that JSON to a file and hands
it here); this script never talks to NoNighter's API itself and holds no credential. It downloads each
package from the presigned S3 URL in the manifest, verifies its sha256, and installs it.

Where a skill is installed:

    <workstation>/.claude/skills/<name>/   when the user has a NoNighter workstation (a folder holding
                    `.nonighter/instance.json`, found from --workstation, CLAUDE_PROJECT_DIR or the current
                    folder, walking up). The user sees their skills there and may adapt them. Claude
                    discovers a project's `.claude/skills/` on the command line, the desktop app's Code
                    tab and Cowork (measured 2026-11-11), in sessions opened in that folder.
    <plugin root>/skills/<name>/           when there is no workstation, and always for PLUGIN_ONLY: the
                    workstation installer cannot live inside a workstation it has not created yet.

Three folders, three jobs:

    <workstation>   the user's copy. Never rebuilt by Claude; the user may edit it. Each installed file's
                    sha256 is receipted, so a copy the user changed is never overwritten or removed: the
                    new version is cached and reported as available instead.
    <plugin root>   the working copy of plugin-only skills. Rebuilt by Claude on every plugin version (and
                    per session in Cowork), so anything installed here can vanish and is simply installed again.
    <data dir>      the durable copy, when the surface has one: the plugin's persistent data folder
                    (`${CLAUDE_PLUGIN_DATA}`, ~/.claude/plugins/data/<plugin>/). Holds the receipt and a
                    cache of the downloaded zips so `restore` can re-copy skills without network. Where
                    it does not exist or cannot be written, the receipt lives inside the plugin root and
                    there is no cache — everything still works, one network round trip more.

Commands (all take --plugin-root and --data-dir; defaults from CLAUDE_PLUGIN_ROOT / CLAUDE_PLUGIN_DATA):
    apply --manifest FILE [--check]   reconcile receipt vs manifest: install / update / keep / remove
    restore                           re-copy receipted skills whose folder vanished, from the zip cache
    status                            JSON: receipt present, age, missing skill folders, what is restorable
    uninstall                         remove everything the receipt lists, then the receipt

Guards:
  - a package must carry SKILL.md at its root, or it is not installed
  - a skill whose folder already exists and is NOT in the receipt is refused: it is one of the plugin's
    own skills, or one the user wrote in their workstation, and a downloaded package never overwrites either
  - a workstation skill the user changed is never overwritten or removed; a newer version is cached and
    reported as `modified`, for the user (with Claude) to merge
  - a workstation skill the user deleted is not reinstalled unless they ask for it (--reinstall NAME)
  - a download whose sha256 differs from the manifest is refused, never retried blindly
  - remove touches only folders the receipt lists

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
WORKSTATION_MARKER = Path(".nonighter") / "instance.json"
# Infrastructure, not the user's to adapt: stays in the plugin even when a workstation exists.
PLUGIN_ONLY = {"workstation-init", "sync-skills"}


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


def find_workstation(start: Path) -> Path | None:
    """The folder holding `.nonighter/instance.json`, from `start` upwards, or None."""
    try:
        start = start.resolve()
    except OSError:
        return None
    for folder in (start, *start.parents):
        if (folder / WORKSTATION_MARKER).is_file():
            return folder
    return None


def resolve_workstation(arg: str | None) -> Path | None:
    if arg:
        return find_workstation(Path(arg).expanduser())
    return find_workstation(Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()))


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


def save_receipt(plugin_root: Path, data_dir: Path | None, tenant: str, items: dict,
                 workstation: Path | None) -> Path:
    p = receipt_path(plugin_root, data_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "tenant": tenant,
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workstation": str(workstation) if workstation else None,
        # name -> {name, version, kind, sha256, dest, files}; never the URLs, they expire.
        # `files` is relative path -> sha256 as installed: what tells a user's edit from our copy.
        "items": items,
    }, indent=2), encoding="utf-8")
    return p


def target_dir(name: str, plugin_root: Path, workstation: Path | None) -> Path:
    """Where a skill is installed now: the workstation when there is one, else the plugin."""
    if workstation and name not in PLUGIN_ONLY:
        return workstation / ".claude" / "skills" / name
    return plugin_root / "skills" / name


def skill_dir(item: dict, plugin_root: Path) -> Path:
    """Where a receipted skill IS. Receipts written before workstations carry no `dest`: the plugin."""
    return Path(item["dest"]) if item.get("dest") else plugin_root / "skills" / item["name"]


def in_plugin(item: dict, plugin_root: Path) -> bool:
    try:
        return skill_dir(item, plugin_root).resolve().is_relative_to(plugin_root.resolve())
    except OSError:
        return True


def file_hashes(dest: Path) -> dict:
    return {f.relative_to(dest).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(dest.rglob("*")) if f.is_file()}


def is_modified(item: dict, plugin_root: Path) -> bool:
    """True when the user changed, added or deleted a file in an installed skill. Unknown => False."""
    dest = skill_dir(item, plugin_root)
    if not item.get("files") or not dest.is_dir():
        return False
    return file_hashes(dest) != item["files"]


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


def install_blob(item: dict, blob: bytes, plugin_root: Path, dest: Path | None = None) -> Path:
    dest = dest or skill_dir(item, plugin_root)
    files = extract(blob, dest)
    if "SKILL.md" not in files:
        shutil.rmtree(dest)
        raise SystemExit(f"{item['name']}: package has no SKILL.md at its root; not a skill, not installed")
    return dest


def missing_skills(receipt: dict, plugin_root: Path) -> list[dict]:
    """Receipted skills whose folder is gone, except those the user chose to delete."""
    return [i for i in receipt["items"].values()
            if not i.get("deleted_by_user") and not (skill_dir(i, plugin_root) / "SKILL.md").exists()]


def receipted(m: dict, dest: Path) -> dict:
    entry = {k: m[k] for k in ("name", "version", "sha256")} | {"kind": m.get("kind", "skill"), "dest": str(dest)}
    entry["files"] = file_hashes(dest) if dest.is_dir() else {}
    return entry


# ----------------------------------------------------------------------------- commands

def cmd_apply(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    tenant = manifest.get("tenant") or manifest.get("user") or "unknown"
    entries = manifest.get("skills", [])
    receipt = load_receipt(plugin_root, data_dir)
    workstation = resolve_workstation(a.workstation)
    reinstall = set(a.reinstall or [])

    print(f"plugin root : {plugin_root}")
    print(f"workstation : {workstation if workstation else '(none - skills go into the plugin)'}")
    print(f"data dir    : {data_dir if data_dir else '(none - no cache on this surface)'}")

    names = [m["name"] for m in entries]
    duplicated = {n for n in names if names.count(n) > 1}
    wanted = {m["name"]: m for m in entries if m["name"] not in duplicated}
    plan, refused = [], []
    for m in entries:
        if m["name"] in duplicated:
            refused.append((m, "listed more than once in the manifest; ambiguous, nothing installed under it"))
    for name, m in wanted.items():
        dest = target_dir(name, plugin_root, workstation)
        prev = receipt["items"].get(name)
        here = skill_dir(prev, plugin_root) if prev else dest
        if dest.exists() and (not prev or here.resolve() != dest.resolve()):
            refused.append((m, "a skill with this name already exists there (shipped with the plugin, or the "
                               "user's own); a downloaded package never overwrites it"))
            continue
        present = (here / "SKILL.md").exists()
        same = bool(prev) and prev["version"] == m["version"] and prev["sha256"] == m["sha256"]
        if prev and not present and not in_plugin(prev, plugin_root) and name not in reinstall:
            plan.append(("deleted", m, here))  # the user removed it from their workstation
        elif prev and present and is_modified(prev, plugin_root):
            plan.append(("keep" if same else "modified", m, here))
        elif same and present:
            plan.append(("keep" if here.resolve() == dest.resolve() else "move", m, dest))
        elif prev:
            plan.append(("update", m, dest))
        else:
            plan.append(("install", m, dest))
    for name, prev in receipt["items"].items():
        if name not in wanted and name not in duplicated:
            plan.append(("kept" if is_modified(prev, plugin_root) else "remove", prev, skill_dir(prev, plugin_root)))

    notes = {"modified": "  (changed by the user: NOT overwritten; the new version is cached)",
             "deleted": "  (deleted by the user: not reinstalled; --reinstall NAME brings it back)",
             "kept": "  (no longer licensed, but changed by the user: NOT removed)"}
    for action, m, dest in plan:
        print(f"  {action:8s} {m['name']}@{m['version']}  -> {dest}{notes.get(action, '')}")
    for m, why in refused:
        print(f"  REFUSED  {m['name']}@{m.get('version', '?')}  - {why}")
    if a.check:
        print("--check: nothing written")
        return 0

    new_items = {}
    for action, m, dest in plan:
        prev = receipt["items"].get(m["name"])
        if action == "remove":
            if dest.exists():
                shutil.rmtree(dest)
            continue
        if action in ("kept", "deleted"):
            new_items[m["name"]] = dict(prev) | ({"deleted_by_user": True} if action == "deleted" else {})
            continue
        if action == "keep":
            new_items[m["name"]] = dict(prev) if prev and prev.get("files") else receipted(m, dest)
            continue
        blob = download(m["url"])
        got = sha256(blob)
        if got != m["sha256"]:
            raise SystemExit(f"{m['name']}: sha256 mismatch (manifest {m['sha256'][:12]}, got {got[:12]}); not installed")
        cache = cached_zip(m, data_dir)
        if cache:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(blob)
        if action == "modified":
            # The user's copy stays as it is. The installed version's zip (the merge base) and this one
            # both stay cached, so a merge can see what each side changed.
            new_items[m["name"]] = dict(prev) | {"available": {"version": m["version"], "sha256": m["sha256"]}}
            continue
        old = skill_dir(prev, plugin_root) if prev else None
        install_blob(m, blob, plugin_root, dest)
        print(f"  wrote    {m['name']}@{m['version']} -> {dest}")
        if old and old.resolve() != dest.resolve() and old.exists():
            shutil.rmtree(old)  # moved: plugin -> workstation
        new_items[m["name"]] = receipted(m, dest)

    if data_dir and (data_dir / PACKAGES).exists():  # drop cached zips no longer receipted
        keep = {cached_zip(i, data_dir).name for i in new_items.values()}
        keep |= {cached_zip(i["available"] | {"name": i["name"]}, data_dir).name
                 for i in new_items.values() if i.get("available")}
        for z in (data_dir / PACKAGES).glob("*.zip"):
            if z.name not in keep:
                z.unlink()

    print(f"receipt     : {save_receipt(plugin_root, data_dir, tenant, new_items, workstation)}")
    changed = [m["name"] for act, m, _ in plan if act in ("install", "update", "move")]
    if changed:
        print(f"NOTE: {', '.join(changed)} installed. Claude lists skills when a session starts, so they appear as "
              f"skills from the NEXT session; in this one, read each skill's SKILL.md directly if it is needed.")
    return 0


def cmd_restore(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    receipt = load_receipt(plugin_root, data_dir)
    restored, uncached = [], []
    for item in missing_skills(receipt, plugin_root):
        if not in_plugin(item, plugin_root):  # a workstation folder that vanished: the user's to decide
            uncached.append(item["name"])
            continue
        z = cached_zip(item, data_dir)
        if z and z.exists():
            blob = z.read_bytes()
            if sha256(blob) == item["sha256"]:
                install_blob(item, blob, plugin_root)
                restored.append(item["name"])
                continue
        uncached.append(item["name"])
    print(json.dumps({"restored": restored, "not_in_cache": uncached}))
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
    missing = missing_skills(receipt, plugin_root)
    print(json.dumps({
        "receipt": receipt["tenant"] is not None or bool(receipt["items"]),
        "data_dir": str(data_dir) if data_dir else None,
        "tenant": receipt["tenant"],
        "age_days": age_days,
        "items": len(receipt["items"]),
        "missing_skills": [i["name"] for i in missing],
        "restorable": [i["name"] for i in missing if in_plugin(i, plugin_root)
                       and (cached_zip(i, data_dir) or Path("/nonexistent")).exists()],
        "workstation": receipt.get("workstation"),
        "modified": [i["name"] for i in receipt["items"].values() if is_modified(i, plugin_root)],
        "updates_waiting": {i["name"]: i["available"]["version"] for i in receipt["items"].values() if i.get("available")},
    }))
    return 0


def cmd_uninstall(a) -> int:
    plugin_root = resolve_plugin_root(a.plugin_root)
    data_dir = resolve_data_dir(a.data_dir, plugin_root)
    receipt = load_receipt(plugin_root, data_dir)
    for item in receipt["items"].values():
        dest = skill_dir(item, plugin_root)
        if is_modified(item, plugin_root):
            print(f"  kept     {item['name']} -> {dest}  (changed by the user; delete it by hand if unwanted)")
            continue
        if dest.exists():
            shutil.rmtree(dest)
        print(f"  removed  {item['name']} -> {dest}")
    if data_dir and (data_dir / PACKAGES).exists():
        shutil.rmtree(data_dir / PACKAGES)
    for p in ([data_dir / RECEIPT] if data_dir else []) + [plugin_root / RECEIPT]:
        if p.exists():
            p.unlink()
    print("uninstalled" if receipt["items"] else "nothing was synced here")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plugin-root", help="default: CLAUDE_PLUGIN_ROOT, else derived from this script's location")
    ap.add_argument("--data-dir", help="default: CLAUDE_PLUGIN_DATA, else ~/.claude/plugins/data/nonighter; unusable => no cache")
    sub = ap.add_subparsers(dest="command", required=True)
    ap.add_argument("--workstation", help="default: the workstation holding CLAUDE_PROJECT_DIR or the current folder; none => the plugin")
    p = sub.add_parser("apply"); p.add_argument("--manifest", required=True); p.add_argument("--check", action="store_true")
    p.add_argument("--reinstall", action="append", metavar="NAME", help="bring back a skill the user deleted from their workstation")
    p.set_defaults(fn=cmd_apply)
    sub.add_parser("restore").set_defaults(fn=cmd_restore)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("uninstall").set_defaults(fn=cmd_uninstall)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
