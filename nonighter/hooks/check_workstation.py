#!/usr/bin/env python3
"""SessionStart for the NoNighter plugin: restore what was synced, then hand over to the workstation.

This plugin ships a connector, this hook and `sync-skills`, and nothing else. Everything a client
actually works with - the modeling skills, the presentation skills, the workstation installer, the
document import - arrives per licence through `sync-skills` and installs under `skills/<name>/`,
the same folder a shipped skill would occupy.

So this hook does two things, in order:

  1. **Its own bootstrap.** Re-copy receipted skills that a plugin-version rebuild dropped, and say
     something when nothing has ever been synced here or the last sync has gone stale. That is this
     plugin's own business and it runs whatever the licence turns out to include.

  2. **Hand over to `skills/workstation-init/scripts/session_start.py`, if it is there.** That skill
     owns the workstation - finding it, loading what its router declares, the upgrade offer, the
     maintenance nudge, and the rules for asking and reporting - and it is licensed separately. A
     client who does not have it simply has no workstation, which is an ordinary state and not a
     fault: this hook says nothing about it rather than reporting a problem the user cannot act on.

Anything needing an answer goes FIRST across both halves - this hook's sync notice, then the
workstation's own asks - under the single truncation warning that introduces them. That warning
belongs to the skill, so it is only used when the skill is present; the sync notice on its own is
short enough not to need it.

Written to fail quiet: every path still prints valid JSON, so a session never breaks over a status
probe.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

# The modeling skills are not in this plugin: `sync-skills` fetches them for a licensed user and
# installs them under skills/. That folder is rebuilt on every plugin version (and per session in
# Cowork), so this hook re-copies receipted skills from the local zip cache when they are missing -
# no network, no model - before Claude enumerates skills.
SYNC_STALE_AFTER_DAYS = 7


def emit(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": text}}, separators=(",", ":")))


def sync_skills_notice() -> str:
    try:
        plugin_root = PLUGIN_ROOT
        sys.path.insert(0, str(plugin_root / "skills" / "sync-skills" / "scripts"))
        import sync_skills as ss  # noqa: E402

        data_dir = ss.resolve_data_dir(os.environ.get("CLAUDE_PLUGIN_DATA"), plugin_root)
        receipt = ss.load_receipt(plugin_root, data_dir)
        if receipt["tenant"] is None and not receipt["items"]:
            return ("NoNighter skills: NOT SYNCED on this machine - the skills a licence includes are "
                    "fetched per licence and none is installed yet. "
                    "**Run the sync-skills skill now, first thing, before the user's request and without asking** - "
                    "it asks nothing of them and touches nothing of theirs. If the nonighter connector is not "
                    "authorised, the skill will say so in one line; then get on with what they asked. If they "
                    "ask for modeling work in THIS session after the sync, read the installed SKILL.md under "
                    "skills/<name>/ directly and follow it - skills installed mid-session are listed from the "
                    "next session, not this one.")
        restored, uncached = [], []
        for item in ss.missing_skills(receipt, plugin_root):
            z = ss.cached_zip(item, data_dir)
            if z and z.exists():
                blob = z.read_bytes()
                if ss.sha256(blob) == item["sha256"]:
                    ss.install_blob(item, blob, plugin_root)
                    restored.append(item["name"])
                    continue
            uncached.append(item["name"])
        parts = []
        if restored:
            parts.append("NoNighter skills: the plugin folder was rebuilt, so {} were re-installed from the local "
                         "cache before this session started; they are available now.".format(", ".join(restored)))
        if uncached:
            parts.append("NoNighter skills {} are recorded as installed but missing and not in the cache: run the "
                         "sync-skills skill now, without asking, to fetch them again.".format(", ".join(uncached)))
        age = None
        if receipt.get("synced_at"):
            try:
                from datetime import datetime, timezone
                synced = datetime.strptime(receipt["synced_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - synced).days
            except ValueError:
                pass
        if age is not None and age > SYNC_STALE_AFTER_DAYS and not uncached:
            parts.append("NoNighter skills were last synced {} days ago: offer to run sync-skills once, at the end "
                         "of the first turn where the user asks for NoNighter's help, after answering them - "
                         "never before, never gating their work.".format(age))
        return " ".join(parts)
    except Exception:
        return ""


def payload(timeout: float = 2.0) -> dict:
    """This hook's own input, or an empty dict. Never raises, and never blocks for long.

    `sys.stdin.read()` waits for end-of-input. The harness closes the pipe, so it returns at once - but
    anything that invokes this hook without closing stdin hangs it until the 15-second timeout kills it,
    and then the session gets no workstation context at all. Caught by a test of my own that piped
    stdout and left stdin attached to the terminal: it hung for two minutes.

    The whole payload is worth one small optional field, so it is read behind a tty check and a short
    thread with a deadline. Losing `source` costs the short form on a resume. Losing the payload costs
    the session everything this hook does.

    Read HERE and passed down, never read twice: stdin yields its contents once, so the workstation
    module takes `resumed` as an argument rather than going back to a pipe this has already drained.
    """
    try:
        if sys.stdin is None or sys.stdin.closed or sys.stdin.isatty():
            return {}
    except Exception:
        return {}

    box = {}

    def read_it():
        try:
            box["raw"] = sys.stdin.read()
        except Exception:
            pass

    reader = threading.Thread(target=read_it, daemon=True)
    reader.start()
    reader.join(timeout)
    raw = box.get("raw")
    if not raw or not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def workstation_module():
    """The workstation module, or (None, reason). An absent skill is not a reason - it is normal.

    Loaded by absolute path rather than by name. `import session_start` searches sys.path, and this
    hook has just put a skill's scripts folder on it, so a file of that name anywhere along it would
    be imported and run instead, with nothing to show it happened.

    A licence without `workstation-init` is the ordinary case here, so a missing folder returns no
    reason and the hook says nothing about workstations at all. A folder that is present but will
    not load is different: something is broken rather than merely unlicensed, and that is worth one
    line.
    """
    skill_root = PLUGIN_ROOT / "skills" / "workstation-init"
    scripts = skill_root / "scripts"
    module, library = scripts / "session_start.py", scripts / "workstation_lib.py"

    # Absent means the FOLDER is not there: not licensed, or not synced yet. Normal, and silent.
    #
    # Deciding that on the script files instead would swallow the case this diagnostic exists for.
    # `sync_skills.py` treats any package with a root SKILL.md as installed, so a package that
    # arrived without its scripts leaves the folder present and both files missing - which read as
    # "no such skill" and said nothing, while Claude lists the skill and the user reasonably
    # expects a workstation. The folder is the question; what is inside it is the answer.
    if not skill_root.is_dir():
        return None, ""
    missing = [p.name for p in (skill_root / "SKILL.md", module, library) if not p.is_file()]
    if missing:
        # The repair is two steps, and saying "re-sync" alone would send them in a circle:
        # sync-skills decides a package is already installed from its version, its hash and the
        # presence of SKILL.md, so a folder that still has that file is kept and never fetched
        # again however little else is in it. Removing the folder is what turns the next sync
        # from "keep" into "install".
        return None, ("NoNighter workstation: status unknown - the workstation-init skill is installed "
                      "at {} but {} {} missing, so its session-start module cannot run. **A plain "
                      "re-sync will not repair this**: sync-skills treats a folder that still has a "
                      "SKILL.md as already installed and leaves it alone. Offer to delete that folder "
                      "and then run sync-skills, which reinstalls it. Until that is done, treat the "
                      "workstation as possibly absent."
                      .format(skill_root, " and ".join(missing),
                              "is" if len(missing) == 1 else "are"))
    try:
        spec = importlib.util.spec_from_file_location("nonighter_workstation_session_start", module)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded, ""
    except Exception as exc:
        return None, ("NoNighter workstation: status unknown - the workstation-init skill is installed "
                      "but its session-start module at {} could not be loaded ({}). Treat the "
                      "workstation as possibly absent and verify with the workstation-init skill "
                      "before relying on it.".format(module, exc))


def main() -> int:
    # The sync notice runs FIRST because it restores skills from the cache - including, possibly, the
    # very workstation-init folder the handover below then looks for.
    try:
        sync = sync_skills_notice().strip()
    except Exception:
        sync = ""

    try:
        resumed = str(payload().get("source") or "") == "resume"
    except Exception:
        resumed = False

    module, problem = workstation_module()

    if module is None:
        # No workstation half to add. Emit whatever this plugin has of its own, with no truncation
        # warning: that warning is the skill's, and the sync notice alone is short enough to survive
        # a preview intact.
        emit("\n\n".join(p for p in (sync, problem) if p))
        return 0

    try:
        block = module.session_start(PLUGIN_ROOT, resumed)
        # Everything needing an answer goes above everything that does not, across both halves. This
        # hook's own ask comes before the workstation's: a client who has synced nothing cannot act
        # on a workstation question yet.
        asks = "\n\n".join(p for p in (sync, (block.get("asks") or "").strip()) if p)
        context = block.get("context") or ""
        emit((module.TRUNCATION_WARNING + asks + "\n\n" if asks else "") + context)
    except Exception as exc:
        emit("\n\n".join(p for p in (sync, (
            "NoNighter workstation: status unknown - the check failed ({}). Treat the workstation as "
            "possibly absent and verify with the workstation-init skill before relying on it."
            .format(exc))) if p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
