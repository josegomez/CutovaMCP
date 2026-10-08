---
name: epicor-baq-builder
description: Create, modify, clone, export, import, and inspect Epicor Kinetic BAQs (Business Activity Queries) using the Lens MCP tools. Use this skill whenever the user mentions BAQs, .baq files, ExportBAQ/ImportBAQ, building a query in Epicor, converting a SQL statement into a BAQ, adding tables/joins/criteria/parameters/calculated fields to a query, cloning a BAQ, updatable BAQs (UBAQ), or migrating queries between Epicor environments — even if they just say "make me a query that shows X from Epicor" without saying the word BAQ.
---

# Epicor BAQ Builder

Build and modify Epicor Kinetic BAQs programmatically. A BAQ is Epicor's stored, designer-managed query: it lives in the database as rows across a family of `Ice.Query*` tables, exports as a `.baq` file (a plain ZIP), and can be re-imported under any name. This skill was validated end-to-end on a live Kinetic 2025+ system: exporting, cloning, and authoring brand-new multi-table BAQs from a SQL spec, first try.

If you have never seen a BAQ before, that is fine — read `references/baq-anatomy.md` and you will know exactly what every row means. This file covers the workflow; the references cover the object in full detail.

## Rule zero: back up before any import

Before ANY ImportBAQ call that could touch an existing query, export the current version and save an untouched copy (e.g. `backups/<BAQID>_ORIGINAL_<date>.baq`). Imports overwrite silently and there is no undo. This applies even when "just renaming" — a typo in the BAQID parameter can overwrite the wrong query. Never skip this; tell the user where the backup is.

## The tools

| Tool | What it does |
|---|---|
| `MCPBaq-ExportBAQ` (param `baqID`) | Exports a BAQ. Returns a **download URL** (not inline data) — fetch it with curl/requests. |
| `MCPBaq-ImportBAQ` (params `BAQData`, `BAQID`, `GsmUserOverwritesAnothersQuery`) | Imports a .baq file. `BAQData` is a **fileRef** from `request_file_upload` (see upload flow below). **`BAQID` alone performs a rename** — you do NOT need to edit QueryID inside the XML; the server rewrites everything, including company/BAQID embedded in UBAQ BPM method codes. |
| `MCPBaq-GetBAQDefinition` (param `BAQID`) | Returns the full definition as structured data. Use to confirm a BAQ exists before export and to **verify every import**. |
| `MCPBaq-GetUBAQBpm` (param `BaqID`) | BPM directives attached to an updatable BAQ. |
| `zDataTable` | Data-dictionary table list (DataTableID, SchemaName, DBTableName, type, restrictions). |
| `zDataFields` (params `SystemCode`, `DataTableID`) | Fields of one table: name, data type, format, label. SystemCode values in data are uppercase (`ERP`, `ICE`). |
| `zDataRelationships` (params `ParentSystemCode`, `ParentTableID`, optional child params) | System foreign-key joins, **one row per join field pair** — maps 1:1 onto QueryRelationField rows. Use it to get correct join conditions; dedupe repeated pairs. |

The BAQ tools live in the **MCPBaq** function library (tool names `MCPBaq-ExportBAQ`, `MCPBaq-ImportBAQ`, `MCPBaq-GetBAQDefinition`, `MCPBaq-GetUBAQBpm`). In environments running an older Lens MCP configuration they may still appear under the legacy `MCPTools-` prefix — same parameters and behavior; match by suffix when searching for tools.

These are OData-style BAQ tools: before using their `filter`/`select` params, call `describe_baq_fields` with the tool name to get exact field names.

The three zData* tools are backed by BAQs that must exist in the Epicor environment. If they are missing (tool returns not-found), their definitions are bundled in `assets/zDataTable.baq`, `assets/zDataFields.baq`, `assets/zDataRelationships.baq` — import each with ImportBAQ under its own name to bootstrap schema discovery.

## Export flow

1. `ExportBAQ` with the BAQ ID → response contains `downloadUrl`.
2. Download out-of-band: `curl -so file.baq "<downloadUrl>"` (URL expires in ~15 min).
3. **Verify the download is the right BAQ** — check the `<QueryID>` inside DynamicQuery matches what you asked for (a wrong artifact has been served once in practice).
4. Save the backup copy immediately.

## Import flow

1. `request_file_upload` (tool=`MCPBaq-ImportBAQ`, param=`BAQData`) → returns `uploadUrl` + `fileRef`.
2. `curl -sS -T file.baq -H "Content-Type: application/octet-stream" "<uploadUrl>"` — expect HTTP 200.
3. `ImportBAQ` with `BAQData=<fileRef>`, `BAQID=<target name>`. Use a NEW BAQID unless the user explicitly wants to overwrite.
4. **Always verify**: `GetBAQDefinition` on the new BAQID; confirm tables, joins, fields, and criteria landed.

## The .baq file

A `.baq` is a standard ZIP (deflate), flat entries, no folders:

| Entry | Content | Present |
|---|---|---|
| `BAQVersion` | version string, e.g. `5.1.100.0` | always |
| `DynamicQuery` | **the query definition** — a .NET DataSet XML: embedded `xs:schema` + one element per DB row | always |
| `DynamicQueryDesign` | designer canvas layout (bzip2 blobs). Cosmetic — never edit, safe to leave stale | always |
| `QueryDependencies` | empty in every specimen observed | usually |
| `version` + `BpMethodDataset` | UBAQ method/BPM directive data | only updatable BAQs with BPM |

Inside `DynamicQuery`, data rows follow the schema as sibling elements of the root `<BAQDesignerDataSet>`: one `<DynamicQueryDesigner>` header, then `<QuerySubQueryDesigner>`, `<QueryTableDesigner>`, `<QueryFieldDesigner>`, `<QueryRelationDesigner>`, `<QueryWhereItemDesigner>`, etc. Every row type, every field, and every pattern (joins, criteria, parameters, calculated fields, subqueries, CTEs, unions, group-by, IN-lists, UBAQ, external BAQs) is documented with real examples in **`references/baq-anatomy.md`** — read it before constructing or editing rows.

Calculated-field formulas are plain T-SQL plus two extensions (`{SubQueryName}` scalar refs and `Constants.<Name>`); the function/constant catalog is in **`references/formula-language.md`**.

## Workflow A — Inspect / understand a BAQ

`GetBAQDefinition` is usually enough. For UBAQs also call `GetUBAQBpm`. Export only when you need the raw XML or a backup.

## Workflow B — Clone or modify an existing BAQ

1. Export + backup (rule zero).
2. Unzip; edit `DynamicQuery` as text or via ElementTree.
3. To clone under a new name, do NOT edit QueryID in the XML — just pass the new name as `BAQID` on import.
4. For content edits (add a field, change a formula, add criteria): construct rows per `references/baq-anatomy.md`, matching the element order in the file's own embedded `xs:schema`.
5. Re-zip the same entry names flat, upload, import, verify.

## Workflow C — Author a new BAQ from scratch (proven recipe)

Never generate the XML from nothing. Start from the bundled seed: **`assets/BasicBAQ_template.baq`** — a minimal valid BAQ (one TopLevel subquery, the mandatory `Calculated` pseudo-table row, one table, one field). Then:

1. **Discover schema**: `zDataTable` to confirm table names/schemas → `zDataRelationships` for join field pairs → `zDataFields` for each display field's data type and format.
2. **Build**: run/adapt **`scripts/build_baq.py`** — it strips the template's seed table/field rows and splices in your tables, joins, fields, criteria, group-bys and value sets with correct element order. It encodes every hard-won gotcha (CRLF, XML escaping, schema ordering).
3. Zip → upload → `ImportBAQ` with the new BAQID → **verify with `GetBAQDefinition`**.

You only need the structural minimum: **the server hydrates minimal rows from the data dictionary on import** — it fills in field descriptions, formats, captions, Like references, Required/BizType attributes, and recognizes `_c` user-defined columns automatically. Don't waste effort supplying metadata the dictionary already knows.

Translating a SQL statement into a BAQ? A complete worked example (4 tables, cross-schema join, UD field, IN-list, GROUP BY) is in **`references/worked-example.md`**.

## Gotchas (all hit in practice)

- The DynamicQuery XML uses **CRLF** line endings and may start with a BOM. Regex with `\r?\n`; open with `encoding='utf-8-sig'`, write back with `newline=''`.
- **XML-escape values**: a `<>` comparison operator written raw breaks the file. Use `xml.sax.saxutils.escape`.
- Element order inside each row must follow the embedded `xs:schema` sequence. Extract it programmatically (build_baq.py does).
- **`QueryField.Seq` must be unique per subquery** (regular + calculated fields share one sequence). Duplicates import cleanly but corrupt the designer's field ordering. Adding a field to an existing BAQ = scan existing Seqs (incl. calc fields), use max+1. build_baq.py validates this at build time.
- Omit `SysRevID`/`SysRowID` in new rows — the server regenerates all of them. New GUIDs are only needed for `RelationID`, `CriteriaID`, `GroupByID`, and value-set IDs.
- The `DisplayPhrase` header field is a generated SQL *preview* — informational only, stays stale after import, and contains field names (don't string-match against the file naively).
- Some `unzip` CLI builds complain about these archives; Python `zipfile` reads and writes them cleanly.
- UD fields (`_c` suffix) live in `<Table>_UD` (metadata via `zDataFields` on `<Table>_UD`). **Always include the hidden `_UD` extension table** (`TableType=UD`, `IsVisibleInDesigner=false`, Seq 101+, FK join `SysRowID = ForeignSysRowID`) and reference every `_c` field through it — display AND join usage. Referencing `_c` on the base table imports fine and even runs in the BAQ Designer (which auto-attaches `_UD`), but FAILS at layer/grid runtime with `Invalid column name 'X_c'` because ExecuteBaq does not auto-attach. Full recipe in the anatomy reference, section 5.
- `CriteriaType` on criteria: 2 = Table Criteria (normal case), 0 = SubQuery Criteria (calculated fields, cross-table OR), 1 = HAVING. `Seq`/`AndOr` chains restart per collection — the first criterion of each table's set AND of the subquery set must have empty `AndOr`. A wrong value imports "successfully" but renders broken in the designer, so verify placement.
- Upload `fileRef`s are **single-use** — request a fresh one for every ImportBAQ attempt, including retries.
- `ImportBAQ` returns `{"Success": false}` (no error message) when the target BAQID **already exists** and `GsmUserOverwritesAnothersQuery=false`. Despite its name, the flag gates overwriting ANY existing BAQ — including your own (verified by re-importing an identical file: false → failed, true → succeeded). So: new BAQID → flag false; intentional overwrite → **back up the existing BAQ first (rule zero), then flag true**. Never flip the flag to true just to make an error go away — confirm the user wants the overwrite.
- Subquery-as-table references: `DBTableName` = the target's **bare SubQueryID GUID** (never a dotted/decorated form), alias a CTE reference with the CTE's exact Name, and make the SQ table the **child** side of any join. Getting these wrong still imports "successfully" — the failure only appears when the query runs.
- **A successful import is NOT a working query.** GetBAQDefinition proves structure, not executability. For anything beyond simple single-table queries — especially subquery/CTE/union references — ask the user to Analyze/execute in the BAQ Designer (or run the BAQ) as the final verification, and expect to iterate on designer errors.

## Naming & safety conventions

- New/experimental BAQs: use a clearly-marked test name (e.g. a `-TEST` or `-COPY` suffix). Ask if unsure.
- Leave `GsmUserOverwritesAnothersQuery=false` unless the user explicitly wants to take over someone else's query.
- Report what was created, where the backup is, and the verification result.
