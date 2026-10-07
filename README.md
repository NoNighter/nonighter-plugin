# NoNighter plugin for Claude

Financial modeling in Excel with Claude: import financial statements from PDFs, and build operating
models and valuations with the modeling skill delivered to users with a NoNighter licence.

## Install

**Claude Desktop / Cowork:** Plugins → add marketplace from GitHub → `NoNighter/nonighter-plugin` → install
**NoNighter**.

**Claude Code (CLI):**

```bash
claude plugin marketplace add NoNighter/nonighter-plugin
claude plugin install nonighter@nonighter
```

Then authorise the **NoNighter** connector when Claude asks — it is how the plugin reaches NoNighter's
services and how your licence is checked. On the first session the plugin fetches the modeling skills
your licence includes; they appear in the skills list from the next session.

Requires Python on the machine (`py` on Windows, `python3` elsewhere).

## What is in the plugin

Three things, and deliberately nothing else:

| Piece | What it does |
|---|---|
| the connector | Reaches NoNighter's server, where your licence is checked |
| the session hook | Keeps your fetched skills in place, and prompts the first sync |
| `sync-skills` | Fetches the skills your licence includes, and installs them |

Everything else is **fetched, not shipped** — the modeling and presentation skills, the workstation
setup, the document import. Which ones you get is decided by the store and answered per licence, so
this repository does not name them and no change to the catalogue needs a change here. It also keeps
the sync honest: a skill delivered by licence must not also sit in the plugin, or the installer
refuses to overwrite it.

## Which environment this plugin talks to

`nonighter/.mcp.json` names the NoNighter server an installed copy uses, and it is the one thing here
that decides which environment a user's skills come from. **It points at `https://mcp.nonighter.com`
as of 2026-10-07** — production, with the skills service published behind it and every package
fetching and verifying.

It pointed at a test environment twice before: at dev until 1.0.2, and at qa until 1.0.4 while the
production half of the skills service was being stood up. The first of those lasted months, because
nothing checks this line and it was nobody's job to look. Nothing checks it now either — if it ever
changes again, it changes deliberately, and the version moves with it.

## Repository layout

```
.claude-plugin/marketplace.json   the marketplace (one plugin)
nonighter/                        the plugin
  .claude-plugin/plugin.json      manifest — its version is the marketplace's update signal
  .mcp.json                       the NoNighter MCP connector
  hooks/                          SessionStart: restores synced skills, hands over to the workstation
  skills/sync-skills/             the one skill that ships; the rest arrive by licence
```

## Versioning

`nonighter/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` carry one number. **Anything
that changes under `nonighter/` moves it**, because the marketplace compares only that number: a change
merged without a bump reaches no installed copy. A pull-request check enforces it.

## Licence

Proprietary — see `LICENSE`. The Plugin may be installed and read to use NoNighter's services; it may
not be copied, modified, redistributed or used with other services. The modeling skills it fetches are
licensed NoNighter content and are not part of this repository.
