---
name: concept-value-lookup
description: |
  Look up the numeric value of an indexed financial concept for one or more
  years, from tables extracted out of imported PDFs. Use when the user asks
  "what was [concept] in [year]", "revenue of [company] in 2023", "how much
  [concept] across these years", "get the value of [concept] from the index",
  "compare [concept] over 2022-2024", or otherwise wants the *value* (not just
  the location) of a concept the NoNighter index already resolved.
---

# Concept Value Lookup

Answers "what was the value of concept X in year Y?" by joining two NoNighter
connectors: the Workflow Concept Index (which knows **where** a concept lives)
and the imported PDF table (which holds the **values**).

The index resolves every extracted PDF concept to a catalog concept and records,
for each one, its source `table_id` and its position (`row`, `column`) inside
that table. The value for a given year is simply the table cell at
*(concept's row × that year's column)*. This skill looks the concept up, fetches
its table, and reads the cell(s).

## Prerequisites

- The `nonighter` MCP connector must be available.
- The concept must already be indexed from an **imported PDF** (`source=pdf`).
  If the document has not been imported yet, run the `import-to-excel` skill
  first, then come back. Excel-sourced index rows (`source=excel`) have no
  `table_id`; their values live in the user's live workbook, not in a PDF table,
  so they are out of scope here.

## Connectors used

| Tool | Purpose |
|------|---------|
| `mcp__nonighter__workflow-concept-autofill-lookup` | Find where a concept is indexed. Accepts an optional `concept_query` (coarse concept/alias pre-filter). Returns each resolved concept with `catalog_id`, `concept`, `alias`, `source`, `table_id`, `sheet_name`, `row`, `column`, `file_name`, and (in cross-workbook mode) its `workflow_id`. |
| `mcp__nonighter__import-document-get-table` | Fetch the source table's normalized cells (`dto`) so the values can be read. |
| `mcp__nonighter__import-document-list-tables` | Fallback only — locate the table by `sheet_name` when a matched index row is missing `table_id`. |

## Key facts about the data

- **A PDF document is the "workbook".** For `source=pdf` index rows, the
  `workflow_id` **is** the `document_id` (`pdfext_...`). With `document_id` +
  `table_id` you can fetch the exact source table.
- **The index `row` is the table's grid row.** The concept's `row` in the index
  is the same `row` value used in the table DTO cells, so it locates the concept
  line directly in the DTO.
- **The DTO is a flat list of cells.** `import-document-get-table` returns
  `dto.items`, a list of cell records like `{ "row": <int>, "column": <int>,
  "text": "<value>" }`, with the value columns already sorted left-to-right by
  year.
- **Year columns are a header row.** One row near the top holds the period
  labels (e.g. `2023`, `2024`, `Dec-23`) across the non-concept columns. Its
  cells map each value column to a year.
- **Values are as-reported.** A "-" / "–" / "—" cell is normalized to `0` in the
  DTO. Parentheses (e.g. `(1,234)`) mean negative. The magnitude scale
  (thousands / millions) and currency are usually stated in the table
  title/subtitle — surface it, don't silently rescale.

## Workflow

### Step 1 — Gather the request

Identify from the user (ask only for what's missing):

- the **concept** (they may give the catalog concept name or their own label /
  alias — either works);
- the **year(s)** wanted (one or several);
- optionally a **company / document** to scope the search.

**Same-session document → always scope to it.** If the user imported/indexed a PDF
earlier in this conversation (via `import-to-excel`) and is now asking about *that*
document, reuse its `document_id` (`pdfext_...`) as `workflow_id` and go straight to the
scoped lookup — do **not** ask again or re-list `import-document-jobs`. (For a PDF there is
no separate "index" step: importing it is what indexes its table concepts.)

> **Indexing is asynchronous.** The index is populated by a background worker a few seconds
> after a table transforms, so a scoped lookup done *immediately* after import may return
> few or no rows. If a scoped lookup for a just-imported document comes back empty, wait a
> few seconds and retry once or twice before concluding the concept isn't there.

### Step 2 — Locate the concept in the index

Call `workflow-concept-autofill-lookup`:

- **Scoped (preferred when a document is known):** pass `workflow_id = <document_id>`.
  Get the `document_id` from the current session or by listing
  `import-document-jobs` and picking the right PDF.
- **Cross-workbook:** call it with **no** `workflow_id` to search every workbook the
  user has indexed. Use it when they don't name a document. An omitted `workflow_id`
  is routed to the collection route, which reads every resolved concept for the
  authenticated user, and each returned item then carries its own `workflow_id` (the
  source document). This mode is unbounded — with no `concept_query` it returns every
  concept the user has ever indexed — so pass one, and see below for what to do when the
  filter leaves nothing.

Pass `concept_query` with the user's concept text (e.g. `concept_query="revenue"`) on
either path. It is a **coarse server-side pre-filter** (normalized substring match on
`concept`/`alias`) that shrinks the response, and it is intentionally lenient: use a short,
distinctive token (a single word like `"revenue"` or `"assets"` beats a long phrase), and
still do the final matching yourself (step below).

**When a pre-filtered lookup comes back empty**, the concept is probably phrased
differently from the catalog text — but how to widen the search depends on the path.

- **Scoped:** retry **without** `concept_query` and match client-side. One document's
  concepts are a bounded response.
- **Cross-workbook:** retry with a *different* token — a shorter or more distinctive one.
  If that still comes back empty, identify the document with `import-document-jobs` and
  **switch to the scoped lookup**, where dropping `concept_query` is safe. Never call
  cross-workbook without `concept_query`: unfiltered, it returns the user's entire index.

From the returned `items`, keep the ones that:

1. match the requested concept — compare case-insensitively against both
   `concept` and `alias`; prefer an exact match, then a contains match; and
2. have `source == "pdf"` with a non-null `table_id`.

Then:

- **One match** → continue with its `table_id`, its `document_id` (the row's
  `workflow_id` in cross-workbook mode, or the `workflow_id` you passed), and its
  `row`.
- **Several matches** (same concept in different documents/tables) → show the
  candidates (`file_name`, `sheet_name`, `concept`) and ask the user which one,
  unless they clearly meant all of them (e.g. "compare across my reports").
- **No match** → see Error Handling.

### Step 3 — Fetch the source table

For the chosen match, call `import-document-get-table` with its `document_id`
and `table_id`. Read `dto.items` (the cell list).

### Step 4 — Map the year columns

Scan `dto.items` for the **header/period row**: the row whose non-concept cells
are mostly date-like (years / month-year labels). Build a map of
`column → year` from that row's cells. Note which columns are *not* periods
(e.g. a "% change" or "Notes" column) and ignore them.

### Step 5 — Read the value(s)

The concept's line is the DTO cells with `row == <index row>`. For each
requested year, read the cell whose `column` is that year's column; its `text`
is the value.

- Apply sign: parentheses → negative; a normalized `0` cell means the source
  showed a dash.
- If a requested year has no column in this table, say so (and list the years
  the table does cover).

### Step 6 — Answer with provenance

Report the value per year, and always cite where it came from: `file_name`, the
table title / `sheet_name`, the page, and the cell. State the scale/currency
from the table title/subtitle if present.

> Example: *"Total Sales (your label: 'Revenue') — 2023: 1,234; 2024: 1,410.
> Source: `acme_10k.pdf`, "Income Statement" (p.3), figures in USD thousands."*

## Fallback — matched row without `table_id`

Older index rows (indexed before `table_id` was exposed) may come back with a
null `table_id`. To recover it:

1. Call `import-document-list-tables` with the row's `document_id` (`mode=auto`).
2. The index row's `sheet_name` is built as `"<table title> - p<page>.<page_table_index>"`.
   Find the table whose `title`, `page_number`, and `page_table_index`
   reconstruct that `sheet_name`.
3. Use that table's `table_id` and continue at Step 3.

If it still can't be resolved, tell the user the concept is indexed but its
source table can't be located, and suggest re-importing / re-indexing the PDF.

## Error Handling

| Condition | Response |
|-----------|----------|
| Connector unavailable | Tell the user this requires the NoNighter MCP server; verify the `nonighter` connector is connected. |
| Concept not found in the index | The PDF may not be imported/indexed yet — suggest the `import-to-excel` skill. Also retry with the other of concept/alias, and broaden to cross-workbook (no `workflow_id`) if a scoped lookup was empty. |
| Match is `source=excel` (no `table_id`) | This skill reads PDF-extracted values. For Excel-indexed concepts the value is in the live workbook — use `workflow-autofill` / read the sheet instead. |
| `get-table` fails or table not `READY` | The table may still need transformation; report the table's `transform_status` and suggest transforming it (see `import-to-excel`) before retrying. |
| `get-table` returns a DTO-retrieval error (e.g. `NoSuchKey`) | The table's DTO asset isn't in the environment the connector points at — index rows and S3 assets can live in different environments. Report it plainly; values can't be read until the document is (re)processed in the connector's own environment. |
| Requested year not in the table | List the periods the table actually contains and ask which to use. |
| Multiple concept matches | Disambiguate by `file_name` / `sheet_name` before reading values. |
