---
name: import-to-excel
description: |
  Import data from PDFs and images into Excel. Use when the user asks to
  "import this PDF", "extract the table from this document", "pull the
  financials from this report", "parse this PDF into Excel", "import financial
  statements", "OCR this image into a table", or "extract data from a file".
---

# Import to Excel

Extracts structured tables from PDFs and images using NoNighter's import
connectors and writes them into Excel worksheets.

## Prerequisites

- The `nonighter` MCP connector must be available.
- The source must be a PDF file (path/bytes) or an image (for OCR).

## Connectors used

PDF pipeline (`mcp__nonighter__import-document-*`):

| Tool | Purpose |
|------|---------|
| `import-document-create-upload` | Get a presigned S3 URL for the PDF |
| `import-document-submit` | Start async processing → returns `document_id` (`pdfext_...`) |
| `import-document-status` | Poll until the job leaves `PENDING`/`PROCESSING` |
| `import-document-list-tables` | List detected tables (`mode=auto`) |
| `import-document-get-table` | Fetch a table's normalized cells (`dto`) when `READY` |
| `import-document-transform-table` | Transform a quick table on demand (e.g. `statement_type=other`) |
| `import-document-get-index` | Detected PDF index (table of contents), when available |
| `import-document-jobs` | List previous imports so a file need not be re-uploaded |

Image OCR pipeline (`mcp__nonighter__import-image-*`):

| Tool | Purpose |
|------|---------|
| `import-image-upload` | Upload base64 image bytes → returns `item_id` |
| `import-image-process` | Run OCR on the `item_id` → extracted cells |
| `import-image-retrieve` | Re-fetch a previous OCR result + preview URL |

## Workflow — PDF

### Step 0 — Reuse if already imported

If the user refers to a document they imported before, call
`import-document-jobs` and reuse its `document_id` instead of re-uploading.
Jump to Step 4.

### Step 1 — Upload the PDF

1. Call `import-document-create-upload` with `file_name` (must end in `.pdf`).
2. `PUT` the raw PDF bytes to the returned `upload_url` with header
   `Content-Type: application/pdf`.
3. Keep the returned `upload_id` and sanitized `file_name`.

### Step 2 — Submit for processing

Call `import-document-submit` with `upload_id` and `file_name`. Save the
returned `document_id` (`pdfext_...`).

### Step 3 — Poll until ready

Poll `import-document-status` with the `document_id` until the status leaves
`PENDING`/`PROCESSING`. Surface progress counts to the user while waiting; do
not proceed until tables are available.

### Step 4 — Discover tables

Call `import-document-list-tables` with `mode=auto`. Optionally call
`import-document-get-index` for the PDF's table of contents. Present the
detected tables (title, `statement_type`) and confirm which ones the user
wants.

### Step 5 — Fetch cells

For each chosen table call `import-document-get-table`. If a quick table is not
transformed yet (`transform_status` ≠ `READY`, common for
`statement_type=other`), call `import-document-transform-table` first, then read
the returned `dto` (normalized cells).

### Step 6 — Write to Excel

Use `execute_office_js` to write the `dto` cells into the target worksheet with
headers and formatting. One sheet per table unless the user asks otherwise.

### Step 7 — Confirm

Summarize what was imported (rows, columns, sheet name) and flag any cells the
extraction marked low-confidence.

## Workflow — Image (OCR)

1. `import-image-upload` — pass the base64 image bytes (no `data:` prefix) and
   `file_type`. Save the `item_id`.
2. `import-image-process` — run OCR on the `item_id`; read the returned cells.
   (`import-image-retrieve` re-fetches a prior result.)
3. Write the cells to Excel with `execute_office_js` (Steps 6–7 above).

## Error Handling

| Condition | Response |
|-----------|----------|
| Connector unavailable | Tell the user the import tools require the NoNighter MCP server; verify the `nonighter` connector is connected. |
| Upload PUT fails | Re-request a presigned URL with `import-document-create-upload` (URLs expire) and retry the PUT. |
| Status stuck / `FAILED` | Report the failed job status; suggest re-uploading or a different source PDF. |
| No tables detected | Show the index/`list-tables` result and ask the user to point to a specific page or table. |
| Table not `READY` | Call `import-document-transform-table` before `get-table`. |
| Unsupported format | Only PDFs (`import-document-*`) and images (`import-image-*`) are supported; ask the user to convert the file. |
