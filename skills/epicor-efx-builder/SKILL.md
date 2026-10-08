---
name: epicor-efx-builder
description: Inspect, export, back up, modify, create, import, and verify Epicor Kinetic Function Libraries and EFX/EFXJ packages through Epicor MCP tools. Use for Function Library reviews, individual Epicor Function analysis, .efxj files, ExportEFX/ImportEFX, custom-code or signature changes, new functions, and promotion between Epicor environments.
---

# Epicor EFX Builder

This skill is self-sufficient: everything needed to author a **valid Epicor Function from scratch** is written into this skill and its bundled `references/` files — package JSON shapes, signature rules, the four reference types, the custom-code (Kind 2) C# idioms, and the visual (Kind 1) widget XAML grammar. You do **not** need an existing library as a template. Reading a live comparable function is an optional sanity check, never a prerequisite.

The templates use generic placeholders in `<...>`. Never paste secrets, URLs, tokens, company codes, connection strings, or proprietary method bodies into a new package or into this skill; supply real values only inside the target environment.

## Reference files (bundled with this skill)

The deep component detail lives in `references/`; section numbers are shared across this file and the references, so a cross-reference like "§5.3" always resolves. Read only the reference(s) a task needs.

- **[references/package-anatomy.md](references/package-anatomy.md)** — §3 package/library/function JSON shapes, field defaults, and a complete minimal valid package.
- **[references/signatures-and-dependencies.md](references/signatures-and-dependencies.md)** — §4 signatures & data types; §7 references, mappings, and the derive-from-code checklist.
- **[references/custom-code-functions.md](references/custom-code-functions.md)** — §5 Kind 2 C# idioms: BO calls, cross-library calls, Db/LINQ, REST, transactions, errors/logging, BAQ/report/scheduling, prohibited SQL.
- **[references/visual-functions.md](references/visual-functions.md)** — §6 Kind 1 XAML widget grammar: namespaces, node connection, the proven widgets, bindings, and types.
- **[references/pattern-index.md](references/pattern-index.md)** — a task → kind/widget/pattern decision guide (self-contained; names no libraries).
- **[references/mcp-file-transport.md](references/mcp-file-transport.md)** — connector file-transport requirements for Export/ImportEFX.

Sections §3–§7 live in those files; §0–§2 and §8–§11 are below.

## 0. Environment and governance

Work against the Epicor environment the user names. If none is named, ask before any write. Never infer that Testing content should be promoted to Production. State the environment and library immediately before an import.

Discover the connector's tools at runtime; do not assume the catalog is limited to the names below. Common Epicor MCP tools:

- `MCPToolsEfx-GetEpicorFunctionDefinition(iLibraryID, iFunctionID)` — read one function.
- `MCPToolsEfx-GetEpicorFunctionLibraryDefinition(LibraryID)` — read a whole library: metadata, functions, signatures, references, mappings.
- `MCPToolsEfx-ExportEFX(libraryID)` — export a full `.efxj` package (backup / raw-package inspection / migration).
- `MCPToolsEfx-ImportEFX(EFXData, LibarayID)` — import a package (force overwrite; note the tool's current parameter spelling `LibarayID`).
- `MCPToolsEfx-ValidateEFXCustomCode(iLibraryID, iFunctionID)` — run Epicor's native editor validation for one live Kind 2 function.
- `MCPToolsEfx-ValidateEFXWidgetFunction(iLibraryID, iFunctionID)` — run Epicor's native workflow validation for one live Kind 0/1 function; the wrapper converts stored XAML through `GetKineticFunction` first.
- `MCPToolsEfx-EnableEFXWithDiagnostics(iLibraryID)` — enable every function, enable the library, and regenerate through `ApplyChangesWithDiagnostics`; returns compiler exception details when regeneration throws.
- `MCPToolsEfx-EnableEFXForCompany(iLibraryID, iCompanyID)` — idempotently add or enable an `EfxLibraryMapping` row and verify the company is allowed.
- `request_file_upload(...)` — get a one-time upload target for file-typed tool inputs.

**Choose the smallest live read.** One function → `GetEpicorFunctionDefinition`. Enumerate/compare/verify a library → `GetEpicorFunctionLibraryDefinition`. Export only for backup, raw inspection, modification, creation, or migration. Treat a mismatched single-function response as a tool defect; cross-check `FunctionID` and body against the full library definition.

When summarizing a library, report metadata, functions and signatures, referenced libraries, referenced assemblies, custom code, dependencies, invalid/disabled state, and concrete risks. **Redact secrets in chat.**

---
## 1. Rule zero: preserve the live package

Before every import that can replace an existing library:

1. Read the live library definition.
2. Export the current library and download the complete `.efxj` out of band.
3. Validate it and retain an untouched, timestamped backup.
4. Record a structural snapshot with `scripts/efx_package.py snapshot` (if the script is present; otherwise keep the raw export).

Never import if the backup cannot be retrieved and validated. Epicor imports use **force overwrite** and provide no skill-level undo.

---
## 2. File transport (export / import)

Use connector-declared file transport, never prompt-sized Base64.

**Export**
1. Call `MCPToolsEfx-ExportEFX(libraryID=...)`.
2. The result field `EFXBae64` is an **off-band download**: a short-lived `downloadUrl` plus metadata (filename, `sizeBytes`, `contentType`), not inline Base64.
3. Download it with a direct HTTP GET (`curl -o <LibraryId>.efxj "<downloadUrl>"`), then validate the file. Do not echo or relay Base64.

If the call returns inline Base64, stop before modifying or importing; the connector metadata needs updating (ExportEFX must expose `EFXBae64` as an off-band download, not an inline string).

**Import**
1. Call `request_file_upload` for tool `MCPToolsEfx-ImportEFX`, param `EFXData`, filename `<LibraryId>.efxj`, contentType `application/json`.
2. Upload the exact file bytes to the returned `uploadUrl` with a direct HTTP PUT (`curl -T <file> "<uploadUrl>"`).
3. Call `MCPToolsEfx-ImportEFX` passing the returned one-time `fileRef` as `EFXData` and the target as `LibarayID` (current spelling).
4. Request a fresh `fileRef` for every retry.

If `EFXData` is exposed as a normal string rather than a file input, stop; never inline the package or send a truncated library.

**Import result parsing.** `MCPToolsEfx-ImportEFX` returns structured results. A clean import returns `Success: true` with `Log` = JSON `{Success:true, Result:{BOUpdErrorTableset...}}`. An import exception returns `Success: false` with `Log` = JSON containing an `Exceptions` array (each type + message in the inner-exception chain). Parse `Log` as JSON and summarize only the useful, non-sensitive messages. A compilation failure does **not** arrive as an MCP HTTP 500; it can still import and disable the library while returning a clean `Success:false`. Transport/auth/file-resolution failures may surface as tool errors instead.

---

---

## 8. Build a new function from scratch — procedure

1. **Decide the kind.** Custom code (Kind 2) unless the user needs a visual/widget function; branching favors Kind 2 or a CustomCodeAction widget.
2. **Define the signature** ([§4 signatures](references/signatures-and-dependencies.md)): name every input (`Response:false`) with an `i` prefix and every output (`Response:true`) with an `o` prefix; also require unique `ParameterID`/`Order` per direction, the correct `DataType`, and `DataTypeInfo` for any tableset. Preserve untouched legacy signatures during an unrelated edit, but apply the prefix rule to every argument you create or rename.
3. **Write the body** ([§5 custom code](references/custom-code-functions.md) for code, [§6 visual functions](references/visual-functions.md) for visual), binding inputs/outputs by their declared `ArgumentName` (assign every output on every path), following the success-bool + message-string return pattern ([§5.7 custom code](references/custom-code-functions.md)) using the names the signature actually declares.
4. **Reconcile references and flags** ([§7.3 references](references/signatures-and-dependencies.md)): add every type-0/1/2/3 reference the body implies, set `DirectDBAccess`, `AllowCustomCode*`.
5. **Assemble the package** ([§3 package anatomy](references/package-anatomy.md)): put the function into `Library.Functions`, or start from the [§3.4 package anatomy](references/package-anatomy.md) minimal package for a new library. Give a new library a fresh `GlobalID`; keep it `Published:false` while drafting. Serialize with a UTF-8 BOM.
6. **Validate** (§9), including the native validator appropriate to each live function kind when the function already exists.
7. **Import into Testing first** whenever the shape is new or promotion is requested; then verify (§10) before Production.

Preserve IDs and fields whose semantics are not understood. Do not claim a new structural pattern is supported merely because JSON/XML validation passes — validity is necessary, not sufficient; only a Testing compile proves it.

---
## 9. Validation and pre-import gate

If `scripts/efx_package.py` is present, use it: `validate` (checks the UTF-8 BOM on the file, unresolved `<...>` placeholder values, top-level fields, unique non-empty FunctionIDs, unique ParameterID/Order per direction, letters-and-digits-only ArgumentNames, parseable bodies per kind, optional `--library`/`--count`/`--target`; add `--enforce-io-prefixes` for a new library or when every signature in the package is governed by the prefix rule), `snapshot` (structural hashes), `diff before after` (changed JSON paths), `add-code-comment` (safe leading comment without hand-escaping), and `scaffold --library <Id> [--function <Fn>] [--kind 0|1|2] [--company <C>] [--owner <U>]` (emit a minimal valid package with narrowest flags and `i*`/`o*` arguments). If the script is absent, validate manually against [§3 package anatomy](references/package-anatomy.md)–[§7 references](references/signatures-and-dependencies.md) (including a first-three-bytes BOM check and a grep for leftover `<...>` placeholders).

**What `validate` does and does not prove.** It proves the package is well-formed and import-shaped: file BOM present, no `<...>` placeholders, JSON shape, unique IDs/orders, and that each body parses (Kind 2 → `{Code,Usings}` JSON; Kind 1 → XML rooted at `DirectiveDefinition2`). It does **not** compile the C#, prove that a widget's XAML actually deserializes in Epicor, verify a BO method/field name exists, confirm every `Db`/BO/EfxLib use has a matching reference, or check that a `Company` predicate is present. `valid:true` is necessary, never sufficient — only a **Testing import** proves a body compiles. So for any new C# body, new visual graph, or new structural shape, import into Testing and verify (§10) before Production.

**Native validation workflow.** These tools validate functions already present in the target environment; they do not accept an unimported package body.

1. Run local package validation first.
2. For an existing Kind 2 function, call `MCPToolsEfx-ValidateEFXCustomCode`. Treat `oSuccess:false` as a failed gate. Parse `oLog.Validation.diagnostics`; report `Code`, `Message`, `File`, and `Span.start.line/column`. A clean result has `diagnostics:null` or an empty collection.
3. For an existing Kind 0/1 function, call `MCPToolsEfx-ValidateEFXWidgetFunction`. Treat `oSuccess:false` as a failed gate. Parse `oLog.Validation.BpValidation`; report each row's `Severity`, `Text`, `Element`, and `ElementId`. Severity 3 is informational success; the wrapper treats severity 0 or 1 as critical/error.
4. Do not call the custom-code validator for Kind 0/1 or the widget validator for Kind 2. If the kind is unknown, read the function or library definition first.
5. For a new function that is not live yet, import only into Testing. A failed import may intentionally leave it disabled. Then run the kind-specific validator against that disabled function to obtain actionable diagnostics; correct the local package and request fresh import authorization before retrying.
6. After import, use `MCPToolsEfx-EnableEFXWithDiagnostics` when the library or any function is disabled, or when an enabled-state regeneration is part of acceptance. It mutates live state: it clears function `Disabled`/`Invalid`, clears library `Disabled`, and calls `ApplyChangesWithDiagnostics`. Treat it as a write requiring authorization. On failure, parse `Exceptions[].Properties.ExceptionMessageList[].Properties.Errors`; this contains compiler filename, line, column, code, and message. Do not rely only on the generic `CompilationException.Message`.
7. Stop and report diagnostics before another import. Never loop import/enable attempts automatically.

**Pre-import gate — require all:** valid UTF-8 JSON with the preserved UTF-8 BOM; no unresolved `<...>` placeholder literals in any field (`GlobalID`, `OwnedByCompany`, `Owner`, mapping companies, etc. filled with real target-environment values); real `Version`/`EpicorVersion` for the target; required top-level fields; expected `LibraryId` and function count; unique FunctionIDs; unique ParameterID/Order per direction; every `ArgumentName` letters and digits only (a-z, A-Z, 0-9), starting with a letter; every newly created or renamed input begins with `i` and output begins with `o`; parseable bodies appropriate to each `Kind` (Kind 2 → JSON `{Code,Usings}`; Kind 1 → XML rooted at `DirectiveDefinition2`); exactly one target for a modification; only intended changed paths; every reference the body implies present and flags scoped per [§7.3 references](references/signatures-and-dependencies.md); a complete package; a validated untouched backup; a reviewed secret scan; no newly introduced direct-SQL pattern; explicit write authorization; a clear environment. Abort on any failed gate; do not loosen validation to make an import succeed.

---
## 10. Post-import verification

Treat the import result as advisory, not proof of live state. After every import response, re-read and export the live library before declaring success, failure, or retrying. Confirm the exact change; function/signature/reference counts; target signatures; mappings; referenced libraries and assemblies; and all unchanged function bodies. Run the kind-specific native validator for each changed function. If anything is disabled, use `EnableEFXWithDiagnostics` only with explicit write authorization, then re-read the final state.

When the imported library must be available to one or more companies, compare the requested company IDs to live `EfxLibraryMapping` rows. With explicit write authorization, call `EnableEFXForCompany` once per missing or disallowed company. Treat `Available:true` as the acceptance condition. `Created:true, Changed:true` means a mapping was added; `Created:false, Changed:false` means it was already available. Re-read the library and confirm each requested mapping has `Allowed:true`. Do not invent company IDs or automatically enable every tenant company.

A compilation failure can still import the package and **disable** the library and its functions while `ImportEFX` returns a clean `Success:false`. Never retry the failed package automatically. Inspect live state immediately; if the library was changed or disabled, restore the validated pre-import backup unless the user explicitly asked to keep the failed state for diagnosis. Re-read the restored library and verify it is enabled, valid, and structurally identical to the backup.

---
## 11. Sensitive content

EFX code can contain credentials. Keep exports and backups private, never paste full packages into chat, redact suspected tokens/passwords/connection strings, and show only the minimum code needed for review. Do not store secrets or proprietary method bodies in this skill or its references. Do not normalize, reformat, or replace secrets during unrelated edits.
