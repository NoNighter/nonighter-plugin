# NoNighter plugin for Claude

Financial modeling in Excel with Claude: import financial statements from PDFs, and build 3-statement
models, DCF valuations, scenario managers and football-field summaries — the modeling skills are
delivered to users with a NoNighter licence.

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

| Skill | What it does |
|---|---|
| `import-to-excel` | Import tables from PDFs and images into Excel |
| `workstation-init` | Set up a folder so Claude remembers how you work there — conventions, memory, context |
| `sync-skills` | Fetch the modeling skills your licence includes |

Fetched by `sync-skills` for licensed users: `3-statement`, `dcf`, `scenario-manager`, `football-field`.

## Repository layout

```
.claude-plugin/marketplace.json   the marketplace (one plugin)
nonighter/                        the plugin
  .claude-plugin/plugin.json      manifest — its version is the marketplace's update signal
  .mcp.json                       the NoNighter MCP connector
  hooks/                          SessionStart: loads the workstation, restores synced skills
  skills/                         the three skills above
```

## Versioning

`nonighter/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` carry one number. **Anything
that changes under `nonighter/` moves it**, because the marketplace compares only that number: a change
merged without a bump reaches no installed copy. A pull-request check enforces it.

## Licence

Proprietary — see `LICENSE`. The Plugin may be installed and read to use NoNighter's services; it may
not be copied, modified, redistributed or used with other services. The modeling skills it fetches are
licensed NoNighter content and are not part of this repository.
