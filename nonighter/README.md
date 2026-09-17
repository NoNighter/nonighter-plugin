# NoNighter plugin — how it works

The plugin is a shell. It ships the PDF import skill, which needs a NoNighter account to do anything, plus
the two pieces that make a folder and a machine ready: the workstation installer and the skill sync.
The concept-index skills (`workflow-autofill`, `concept-value-lookup`) are not offered yet.

## Skills

| Skill | Status | Description |
|-------|--------|-------------|
| `workstation-init` | Wired | Install, verify, upgrade or unwire the `.nonighter/` workstation in a folder from the bundled template set |
| `import-to-excel` | Wired | PDF import + image OCR via the `import-document-*` / `import-image-*` MCP tools |
| `sync-skills` | Wired | Fetch the modeling skills a licensed user is entitled to, through the MCP tool `skills-provision`, and install them under `skills/` |

Fetched, not shipped: whatever the licence includes, named by the store rather than here. Each lands
under `skills/<name>/` on the user's machine and is listed as `nonighter:<name>` from the next session.

## The skill sync

1. On every SessionStart the hook checks the sync receipt. Never synced on this machine → it tells the
   session to run `sync-skills` at once, before the user's request and without asking. Synced but the
   plugin folder was rebuilt (every plugin version; every session in Cowork) → the hook re-copies the
   skills from the local zip cache itself, no network. They are on disk for that session but **not in
   its skill list** (the list is taken before the hook runs — measured 2026-09-17), so the hook tells the
   session to read the `SKILL.md` directly if asked; the next session lists them. Last sync older than
   seven days → the session offers a refresh once, after answering.
2. `sync-skills` calls the MCP tool `skills-provision`. The MCP authenticates the user (Entra) and checks
   the licence; the answer is a manifest of presigned S3 URLs, valid ~15 minutes.
3. `skills/sync-skills/scripts/sync_skills.py` downloads each package, verifies its sha256 and installs
   it. Receipt and zip cache live in `${CLAUDE_PLUGIN_DATA}` (the plugin's persistent data folder) when
   the surface has one; otherwise the receipt sits in the plugin root and there is no cache.
4. A downloaded package never overwrites a shipped skill: the script refuses a folder its receipt does
   not list.

Skills installed mid-session are listed from the next session; the hook tells the session to read the
installed `SKILL.md` directly if modeling work is asked for in the meantime.

## The workstation

The modeling skills work against a **workstation**: a file-based context in the user's own folder that
says how to work there — the activity taxonomy, the authoring conventions, and the memory and context
systems. It lives at `<host>/.nonighter/`, hidden, where `<host>` is the folder the session was opened in.

**A workstation goes in a folder the user controls, never in one the whole team can write to.** The hook
injects the content of `.nonighter/*` into the session, which makes those files effective instructions
for every session in that folder — anyone with write access to that folder can put instructions into
every session run there. A synced company library is the wrong home for exactly that reason.

- The **SessionStart hook** (`hooks/check_workstation.py`) finds the workstation, injects its session-start
  files, and names `AGENTS.md` as the router. When none is found it tells the session to offer one, once,
  after answering the user.
- **`workstation-init`** builds it when it is missing: it interviews the user, then runs
  `init_workstation.py`, which writes `.nonighter/` from `templates/manifest.json`. The scripts do the
  stamping, not the model. The same skill upgrades an installed workstation file by file and unwires
  one on request; `.nonighter/` itself is never deleted.

The scripts are Python, run as `py` on Windows or `python3` elsewhere.

## MCP connector

Every data skill talks to the NoNighter MCP server named in `.mcp.json`. The URL is per environment and
is set at release time.

## Two version numbers, opposite jobs

`plugin.json` and `marketplace.json` carry the **plugin** version — the marketplace's only update signal;
a change published without a bump reaches nobody, and a pull-request check enforces the bump. The
workstation template has its own stamp in `templates/manifest.json`, compared per file by an upgrade.
The fetched modeling skills have theirs in NoNighter's catalog, and move without a plugin release.
