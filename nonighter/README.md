# NoNighter plugin — how it works

The plugin is a **bootstrap, and only that**. It ships the connector to NoNighter's server, a
SessionStart hook, `sync-skills`, and an empty stand-in for the NoNighter App. Everything a user
actually works with — the modeling skills, the presentation skills, the workstation installer, the
document import, the App — is fetched per licence and installed on their machine. Nothing about what a
licence includes is written here, so a skill added or retired in the store needs no release of this
plugin.

## What ships

| Piece | What it does |
|-------|--------------|
| `.mcp.json` | The connector. Names the NoNighter server this build talks to; the URL is per environment and set at release time |
| `hooks/check_workstation.py` | On every session start: re-installs synced skills and mods the plugin folder lost, says when nothing has ever been synced, and hands over to the workstation skill when the licence includes one |
| `hooks/hooks.json` | That hook, and `modules`: the App's hooks module at `../mods/noni-app/hooks/register.tsx` |
| `skills/sync-skills` | Fetches what the licence covers, through the MCP tool `skills-provision`, and installs skills under `skills/` and mods under `mods/` |
| `mods/noni-app/` | The placeholder: an empty module, an empty types contract and a `.placeholder` flag. Present so an unlicensed install loads clean instead of "failed to load". `plugin.json` names its `types/index.d.ts` as the plugin's types contract, because the App keeps `$.state` and validation holds state keys to that contract. Identical to `skills/sync-skills/mod-placeholder/`, the copy the sync puts back |

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

## Mods

A catalogue item of `kind: "mod"` is a hooks module rather than a skill: a zip whose root holds
`hooks/register.tsx` and a `build.json` whose `"version"` equals the store's, and no root `SKILL.md`.
It installs to `mods/<name>/` and runs inside the plugin named `nonighter`. Today there is one, the
NoNighter App (`noni-app`). Any other `kind` is refused, never installed as a skill; only an absent
`kind` means skill. A mod is installed only under a name `hooks.json` loads (`../mods/<name>/hooks/register.tsx`).

An update is unpacked and checked in a staging folder beside `mods/<name>/`, and replaces the folder by a
rename only once it passes. A broken or mismatched package therefore never touches the App that works;
the receipt and the cached zip keep the previous version, so the hook can still restore it.

1. **Placeholder.** The plugin ships `mods/noni-app/` as an empty stand-in flagged by `.placeholder`,
   because `hooks.json` names that module and a missing module marks the whole plugin "failed to load".
   A folder holding `.placeholder` is the one shipped folder the sync may overwrite; removing or
   uninstalling the mod puts the stand-in back. "Installed" means `hooks/register.tsx` is there and
   `.placeholder` is not.
2. **Reload.** Claude reads a plugin's modules when plugins load, which is before the SessionStart
   hook runs. A mod installed by the sync, or restored by the hook after a plugin rebuild, is therefore
   on disk but not loaded in that session: it appears after `/reload-plugins` (no reinstall needed) or
   in the next session. The sync's output and the hook's notice both say so.
3. **Cowork.** The plugin folder is rebuilt every Cowork session, and the stand-in loads before the
   hook restores the App, so the App never stays loaded across Cowork sessions; each one needs a
   reload. Not tested in Cowork itself.
4. **Claude Code version.** The App's module loads on Claude Code **2.1.299 or newer**. Older versions
   never break the plugin over it: before 2.1.250 the `modules` key is ignored; from 2.1.250 to 2.1.296
   the App's module is not loaded (validation reports it; 2.1.260 to 2.1.296 log "failed to load") and the
   rest of the plugin — skills, connector, this hook — loads as usual. The shipped placeholder loads clean on every version tested (2.1.150 to 2.1.309).
   On versions where modules sit behind the `tengu_plugin_hooks_modules` rollout flag, an account with
   the flag off loads no module at all, the App included, and the rest works the same way.

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
