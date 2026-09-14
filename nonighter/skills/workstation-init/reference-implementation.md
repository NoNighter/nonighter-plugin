# Reference — implementation

> How the install is put together: the layout it produces, the manifest contract the scripts read,
> how versioning and upgrades are tracked, and the traps the code is written around. Read before
> changing anything under `scripts/`.

## 1. The layout

```
<host>/                               the folder the user is working in
  CLAUDE.md                           the route, between the template's markers (created or appended)
  AGENTS.md                           the same block appended, only where the host already has one
  .nonighter/                         the instance: the template set stamped with the answers
    AGENTS.md, CONVENTIONS.md, MEMORY.md, operating-manual.md
    instance.json                     state - version, instance block, systems, host-wiring, stamped
    memory/, context/, tools/ ...  only the systems the interview switched on
```

An upgrade (SKILL.md section 7) copies `.nonighter/` to a folder **outside** the instance first and
deletes that copy once the user confirms the result; the instance itself carries no backup folder.

Nothing else. Earlier versions also wrote `.claude/settings.local.json`, junctions under
`.claude/skills/`, and a `/mode` command into the host folder, to carry the v1 template's own hooks
and workstation-local skills. The v2 template set ships no `.claude/` and no skills — all skills are
plugin-level — so all of that is gone.

## 2. The manifest is the contract

`templates/manifest.json` is the only thing that says what an install consists of. The scripts know
four things and nothing else: the workstation folder name (`.nonighter`), the state file name
(`instance.json`), the `{{TOKEN}}` and `<!-- if:system -->` syntaxes, and that `AGENTS.md` is the
router. Everything else — which folders exist, which files are stamped, which tokens are asked for,
which files are hashed, which are copied verbatim — is read from the manifest at run time.

This matters because the template set and the scripts are authored separately. Anything the scripts
hardcode about the template's contents is a future silent breakage.

Three rules the loader enforces rather than trusting:

- **A row naming a system the manifest does not declare fails at load**, naming the row. Left
  permissive, such a row is silently skipped on every install: the manifest lists a file, the
  installer never delivers it, and nothing anywhere says so.
- **A row with no `system` is unconditional**, the same as `"always"`. The earlier version required
  the key, which meant a newly added file with no `system` vanished with no error — found by adding
  one and watching the upgrade plan not mention it.
- **A `.json` target takes JSON-escaped values.** `{{HOST_PATH}}` on Windows carries backslashes, and
  a raw backslash is an invalid JSON escape. An `instance.json` written without this does not parse,
  and both verify and upgrade then refuse to run — which is the whole state file gone over one
  substitution.

Conditional blocks are resolved **before** token substitution, and the resolver repeats until the
text stops changing so that a disabled outer block takes an inner one with it. A disabled block is
removed whole, including its trailing newline: leaving the blank line behind splits the retrieval
table in `AGENTS.md` into two tables, and the second one stops reading as part of the map.

After stamping, every file is scanned for a surviving `{{` or `<!-- if:`. Either one is an install
defect and stops the install: a token left in the router is read as literal text every session
after, forever, and it costs nothing to catch here.

## 3. The context comes from the plugin hook, not from the folder

Measured in a real **Cowork** session against a v1 install: neither the project hooks in
`.claude/settings.local.json` nor the linked skills in `.claude/skills/` were active. Asked to quote a
canary line planted in `MEMORY.md`, the agent read the file instead of quoting injected context;
asked for its skills, it reported the workstation-local ones as "not loaded as invokable skills here."

Project `.claude` configuration is trust-gated — it needs a workspace-trust dialog no script can
accept for the user — and Cowork honours plugin components rather than a folder's own `.claude`.
Plugin hooks need neither trust nor a particular surface.

With the v2 template set shipping no `.claude/` at all, this stops being a preference and becomes the
only path: **`nonighter/hooks/check_workstation.py` is the sole mechanism that loads the
workstation's context.** It finds `.nonighter/`, injects `MEMORY.md` and `operating-manual.md` (capped
at 8,000 characters each — paid every session, and a working client's memory grows), and names
`AGENTS.md` as the router. The `CLAUDE.md` block is the fallback for a session running without the
plugin; it routes, but it injects nothing.

### A bundled template may not carry skills of its own

Measured against the account-level skill uploader: it rejects a package with more than one
`SKILL.md` anywhere inside it — *"Zip must contain exactly one SKILL.md file. Currently there are
5."* The v1 template shipped four workstation-local skills under `.claude/skills/`, so the skill
could not be packaged for that channel at all.

The v2 template set moves every skill to plugin level, which removes the collision. That decision was
made for distribution reasons — one plugin release instead of an upgrade on every client — and it
turns out to be a hard packaging requirement for the account-level channel as well.

The rule to keep: **whatever `templates/` contains, it must not contain a `SKILL.md`.** If a future
template reintroduces workstation-local skills, this skill stops being publishable as a standalone
skill, and the only route left is the plugin.

### Finding the user's folder: never the working directory

The hook does not run where the user is, and the path it *can* reach is not the path to record.
Measured in Cowork, the process starts under the app's own session directory:

```
C:\Users\<user>\AppData\Roaming\Claude\local-agent-mode-sessions\<id>\<id>\local_<id>\outputs
```

Walking up from there reaches `C:\`, never the connected folder. For days the hook reported NOT
INSTALLED over an installed workstation because of it, and the agent believed the hook and offered to
install again — a wrong answer delivered confidently is worse than no answer.

The surface names the folder in an environment variable, and it took a diagnostic to find which:
**`CLAUDE_CODE_WORKSPACE_HOST_PATHS`**. `CLAUDE_PROJECT_DIR` is checked after it, and the walk up
from the working directory survives only as a fallback for a surface that sets neither. This is why
every script prints the host folder it resolved as its first line, and why the skill is told to read
that line back to the user before anything is written.

Two things to keep:

- **The value is a list** — the name is plural. `;`, newlines and a JSON array are all handled.
  Never split on `:`, which a Windows drive letter contains.
- **The resolution lives in `workstation_lib`, and the hook imports it** rather than keeping its own
  copy. Two copies drifting apart is exactly how a hook ends up contradicting the installer that just
  ran, which is the failure this section is about.

The way it was found is worth copying: rather than guessing variable names, the not-found message was
made to print every environment variable holding a path and ask whoever read it to say which one was
the user's folder. One run answered it. The same move fixed an invalid permission rule earlier — when
a mechanism fails somewhere you cannot observe, make the failure carry the evidence.

### Reaching a folder and recording it are different questions

Measured on the first Cowork install: the folder was reachable at
`/sessions/<session-name>/mnt/<folder>`, and that is what the install recorded — in `instance.host`,
in the `{{HOST_PATH}}` stamped into the router, the conventions, the operating manual and the host
`CLAUDE.md`, and in all four rows of `sources.json`. The session name is per-session, so every one of
those paths was dead the next morning and had never been valid in Code. The install reported success.

So the two questions are separated in the interface: `--host` is what to write **through**,
`--host-path` is what to **record**. `is_ephemeral_path()` recognises the per-session mount shape and
the installer stops rather than stamping it, printing the exact re-run and the environment diagnostic
above — because the same variable might carry the durable path on some surface, and the failure is the
cheapest place to find out.

The durable fix for sources goes further: a source inside the host folder is recorded **relative to
the host**, with a `base` field saying so. A relative path resolves on every surface, which no absolute
one does. Only a folder outside the host needs an absolute path, and an ephemeral one there is refused
rather than written.

## 4. The route block, and the two files it lives in

The markers are **read from `templates/host/route-block.md`**, never hardcoded. They were hardcoded
once, to the v1 strings, while the v2 template used different ones: the refresh path then never
matched, so re-wiring appended a *second* route block instead of replacing the first, leaving two
routes in the host `CLAUDE.md` and no error anywhere. The loader now requires exactly one
`nonighter:*:start` and one `:end` in that file and fails if it finds otherwise.

`CLAUDE.md` is created from `templates/host/CLAUDE.md` when the host has none, and otherwise gets the
block appended — nothing outside the markers is touched, ever. `AGENTS.md` gets the block only when
the host already has one, because a harness reading that file instead of `CLAUDE.md` would otherwise
never find the route.

When the installer creates `CLAUDE.md` it records a hash of exactly what it wrote, under
`host-wiring["claude-md-hash"]`. That is what lets uninstall tell "the installer's file, untouched"
from "the user has written in it" **exactly**, instead of guessing from the file's shape. The first
attempt compared the file against the template with token-bearing lines dropped, which never matched
and so never offered the deletion at all. Without a recorded hash the answer is no: an unverifiable
guess is not grounds for deleting somebody's file.

## 5. Files the scripts own, and memory maintenance

Files the manifest marks `hashed: false` are **state, not content** — `instance.json` and
`context/sources.json`. They are stamped once at install and then never compared and never overwritten. They appear in an upgrade plan in one case only: as an `add`, when the file is missing, so a state file introduced by a later template version reaches an existing instance.
The reason is the same for both: they are client state, and a template has no business overwriting
client state. Without the exclusion, a template shipping a `sources.json` stub would show up as a
conflict on every single upgrade, and the client's registered folders would be one careless overwrite
from gone.

### Memory maintenance runs at session start, not on a timer

No scheduled task is created, and that is a design choice rather than a gap. A Windows task can only
run a program, so it would need a command-line Claude that is installed, signed in, and at a path
that survives an app update. Measured on a developer machine: the bundled `claude.exe` exists but
reports "Not signed in", and its path carries the version number
(`AppData/Roaming/Claude/claude-code/2.1.237/claude.exe`), so it moves on every update. A task built
on that fails silently, daily, while the user believes their memory is being maintained.

Instead the plugin hook checks `memory/runs/` for a recent record and, when there is none, tells the
agent to offer maintenance and points at `memory/instructions-memory-maintenance.md`. No CLI, no
login, nothing to break on update, and it works in Cowork. The hook never instructs the agent to just
run it: rewriting the client's memory unasked, before they have said a word, is not ours to decide.

The trade is that maintenance only happens when the user shows up — which is also when there are new
conversations to fold in.

## 6. The hash contract

One normalisation, shared by install, verify and upgrade, in `workstation_lib.normalise_for_hash`:
CRLF and CR become LF, trailing whitespace is stripped from every line, and the text ends in exactly
one newline. Then SHA-256, **lowercase** hex - what `hashlib.sha256(...).hexdigest()` returns.

It has to be exactly this, because it is `reference-verify.md`'s published contract and because the
alternative was measured: with line-ending normalisation alone, rewriting a file with CRLF and
trailing spaces changed its hash, so **every** file read as edited and an upgrade touched nothing.
The check that settled it: rewrite a stamped file with CRLF plus trailing spaces, then confirm the
normalised hash is unchanged while the raw byte hash is not.

The version lives in `manifest.json` and is stamped into `instance.json` at install. There is no
separate content hash and no version-stamp file: the manifest is the version, and the per-file
hashes live in the instance where they describe *that install*.

**The version tracks the template set's content, and nothing else.** Bump it when a file under
`templates/` changes; do not bump it for a change to `SKILL.md`, a reference file, or a script. The
reason is mechanical: the session-start hook compares an instance's recorded version against the
bundled one and offers an upgrade when the bundle is newer. A bump with no template change makes
every installed instance announce an upgrade that then reports "nothing to do" - which teaches the
user to ignore the notice, and the notice only exists because a real fix would otherwise never reach
them. This happened once, at 0.2.2, and was reverted.

A repo-root `.gitattributes` marks the bundled template `-text` so git never rewrites its line
endings. Without it, a checkout on another machine would disagree with the stamped hashes.

## 7. Upgrades: two sides and the hashes

By the time the template changes, the user's workstation holds real work — memory, records, context
cards, sometimes their own edits to the mechanism files. Replacing the folder loses that; leaving it
alone means they never receive a fix. There is no upgrade script: the instance is read against the
bundled template and edited, and `SKILL.md` §7 is the procedure.

The design turns on one asymmetry. **Which files the user has touched is a fact, and the hashes
answer it. What to do about a file they have touched is a judgement, and only reading it answers
that.** So the hashes are consulted first, and they retire most of the work:

| | |
|---|---|
| hash matches `stamped` | never touched — this version's copy replaces it whole, mechanically |
| hash differs | theirs — read both sides, edit only what this version changed |
| no hash recorded | they created it, or the manifest marks it `hashed: false` — never compared, never overwritten |

`stamped` records the **pristine** template content, never what happens to be on disk, and that
semantic is the one thing not to get wrong. After an upgrade it is re-recorded to the *new* pristine
hashes for every hashed file — the ones the user had edited included, where their own text stayed in
place. Recording the on-disk hash there instead would make the next upgrade read their edit as
untouched and quietly overwrite it. Checked by hand this way: edit `CONVENTIONS.md`, change it in the
template too, upgrade, then upgrade again and confirm the second run still reads it as theirs.

Three properties are worth naming:

- **Files the template never delivered are out of reach.** The work folders and anything the user
  created appear in neither the manifest nor `stamped`, so an upgrade cannot touch them by
  construction rather than by rule. The cost is that a *renamed* work folder is equally invisible,
  which is why the procedure reads folder names against the manifest as a step of its own.
- **Nothing is left beside the user's file.** A file they edited is resolved with them in the session
  that found it. A second copy sitting in their folder is an unfinished upgrade that no one comes
  back for.
- **`HOST_PATH` is recomputed, not read back.** The folder may have been moved or renamed; stamping
  the old path into every file would be worse than a stale record in `instance.json`.

## 8. Traps the helpers are written around

These produce damage that survives into the client's files, and none of them raises an error. Use the
helpers in `scripts/workstation_lib.py` rather than the raw primitives.

1. **Encoding.** Windows PowerShell 5.1's `Get-Content` / `Set-Content` default to the system ANSI
   codepage, so a read-modify-write of a UTF-8 file double-encodes every non-ASCII character — the
   template's em dashes came out as `Ã¢â‚¬â€` in an installed file. The Python helpers read and write
   UTF-8 explicitly, with no BOM and LF endings. Any future PowerShell tooling must use
   `[System.IO.File]::ReadAllText/WriteAllText`.
2. **Read-only template files.** Files inside an installed plugin are read-only, and `shutil.copy2`
   preserves that: an early version copied and then substituted, so substitution failed partway and
   left a `.nonighter/` the user could not delete. Text files are therefore read, stamped and written
   straight to the destination in one pass; binaries are copied and then made writable.
3. **Recursion follows junctions.** An installed workstation may mount a company document library. A
   naive recursive walk goes straight into it, hashing the client's entire SharePoint library into the
   instance and duplicating it into the backup. `walk_files` prunes links and never descends one.
4. **Two ways to get the link test wrong.** The ReparsePoint attribute alone does not mean "link":
   OneDrive Files-On-Demand marks every synced folder `Directory, ReparsePoint` (1040) with no
   LinkType and no Target, so pruning on the attribute alone made the *authoring* template
   unreadable — an enumeration found 11 files instead of 41 and would have shipped a gutted template.
   A real junction also reports a LinkType or a Target. In PowerShell there is a second edge:
   `[bool]($x -band [IO.FileAttributes]::ReparsePoint)` is **always true**, because `-band` on enums
   returns an enum and a zero-valued enum casts to `$true`; the comparison must go through `[int]`.
5. **8.3 short paths.** `C:\Users\VICTOR~1` expands to `C:\Users\VictoriaTeran` during enumeration, so
   deriving a relative path with `path[len(root):]` silently truncates the first characters of every
   result — a manifest full of paths like `ation/README.md`. `walk_files` accumulates relative paths
   during the walk instead of slicing them afterwards.
6. **MAX_PATH.** 260 characters on Windows. The installer projects the deepest target against the host
   folder length and warns before writing, because the honest fix is a shorter host folder and that
   choice belongs to the user, before the tree exists rather than after.
