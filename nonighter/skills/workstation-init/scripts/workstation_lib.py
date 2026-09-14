"""Shared helpers for the workstation scripts.

The Python port of lib-tree.ps1 + lib-wire.ps1. Four of the seven bugs found while the originals
were in Windows PowerShell 5.1 were quirks of that language rather than mistakes in the logic, and
they are simply absent here:

  - Get-Content/Set-Content defaulted to the system ANSI codepage, so a read-modify-write
    double-encoded every non-ASCII character. Python's encoding is explicit.
  - `[bool]($x -band $y)` was always true: -band on two enums returns an enum, and a zero-valued
    enum casts to $true. Python has real booleans.
  - `@($raw | ConvertFrom-Json)` wrapped a deserialised JSON array in a one-element array, so a loop
    ran once with the whole array bound. json.loads returns a list.
  - a character-class regex losing a backslash, so it matched only the forward slash.

What does NOT go away, because it is the filesystem and not the language:

  - a recursive walk must not descend into a junction or symlink, or an installed workstation's
    mounted company library gets enumerated along with it
  - OneDrive Files-On-Demand marks every synced folder as a reparse point, so "is a link" cannot be
    answered from that flag alone
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

# The file types placeholder substitution applies to. One list, shared by install and upgrade: if
# they disagree about which files are text, they disagree about how a file is hashed, and every such
# file looks edited on upgrade.
TEXT_SUFFIXES = {".md", ".json", ".ps1", ".py", ".bat", ".txt"}

FILE_ATTRIBUTE_REPARSE_POINT = 0x400

# The variables that name the user's real folder, in the order they are trusted. The current
# directory is not among them: in Cowork it points inside the sandbox and has nothing to do with the
# folder the user connected.
SCOPE_ENV_VARS = ["CLAUDE_CODE_WORKSPACE_HOST_PATHS", "CLAUDE_PROJECT_DIR"]


@dataclass(frozen=True)
class TreeFile:
    rel: str
    full: Path
    suffix: str


def normalise_rel(rel: str) -> str:
    return rel.replace("\\", "/")


def is_text_file(suffix: str) -> bool:
    return suffix.lower() in TEXT_SUFFIXES


def find_marked_spans(text: str, begin: str, end: str) -> list:
    """Every (start, stop) of a begin..end span, in order. Shared so wiring and unwiring agree.

    **The end marker is searched for after its own begin**, which is the whole point. Both callers used
    to take `text.index(end)` from position zero: with two blocks in the file that can return an end
    belonging to the earlier one, and the slice between the two markers - the user's own text - is what
    gets replaced or deleted.
    """
    spans, at = [], 0
    while True:
        start = text.find(begin, at)
        if start < 0:
            return spans
        stop = text.find(end, start + len(begin))
        if stop < 0:
            return spans           # an unterminated begin is left alone; nothing can be said about it
        stop += len(end)
        spans.append((start, stop))
        at = stop


def shell_without_blocks(text: str, begin: str, end: str) -> str:
    """The file with every marked span removed - what it would be if this system had never touched it.

    Hashing THIS rather than the whole file is what keeps two different questions apart. "Has the file
    changed since we last wrote it?" and "does the file hold anything of the user's?" are not the same
    question, and one recorded hash answered whichever the caller assumed: the uninstall read a
    whole-file hash as the second, so a block refreshed by any upgrade folded the user's own text into
    the baseline and the file was then deleted as "holding nothing else". Reproduced, and it destroyed
    a file whose only backup did not exist - the upgrade's backup copies .nonighter/ and not the host.

    The span content is excluded, so refreshing the block as often as we like changes nothing here,
    while one line the user adds outside it changes everything - which is exactly the contract the
    uninstall needs.
    """
    spans = find_marked_spans(text, begin, end)
    if not spans:
        return text
    out, previous_end = text[:spans[0][0]], spans[0][1]
    for start, stop in spans[1:]:
        out += text[previous_end:start]
        previous_end = stop
    return out + text[previous_end:]


def shell_is_untouched(text: str, recorded: Optional[str], begin: str, end: str) -> bool:
    """Is everything outside our marked block still exactly what the installer wrote?

    One definition, two callers, and they must not drift: the uninstall asks it before offering to
    delete a host file, and `--verify` asks it before deciding how much of that file it may scan for
    leftover tokens. Both are really asking "does this file hold anything of the user's", and both get
    it wrong in a costly direction if they answer it differently - one deletes their text, the other
    reports their text as an install defect.

    Compares the file with our span removed against the shell hash recorded at creation. No recorded
    hash means no: an unverifiable guess is not grounds for either decision.
    """
    if not recorded:
        return False
    return hash_text(shell_without_blocks(text, begin, end)).lower() == str(recorded).lower()


def replace_marked_spans(text: str, begin: str, end: str, block: str) -> tuple:
    """Replace the first marked span with `block` and drop the rest. Returns (text, spans found).

    Dropping the extras rather than leaving them is deliberate: a host file carrying two route blocks
    is the state `--verify` reports as broken, and the operation that rewrites the block is the natural
    place to repair it. Only content strictly between our own markers is touched.
    """
    spans = find_marked_spans(text, begin, end)
    if not spans:
        return text, 0
    out, previous_end = text[:spans[0][0]] + block, spans[0][1]
    for start, stop in spans[1:]:
        out += text[previous_end:start]
        previous_end = stop
    return out + text[previous_end:], len(spans)


def is_link(path: Path) -> bool:
    """Is this a junction or symlink - something a recursive walk must not follow?

    is_symlink() covers symlinks on both platforms. A Windows junction is not a symlink to Python, so
    it needs the reparse-point flag - but that flag alone is not enough, because OneDrive
    Files-On-Demand sets it on every synced folder. A junction resolves somewhere else; a OneDrive
    placeholder resolves to itself.
    """
    if path.is_symlink():
        return True
    try:
        attrs = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    if not attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return False
    try:
        return path.resolve() != path.absolute()
    except OSError:
        return False


def walk_files(root: Path) -> Iterator[TreeFile]:
    """Every file under root. Relative paths are accumulated during the walk, never sliced off the
    full path, and links are never followed."""
    root = root.resolve()
    pending = [(root, "")]
    while pending:
        directory, prefix = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for entry in entries:
            rel = "{}/{}".format(prefix, entry.name) if prefix else entry.name
            if entry.is_dir():
                if not is_link(entry):
                    pending.append((entry, rel))
            else:
                yield TreeFile(rel=rel, full=entry, suffix=entry.suffix)


def read_text(path: Path) -> Optional[str]:
    """UTF-8, BOM tolerated. None when the file does not exist."""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8-sig")


def make_writable(path: Path) -> None:
    """Clear the read-only bit, if it is set.

    Template files inside an installed plugin are read-only, and a copy carries that across.
    Anything we put in the workstation has to stay writable: the user edits it, the upgrade
    rewrites it, and a failed install has to be deletable so a retry can proceed.
    """
    try:
        mode = path.stat().st_mode
        if not mode & stat.S_IWRITE:
            path.chmod(mode | stat.S_IWRITE)
    except OSError:
        pass


def write_text(path: Path, content: str) -> None:
    """UTF-8 without a BOM, newlines always \n - so a hash is reproducible across machines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        make_writable(path)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def read_json(path: Path):
    raw = read_text(path)
    return None if raw is None else json.loads(raw)


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalise_for_hash(content: str) -> str:
    """The content a hash is taken over, per the template set's hash contract.

    Line endings to LF, trailing whitespace stripped from every line, exactly one trailing
    newline. The digest is lowercase hex - the reference verifier in the template set's
    authoring kit compares the recorded string exactly, so the case is part of the contract.

    Normalising matters more than it looks: without it, an editor that rewrites line endings makes
    every file look edited, and an upgrade that treats an edited file as untouchable then refuses to
    touch anything at all. Stripping trailing whitespace covers the same class - an invisible change
    that would otherwise read as the user's work.
    """
    lines = content.replace(chr(13) + chr(10), chr(10)).replace(chr(13), chr(10)).split(chr(10))
    return chr(10).join(line.rstrip() for line in lines).rstrip(chr(10)) + chr(10)


def hash_text(content: str) -> str:
    """The hash of a string's normalised content."""
    return hashlib.sha256(normalise_for_hash(content).encode("utf-8")).hexdigest()


def hash_file_normalised(path: Path) -> str:
    """The hash of a file's normalised content - the one the contract compares.

    hash_file() stays for anything genuinely byte-oriented (binaries, the template stamp), where
    normalising would be wrong.
    """
    return hash_text(read_text(path) or "")


# A Cowork session mounts the user's folder at /sessions/<session-name>/mnt/<folder>, and that
# session name dies with the session. A path like that is fine to READ through and catastrophic to
# RECORD: measured on a real install, every stamped file, the host CLAUDE.md, sources.json and
# instance.json all named a folder that would not exist the next morning.
EPHEMERAL_MOUNT_RE = re.compile(r"^/sessions/[^/]+/mnt(/|$)")


def is_ephemeral_path(path) -> bool:
    """Is this a per-session sandbox mount rather than a durable path?"""
    return bool(EPHEMERAL_MOUNT_RE.match(str(path).replace(chr(92), "/")))


def durable_equivalent(path, reachable_host, durable_host):
    """The durable path for something reached through a per-session mount, or None.

    Given a folder reached at /sessions/<x>/mnt/<something> and the knowledge that the host folder is
    reached at /sessions/<x>/mnt/<leaf> while its durable path ends in that same <leaf>, everything
    beside the host maps too: the mount root corresponds to the durable host's parent. That is the
    whole translation, and it is what lets a shared library one folder up be recorded rather than
    abandoned - which is what happened before this existed.
    """
    reached, host_reached = str(path).replace(chr(92), "/"), str(reachable_host).replace(chr(92), "/")
    if not is_ephemeral_path(reached) or not is_ephemeral_path(host_reached):
        return None
    durable = Path(durable_host)
    mount_root = host_reached[:-(len(durable.name) + 1)]
    if not host_reached.endswith("/" + durable.name) or not reached.startswith(mount_root + "/"):
        return None
    rest = reached[len(mount_root) + 1:]
    return durable.parent / rest


def split_path_list(value: str) -> list:
    """One or more paths out of an environment variable, whatever separator it used.

    The name is plural, so treat it as a list. Splitting on ':' is not safe - a Windows path has one
    after the drive letter - so ';' and newlines only, plus a JSON array.
    """
    if not value:
        return []
    value = value.strip()
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(p).strip().strip('"') for p in parsed if str(p).strip()]
        except ValueError:
            pass
    parts = []
    for chunk in value.replace("\r", "\n").split("\n"):
        parts.extend(chunk.split(";"))
    return [p.strip().strip('"') for p in parts if p.strip()]


def candidate_scopes() -> list:
    """Every folder that could be the host, most likely first.

    The environment variables come first because that is the surface telling us directly. Walking up
    from the working directory is the fallback for a surface that sets neither.
    """
    seen = []
    for name in SCOPE_ENV_VARS:
        for raw in split_path_list(os.environ.get(name, "")):
            try:
                seen.append(Path(raw))
            except (OSError, ValueError):
                continue
    try:
        cwd = Path(os.getcwd())
        seen.append(cwd)
        seen.extend(cwd.parents)
    except OSError:
        pass
    out = []
    for path in seen:
        if path not in out:
            out.append(path)
    return out


def default_scope() -> Path:
    """The folder to act on when the caller did not name one."""
    scopes = candidate_scopes()
    return scopes[0] if scopes else Path(os.getcwd())


def path_like_environment(limit: int = 25) -> list:
    """Environment variables whose value looks like a filesystem path, for diagnostics.

    Printed only when the workstation is not found. Rather than guess which variable names a surface
    exposes, print the ones holding a path and let one run answer it - which is exactly how
    CLAUDE_CODE_WORKSPACE_HOST_PATHS was found.

    **It prints values, so it must not print secrets.** "Contains a slash" was the whole test, which
    matches an API endpoint, a connection string, a bearer token with a `/` in its base64, and a
    proxy URL carrying a password. Those get printed into a user-visible diagnostic - and this path
    runs precisely when something is already wrong, so the output tends to be pasted into a chat.

    So the test is now "looks like an absolute filesystem path", which is what this diagnostic is
    actually for, and anything with a URL scheme or credential punctuation is skipped whatever else it
    looks like. A missed variable costs one more round of diagnosis; a leaked one cannot be taken back.
    """
    out = []
    for name, value in sorted(os.environ.items()):
        if not value or len(value) < 3 or value.startswith("-"):
            continue
        if "://" in value or "@" in value:
            continue                          # a URL or a credential, whatever else it resembles
        if any(word in name.upper() for word in
               ("TOKEN", "SECRET", "KEY", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTH", "SESSION")):
            continue
        parts = [p for p in value.replace("\\", "/").split(os.pathsep) if p]
        if not parts or not all(p.startswith("/") or re.match(r"^[A-Za-z]:/", p) for p in parts):
            continue                          # not absolute paths - not what this diagnostic is for
        if len(value) > 300:
            value = value[:300] + " ..."
        out.append("  {} = {}".format(name, value))
        if len(out) >= limit:
            break
    return out


def find_workstation(workstation_rel: str, router: str = "AGENTS.md"):
    """(workstation dir, scopes checked). The dir is None when none of them has one."""
    checked = []
    for scope in candidate_scopes():
        checked.append(scope)
        if (scope / workstation_rel / router).exists():
            return scope / workstation_rel, checked
    return None, checked
