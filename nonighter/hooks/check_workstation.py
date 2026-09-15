#!/usr/bin/env python3
"""SessionStart: find the NoNighter workstation and load its context, or say it is missing.

This is the plugin's own hook, and that is the point. Configuration in the HOST folder's `.claude/`
is trust-gated and was measured inert in Cowork, and nothing here relies on it - the installer
writes none. (The template ships no `.claude/` at all, so there is nothing else that could load it.) So
this hook is the only thing that loads the workstation's context. There is no second one behind it.

    workstation present -> inject the files AGENTS.md lists under "## Session start files", in its
                           order, and name AGENTS.md itself as the router
    workstation absent  -> tell the agent to run the workstation-init skill before finance work

It only reads. Installing needs answers from the user and belongs to the skill.

Written to fail quiet: any error still prints valid JSON, so a session never breaks over a status
probe.
"""

from __future__ import annotations

import json
import re
import os
import sys
import threading
from pathlib import Path

# The shared library lives with the skill, inside this same plugin. Importing it rather than
# keeping a second copy of the scope resolution is the point: the two drifting apart is how a
# hook ends up reporting NOT INSTALLED over a workstation the installer just wrote.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "workstation-init" / "scripts"))
import workstation_lib as wl  # noqa: E402

WORKSTATION_REL = ".nonighter"
# The template declares its own session-start list, in order, under "## Session start files" in
# AGENTS.md. Read it from there rather than hardcoding: the list moved between template versions
# (v0.1.0 added memory/index-memory-records.md and put operating-manual.md first) and a hook that
# disagrees with the router injects the wrong files while claiming they are already read. The
# fallback is only for a template that stops declaring one.
SESSION_START_HEADING = "## Session start files"
SESSION_START_FALLBACK = ["operating-manual.md", "MEMORY.md", "memory/index-memory-records.md"]
# Headroom over what the router actually declares (6 at template 0.5.0, with context enabled). Set to
# exactly that number, the next file added to the template would be dropped, and the payload is where a
# silently dropped file is hardest to notice - the session cannot tell it never arrived.
MAX_SESSION_START_FILES = 8
INSTANCE_FILE = "instance.json"

# Per-file cap. A working client's MEMORY.md grows, and this is paid on every single session.
MAX_CHARS_PER_FILE = 8000

# Memory maintenance runs when the user opens a session, not on a timer: a scheduled task would need
# a signed-in command-line Claude at a path that survives an app update, and none of that holds.
# "When did it last run" needs no new bookkeeping - memory/runs/ holds a record per run, so the newest
# file in it IS the answer.
MAINTENANCE_RUNS_REL = "memory/runs"
MAINTENANCE_INSTRUCTIONS_REL = "memory/instructions-memory-maintenance.md"
MAINTENANCE_DUE_AFTER_DAYS = 1

# The template set that ships with THIS plugin. Comparing it against the instance's own version is
# the only way a client ever learns a newer template exists: nothing else tells them, and asking
# them to ask is not a mechanism.
BUNDLED_MANIFEST_REL = Path("skills") / "workstation-init" / "templates" / "manifest.json"


# Injected in both branches, because it is a property of the surface rather than of this skill,
# and every NoNighter skill that asks the user anything runs into it. Measured twice: a rendered
# widget came back carrying only its multiple-choice answers, every free-text field arrived empty,
# so the user typed answers that were silently lost and was asked again.
#
# The memory pass and the install both produced reports full of the mechanism's own vocabulary -
# buffers, slugs, frontmatter, pristine counts, instance.json. The user is not a maintainer of this
# system and did not ask to become one.
REPORT_RULE = (
    chr(10) + chr(10) +
    "How to report anything to this user: in their terms, not the workstation's. Say what changed "
    "about their work - what was recorded, what is still open, what needs a decision from them. This "
    "system's internal vocabulary - buffers, bands, slugs, frontmatter, pristine and edited counts, "
    "instance.json, hashes, transcript slugs - stays internal. Where an internal detail changes what "
    "they should do, say the consequence and leave the mechanism out." +
    chr(10) + chr(10) +
    "**Report what happened, not what was meant to happen.** Look at what is actually on disk before "
    "summarising, and where a step was planned and skipped, say it was skipped. An install reporting "
    "tracking for folders it never created has told the user something false about their own disk." +
    chr(10) + chr(10) +
    "**Ask confirmations as the consequence, not as a table of paths and fields:** \"I would leave a "
    "short reference note in each of these three folders in the shared library, which your colleagues "
    "will see. Create them?\" An outward action is still never taken silently. Their own work folders "
    "are the exception to all of this - those are theirs and they see them in the file explorer, so "
    "name them normally."
)

# Goes above anything that needs an answer, because the reader may be looking at a preview rather than
# the whole message. A session that sees only the first couple of thousand characters cannot know that
# something was cut - truncation is invisible from inside it - so the first thing it reads has to be
# that the rest exists and where to get it.
TRUNCATION_WARNING = (
    "ACTION NEEDED FROM THE USER - this comes first because the rest of this message may be shown to "
    "you as a truncated preview. If you are seeing a preview, read this whole message before "
    "answering: it carries the workstation's own rules and its session-start files, and its full text "
    "is on disk if the surface saved it. What follows immediately below needs a reply from the user, "
    "asked through the harness's own question mechanism, near the start." + chr(10) + chr(10)
)

ASK_RULE = (
    chr(10) + chr(10) +
    "How to ask this user anything, in this session and in any NoNighter skill: use the harness's own "
    "question mechanism, never a rendered HTML widget. A rendered form returns only its "
    "multiple-choice answers - every free-text field comes back empty, so typed answers are lost "
    "silently and the user gets asked twice." +
    chr(10) + chr(10) +
    "**Anything that needs a decision goes through that mechanism. Prose is for what they do not have "
    "to answer.** A sentence inside a paragraph reads as commentary, and commentary does not get "
    "replied to. Before writing an offer in prose, ask whether you want an answer to it: if you do, it "
    "is a question." +
    chr(10) + chr(10) +
    "The harness's own mechanism carries typed text fine, so do not avoid asking for something typed - "
    "put it in the same question as the choice that leads to it. \"Is there another folder outside this "
    "one, and if so where is it?\" is ONE question with a place to type, not two round trips." +
    chr(10) + chr(10) +
    "**Some answers are typed, not picked, and offering options for them is guessing at the user.** "
    "What somebody does for a living, what a folder is for, what they want something called - these "
    "have no option list, and inventing one asks them to recognise themselves in three guesses. Ask "
    "those openly, with a place to write, and keep the picker for a real choice between things you can "
    "enumerate." +
    chr(10) + chr(10) +
    "**Say what will take a while before starting it, not after.** Describing a large folder or library "
    "can run for minutes with nothing on screen. One sentence first - roughly how long, and what they "
    "get - then let them say go, skip it, or do it later." +
    chr(10) + chr(10) +
    "**An option label has a few words: make those words the CONSEQUENCE, not a name for the option.** "
    "\"Leave it out\" and \"Merge rules\" are category names - the user learns which is which and nothing "
    "about what either does. Where an option needs more, add one short line per option under the "
    "question; the body has room, the label does not:" + chr(10) +
    "    This folder already has its own instruction file. If I also track it from here, two sets of "
    "rules cover one folder." + chr(10) +
    "      1 - I note it exists and that it has its own rules, and track nothing in it." + chr(10) +
    "      2 - I record what gets done and what is next, and its own file still governs how." + chr(10) +
    "Every option, the do-nothing one included, has to be answerable by someone who has never read a "
    "line of this system." +
    chr(10) + chr(10) +
    "**Keep an option that edits or deletes something of the user's - or their team's - OUT of the "
    "picker.** Name it in a sentence under the options, as something they can ask for. A destructive "
    "choice one keystroke from a recommended one gets taken by someone who has not understood it yet."
)

def emit(text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": text}}, separators=(",", ":")))


def read_capped(path: Path, label: str) -> str:
    """One session-start file, capped. **Degrades per file and never raises.**

    Unguarded, a single bad byte in one file took down the whole payload: the exception reached main()'s
    handler, which emits "status unknown" - so the router, the version comparison and both offers were
    dropped for the entire session because one file had a mangled character. That is the opposite of
    what this file's own docstring promises, and the failure would be invisible: the session simply
    would not know a workstation was there.

    A decode problem is recovered rather than reported and lost: the file is re-read with the bad bytes
    replaced, which leaves the content usable, and the note says so. Anything else - locked, gone
    between the exists() check and the read, permissions - names the file and lets the rest load.
    """
    if not path.exists():
        return "===== {} ===== (not present)".format(label)
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            label += " (not valid UTF-8 - unreadable characters replaced)"
        except OSError as exc:
            return "===== {} ===== (could not be read: {})".format(label, exc)
    except OSError as exc:
        return "===== {} ===== (could not be read: {})".format(label, exc)
    if len(raw) > MAX_CHARS_PER_FILE:
        raw = raw[:MAX_CHARS_PER_FILE] + (
            "\n\n[truncated at {} characters - read the file directly for the rest]".format(MAX_CHARS_PER_FILE))
    return "===== {} =====\n{}".format(label, raw)


def session_start_files(ws_dir):
    """The files the instance's own router says to load, in its order."""
    router = ws_dir / "AGENTS.md"
    try:
        text = router.read_text(encoding="utf-8-sig")
    except Exception:
        return SESSION_START_FALLBACK
    lower = text.lower()
    start = lower.find(SESSION_START_HEADING.lower())
    if start < 0:
        return SESSION_START_FALLBACK
    end = text.find(chr(10) + "## ", start + 1)
    section = text[start:end if end > 0 else len(text)]

    found = []
    for token in re.findall(r"`([^`]+)`", section):
        token = token.strip()
        if not token.endswith((".md", ".json")) or "<" in token or "*" in token:
            continue
        if token.startswith(("../", "/")) or ":" in token:
            continue                       # outside the instance, or not a relative path
        if token not in found and (ws_dir / token).is_file():
            found.append(token)
    if len(found) > MAX_SESSION_START_FILES:
        # Silent truncation here means the router declares a file and the session never receives it,
        # with nothing anywhere saying which one was dropped. Say it instead: the cap exists to stop a
        # runaway list, not to quietly disagree with the template.
        print("nonighter: the router declares {} session-start files and the cap is {}; dropped {}"
              .format(len(found), MAX_SESSION_START_FILES,
                      ", ".join(found[MAX_SESSION_START_FILES:])), file=sys.stderr)
    return found[:MAX_SESSION_START_FILES] or SESSION_START_FALLBACK


def version_tuple(text):
    """A comparable version, or None when it is not a plain dotted number."""
    parts = str(text or "").strip().split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def bundled_version() -> str:
    """The template version shipped inside THIS plugin, or "unknown"."""
    where = Path(__file__).resolve().parent.parent / BUNDLED_MANIFEST_REL
    return str((wl.read_json(where) or {}).get("version") or "unknown")


def upgrade_available(ws_dir):
    """A line naming a newer bundled template, or nothing at all.

    Silent unless both versions parse and the bundled one is genuinely newer. A version this hook
    cannot compare is not an occasion to nag: the skill compares them properly when it runs.
    """
    where = Path(__file__).resolve().parent.parent / BUNDLED_MANIFEST_REL
    bundled = wl.read_json(where)
    instance = wl.read_json(ws_dir / INSTANCE_FILE)
    if not bundled:
        # Silence here is indistinguishable from "you are up to date", and that is the failure this
        # notice exists to prevent: a client would never learn a fix shipped, and nothing anywhere
        # would say why. Say it instead - it costs one line and it is the only symptom there is.
        return ("\n\nNote for whoever maintains this plugin: the bundled template set could not be "
                "read at {}, so this session cannot tell whether the user's workstation is out of "
                "date. Mention it once if the user raises upgrades; otherwise it is a packaging "
                "problem, not theirs.".format(where))
    if not instance:
        return ""
    here, theirs = version_tuple(bundled.get("version")), version_tuple(instance.get("version"))
    if not here or not theirs or here <= theirs:
        return ""
    return ("\n\nA newer version of this workstation's template is bundled with the plugin: the "
            "folder is set up as version {} and {} is available. **Offer it through the harness's own "
            "question mechanism**, once, near the start:" + chr(10) + chr(10) +
            "    Update this folder's setup? It picks up the fixes and rules added since you "
            "installed, and keeps everything you have written." + chr(10) +
            "      1 - Yes, update it" + chr(10) +
            "      2 - Not now" + chr(10) + chr(10) +
            "Say what it means for their work, never a version number - a number tells them nothing "
            "about whether they want it. Do NOT upgrade unasked. If they decline, drop it for the "
            "session. The upgrade path keeps every file they have edited and merges the rest with "
            "them, so there is nothing for them to lose by saying yes."
            ).format(instance.get("version"), bundled.get("version"))


def maintenance_nudge(ws_dir: Path) -> str:
    """A line telling the agent maintenance is due, or nothing at all.

    Silent unless the workstation actually has the memory system, so a template without it is never
    nagged about a feature it does not have. Never instructs the agent to just do it: rewriting the
    client's memory unasked, before they have said a word, is not the agent's call.
    """
    import datetime
    runs = ws_dir / MAINTENANCE_RUNS_REL
    instructions = ws_dir / MAINTENANCE_INSTRUCTIONS_REL
    if not runs.is_dir() or not instructions.exists():
        return ""
    records = [p for p in runs.iterdir() if p.is_file()]
    if records:
        newest = max(records, key=lambda p: p.stat().st_mtime)
        days = (datetime.datetime.now() - datetime.datetime.fromtimestamp(newest.stat().st_mtime)).days
        if days < MAINTENANCE_DUE_AFTER_DAYS:
            return ""
        since = "the last run was {} day(s) ago".format(days)
    else:
        # "Never run" is not the same as "overdue". On a fresh install this folder is empty by
        # definition, so the FIRST session after installing opened with "ACTION NEEDED - memory
        # maintenance is DUE, it has never run here" - offering to rewrite a memory the user had not
        # written a line of yet, in the position that was fought for so real questions land first.
        #
        # The pass reads the day's sessions, so before a day has passed there is nothing for it to
        # read. Measure against the install date instead: due once the instance has existed long
        # enough to have a day of work in it.
        installed = ((wl.read_json(ws_dir / INSTANCE_FILE) or {}).get("instance") or {}).get("installed")
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(str(installed))).days
        except (TypeError, ValueError):
            age = MAINTENANCE_DUE_AFTER_DAYS   # unreadable date: fall back to the old behaviour
        if age < MAINTENANCE_DUE_AFTER_DAYS:
            return ""
        since = "it has never run in this workstation, installed {} day(s) ago".format(age)
    return ("\n\nMemory maintenance is DUE - {}. The procedure is {}; read it and follow it when you "
            "run this.\n\n"
            "**Offer it through the harness's own question mechanism, as a yes/no question** - not "
            "as a sentence in a paragraph. Offered in prose it reads as commentary and goes past the "
            "user unanswered, which is the same as never having offered it. Ask once, near the start. "
            "Only run it if they agree: it rewrites their memory, so it is their call, not yours. If "
            "they decline or ignore it, drop the subject for this session and get on with what they "
            "asked for.").format(since, MAINTENANCE_INSTRUCTIONS_REL)



# The modeling skills are not in this plugin: `sync-skills` fetches them for a licensed user and installs
# them under skills/. That folder is rebuilt on every plugin version (and per session in Cowork), so this
# hook does two things on every start, both before Claude enumerates skills: re-copy receipted skills
# from the local zip cache when they are missing (no network, no model), and tell the session what to do
# when nothing was ever synced here (run sync-skills at once) or the last sync is stale (offer it once).
# Fail-quiet like everything else in this hook.
SYNC_STALE_AFTER_DAYS = 7


def sync_skills_notice() -> str:
    try:
        plugin_root = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(plugin_root / "skills" / "sync-skills" / "scripts"))
        import sync_skills as ss  # noqa: E402

        data_dir = ss.resolve_data_dir(os.environ.get("CLAUDE_PLUGIN_DATA"), plugin_root)
        receipt = ss.load_receipt(plugin_root, data_dir)
        if receipt["tenant"] is None and not receipt["items"]:
            return ("\n\nNoNighter skills: NOT SYNCED on this machine - the financial-modeling skill (one skill: "
                    "3-statement, DCF, comps, LBO, scenario manager, football field, ...) is fetched per licence and is not installed yet. "
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
        return ("\n\n" + " ".join(parts)) if parts else ""
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


def main() -> int:
    try:
        # SessionStart fires in four situations, not one: startup, resume, clear and compact. On a
        # RESUME the whole payload was re-sent although the conversation already holds it - measured at
        # 15,811 characters, about 4,000 tokens, paid again for nothing.
        #
        # The fix is not to go silent there, which was the obvious move and the wrong one: both offers -
        # the upgrade and the memory pass - live inside this payload, so a user who works for days by
        # resuming one session would never be shown either. What is redundant on a resume is the
        # *context*: the files, the rules, the router. What is not is anything needing an answer, and
        # the two version numbers, since the plugin may have been updated since the session began.
        resumed = str(payload().get("source") or "") == "resume"
        ws_dir, checked = wl.find_workstation(WORKSTATION_REL)

        if ws_dir is None:
            # The trigger below is "are they asking US for help", not "is their subject ours". It used
            # to read "financial-modeling, valuation or document-import work", and a user doing his own
            # taxes was offered a workstation - taxes are documents, so a fair reading of that list
            # includes them, and no wording of a subject list has an edge. Whether somebody wants
            # NoNighter to work on something is observable; whether their topic belongs to a category is
            # a guess. Do not reintroduce a subject test.
            emit(
                "NoNighter workstation: NOT FOUND (no {rel}/AGENTS.md in any folder I can see).\n\n"
                "**The one thing to do about that.** The FIRST time in this session that the user asks "
                "for NoNighter's help with work - they invoke one of its skills, or they name NoNighter "
                "- offer to set the folder up. **Answer them first.** Do the work they asked for, say "
                "what you found, and put the offer at the END of that same turn, after the answer. "
                "A person who asks for help with a valuation and gets a setup question as the first "
                "thing on screen has been answered with paperwork.\n\n"
                "Then **ask through the harness's own question mechanism** - the same picker you "
                "would use for anything else. Not a line inside a paragraph: an offer "
                "in prose reads as commentary and goes past unanswered, which is the same as never "
                "having made it. Roughly:\n\n"
                "    Set this folder up, so it remembers your details and what gets decided here?\n"
                "      1 - Yes, set it up\n"
                "      2 - No, work without it\n\n"
                "The offer never gates the help - not the question, not a yes, not a no. "
                "Ask it once. If they decline "
                "or leave it unanswered, drop it for the whole session and get on with the work.\n\n"
                "**This is the only thing to do about it.** Do not mention the workstation in any "
                "other situation, do not treat its absence as a problem to report, and do not install "
                "anything without the user's answers. A session that says nothing when they ask for a "
                "valuation has missed the one moment that mattered; a session that raises it twice is "
                "worse.\n\n"
                "--- diagnostics, not something to relay ---\n"
                "Folders checked, in order:\n{checked}\n"
                "If the user's connected folder is in none of those, the workstation may be installed "
                "and simply out of this hook's reach: check for {rel}/ in the folder they are working "
                "in before telling them it is missing, and trust the filesystem over this message."
                .format(rel=WORKSTATION_REL,
                        checked="\n".join("  - {}".format(p) for p in checked))
                + sync_skills_notice() + ASK_RULE + REPORT_RULE)
            return 0
        version, instance = "unknown", None
        try:
            instance = json.loads((ws_dir / INSTANCE_FILE).read_text(encoding="utf-8-sig"))
            version = instance.get("version", "unknown")
        except Exception:
            pass

        systems = (instance or {}).get("systems") or {}
        on = sorted(k for k, v in systems.items() if v)
        off = sorted(k for k, v in systems.items() if not v)
        standing = ""
        if on or off:
            standing = ("\n\nWhat this instance has: {}.{}\n"
                        "That is the answer when the user asks what they have set up - said in their "
                        "terms, not in these names. Anything switched off can be turned on later "
                        "without reinstalling, so say that rather than letting a decision read as "
                        "settled."
                        ).format(", ".join(on) or "the always-on parts only",
                                 " Switched off: {}.".format(", ".join(off)) if off else "")

        # Both numbers, and where the second one came from. The comparison behind the upgrade offer was
        # invisible: the header named the folder's version and nothing else, so a session that stayed
        # silent about an upgrade was indistinguishable from one that had nothing to offer. Three test
        # rounds went into finding out that two copies of the plugin were installed and the hooks were
        # firing from the older one - whose bundled template matched the folder, so silence was correct
        # and unexplainable. Printing what it compared against makes that visible in the first line.
        bundled_at = Path(__file__).resolve().parent.parent
        header = (
            "NoNighter workstation: INSTALLED at {found} (template v{version}; the plugin running this "
            "check is at {plugin} and bundles template v{bundled})." + standing + "\n\n"
            "It is the source of truth for how to work in this folder - the activity taxonomy, the "
            "authoring conventions, and the memory and context systems. Its router is "
            "{rel}/AGENTS.md: read it before non-trivial work here and follow it, and note that paths "
            "inside it are relative to {rel}, not to this folder.\n\n"
            "The session-start files follow, loaded for you. Treat them as already read; do not "
            "re-read them unless you are about to write to one.\n\n"
            "One rule from this instance worth having before you read anything: **sessions do "
            "not write memory and do not checkpoint** - not mid-session, not at the end, and do "
            "not offer to. A daily pass reads the transcripts and writes every memory file. "
            "Record decisions in the conversation and let the pass harvest them."
        ).format(rel=WORKSTATION_REL, version=version, found=ws_dir,
                 plugin=bundled_at, bundled=bundled_version())

        asks = (sync_skills_notice() + upgrade_available(ws_dir) + maintenance_nudge(ws_dir)).strip()

        if resumed:
            # The short form. Everything dropped here is already in the conversation this session is
            # resuming: the files, the rules, the router, the description of what the instance is. What
            # is kept is what a resume can genuinely have changed or never had - anything needing an
            # answer, and the two version numbers, because the plugin may have been updated since the
            # session began and that is precisely how the upgrade offer reaches somebody who lives in
            # one long session.
            emit((TRUNCATION_WARNING + asks + "\n\n" if asks else "")
                 + "NoNighter workstation: still at {found} (template v{version}; the plugin running "
                   "this check bundles v{bundled}). This session was resumed, so its context is "
                   "already above - nothing is re-sent but the line you are reading and anything that "
                   "needs an answer. The router is {rel}/AGENTS.md."
                   .format(found=ws_dir, version=version, rel=WORKSTATION_REL,
                           bundled=bundled_version()))
            return 0

        loaded = [read_capped(ws_dir / name, name) for name in session_start_files(ws_dir)]
        # Order: what needs an answer, THEN status, THEN the rules, THEN the files. Measured on a real
        # instance: this message runs to 17,500 characters, the surface showed the session a 2,000
        # character preview of it, and both things needing an answer began past character 6,900 - so
        # neither was ever seen. The session was not ignoring them. It never received them.
        #
        # That is the fourth time in this system that a rule was present, correct, and positioned where
        # nothing could act on it. Hence the ordering rule, which is the durable part of this fix: in
        # anything injected, what needs a reply goes at the top. And note what had done the pushing -
        # 7,000 characters of prose about how to ask the user things, grown one failure at a time,
        # which crowded out the asks themselves.
        emit((TRUNCATION_WARNING + asks + "\n\n" if asks else "")
             + header + ASK_RULE + REPORT_RULE + "\n" + "\n\n".join(loaded))
        return 0
    except Exception as exc:  # never break a session over a status probe
        emit("NoNighter workstation: status unknown - the check failed ({}). Treat the workstation as "
             "possibly absent and verify with the workstation-init skill before relying on "
             "it.".format(exc))
        return 0


if __name__ == "__main__":
    sys.exit(main())
