---
name: sync-skills
description: Fetch and install the NoNighter skills the user's licence includes — the financial-modeling skills — into this plugin, from NoNighter's store through the MCP. Use when the SessionStart hook says the skills were never synced on this machine or the last sync is stale, or when the user asks to "sync my skills", "actualizar mis skills", "update my NoNighter skills", "why don't I have the DCF skill". Not the workstation installer — that is workstation-init.
---

# sync-skills

The plugin you installed is a shell. The skills that do the modeling — `3-statement`, `dcf`,
`scenario-manager`, `football-field` — are fetched here, once per machine and again whenever a new
version is published, for users with an active NoNighter licence. Nothing is stored about the user, no
credential is kept: the MCP authenticates, the packages download straight from S3 through links that
expire in about 15 minutes.

## Procedure

1. **Ask the store.** Call the MCP tool `skills-provision` with no arguments. It is served by NoNighter's
   MCP server, which may appear in this session under more than one name — the plugin's own `nonighter`
   connection, or a `nonighter`/`nonighter-dev` connector the user added to their account. **Any of them
   is fine: look for the tool by name across every connected NoNighter server.** It answers with a
   manifest: a `skills` list of `{name, version, kind, sha256, size, url}`. Save that JSON, exactly as
   returned, to a temporary file (`manifest.json` in the session's scratch folder is fine).
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

4. **Report in one or two lines, in the user's terms.** "Your NoNighter modeling skills are installed:
   3-statement, DCF, scenario manager, football field." Then the one fact that matters:
   **they show up in the skills list from the next session.** If the user asks for modeling work *in
   this session*, do not say the skill is missing: open `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`
   and follow it as if the skill had been invoked. Never quote paths, hashes, or the word "manifest".

## What the script refuses, and what to say

- **sha256 mismatch** — the download does not match what the store promised. Report it, do not retry
  blindly; it is a store problem, not a network one.
- **REFUSED … already ships in the plugin** — a downloaded package carries the name of a shell skill.
  Nothing is overwritten. Tell the user NoNighter has to rename that package.
- **download failed: HTTP 403** — the links expired. Re-run from step 1.
- **The tool is missing although the user says the connector is connected** — they are probably right; this
  session's tool list predates the connection or the server's latest deploy. Say so, and that a new session fixes it.

## When the hook triggers this

The SessionStart hook restores previously synced skills from the local cache by itself, without
network, when a plugin update rebuilt the plugin folder. It calls for this skill in two cases: nothing
was ever synced on this machine — then run it **right away, before the user's request, without asking**
— or the last sync is older than seven days — then **offer** it once, at the end of the first turn, after
answering, and never gate the user's work on it.
