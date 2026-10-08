# Uplift Mapping, Foreign Key Views, Dashboards & Debugging

The other reference files describe the Kinetic machinery. This one is about *applying* it: turning a classic customization into layer mechanisms, the verified Foreign Key View recipe, building a dashboard layer, and diagnosing failures from console signatures.

---

## 1. Classic -> Kinetic translation table

Inventory the classic customization (`MCPToolsKinetic-GetCustomizationByID`), then map each piece:

| Classic construct | Kinetic layer mechanism |
|---|---|
| EpiTextBox / EpiNumericEditor / EpiCurrencyEditor / EpiCheckBox / EpiDateTimeEditor + `EpiBinding` | a field component (`erp-text-box`, `erp-numeric-box`, `erp-currency-box`, `erp-check-box`, `erp-date-picker`) with `model.epBinding = "<View.Column>"` |
| EpiCombo | `erp-combo-box` — pick a data-source variant (UserCodes/BAQ/Service/View/zdata or a shared `$ref` combo); see components.md §6 |
| Label / static text | `ep-label` or the host field's `labelText` |
| Custom button | `erp-button` (target of a `Control/onClick` event) or, better, a field's built-in search icon (`enableSearch:true`) |
| Multi-line "notes/reason" textbox | `erp-text-box` with `model.multiline:true, rows:3` (or `erp-text-area`) |
| Foreign Key View (adapter pulls related record) | a child dataview + a `rest-erp` with `responseParamArgs` that routes the BO response into that view (see §2) |
| RowRule: highlight / disable / readonly / required / hide | a `rules` entry with `SettingStyle.Disabled|Invisible|ReadOnly` (per binding) or `DisableRow`/`DisableColumns` (see rules-and-dataviews.md) |
| Code-behind field defaulting / calc | a `row-update` action on a `columnChanged`/`rowChanged` event |
| Code-behind validation | a `condition` + `erp-message-handler` in an event |
| BeforeAdapterMethod / AfterAdapterMethod hooks | override the matching system event (`Event/override` or `Event/after`, e.g. `AfterGetByID`) or call an Epicor Function |
| Save-time logic | chain into the base `Update` (Save) event via `event-next`; put heavy logic in an Epicor Function/BPM and call it |
| Custom grid | `metafx-panel-card-grid` — bound (child view) or BAQ provider (`providerModel.baqId`) |
| Sheet/Tab | a page section (`viewType:"TabPage"`) or an inner `metafx-tabstrip`; keep base sections intact |
| Context menu launch to another form | `app-open` action |

**Uplift completeness check:** after building, diff the classic control set's `EpiBinding` values against the layer's `epBinding` values to confirm every data-bound field made it across. Preserve exact classic bindings for any field a BPM depends on (e.g. a `CallContextBpmData.CheckboxNN` a server BPM reads) even if a cleaner binding exists — the BPM reads that specific path.

Anything not expressible in the UI layer (server-side roll-ups, complex transaction logic) belongs in an **Epicor Function** or **BPM**, called from an event — don't force it into the layer.

---

## 2. Foreign Key View recipe (VERIFIED)

To replicate a classic FKV (load a related record's fields when a key changes):

1. **Define the child dataview** whose `datasetId` you'll target, with a real `serverDataset`:
   ```json
   {"id":"ShipTo","schema":"Erp","table":"ShipTo","serverTable":"ShipTo",
    "datasetId":"CustomerDS","serverDataset":"Customer",
    "parent":{"parentDataview":"Customer","parentColumns":["CustNum"],"childColumns":["CustNum"]},
    "sort":[{"column":"ShipToNum","descending":false}]}
   ```
2. **On the key's `columnChanged`**, call the BO with `responseParamArgs` (NOT `requestParamArgs`) so the response is *fetched into views*:
   ```json
   {"type":"rest-erp","param":{
     "svc":"Erp.BO.CustomerSvc","svcPath":"GetByCustID","requestMethod":"POST",
     "erpRequestMethod":"ErpPostWithDataViewProcessing",
     "methodParameters":[{"field":"custID","type":"string","epBinding":"UD103.EpicorCustID_c"}],
     "erpRestPostArgs":{"responseParamArgs":[
       {"dataset":{"systemCode":"Erp","datasetId":"CustomerDS"},"responsePath":"returnObj"}]}}}
   ```
   The dataset-mapping service expands the one `datasetId` arg into per-view args for **every** view sharing that `datasetId`. Using `requestParamArgs` here returns 200 but leaves fields blank — that's the round-trip (send-`ds`) shape, wrong for a fetch. See search-baq-rest.md §3.5.

---

## 3. Dashboards (BAQ-driven layers)

A dashboard app differs from an entry app in a few concrete ways:

- `layout.viewType: "Dashboard"` (entry apps use `"Apps"`).
- Data comes from **BAQ-backed dataviews** (`schema:"baq"`, `data:"<BAQId>"`) rather than BO tablesets — no `serverDataset` needed, but `table`, `tools`, and `mode` ARE (required set `{id, schema:"baq", data, table, tools, mode}` — rules-and-dataviews.md §B12).
- A `metafx-panel-card-grid` renders results either via a bound BAQ view or directly with `providerModel:{baqId:"<BAQ>"}` + `autoLoadColumns:true` (no epBinding, no dataview — the grid makes its own view).
- **Auto-run on open:** a `{"type":"Window","hook":"onLoad"}` event runs the BAQ (an `erp-baq` action, or the grid auto-loads).
- **Per-parameter filtering:** grid `baqOptions.whereList` with `??{ParamView.Col}` tokens (double-`?` = optional/skip-if-empty). See search-baq-rest.md §2.3–2.4b (item shape, quoting, and the gate pattern for "don't run until a filter is entered").
- Read-only grids should set `allowAddNew:false`, `allowDelete:false`, `hideViewSelector`, `fullScreenButtonVisible:false`, and give `gridModel` an explicit `height` (don't use `autoFillContainer` in a small card).

- **`imports` blocks (base-app dashboard files) — exact shapes or nothing (VERIFIED vs schema + a real generated dashboard):** App-Studio-generated dashboards ship an `imports` array in `dataviews/events/rules/strings/tools.jsonc` pulling shared `../shared/imports/UIDashboards/base/*` content. The item KEY is per-file: `dataviews`/`events`/`rules`/`tools` match the file name — **but `strings.jsonc` uses `default`** (`{"default":{"$ref":"../shared/imports/UIDashboards/base/strings.jsonc#/strings"}}`; the v3.0 strings schema allows ONLY `default`, additionalProperties:false). A wrong key in strings.jsonc (e.g. `strings`) throws `InvalidCastException: JArray→JObject` in `Translation.MergeWithGeneratedString` during `GetApp` — **only on a real menu launch; App Studio preview never runs the translation merge**, so preview passes while the menu 500s with a generic correlation-ID error. If you have no shared content to merge, `"imports": []` (or omitting the block) is safe and ships in real apps too. Never invent import shapes — copy them from a real generated dashboard.

Everything else (diff wrapper, sections, versions, import round-trip) is identical to an entry-app layer.

---

## 4. Error signature -> cause table

| Console signature | Likely cause | Fix |
|---|---|---|
| `Cannot read properties of undefined (reading 'view')` at binding registration | a component bound to a dataview whose `serverDataset` isn't a real server tableset | use a real tableset name; for client-only flags bind to a `TransView.*` column |
| kendo `orderBy` crash / `reading 'replace'` on table load | dataview `sort` used `{columnName,sortDirection}` | use `{"column","descending"}` (or a plain `"Col ASC"` string) |
| `TypeError: Cannot read properties of null (reading 'split')` on Refresh/load, in the crumb/binding path | a **null page `/navigation/epBinding`** (or `dataSetId`) diff | remove the null-`epBinding` override so the base value stands; set page Ep Binding (e.g. `OrderHed.OrderNum`) + Data Set (e.g. `SalesOrder`). Audit `/navigation/*` diffs FIRST on any crumb split-null |
| App Studio Data Rules panel shows **zero** rules; every status shape lights up | a **malformed diff wrapper** — a new rule added as bare `{Operation,Value}` missing `Id`/`Path`/`Index` | copy an existing sibling's full wrapper: `{"Id":"<ruleId>","Path":"","Value":{...},"Operation":"Add","Index":<max+1>}` |
| `Invalid session value` | `%View.Column%` (percent around a view field) | use `{View.Column}` (curly) for view fields; `%...%` is only session/dataset/patch constants |
| `SyntaxError: Invalid or unexpected token` from a `#_ … _#` expression | double-evaluation of the returned string | wrap the whole thing in quotes: `'#_ new Date().toISOString() _#'` |
| Combo renders `[object Object]` | missing `textField`/`valueField` | add both; UserCodes combos also need `dataMode:"rows"` |
| UserCodes combo "table not found" | List dataset used | set `dataMode:"rows"` |
| Grid collapses to ~2 rows | `autoFillContainer` in a small card | set explicit `gridModel.height` |
| Field search icon does nothing (App Studio shows `+` on "On Search Click") | wrong trigger for the icon | use `{"type":"EpBinding","hook":"onClick","target":"<DataView.Column>"}` (App Studio then shows an ellipsis) |
| Inline search fires twice / wide-open GetList loops the client | event writes back to the binding its own trigger watches | bracket the `search-value-set` with `event-column-disable`/`event-column-enable` (top-level `dataTable` on the action — `param.dataTable` is not read; see events.md §2.4) |
| Read-only "lock won't release" on a true->false toggle | a custom `DisableRow` rule conflicting with the base rule that governs the same dataview | delete the custom rule; drive the base flag (`TransView.SysReadOnly`) and let the base `openOrderRule` do the lock/reverse |
| `property-set enabled` on a button does nothing | `enabled` isn't reactive on buttons | use `disabled`; or give the control a `TransView` binding and use a rule |
| Native status shapes grey out when locking | `DisableRow` greys shapes bound to `OrderHed.*Shape` | add those real column names to `exceptTheseColumns` |
| Whole form blank after import | base layout sections were pruned | keep ALL base sections; only add/replace |
| Fields / a whole matrix column / a region silently missing, NO console error | `metafx-matrix` rules violated: `model.columns`/`model.rows` are SWAPPED (`columns` = ROW count, `rows` = COLUMN count) and CLIP — cells with `y >= columns` or `x >= rows` are silently dropped; or multiple controls in one cell (only first renders); or empty cells in the bounding grid | set `columns = max(y)+1`, `rows = max(x)+1`; one control per cell; blank `ep-label` spacers for empty cells; fill every `(x,y)` (components.md §3.8a) |
| Custom component lands in the wrong slot despite a high `Index` | render order = physical array order, not `Index` | move the diff object to the right position in the section's `Diffs` array |
| Re-import silently dropped an earlier change | built from a stale local copy; import replaces everything | re-download the current published layer before every edit; build the complete end-state |
| Import over an EXISTING layer rejected — "customization already exists in another company" (persists across package shapes/companies) | the record can't be overwritten in place on this system | fallback: confirm with user → save current server content locally → `MCPToolsKinetic-DeleteLayer` → re-import under the SAME layer name (import-first is still the default path; lens-mcp-tools.md) |
| Export shows far fewer rules than App Studio | `GetIndividualLayer` returns only **published**; user has draft | `GetLayers IncludeUnpublished:true` -> check `HasDraftContent`; have the user publish first — or diff the export's `SysCharacter03` (draft) block against `Content` (lens-mcp-tools.md) |
| `TypeError: t.replace is not a function` at `processValue -> getCriteria -> getProcessedWhereClause` | a boolean `honorNull` (or other extra key) on a `baqOptions.whereList` item | strip each item to exactly `{column, condition, value}` (search-baq-rest.md §2.3) |
| BAQ-provider grid throws "Invalid column name" (complex multi-subquery BAQ) | a `columns` array made the grid emit a restrictive dynamic `Select` | remove `columns`; use `autoLoadColumns:true` (components.md §3.7) |
| Server-paged BAQ grid: sort broken / events reading the result view get empty values | `serverPaging:true` projects ONLY the enumerated fields; key/`QuerySortBy` columns aren't display fields so the paged `Select` drops them | set `baqOptions.select` with the full bracketed list (preferred), or `autoLoadColumns:false` + COMPLETE `columns` list with key/sort columns `hidden:true` — never a partial list under `autoLoadColumns:true` (search-baq-rest.md §2.3b/§2.3d) |
| Hardcoded grid columns don't appear in the emitted `ExecuteBaq` Select; Select = exactly the BAQ's display columns | live grid model had NO columns at provider init (draft block winning, diff not applied, columns under `providerModel.columns` which the Select path never reads, or saved personalization) | add the fields to `providerModel.baqOptions.select` (bracketed `"[UD103_Key2]"`) — unioned in verbatim; and audit draft/diff/personalization (search-baq-rest.md §2.3c) |
| UBAQ columns render but come back BLANK / missing from the `ExecuteBaq` Select (server-paged grid) | VERIFIED: newer client builds gate the Select enumeration in `updateFieldMetadata` — a column is fetched only if its BAQ metadata is found AND `updatable === false`; `QuerySortBy` fields get re-appended at the END (masking sort-coincident cases) unless a saved personal sort/grouping disables the append | set `baqOptions.select` (full bracketed column list) — unioned in first, immune to all of it; clear saved grid layouts when debugging (search-baq-rest.md §2.3d). Also note: `timestamp`/`guid` columns are auto-hidden client-side |
| Reusable-combo dropdown comes up empty | only `type`/`subType` emitted; the resolved fetch definition is missing | emit the full resolved model (svc/svcPath/tableName/valueField/textField/filters/filtersParams) or let App Studio resolve it once and adopt it (components.md §6.2) |
| A hand-built dataview silently disappears after import | a SQL `datatype` on a column (`"nvarchar"`) OR a missing `tools` block | use Kinetic type tokens (`string`/`int`/`decimal`/`date`/`boolean`/`guid`) and give every view `tools:{"new":{"hidden":true},"delete":{"hidden":true}}` (rules-and-dataviews.md §B12) |
| A dataview imports but isn't in App Studio's Data View picker / behaves inconsistently | missing `table` property (common on BAQ views) | add `table` (convention: same string as the view `id`) (rules-and-dataviews.md §B12) |
| A `columnChanged` event never fires | `DataTable` trigger `target` was the dataview id | target the **table** id (the view's `table` property) (events.md §2.4) |
| Imported changes "don't take"; stale config (old `queryId`) keeps running | App Studio is open — the draft block `SysCharacter03` overrides/re-freezes over imports | write `Content` AND `SysCharacter03` identical, have the user close App Studio / hard-refresh (lens-mcp-tools.md "two content blocks") |
| App Studio preview works but real MENU launch fails with a generic "unexpected internal problem" + Correlation ID; server log: `InvalidCastException: JArray→JObject` at `Translation.MergeWithGeneratedString` in `GetApp` | malformed `imports` block in a base-app file — in `strings.jsonc` the import item key must be **`default`** (a guessed key like `strings` crashes the translation merge, which only runs on real launch, never in preview) | use the exact per-file import shapes from a real generated dashboard, or `"imports": []` when there's no shared content (§3). Diagnose menu-launch 500s by pulling the server log by Correlation ID |

---

## 5. Debugging workflow

1. **Reproduce with debug logging on.** Ask the user to reload the app/layer in App Studio (or the runtime) with browser console open, and share the console log + a screenshot.
2. **Read the substituted expression.** The engine prints token-substituted conditions/expressions literally — mistakes (`Invalid session value`, wrong quoting) are visible directly.
3. **Match the signature** to §4. For crumb/binding `split`-of-null, audit `/navigation/epBinding` + `/navigation/dataSetId` before anything else.
4. **Revert first, diagnose second** when a change has blast radius beyond the intended control (e.g. every base status shape lights up) — don't stack a speculative fix on a visible regression.
5. **Bisect correctly.** Page/navigation-level diffs (`/navigation/*`, `/model/*`, any Path-based diff with no component `id`) are NOT components — bisect them separately from component diffs, or a component-only bisection will never reproduce a page-level crash.
6. **Verify by re-download.** After import, re-download; if it still shows the old state it's publish lag, not a failed import — the user's App Studio reload reflects the import.
6a. **A passing App Studio preview is NOT sufficient sign-off** — some server paths (e.g. the `GetApp` translation-string merge) run only on a real menu-driven launch. Test from the actual menu before calling an uplift done; on a generic menu-launch failure, get the server log by Correlation ID.
7. **Inspect a working base control first** when replicating base behavior (a search icon, a status shape, a read-only lock). Reading how the base app wires the same thing (`GetNativeKineticApp`) is faster than guessing trigger/param permutations.
