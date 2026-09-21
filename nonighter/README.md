# NoNighter plugin — how it works

The plugin is a **bootstrap, and only that**. It ships three things: the connector to NoNighter's
server, a SessionStart hook, and `sync-skills`. Everything a user actually works with — the modeling
skills, the presentation skills, the workstation installer, the document import — is fetched per
licence and installed on their machine. Nothing about what a licence includes is written here, so a
skill added or retired in the store needs no release of this plugin.

## What ships

| Piece | What it does |
|-------|--------------|
| `.mcp.json` | The connector. Names the NoNighter server this build talks to; the URL is per environment and set at release time |
| `hooks/check_workstation.py` | On every session start: re-installs synced skills the plugin folder lost, says when nothing has ever been synced, and hands over to the workstation skill when the licence includes one |
| `skills/sync-skills` | Fetches the skills the licence covers, through the MCP tool `skills-provision`, and installs them under `skills/` |

Fetched, not shipped: whatever the licence includes, named by the store rather than here. Each lands
under `skills/<name>/` on the user's machine — the same folder a shipped skill would occupy — and is
listed as `nonighter:<name>` from the next session.

## The skill sync

1. On every SessionStart the hook checks the sync receipt. Never synced on this machine → it tells the
   session to run `sync-skills` at once, before the user's request and without asking. Synced but the
   plugin folder was rebuilt (every plugin version; every session in Cowork) → the hook re-copies the
   skills from the local zip cache itself, before Claude lists skills, so they are available in that
   session. Last sync older than seven days → the session offers a refresh once, after answering.
2. `sync-skills` calls the MCP tool `skills-provision`. The MCP authenticates the user (Entra) and checks
   the licence; the answer is a manifest of presigned S3 URLs, valid ~15 minutes.
3. `skills/sync-skills/scripts/sync_skills.py` downloads each package, verifies its sha256 and installs
   it. Receipt and zip cache live in `${CLAUDE_PLUGIN_DATA}` (the plugin's persistent data folder) when
   the surface has one; otherwise the receipt sits in the plugin root and there is no cache.
4. A downloaded package never overwrites a shipped skill: the script refuses a folder its receipt does
   not list. **This is why the plugin ships so little** — a skill delivered by licence cannot also sit
   in the plugin, or the sync refuses it for every client.

Skills installed mid-session are listed from the next session; the hook tells the session to read the
installed `SKILL.md` directly if work is asked for in the meantime.

## The workstation

Most NoNighter work runs against a **workstation**: a file-based context in the user's own folder that
says how to work there — the activity taxonomy, the authoring conventions, and the memory and folder
systems. It lives at `<host>/.nonighter/`, hidden, where `<host>` is the folder the session was opened in.

**A workstation goes in a folder the user controls, never in one the whole team can write to.** The hook
injects the content of `.nonighter/*` into the session, which makes those files effective instructions
for every session in that folder — anyone with write access to that folder can put instructions into
every session run there. A synced company library is the wrong home for exactly that reason.

**The workstation is a licensed skill (`workstation-init`), not part of this plugin.** It arrives
through the sync like any other, carrying its own installer, its template set and its session-start
behaviour. This plugin's hook is the entry point: where that skill is installed it hands over to
`skills/workstation-init/scripts/session_start.py`, which finds the workstation, injects the files
`AGENTS.md` declares, and offers to build one when there is none. **Where the skill is not installed
the hook says nothing about workstations at all** — a licence without it is an ordinary state, not a
fault, and reporting one would be telling the user about something they cannot act on.

Anything needing an answer from the user — this hook's own sync prompt, then the workstation's —
is emitted above everything that does not, so a truncated preview still shows what needs a reply.

The scripts are Python, run as `py` on Windows or `python3` elsewhere.

## Two version numbers, opposite jobs

`plugin.json` and `marketplace.json` carry the **plugin** version — the marketplace's only update signal;
a change published without a bump reaches nobody, and a pull-request check enforces the bump. Every
fetched skill carries its own version in NoNighter's catalogue, and those move without a plugin release.
That is the split worth keeping: this repository changes when the *bootstrap* changes, which should be
rarely, and never because a skill did.
