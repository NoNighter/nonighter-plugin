---
name: workflow-autofill
description: |
  Index workbook sheets into a NoNighter workflow and autofill financial model
  concepts from that index. Use when the user asks to "index this workbook",
  "index these sheets for autofill", "autofill from my workflow", "look up
  concepts for this model", or "pull indexed values into this model".
---

# Workflow Autofill

Indexes spreadsheet data into a NoNighter workflow and looks up indexed concept
entries to autofill financial models, using the `workflow-concept-*`
connectors.

## Prerequisites

- The `nonighter` MCP connector must be available.
- A `workflow_id` identifying the workflow to index / look up. Ask the user for
  it (or the ID established earlier in the session) before calling either tool.

## Connectors used

| Tool | Purpose |
|------|---------|
| `mcp__nonighter__workflow-concept-index-submit` | Index sheet data into a workflow |
| `mcp__nonighter__workflow-concept-autofill-lookup` | Look up indexed entries for autofill |

## Workflow — Index sheets

### Step 1 — Gather the workflow id and sheets

Confirm the `workflow_id`. Decide which sheets to index and read their rows
from the workbook (e.g. via `execute_office_js`).

### Step 2 — Submit for indexing

Call `workflow-concept-index-submit` with `workflow_id` and **either**:

- `input`: an array of `{ sheet_name, items[] }` (inline rows), **or**
- `input_s3_key`: an S3 key of pre-uploaded data.

Provide exactly one of the two, never both. Prefer `input` for workbook data
read in-session; use `input_s3_key` only when the data was already staged.

### Step 3 — Confirm

Report which sheets were indexed into the workflow.

## Workflow — Autofill lookup

### Step 1 — Look up concepts

Call `workflow-concept-autofill-lookup` with `workflow_id`. Optionally pass:

- `model_name`: filters results to that model's concept map and enriches each
  item with its `input_name`.
- `excluded_sheets`: comma-separated sheet names to exclude from results.

### Step 2 — Apply to the model

Map the returned concept entries (using `input_name` when `model_name` was
provided) to the target cells and write them with `execute_office_js`.

### Step 3 — Confirm

Summarize which concepts were autofilled and flag any the lookup could not
resolve for the user to fill manually.

## Error Handling

| Condition | Response |
|-----------|----------|
| Connector unavailable | Tell the user this requires the NoNighter MCP server; verify the `nonighter` connector is connected. |
| Missing `workflow_id` | Ask the user for the workflow id before calling either tool. |
| Both `input` and `input_s3_key` given | Send only one; drop the other and retry. |
| Empty lookup result | Confirm the workflow was indexed first (`index-submit`); check `model_name`/`excluded_sheets` filters. |
