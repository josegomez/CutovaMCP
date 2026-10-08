# Lens MCP Tools — Complete Reference for Layer Work

These are the live-Epicor tools you drive the whole round-trip with. **Parameter names are INCONSISTENT across tools** — the analysis/read tools use `AppName`/`LayerName`, the import/commit tools use `InID`/`InLayerName`. Passing the wrong name returns a generic HTTP 500 that looks like a server outage but is actually a malformed call. Verify the schema before every call.

Tool ids in your environment are prefixed (e.g. `mcp__<server>__MCPToolsKinetic-GetNativeKineticApp`); the short names below are what you'll recognize them by.

**Library consolidation (2026-09-08):** all layer-work Epicor Functions were copied into ONE library, `MCPToolsKinetic`, and this reference uses those names. The legacy libraries still exist and their functions are byte-identical: `MCPTools-*` (GetLayers, GetIndividualLayer, GetNativeKineticApp, GetCustomizationByID, GetBAQDefinition, GetUBAQBpm, GetEpicorFunction*), `MCPDashboard-GetClassicDashboardDefinition`, and `Kinetic-*` (ImportLayer, Commit, DeleteLayer). **If a session's connector does not yet expose the `MCPToolsKinetic-*` tool names, fall back to the legacy name with the SAME parameters** — the function bodies and signatures are identical (with `Kinetic.ImportLayer` also carrying the `InCompany` input as of the same date).

---

## 1. Reading the world (inputs)

### `MCPToolsKinetic-GetClassicDashboardDefinition`
Pull a **classic dashboard** definition to uplift. `{ "DashboardID": "<ClassicDefinitionID>" }` — returns an off-band download. This is the dashboard counterpart of `GetCustomizationByID` (which covers classic FORM customizations only). Full dashboard uplift playbook: `references/dashboards.md` (§D).

### `MCPToolsKinetic-GetCustomizationByID`
Pull a **classic** customization to uplift. `{ "CustomizationID": "MyCustomization" }`.
Returns JSON; the UI definition is XML in `CustomizationData.XXXDef[0].Content` (`<CustomizationDS>`). Parse it:
- `<Controls>` rows -> `ControlName` / `ControlType` / `ParentControlKey`.
- `<Properties>` rows -> `PropertyName` / `PropertyValue` per control — notably **`EpiBinding`** (the data field), `Text` (label/caption), `Multiline`.
Extract every data-bound control (EpiTextBox, EpiCheckBox, EpiCombo, EpiNumericEditor, EpiCurrencyEditor, EpiDateTimeEditor) and diff its `EpiBinding` against the `epBinding`s in the Kinetic layer to find gaps. This is *only* for classic customizations, not Kinetic UX layers.

### `MCPToolsKinetic-GetNativeKineticApp`
The single most important read: the **BASE** delivered Kinetic app your layer overlays. `{ "AppName": "Erp.UI.SalesOrderEntry" }`.
Returns all base pages, dataviews, events, rules, and tools. Use it to:
- find the real ids of base components you want to reparent into, hide, or Replace;
- find the exact system-event names to override (`Update`, `MasterUpdate`, `Refresh`, `GetNew`, `AfterGetByID`, `PerformUpdate`);
- read `patch.jsonc` constants (`%svc%`, `%datasetId%`, `%keyFieldSearch*%`);
- inspect base rules (e.g. `openOrderRule`, `hideToolsReadOnlyMode`) before adding your own so you don't conflict.
The payload is large (~2MB) and may be saved to a file rather than returned inline — slice it with python/jq. Base layout files live under `AppContent.Files["pages\\<Page>.layout.jsonc"].layout.components` (a FLAT list; each has `parentId`). Panels expose body slots as `<id>#bodyComponents`; rows/cols use the plain id as `parentId`.

### `MCPToolsKinetic-GetLayers`
List layers for an app. `{ "AppName": "Erp.UI.SalesOrderEntry", "IncludeUnpublished": true }`.
Use to confirm a layer exists before editing, and to check publish state. **Check `HasDraftContent`** — `true` means the user has unpublished draft work in App Studio that `GetIndividualLayer` will NOT return (see below). Also note `WIP` and `ChangedOn`.

### `MCPToolsKinetic-GetIndividualLayer`
Export a **published** layer. `{ "AppName": "Erp.UI.SalesOrderEntry", "LayerName": "MyKineticLayer" }`.
Returns an **off-band `downloadUrl`** (under `Base64EncodedLayerZip`), NOT inline base64. `curl -o`/`requests.get` the URL to get the zip directly — this avoids base64 transcription corruption entirely. The zip entry is `Layers/<App>/<Layer>.jsonc`; in a **published** export the manifest JSON lives in the record's **`Content`** field (and `SysCharacter03` may be empty — the opposite of builds you generate). Detect which field holds it by checking which is non-empty.
- **CRITICAL:** this returns only the **published** layer. If `HasDraftContent: true`, the user's draft rules/components are invisible here — have them publish first, or you'll silently drop their work on re-import. (Exception: when the export record's `SysCharacter03` is populated, that IS the App Studio draft — diff it against `Content` to see the user's hand-edits; see "The two content blocks" below.)
- It can **lag a revision** right after a commit (publish/cache lag). Re-download to verify; if it still shows the old state after an import, it's lag, not a failed import.

### The two content blocks — `Content` vs `SysCharacter03` (FIELD-PROVEN)

A layer record carries TWO content blocks:
- **`Content`** — the published layer (what `MCPToolsKinetic-ImportLayer` writes).
- **`SysCharacter03`** — the **App Studio draft**. A running App Studio preview renders the DRAFT, and an open App Studio session **re-freezes `SysCharacter03` over your imports** — so imported changes appear to "not take" and stale config (e.g. an old `queryId`) keeps running.

**Golden rule: keep both blocks byte-for-byte identical whenever you write.**
1. Build the change into `Content`; 2. set `SysCharacter03 = Content`; 3. `ImportLayer` + `MCPToolsKinetic-Commit`; 4. verify BOTH blocks match via a re-download; 5. tell the user to **CLOSE App Studio** (or hard-refresh) before testing.

**Exception — the user hand-edited in App Studio:** their edits live in the draft (`SysCharacter03`), which will differ from `Content`. Do NOT clobber it with a stale `Content`. Pull the layer, **diff the two blocks**, **adopt the draft's version** of whatever they touched (e.g. an App Studio-resolved reusable combo), rebuild BOTH blocks identical including those changes, then import + commit and re-verify. The only legitimate divergence is a live user hand-edit, and the response is pull → read draft → adopt → re-sync.

### `GetSearches`
List the Kinetic Searches available when wiring a `search-show` + `search-value-set`. Run wide-open (`{}`) for the full list, or `{ "top": 10 }` first to learn the filter patterns. `filter`/`orderby`/`select`/`top`/`skip`/`count` are OData-style — but **filterable field names are not listed here**; call `describe_baq_fields` with `baq="GetSearches"` first to learn exact column names/types. Mapping that matters: BAQ `Calculated_Like` -> the **Like\*** property in App Studio; `Calculated_SearchForm` -> the **Search Form** property. A field search needs both `like` (e.g. `"Project.ProjectID"`) and `searchForm:"default"`, or it crashes on `.replace`.

### `MCPToolsKinetic-GetBAQDefinition` / `describe_baq_fields`
`GetBAQDefinition { "BAQID": "MyBAQ" }` returns the BAQ structure, fields, joins, logic — needed to know the **flattened column names** (`PartDtl_PartNum`) you filter on in a grid `executeOptions.where` or `baqOptions.whereList`. `describe_baq_fields { "baq": "<baq tool name>" }` returns filterable field names/types/operator hints — call it before filtering any BAQ-backed tool.

### `MCPToolsKinetic-GetEpicorFunctionDefinition` / `MCPToolsKinetic-GetEpicorFunctionLibraryDefinition` / `MCPToolsKinetic-GetUBAQBpm`
Inspect server logic you may call from an event: `GetEpicorFunctionDefinition { "iLibraryID": "...", "iFunctionID": "..." }` (for an `erp-function` action's `efxLibrary`/`efxPath` + signature), `GetEpicorFunctionLibraryDefinition { "LibraryID": "..." }` (list functions in a library), `GetUBAQBpm { "BaqID": "..." }` (BPMs on an updatable BAQ, relevant to `UpdateBaq` writes).

---

## 2. Writing the world (commit + import)

### `MCPToolsKinetic-Commit`
Checkpoint the layer **before every import**. `{ "InID": "Erp.UI.SalesOrderEntry", "InLayerName": "MyKineticLayer", "InComment": "what this change does" }`.
Returns an incrementing rev number (a rollback point). Note the app id is `InID` here, not `AppName`.

### `MCPToolsKinetic-DeleteLayer`
Delete a layer. `{ "InLayerName": "<layer>", "InViewID": "<AppId>" }` (MetaFXSvc `DeleteLayer`, TypeCode `KNTCCustLayer`, Desktop).

**This is a FALLBACK, not the default path.** Always try `MCPToolsKinetic-ImportLayer` (which overwrites) first. Only when the import over an existing layer is REJECTED — e.g. an error about the customization already existing in another company, persisting across package shapes — delete the layer and re-import under the SAME layer name (menu records and user selections reference the name). Sequence for the fallback: (1) confirm with the user first (`confirm_action`) — deleting is destructive; (2) save the current server content locally so the previous state can be restored if the re-import fails; (3) delete; (4) re-import immediately — mind the window where the layer doesn't exist if users may be on the screen. (Field history: see the dashboard-uplift chapter of lessons-learned.)

### `request_file_upload`
Get a one-time upload target for the layer zip. All params optional but pass them for correct size/type limits: `{ "tool": "MCPToolsKinetic-ImportLayer", "param": "InContent", "filename": "layer.zip", "contentType": "application/zip" }`.
Returns `{ uploadUrl, fileRef }`. **Never send the file through an MCP call or paste base64.** Upload with a direct out-of-band PUT: `curl -T <zip> "<uploadUrl>"`. Each `uploadUrl`/`fileRef` is effectively single-use — request a fresh one per attempt. The endpoint can fail transiently (`HTTP 400 "Connection closed before upload completed"`) on several consecutive attempts then succeed unchanged — treat as transient infrastructure and retry, don't rebuild the zip.

### `MCPToolsKinetic-ImportLayer`
Import/replace the layer. `{ "InContent": "<fileRef GUID from request_file_upload>", "InCompany": "<scope>" }`.
Do NOT pass base64 — pass the `fileRef`. **Import REPLACES the whole layer** — anything not in your zip is lost. So always re-download the current published layer first, and when in doubt build the *complete desired end-state* rather than an incremental diff (self-correcting even if the baseline lagged). Writes to the **published** track; it does not merge into an open App Studio draft.

**`InCompany` — company scope (added 2026-09-08 to the `Kinetic.ImportLayer` Epicor Function):**
- A Company ID (e.g. `C001`) → company-specific import (`overrideCompanyId` and `overridePersonalizationCompanyId` = that company).
- `All Companies`, `All`, or blank/omitted → all-companies import (the pre-2026-09-08 behavior; personalization scoped to the session company). `overrideCompanyId` takes the LITERAL string `"All Companies"` on the MetaFXSvc side.
- Shared customization layers are conventionally all-companies with no user (see the dashboard-uplift chapter of lessons-learned); company-scoped records are typically personalizations/scratch/WIP.

**MANDATORY pre-ask, once per session:** before the first import of a session, ask the user — Current Company, All Companies, or another company — via `ask_user_choice`, unless the scope was already given this session or in the request. Cache the answer for the rest of the session. If the connector tool doesn't expose `InCompany` yet (older metadata), say which scope will apply (omitted = All Companies) rather than silently defaulting.

---

## 3. Interaction & display helpers (optional)

- `ask_user_choice { question, options:[{key,label}], multiple? }` — disambiguate (which app, which layer, which behavior).
- `ask_user_input { question, type:"text|number|date|daterange", ... }` — free-form values.
- `confirm_action { question, summary:[{label,value}] }` — confirm before a write (import/commit). Returns `{ confirmed }`.
- `render_record` / `render_chart` — display a fetched record or dataset visually (not needed for layer building itself).

---

## 4. The canonical round-trip (tool order)

1. `MCPToolsKinetic-GetLayers` (IncludeUnpublished:true) -> confirm the layer exists, check `HasDraftContent`. If draft content exists, ask the user to publish first.
2. `MCPToolsKinetic-GetCustomizationByID` (if uplifting) -> inventory the classic behavior.
3. `MCPToolsKinetic-GetNativeKineticApp` -> learn base ids, events, rules, patch constants.
4. `MCPToolsKinetic-GetIndividualLayer` -> download the **current** published layer (GET the `downloadUrl`). **Always re-download right before editing** — never trust an on-disk copy from a previous turn.
5. Edit the manifest (script it; patch in place). First diff `Content` vs `SysCharacter03` — if they differ, the draft holds user hand-edits to adopt. Then write **both blocks identical** (see "The two content blocks" above).
6. `MCPToolsKinetic-Commit` -> checkpoint with a clear comment.
7. `request_file_upload` -> `curl -T` PUT the zip -> `MCPToolsKinetic-ImportLayer` with the returned `fileRef`. Retry on transient 400s.
8. Ask the user to reload the app in App Studio (debug logging on) and report console/screenshots — **have them close App Studio / hard-refresh first** so the draft block doesn't mask the import. Diagnose, then loop from step 4.
