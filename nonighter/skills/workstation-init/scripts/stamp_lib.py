"""Stamping a template set into a host folder, per templates/manifest.json.

The manifest is the machine contract: it lists every folder and file, which of the optional systems
owns each one, which files are hashed, the token registry, and the conditional-block rule. This module
implements that contract; it invents nothing the manifest does not declare.

Three rules here exist because breaking them produces a tree that reads fine and behaves wrong:

  - **A disabled system leaves no trace.** Not an empty folder, not a stub, not a dead row in the
    router. So conditional blocks are resolved by deleting the markers *and their body*, and the
    line-level bookkeeping matters: leftover blank lines where a block was split a retrieval table in
    two the last time this was done by hand.
  - **A `.json` target takes JSON-escaped values.** The host path on Windows carries backslashes, and
    a raw backslash is an invalid JSON escape - an instance.json written without this does not parse,
    and verify and upgrade then both refuse to run against it.
  - **A stamped file containing `{{` or `<!-- if:` is an install defect**, not a cosmetic problem. A
    token left in the router is read as literal text every session after.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import workstation_lib as wl

# <!-- if:system --> ... <!-- /if:system -->  spanning whole lines.
IF_BLOCK_RE = re.compile(
    r"^[ \t]*<!--[ \t]*if:([a-z-]+)[ \t]*-->[ \t]*\r?\n(.*?)^[ \t]*<!--[ \t]*/if:\1[ \t]*-->[ \t]*\r?\n?",
    re.DOTALL | re.MULTILINE)

LEFTOVER_TOKEN_RE = re.compile(r"\{\{[A-Z_]+\}\}")
LEFTOVER_MARKER_RE = re.compile(r"<!--[ \t]*/?if:")


class Manifest:
    """templates/manifest.json, with the queries the installer actually asks of it."""

    def __init__(self, path: Path):
        self.path = path
        data = wl.read_json(path)
        if not data:
            raise SystemExit("manifest not found or unreadable: {}".format(path))
        self.data = data
        self.root = path.parent
        self._check_systems()

    def _check_systems(self):
        """Every row's `system` must be "always", a declared system, or absent.

        A row naming a system that does not exist would otherwise be silently skipped on every
        install: the manifest lists the file, the installer never delivers it, and nothing anywhere
        says so. Fail at load instead, where the typo is one line away.
        """
        known = set(self.systems) | {"always", None}
        wrong = []
        for kind in ("folders", "files", "host-files"):
            for row in self.data.get(kind, []):
                if row.get("system") not in known:
                    wrong.append("{}: {} -> system \"{}\"".format(
                        kind, row.get("target") or row.get("template"), row.get("system")))
        if wrong:
            raise SystemExit("manifest declares systems {} but these rows name others:\n  {}"
                             .format(sorted(self.systems), "\n  ".join(wrong)))

    @property
    def version(self) -> str:
        return self.data.get("version", "0.0.0")

    @property
    def systems(self) -> list:
        return list(self.data.get("conditional-blocks", {}).get("systems", []))

    @property
    def tokens(self) -> list:
        return [t["token"].strip("{}") for t in self.data.get("tokens", [])]

    @property
    def verbatim(self) -> set:
        return {wl.normalise_rel(v) for v in self.data.get("verbatim", [])}

    @staticmethod
    def _wanted(row, enabled: set) -> bool:
        # No `system` means unconditional, same as "always". Anything else must be switched on.
        system = row.get("system")
        return system in (None, "always") or system in enabled

    def folders(self, enabled: set) -> list:
        return [f["target"] for f in self.data.get("folders", []) if self._wanted(f, enabled)]

    def files(self, enabled: set) -> list:
        return [f for f in self.data.get("files", []) if self._wanted(f, enabled)]

    def host_files(self) -> list:
        return list(self.data.get("host-files", []))


def resolve_conditionals(text: str, enabled: set) -> str:
    """Strip the markers of an enabled block and keep its body; delete a disabled block entirely.

    Nested blocks of different systems are handled by repeating until nothing changes, so an outer
    disabled block removes an inner one with it.
    """
    def replace(match):
        system, body = match.group(1), match.group(2)
        return body if system in enabled else ""

    previous = None
    out = text
    while previous != out:
        previous = out
        out = IF_BLOCK_RE.sub(replace, out)
    return out


def substitute(text: str, values: dict, json_target: bool) -> str:
    """Replace every {{TOKEN}}. In a .json target the value is JSON-escaped, not raw."""
    out = text
    for key, value in values.items():
        placeholder = "{{" + key + "}}"
        if placeholder not in out:
            continue
        if json_target:
            # json.dumps gives us the quoted form; strip the quotes and keep the escaping, so a
            # Windows host path lands as C:\Users\... and the file still parses.
            replacement = json.dumps(str(value))[1:-1]
        else:
            replacement = str(value)
        out = out.replace(placeholder, replacement)
    return out


def stamp_text(template_text: str, target_rel: str, values: dict, enabled: set) -> str:
    """The exact content a target file should hold: conditionals resolved, then tokens substituted.

    Order matters. Resolving first means a token inside a disabled block is deleted with the block
    rather than substituted into text nobody will ever read.
    """
    out = resolve_conditionals(template_text, enabled)
    out = substitute(out, values, json_target=target_rel.lower().endswith(".json"))
    return out


def find_leftovers(text: str) -> list:
    """What should never survive stamping. Anything here is an install defect."""
    found = []
    tokens = sorted(set(LEFTOVER_TOKEN_RE.findall(text)))
    if tokens:
        found.append("unsubstituted token(s): " + ", ".join(tokens))
    if LEFTOVER_MARKER_RE.search(text):
        found.append("unresolved conditional marker")
    return found
