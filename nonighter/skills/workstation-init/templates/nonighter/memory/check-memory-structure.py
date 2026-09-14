"""Conformance check for workstation memory files against CONVENTIONS.md section 4.

Read-only. Reports; never writes. Run it after the daily pass writes the memory
files, and before shipping any hand edit to a memory file:

    python .nonighter/memory/check-memory-structure.py
    ... --quiet     # only files with findings
    ... --json      # machine-readable

Findings split two ways:
  STRUCTURE - the shape is wrong, so a tool silently mis-reads the file
              (the day plan lifts Status / Open threads / Settled by exact H2;
              compaction ages '### YYYY-MM-DD' entries).
              Exit code 1 if any exist.

It also checks the run reports in memory/runs/, for one thing only: that each
records the read cut-off the next pass needs. Nothing else read them, so a report
that omitted it passed unnoticed and the following pass had to reconstruct the
cut-off from the transcripts.
  STYLE     - readable by the tools, off the written standard. Does not fail.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]        # the .nonighter/ instance root
SCOPE_DIRS = ["initiatives", "projects", "tasks"]
SKIP = ("_archive", "_backup", "archive", "memory-archive", "_retired")
RUNS_DIR = "memory/runs"

BAND = 2000
STATUS_WORDS = 60          # Status is a two-line snapshot, not a log
HEADLINE_WORDS = 20

REQUIRED = ["Status", "Standing facts", "Recent memory", "Open threads", "Settled"]
OPTIONAL = ["To promote"]
BUCKETS = ["Ready", "Blocked", "Later"]
ROOT_OMITS = ["Status", "Standing facts"]   # root MEMORY.md is a bucket, not a scope
CANONICAL = REQUIRED + OPTIONAL

H2_RE = re.compile(r"^## (.+?)\s*$")
H3_RE = re.compile(r"^### (.+?)\s*$")
ENTRY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*[-–—]\s*(.+)$")
NEXTID_RE = re.compile(r"<!--\s*next-id:\s*[A-Z0-9]+-\d+\s*-->")
STATE_RE = re.compile(r"\*\*State:\*\*\s*\**\s*(active|blocked|paused|done)\b", re.I)
PHASE_RE = re.compile(r"\*\*(Phase|Current phase):\*\*")
CUTOFF_RE = re.compile(r"cut-?off", re.I)
STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def canonical_name(h2):
    """Map a heading to its canonical section name, or None if off-list."""
    for name in CANONICAL:
        if h2 == name or h2.startswith(name + " "):
            return name
    return None


def find_files():
    out = []
    for top in SCOPE_DIRS:
        base = ROOT / top
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("memory-*.md")):
            if any(part in SKIP or part.startswith("_") for part in p.parts):
                continue
            out.append(p)
    root_mem = ROOT / "MEMORY.md"
    if root_mem.is_file():
        out.append(root_mem)
    return out


def find_run_reports():
    base = ROOT / RUNS_DIR
    return sorted(base.glob("*.md")) if base.is_dir() else []


def check_run_report(path):
    """A run report needs one thing from a tool: the cut-off the next pass reads.

    Step 1 of the procedure takes the previous cut-off from the last report, so a report
    without one leaves the next pass no way to tell which turns it already covered - it either
    re-reads whole conversations or skips turns for good. A report that only quotes the previous
    run's cut-off does not count, which is why the line naming it is excluded.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    struct = []
    own = [ln for ln in text.splitlines()
           if CUTOFF_RE.search(ln) and STAMP_RE.search(ln) and "previous" not in ln.lower()]
    if not own:
        struct.append("no read cut-off recorded: no line names a cut-off with a "
                      "YYYY-MM-DDThh:mm stamp, so the next pass has nothing to start from")
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "tokens": int(len(text.split()) * 1.33), "structure": struct, "style": []}


def section_body(lines, name):
    """Text between the first '## <name>' and the next H2."""
    out, inside = [], False
    for line in lines:
        m = H2_RE.match(line)
        if m:
            if inside:
                break
            inside = canonical_name(m.group(1)) == name
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def section_h3s(lines, name):
    body = section_body(lines, name).split("\n")
    return [m.group(1) for m in (H3_RE.match(line) for line in body) if m]


def check(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    is_root = path.name == "MEMORY.md"
    struct, style = [], []

    h2s = [m.group(1) for m in (H2_RE.match(line) for line in lines) if m]
    h3s = [m.group(1) for m in (H3_RE.match(line) for line in lines) if m]
    tokens = int(len(text.split()) * 1.33)

    # H1 and blockquote
    h1 = lines[0].strip() if lines else ""
    want_h1 = "# " + path.name
    if h1 != want_h1:
        style.append("H1 is %r; the standard is %r" % (h1, want_h1))
    if not any(line.startswith(">") for line in lines[1:6]):
        style.append("no blockquote description under the H1")

    # required sections, once each, in order
    required = [s for s in REQUIRED if not (is_root and s in ROOT_OMITS)]
    seen = [canonical_name(h) for h in h2s]
    for name in required:
        n = seen.count(name)
        if n == 0:
            # nothing parses Standing facts, so its absence cannot break a tool:
            # that makes it a standards finding, not a structural one.
            (style if name == "Standing facts" else struct).append(
                "missing required section '## %s'" % name)
        elif n > 1:
            struct.append("'## %s' appears %dx - tools read only one of them" % (name, n))
    order = [s for s in seen if s in required]
    if len(set(order)) == len(order) and order != sorted(order, key=required.index):
        struct.append("sections out of order: %s (expected %s)"
                      % (" -> ".join(order), " -> ".join(required)))

    # sections that are not memory
    for h in h2s:
        if canonical_name(h) is None:
            if h.lower().startswith("how to write this file"):
                struct.append("carries a '## How to write this file' guide - "
                              "the rules live in CONVENTIONS.md, not in the file")
            else:
                struct.append("'## %s' is not a memory section - see CONVENTIONS.md section 4" % h)

    # Settled levelled as H3
    if any(h.strip() == "Settled" for h in h3s):
        struct.append("'### Settled' is an H3 - invisible to the day-plan sweep, "
                      "and its rows fold into the Open threads digest")

    # Standing facts: a briefing, not a second log
    if "Standing facts" in seen:
        body = section_body(lines, "Standing facts")
        bullets = [l for l in body.split("\n") if l.strip().startswith("- ")]
        if len(bullets) > 10:
            style.append("Standing facts has %d bullets (max ~10) - it is a briefing, not a log"
                         % len(bullets))
        if any(H3_RE.match(l) for l in body.split("\n")):
            struct.append("Standing facts carries dated '###' entries - it is curated, "
                          "not appended to; a dated entry belongs in Recent memory")

    # Status block
    if not is_root and "Status" in seen:
        body = section_body(lines, "Status")
        if not STATE_RE.search(body):
            struct.append("Status has no '**State:** active|blocked|paused|done' line")
        if not PHASE_RE.search(body):
            style.append("Status has no '**Phase:**' line")
        words = len(body.split())
        if words > STATUS_WORDS:
            style.append("Status is %d words (max ~%d) - it is a snapshot, not a log"
                         % (words, STATUS_WORDS))

    # Open threads: counter, buckets, columns
    if "Open threads" in seen:
        if not NEXTID_RE.search(text):
            struct.append("'## Open threads' with no '<!-- next-id: XXX-n -->' counter")
        found = [h for h in section_h3s(lines, "Open threads")]
        for h in found:
            if h == "Now":
                struct.append("'### Now' was renamed '### Ready' - nothing is stopping these, "
                              "which is what separates them from Blocked")
            elif h == "Settled":
                pass                      # already reported above, as a levelling error
            elif h not in BUCKETS:
                struct.append("'### %s' is not a bucket - Ready / Blocked / Later" % h)
        body = section_body(lines, "Open threads")
        for line in body.split("\n"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0].lower() == "id":
                if "Due" in cells:
                    struct.append("task table still carries a 'Due' column - it was cut; "
                                  "a real deadline goes in the Done-when text")
                if "Added" not in cells:
                    struct.append("task table has no 'Added' column - without it an item's "
                                  "age is invisible and nothing forces it back to a decision")

    # entry shape
    for name in ("Recent memory", "Medium-term", "To triage"):
        if name not in seen:
            continue
        for h in section_h3s(lines, name):
            m = ENTRY_RE.match(h)
            if not m:
                style.append("entry under '## %s' is not '### YYYY-MM-DD - headline': '%s'"
                             % (name, h[:55]))
            elif len(m.group(2).split()) > HEADLINE_WORDS:
                style.append("headline is %d words (max %d): '%s...'"
                             % (len(m.group(2).split()), HEADLINE_WORDS, m.group(2)[:55]))

    # band
    if tokens > BAND:
        struct.append("over band: ~%d tokens (ceiling %d) - the trim did not reach it"
                      % (tokens, BAND))

    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "tokens": tokens, "structure": struct, "style": style}


def main():
    args = sys.argv[1:]
    quiet = "--quiet" in args
    results = ([check(p) for p in find_files()]
               + [check_run_report(p) for p in find_run_reports()])

    if "--json" in args:
        print(json.dumps(results, indent=2))
        return 1 if any(r["structure"] for r in results) else 0

    bad = [r for r in results if r["structure"]]
    print("memory structure check - %d files, %d with structure findings\n"
          % (len(results), len(bad)))
    for r in results:
        if quiet and not r["structure"] and not r["style"]:
            continue
        print("%s  (~%d tokens)" % (r["path"], r["tokens"]))
        for f in r["structure"]:
            print("   STRUCTURE  " + f)
        for f in r["style"]:
            print("   style      " + f)
        print("")

    n_struct = sum(len(r["structure"]) for r in results)
    n_style = sum(len(r["style"]) for r in results)
    print("%d structure findings across %d files; %d style findings."
          % (n_struct, len(bad), n_style))
    print("Reference: CONVENTIONS.md section 4, 'MEMORY.md / memory-<topic>.md'.")
    return 1 if n_struct else 0


if __name__ == "__main__":
    sys.exit(main())
