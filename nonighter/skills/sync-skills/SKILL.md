---
name: sync-skills
description: Fetch and install the NoNighter skills the user's licence includes into this plugin, from NoNighter's store through the MCP — and the NoNighter App, when the licence includes it. Use when the SessionStart hook says the skills were never synced on this machine or the last sync is stale, or when the user asks to "sync my skills", "actualizar mis skills", "update my NoNighter skills", "why don't I have the modeling skill", "install the NoNighter App". Not the workstation installer — that is workstation-init.
---

# sync-skills

The plugin you installed is a shell. The skills that do the modeling are fetched here, once per
machine and again whenever a new
version is published, for users with an active NoNighter licence. Nothing is stored about the user, no
credential is kept: the MCP authenticates, the packages download straight from S3 through links that
expire in about 15 minutes.

The same sync delivers **mods**: packages that change Claude's own interface rather than teach it a
task. The NoNighter App is one. See [Mods](#mods-the-nonighter-app) for the one way they differ.

## Procedure

1. **Ask the store.** Call the MCP tool `skills-provision` with no arguments. It is served by NoNighter's
   MCP server, which may appear in this session under more than one name — the plugin's own `nonighter`
   connection, or a `nonighter`/`nonighter-dev` connector the user added to their account. **Any of them
   is fine: look for the tool by name across every connected NoNighter server.** It answers with a
   manifest: a `skills` list of `{name, version, kind, sha256, size, url}`, where `kind` is `skill` or
   `mod`. Save that JSON, exactly as returned, to a temporary file (`manifest.json` in the session's
   scratch folder is fine).
   - **Tool not found anywhere** → do not say the connector is "not authorised": you cannot know that.
     Two things cause it, and one message covers both: *"I can't reach NoNighter's skill store from this
     session. Check Settings → Plugins → NoNighter → Connectors: if it says Connect, connect it. Then open
     a new session — the skills install by themselves when it starts."* The second sentence is not
     optional: **a session lists its tools when it starts and never again**, so connecting or refreshing
     a connector mid-session changes nothing here, and asking the user to retry in this session cannot
     work. The hook asks for this sync at every start until it succeeds, so nothing is lost.
   - Refused with "User not found" or "no active licence" → say the user is not registered with
     NoNighter or the licence is inactive, and stop. Nothing else to do.

2. **Plan, writing nothing:**

   ```bash
   py "${CLAUDE_PLUGIN_ROOT}/skills/sync-skills/scripts/sync_skills.py" --plugin-root "${CLAUDE_PLUGIN_ROOT}" --data-dir "${CLAUDE_PLUGIN_DATA}" apply --manifest <the file> --check
   ```

   (`python3` where `py` does not exist — Cowork's sandbox, macOS, Linux. If `${CLAUDE_PLUGIN_DATA}` is
   empty on this surface, omit `--data-dir`; the script then works without a cache.)

3. **Run it** — the same command without `--check`. Do not ask for confirmation when the plan only
   installs or updates: nothing of the user's is touched and nothing is asked of them. **Do ask** before
   a `remove`, since it deletes a skill they may rely on.

4. **Report in one or two lines, in the user's terms.** Name what the sync actually installed, from
   the manifest it returned -- never a list written down anywhere, which goes stale the moment the
   store changes. "Your NoNighter skills are installed: <names>." Then the one fact that matters:
   **they show up in the skills list from the next session.** If the user asks for modeling work *in
   this session*, do not say the skill is missing: open `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`
   and follow it as if the skill had been invoked. Never quote paths, hashes, or the word "manifest".
   **If the script printed a NOTE about the NoNighter App** (installed, updated or removed), add one
   line: *"To see the change, type `/reload-plugins`, or open a new session."*

## What the script refuses, and what to say

- **sha256 mismatch** — the download does not match what the store promised. Report it, do not retry
  blindly; it is a store problem, not a network one.
- **REFUSED … already ships in the plugin** — a downloaded package carries the name of a shell skill.
  Nothing is overwritten. Tell the user NoNighter has to rename that package.
- **REFUSED … kind '…' is not one this plugin installs** — the store sent something this version of the
  plugin does not know. Nothing was installed for it; the rest of the sync went ahead. Tell the user an
  update of the NoNighter plugin is needed for that item.
- **A mod package refused** (no `hooks/register.tsx`, no `build.json`, its version differs from the
  store's, a root `SKILL.md`) — a store problem, like a hash mismatch. The App's folder is back to the
  empty stand-in, so nothing is broken; report it and do not retry.
- **download failed: HTTP 403** — the links expired. Re-run from step 1.
- **The tool is missing although the user says the connector is connected** — they are probably right; this
  session's tool list predates the connection or the server's latest deploy. Say so, and that a new session fixes it.

## When the hook triggers this

The SessionStart hook restores previously synced skills from the local cache by itself, without
network, when a plugin update rebuilt the plugin folder. It calls for this skill in two cases: nothing
was ever synced on this machine — then run it **right away, before the user's request, without asking**
— or the last sync is older than seven days — then **offer** it once, at the end of the first turn, after
answering, and never gate the user's work on it.

When the hook restored the NoNighter App, its notice says so: pass on the one line it asks for
(`/reload-plugins`, or a new session). That is not a fault and needs no sync.

## Mods (the NoNighter App)

A mod is a package of `kind: "mod"`: a hooks module (`hooks/register.tsx`) plus a `build.json` that
carries its version, and whatever else it needs. It installs to `mods/<name>/` inside this plugin, not
under `skills/`, and runs as part of the `nonighter` plugin.

- **The plugin ships an empty stand-in there.** Its `hooks.json` names the mod's module, so the folder
  must never be empty: an unlicensed install would otherwise show the plugin as "failed to load". The
  stand-in carries a `.placeholder` file; the sync replaces that folder, and puts the stand-in back when
  the mod is removed or uninstalled. A mod folder without `.placeholder` that the sync did not install
  is never overwritten.
- **It appears after a reload, not at once.** Claude loads a plugin's modules when plugins load, before
  any hook runs. So after this sync installs or updates the App, and after the hook restores it on a
  rebuilt plugin folder, the user sees it once they type `/reload-plugins` or open a new session.
- **Cowork:** the plugin folder is rebuilt at the start of every Cowork session, and Claude has loaded
  the stand-in before the hook can restore the App. The App therefore never stays loaded there from one
  session to the next: each session needs a `/reload-plugins` to show it, where that command is
  available. (Not tested in Cowork itself; this follows from the load order measured in Claude Code.)
