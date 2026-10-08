# §D. Dashboards — classic dashboard uplift & Kinetic dashboard apps (`Ice.UIDbd.*`)

> **READ THIS FILE IN FULL before ANY dashboard work.** It is the self-contained authority for
> dashboards (it supersedes `uplift-and-debugging.md` §3). It is referenced elsewhere in the skill
> as "§D" / "D.x". Everything here is generic — placeholders `<X>`/`<GV>`/`<TV>`/`<FV>`/`<BAQ>`
> are yours to fill; nothing depends on any pre-existing customization or dashboard.

Everything in this section is **field-verified** on a live Kinetic 2024.x system (a full read-only uplift, a full updatable uplift including base-app creation from scratch via import, and three classic↔Kinetic worked comparisons). It is self-contained and is the authority for dashboards; general layer mechanics in SKILL.md still apply to dashboard layers.

## D.0 Mental model

A **classic dashboard** = one or more BAQs, each rendered as a **Grid + Tracker** pair in a WinForms shell, optionally *deployed* to a compiled `Ice.UI.App.<ID>_<n>.dll`, optionally with a **classic customization** on top (`Key2 = App.<ID>.MainController`). A **Kinetic dashboard** = a MetaFX **base app** with ViewId `Ice.UIDbd.<Name>` (`layout.viewType:"Dashboard"`), plus optional normal **KNTCCustLayer layers**. Uplift = (1) inventory the classic side, (2) get/create the Kinetic base app, (3) build the customization as a layer, (4) iterate via the import round-trip.

**Two archetypes — detect FIRST, it decides all scope:**
- **Read-only analytics/lookup**: plain BAQ(s), `Updatable=False`, no ViewButtons, usually no customization. Uplift = grid + filter panel. ~Half a day.
- **Updatable worklist**: UBAQ-backed grids (`QueryUpdateSettings.UpdatableType "A"` = advanced/BPM-only update — no BO; the real business logic is in the **UBAQ BPM Update directives**, pull with `MCPToolsKinetic-GetUBAQBpm {BaqID}`), checkbox selector columns, ViewButtons firing **BAQ Custom Actions**, almost always customized. Multi-day.

## D.1 Reading the classic side

### D.1.1 `MCPToolsKinetic-GetClassicDashboardDefinition { DashboardID }`
Returns an **off-band download** (`downloadUrl` — curl it; never transcribe base64). JSON tableset:
- `DashBdDef[0]`: `DefinitionID`, `Caption`, `HasDashboardAssembly`, `LastDeployedDate/By`, **`DashboardSchema`** (a large XML string — everything is here), **`DashboardAssembly`** (base64 **zip** containing the deployed `Ice.UI.App.<ID>_<n>.dll`).
- `DashBdBAQ[]`: one row per referenced BAQ → your `MCPToolsKinetic-GetBAQDefinition {BAQID}` pull list. Helper BAQs used by tracker dropdowns or custom code are NOT listed here (D.1.4).

### D.1.2 DashboardSchema XML (root `DashboardDataSet`) — the rows that matter
- **`DashboardQuery`** (one per tab): `QueryID` (guid keying all other rows), `DynamicQueryID` (=BAQ), `Caption` (tab caption), `IsPrimary`, **`ParentView`/`ParentColumn`/`ChildColumn`** (publish/subscribe master-detail; empty = independent tab), `ViewName` = `V_<BAQ>_1View` (the runtime dataview name classic custom code binds via `oTrans.Factory("V_<BAQ>_1View")`).
- **`DashboardView`** (per query, typically Grid + Tracker): `ViewType`, `Caption`, **`ViewPanelID`** — classic custom code grabs the native grid with `csm.GetNativeControlReference("<ViewPanelID>")`. Map these guids → grids FIRST when reading any script.
- **`DashboardViewColumns`**: `ColumnName`, `IsVisible`, `Caption`, `DataType`, and **`DashboardPrompt`** whose meaning depends on the view type: on a **Tracker** = a filter prompt field; on a **Grid** = an **editable/updatable column** (verified: Grid-prompt set == the Kinetic grid's `editable:true` columns == the BAQ's `QueryField.Updatable:true` fields).
- **`DashboardViewOptions`** (PropertyName/Value rows). Grid: `Updatable`, `MultiDirtyRow` (many dirty rows per save), `AllowAddNew`, `StaticGetNew` (client-only staging rows), **`ViewButtons`** (XML list `{Seq,Text,Image,Action}` → toolbar buttons ViewButton1..N firing the BAQ **Custom Action** whose `QueryCustomAction.ActionID == Action`), `GridLayout` (cosmetic). Tracker: `IsSearchPanel`, `InputPrompts`, **`CriteriaRequired`** (query must not run until criteria entered → the Kinetic gate, D.5.3).
- `DashboardQueryOptions`: `IsBaqUpdatable`, `AddNewLabel`. `DashboardProperties`: `Caption`, `PrimaryQuery`. `DashboardViewCustomizations`: usually just Infragistics dock-layout persistence — NOT logic. `DashboardDefinition.DockLayoutXML`: dock persistence — only useful for tab order; classic trackers dock INLINE at top (replicate inline, not as a slider).
- **Calculated-only staging BAQ pattern**: a BAQ with ZERO tables (all `Calculated_*` columns) + `AllowAddNew`/`StaticGetNew` = a client staging grid; rows created client-side (e.g. from a dropped CSV in the customization), then a custom action ships the batch to the BPM. Kinetic mapping: file-upload/EFX or a rebuilt import UX + client rows + UpdateBaqCustomAction.

### D.1.3 The classic customization
If `HasDashboardAssembly` is true, try `MCPToolsKinetic-GetCustomizationByID {CustomizationID}` (often the dashboard name; else ask). A customized dashboard has a record `Key2 = App.<DefinitionID>.MainController`; its `CustomizationData.XXXDef[0].Content` is CustomizationDS XML: `Controls` rows + `Properties` rows (geometry, `EpiLabel`, combo config `DynamicQueryID`/`DisplayMember`/`ValueMember`, and the **`Script`** PropertyValue = the C# code-behind, often 1000+ lines). **A dashboard uplift without this misses most of the UX.**
- **Not-found signature**: HTTP 400 `"Parameter value cannot be null: Key2,Key3."` = no customization record exists (not a tool failure). `HasDashboardAssembly=true` means *deployed*, not *customized*.
- Recurring script idioms → Kinetic mappings: `HandleToolClick("ViewButtonN"/"RefreshTool"/"SaveTool")` after `AppControlPanel.AppController.LastControl = <grid>` (targets which query view the tool acts on) → button events (D.5); grid `CellChange` check-group cascades guarded by a `fromCode` flag → `dataview-condition` + iterative `row-update` (D.5.5); textbox values stamped into calculated "parameter carrier" columns read by the UBAQ BPM → filter-view columns + `row-update` before save; `BAQUpdater.UpdateBAQ(dv)` reflection → `erp-baq mode:"update"` (D.5.4); `DynamicQueryAdapter.ExecuteByID` ad-hoc BAQs → `erp-baq mode:"get"`; `SelectedRows` loops → grid selection + `matches` iterate (D.5.5); OpenFileDialog / Attachment BO / `Process.Start` temp files → `erp-file-box` + `file-transfer-erp` + Epicor Functions (D.5.7); `BAQCombo` reflection refresh hacks → unnecessary; hidden shapes + marquee ProgressBar + `IsEpiReadOnly` → skip (Kinetic busy state / toasts).

### D.1.4 Harvest helper BAQs
Tracker BAQCombos live in the **BAQ** (`QueryCtrl` ControlType `DropDownBAQ` + `QueryCtrlValues` rows `BAQID`/`BAQValueColumn`/`BAQDisplayColumn`) and customization combos in Properties (`DynamicQueryID` + `ValueMember` + `DisplayMember`). Also grep the script for `ExecuteByID("...")`. None appear in `DashBdBAQ`.

### D.1.5 Tracker prompts are NOT BAQ parameters
Verified: a tracker can filter on many columns (even `Calculated_*`) while the BAQ has zero `QueryParameter` rows — classic injects tracker criteria as DynamicQuery **execution filters** at runtime. Kinetic maps this 1:1 to grid `baqOptions.whereList` tokens; **no BAQ changes needed** for read-only uplifts.

## D.2 Dashboard-specific Lens tool notes (general tools: `references/lens-mcp-tools.md`)

| Tool | Params | Notes |
|---|---|---|
| `MCPToolsKinetic-GetClassicDashboardDefinition` | `DashboardID` | off-band download |
| `MCPToolsKinetic-GetUBAQBpm` | `BaqID` | BPM directives on an updatable BAQ |
| `MCPToolsKinetic-GetNativeKineticApp` | `AppName` | `{Success, AppContent}`; AppContent JSON = `{ViewId, CompanyId, Files:{...jsonc files...}}`; **`Files:{}` = app not materialized** (not an error); reading does NOT trigger conversion |
| `MCPToolsKinetic-GetLayers` | `AppName`, `IncludeUnpublished:true` | `TypeCode` KNTCCustLayer vs **KNTCPersLayer** (personalization, name `user^layer`, `ParentLayers` — can MASK your changes for that user during testing); **layer names may contain spaces** — pass exactly as listed |
| `MCPToolsKinetic-ImportLayer` | `InContent` = fileRef, `InCompany` = scope | handles all THREE zip formats (D.4); company scope per the SKILL.md step-7 pre-ask |

## D.3 Three ways an `Ice.UIDbd.*` base app exists

1. **Auto-converted from classic**: Epicor generates `Ice.UIDbd.<ClassicDefinitionID>` when the dashboard is first opened in Kinetic/App Studio. Fingerprints: dataviews named `<SanitizedBAQ>_<q>_<v>` (non-alphanumerics stripped: `CUST-PartTranAll`→`CUSTPartTranAll`; `_0_0`=first query's grid view, `_0_1`=its tracker view), imports from `../shared/imports/UIDashboards/base/*`, tracker as a slide-out page. Multi-query → one card+tracker+refresh event per query, `executeRefreshAll` fanning out. A re-created dashboard may be SPLIT across several differently-named Kinetic apps — always confirm the target app id.
2. **Hand-built in App Studio** (Dashboard template): fingerprints `layout.name:"DashboardTemplate"`, `namespace:"Ice.UIDbd.Template"`, no shared imports, no `_q_v` naming, often no layers (the base app IS the deliverable).
3. **Created by YOU via `MCPToolsKinetic-ImportLayer`** (D.4.1) — full parity; the bootstrap when the app doesn't exist and nobody can open App Studio.

## D.4 Import formats — `MCPToolsKinetic-ImportLayer` handles ALL THREE (verified live)

### D.4.1 BASE APP zip — `Apps/<AppId>/<file>.jsonc`
The RAW jsonc files exactly as `GetNativeKineticApp` returns them — NO record wrapper. The page file's zip **entry name contains a literal backslash**: `Apps/<AppId>/Pages\<PageName>.layout.jsonc`. **A base import REPLACES the entire app — omitted files are DELETED**; always ship the complete set: `dataviews.jsonc, events.jsonc, layout.jsonc, patch.jsonc, rules.jsonc, strings.jsonc, tools.jsonc` (+ `Pages\<TV>.layout.jsonc` only if keeping a slider tracker). Skeletons in D.7. This is how you create `Ice.UIDbd.<X>` from scratch.

### D.4.2 LAYER zip — `Layers/<AppId>/<LayerName>.jsonc`
One JSON **record** (XXXDef row shape). Paste-ready CREATE record (must look NEW — see failure signatures):
```json
{ "$id":"1", "Company":"", "ProductID":"EP", "TypeCode":"KNTCCustLayer",
  "Key1":"<LayerName>", "Key2":"<AppId>", "Key3":"Desktop",
  "Description":"", "LastUpdated":"2026-01-01T00:00:00", "LastUpdatedBy":"lensmcp",
  "Version":"2026-01-01T00:00:00Z", "DataBaseVersion":0,
  "SysCharacter01":"", "SysCharacter02":"", "SysCharacter03":"", "SysCharacter04":"", "SysCharacter05":"",
  "SysNumber01":0.0,"SysNumber02":0.0,"SysNumber03":0.0,"SysNumber04":0.0,"SysNumber05":0.0,
  "SysDate01":null,"SysDate02":null,"SysDate03":null,"SysDate04":null,"SysDate05":null,
  "SysCheckBox01":false,"SysCheckBox02":false,"SysCheckBox03":false,"SysCheckBox04":false,"SysCheckBox05":false,
  "CommentText":"", "CGCCode":"", "SystemFlag":false,
  "SysRevID":"AAAAAAAAAAA=", "SysRowID":"<fresh guid>",
  "SysCheckBox06":false,"SysCheckBox07":false, "OnMenu":true, "Duplicate":false, "Cosmetic":false,
  "Content":"{\"config\":{\"Name\":\"config\",\"Version\":\"2.0\"},\"layout\":{\"Name\":\"layout\",\"Version\":\"3.0\",\"Diffs\":[],\"Operation\":\"Replace\"},\"events\":{\"Name\":\"events\",\"Version\":\"5.0\",\"Diffs\":[],\"Operation\":\"Replace\"},\"rules\":{\"Name\":\"rules\",\"Version\":\"3.0\",\"Diffs\":[],\"Operation\":\"Replace\"},\"tools\":{\"Name\":\"tools\",\"Version\":\"2.0\",\"Diffs\":[],\"Operation\":\"Replace\"},\"dataviews\":{\"Name\":\"dataviews\",\"Version\":\"4.0\",\"Diffs\":[],\"Operation\":\"Replace\"}}" }
```
- `Content` = the layer manifest (JSON string): sections `config 2.0, layout 3.0, events 5.0, rules 3.0, tools 2.0, dataviews 4.0`, each `{"Name","Version","Diffs":[...],"Operation":"Replace"}`, plus optionally `"<PageName>":{"Name":"<PageName>","Version":"3.0","Operation":"Remove"}` to **delete a whole page** (e.g. the generated tracker slider).
- **`SysCharacter03`** = the App Studio DRAFT block. For CREATE leave it `""`. For every UPDATE write, set it byte-identical to `Content`. If a downloaded record's draft differs, it holds user hand-edits: adopt, don't clobber.
- **Failure signatures (verified)**: create-record with populated draft/long Description → `"Base application for An error occurred while updating the entries. See the inner exception for details. does not exist."` — the EF exception leaks into the app-name slot; it means the RECORD WRITE failed, NOT that the base is missing. `SysRevID:null` → `"Error setting value to 'SysRevID' on 'Ice.Tables.XXXDef'"` (rowversion can't be null; use the placeholder). Genuinely missing base → clean `"Base application for <AppId> does not exist. Layers cannot be imported without base application."`
- **Canonical bootstrap** (proven end-to-end): (1) import base-app zip; (2) import the minimal BLANK layer zip above (creates the record); (3) `GetIndividualLayer` → download the server's record (real `SysRowID`/`SysRevID`); (4) set `Content` = `SysCharacter03` = your real manifest, keep server identity fields; (5) `MCPToolsKinetic-Commit`; (6) import; (7) re-download, verify both blocks match. **Re-read before each subsequent edit**, since patching a stale local copy silently loses server state. Verify after each write too, scaling the depth to what is at stake: a content hash catches wholesale replacement cheaply, a property-level check is needed when the change is subtle.

### D.4.3 COMBINED zip
`Apps/<AppId>/*` + `Layers/<AppId>/<Layer>.jsonc` in one zip — imports fine; use for atomic base+layer updates.

## D.5 Build patterns (all field-verified)

### D.5.1 Dashboard-relevant diff notes
General diff mechanics per the main skill; dashboard extras: a top-level manifest section `"<PageName>":{"Name":"<PageName>","Version":"3.0","Operation":"Remove"}` removes a whole page; **navigation.epBinding must be `""`, never null** (`{"Id":"","Path":"/navigation/epBinding","Value":"","Operation":"Replace"}`); **render order** — layer additions can land ABOVE unordered base components; emit explicit `Move` diffs (`{"Id":"<X>","Path":"components","Value":null,"Operation":"Move"}`) for every base card at the desired slot — physical Diffs order = render order.

### D.5.2 Filter/tracker panel that actually works (inline, classic-style)
Bound inputs render **DISABLED when their dataview has no current row**, and `row-update` does NOT create one. Full recipe:
```jsonc
// dataview (base file or layer Add):
{ "id":"<FV>", "table":"<FV>Tbl", "datasetId":"<FV>DS",
  "additionalColumns":[ {"columnName":"Part_PartNum","caption":"Part_PartNum","datatype":"string"}, /*...,*/ {"columnName":"SearchGate","datatype":"string"} ],
  "tools": { "new":{"text":"","hidden":true}, "delete":{"text":"","hidden":true} }, "mode":"U" }
// init event actions (used by load AND Reset):
{"type":"data-clear","param":{"type":"dataview","value":"<FV>"}},
{"type":"row-add","param":{"dataview":"<FV>","values":{"Part_PartNum":"", /*...,*/ "SearchGate":""}}}
```
Layout: `metafx-panel-card` (parentId null) → `metafx-div` row (`model.columns:N`, parentId `"<cardId>#bodyComponents"`) → `metafx-col` columns (`model.flexBasis:"50%"`) → fields (`erp-text-box` `{labelText,epBinding:"<FV>.<Col>",multiline:false}`, `erp-date-picker`, `erp-numeric-box` `{nullable:true,mask:">>>>>>>>9"}`, `erp-check-box` `{threeState:true}` for tri-state filters — init those with row-update `expression:"null"`, strings with `expression:"\"\""`), plus Search/Reset `erp-button`s.
**Init trigger — the preview trap**: App Studio Preview URLs carry **`autoload=false`** — `{"type":"Window","hook":"onLoad"}` NEVER fires there (rowless view → everything disabled, zero errors). Component **`onInit` DOES fire in preview** — chain init from an always-rendered card: trigger `{"type":"Control","hook":"onInit","target":"<gridCardId>"}` → `event-next` init, in addition to the window event (which covers real menu launches).

### D.5.3 The gate (classic CriteriaRequired / "don't run the BAQ until input")
`gridModel.autoLoadGrid:false` does NOT reliably stop a BAQ provider grid. The reliable gate is a **required token** as the FIRST whereList item:
```jsonc
{ "column":"<AnyAlwaysPresentCol e.g. X_Company>", "condition":"<>", "value":"'?{<FV>.SearchGate}'" }
```
Init/Reset set `SearchGate=""` → `?{}` empty → whole query blocked. Search button event: optional "at least one filter" condition (`"expression":"'{<FV>.C1}' !== '' || '{<FV>.C2}' !== '' || ..."`, `onFailure` → `{"type":"erp-message-handler","param":{"type":"Toast","level":"warning","message":"\"Enter at least one search filter.\""},"option":{}}`), `onSuccess` → `row-update` `SearchGate="XXX"` (never equals a real company ⇒ clause always true) → `event-next refresh_<GV>`. Optional auto-gate: trigger `{"type":"DataTable","hook":"columnChanged","target":"<FV>Tbl","columns":[...all filter cols]}` that opens the gate the moment the user types anything (DataTable triggers target the TABLE name, never the view id).

### D.5.4 Saving dirty UBAQ rows / custom actions
Plain save (= classic Save / `BAQUpdater`; `allRows:true` = classic MultiDirtyRow):
```jsonc
{ "type":"erp-baq", "mode":"update", "baqId":"<UBAQ>", "alias":"<GV>", "executeOptions":{},
  "updateOptions":{ "operation":"UpdateBaq", "allRows":true } }
```
Named custom action (classic Ship/Pick/print ViewButtons — the converter emits exactly this):
```jsonc
{ "type":"rest-erp", "param":{ "requestMethod":"POST", "erpRequestMethod":"UpdateBaqCustomAction",
  "erpBaqArgs":{ "baqId":"<UBAQ>", "options":{ "populateDataView":true,
    "updateOptions":{ "operation":"UpdateBaqCustomAction", "actionID":"<QueryCustomAction.ActionID>", "viewName":"<GV>" } } } } }
```
Editable grid: `gridModel.editable:true` + per-column `editable:true` on exactly the classic Grid-prompt column set. The generated multi-view Update button wraps the rest-erp in `{"type":"switch","value":"'%currentDataView%'","param":{"cases":[{"value":"'<GV>'","actions":[...]}]}}` — when hand-authoring per-button saves, call `erp-baq` directly instead (currentDataView may not be your grid at click time).

### D.5.5 Row selection + mass-assign (classic "check rows, set value, save")
Grid model: `"selectable":true, "selectionOptions":{"showCheckBox":true,"showSelectAll":true}` + hidden selector column in `columns`: `{ "field":"Calculated_Selector","selector":true,"skipRowChangeOnLinkClick":true,"hidden":true }` + on the BAQ **dataview**: `"additionalColumns":[{"columnName":"Selector","datatype":"boolean"}]`. Button event:
```jsonc
{"type":"dataview-condition","param":{"dataview":"<GV>","result":"matches","expression":"Calculated_Selector","iterativeEvent":"<IterEvent>"}},
{"type":"erp-baq","mode":"update","baqId":"<UBAQ>","alias":"<GV>","executeOptions":{},"updateOptions":{"operation":"UpdateBaq","allRows":true}}
// <IterEvent> (no trigger; runs over the matches set):
{"type":"row-update","param":[{"columns":[{"epBinding":"matches.<TargetCol>","value":"{<FV>.<ComboCol>}"}]}]}
```
`matches.<Col>` is the result-set binding. An empty combo writes `""` = classic "clear" behavior. This same pattern replaces classic CellChange check-group cascades.

### D.5.6 Master-detail (classic publish/subscribe)
```jsonc
"trigger": { "type":"DataView", "hook":"rowChanged", "target":"<ParentGV>" },
"actions": [ { "type":"erp-baq", "mode":"get", "baqId":"<ChildBAQ>", "alias":"<ChildView>",
  "executeOptions":{ "parameters":[ { "ParameterID":"<param>", "ParameterValue":"", "ValueType":"nvarchar", "IsEmpty":false, "SysRowID":"00000000-0000-0000-0000-000000000000", "RowMod":"" } ] },
  "baqParams":[ { "field":"<param>", "value":"<ParentGV>.", "type":"nvarchar", "isEmpty":false, "epBinding":"<ParentGV>.<KeyCol>" } ] } ]
```
The child BAQ carries a real parameter; classic ParentColumn/ChildColumn links map here (or to a `?{ParentGV.Col}` whereList item if you'd rather not add a parameter).

### D.5.7 Files/attachments, EFX, combos
Attachments: `erp-file-box` component (`epBinding:"<FV>.File"`, placed in `"<gridCardId>#expandedHeaderComponents"`) → button event `{"type":"file-transfer-erp","param":{"transferType":"upload","specialFolder":5,"serverPath":"Uploads\\{<FV>.File}","company":"<Company>","erpFileBoxID":"<fileBoxModelId>"},"onSuccess":[ erp-function ... ]}` → an **Epicor Function** does the Attachment/XFileRef/XFileAttch BO plumbing: `{"type":"erp-function","efxLibrary":"<Lib>","efxPath":"<Fn>","methodParameters":[{"field":"FileName","epBinding":"<FV>.File"},{"field":"PackNum","epBinding":"<GV>.<KeyCol>"}]}`, results via `{actionResult.Success}`/`{actionResult.ErrorMsg}`/`{actionResult.<Out>}`, errors → Toast. Downloads likewise via an EFX returning the file.
Combos, three variants: **BAQ combo** `{"queryId":"<BAQID>","valueField":"<ValCol>","textField":"<TextCol>"}` (maps classic BAQCombo `DynamicQueryID`+`ValueMember`+`DisplayMember`); **shared $ref combo** `{"appDesignerComboType":"../shared/combo/<X>.<Y>Combo/default/combo.jsonc#/combo","$ref":"<same>","appDesignerComboOverride":true,"epBindingTextColumn":"<FV>.<DescCol>","filtersAppend":["CodeTypeID = 'PartTran'"]}` (path depth `../shared/...` from layout, `../../shared/...` from a Pages file); **full svc model** per `references/components.md` §6 when neither fits.

### D.5.8 Cosmetics that bite (verified)
- `erp-button` **`style:1` renders as a TEXT LINK** — omit `style` for the standard blue button; use `style:1` deliberately for link-like actions (Reset).
- **Side-by-side cards** need BOTH `model.columnsWide:"ep-col-6"` AND component-level `layoutData:{"flexLayout":true,"hostId":"<layout.name>"}` — missing either stacks them full-width. `metafx-panel-card-stack` (`model.panels:[{id,name},...]` referencing sibling card ids) = tabbed/stacked cards (classic dockable panes).
- Grid card `actionData` entries: `{id:"<eventTargetId>", description, icon:"mdi mdi-content-save"|"mdi mdi-magnify"|..., showInToolBar:true|false}` (+ optional `userData:{tag:"Update",epBinding:"<GV>",type:"Control",pageLevel:false}`); the id is the Control-onClick event target.

## D.6 Debugging dashboards

- **Debug wedge**: event on an always-rendered component — trigger `{"type":"Control","hook":"onInit","target":"<gridCardId>"}`, action `{"type":"console-write","value":"#_epDebug.setDebugModeStatus(true)_#"}` → verbose Kinetic event/binding/dataview console logging. Add `console-write` traces in suspect events; `{View.Col}` tokens evaluate inside the trace string.
- **Preview noise (expected, harmless)**: `CheckMenuSecurityForUser 400 "Could not find the UI application for the provided menu"` and a null `WebResourceURL` TypeError — the app has no menu record yet.
- **Preview works, real MENU launch fails** with a generic "unexpected internal problem" + Correlation ID → malformed `imports` block in a base-app file (strings.jsonc item key must be `default`); server log shows `InvalidCastException: JArray→JObject` at `Translation.MergeWithGeneratedString` in `GetApp` — a path that never runs in preview. Fix per D.7 / lessons §23. **A passing preview is not sign-off; always test a real menu launch** and pull the server log by Correlation ID on generic failures.
- Symptom table: all filter fields disabled → view has no row (D.5.2) or init never ran (preview `autoload=false`); grid runs on load despite "gate" → autoLoadGrid used instead of the `?{}` token (D.5.3); import 400 with EF text inside the "Base application for ..." message → record write failed (D.4.2); cards stacked → D.5.8; buttons look like links → D.5.8; change "didn't take" → draft block differs / stale-download patch / App Studio open (D.4.2); crumb-bar `reading 'split'` crash → null navigation.epBinding; view silently missing after import → bad `additionalColumns.datatype` (SQL type instead of Kinetic token) or missing dataview keys.

## D.7 Paste-ready base-app skeletons (single updatable query; `<X>`=app suffix, `<GV>`/`<TV>` views, `<BAQ>` id)

All files CRLF jsonc. The layout guid `2dcd1674-5e34-4d98-b493-c75747027376` is the fixed dashboard-template guid observed on every generated/hand-built dashboard — reuse it.

**dataviews.jsonc**: `{"$schema":"https://schemas.developer.epicor.com/schemas/v4.0/dataviews.json","contentVersion":"4.0","imports":[{"dataviews":{"$ref":"../shared/imports/UIDashboards/base/dataviews.jsonc#/dataviews"}}],"dataviews":[{"id":"<GV>","table":"<GV>","schema":"baq","datasetId":"","data":"<BAQ>"},{ <FV per D.5.2, id "<TV>"> }]}`

**layout.jsonc**: `{"$schema":".../v3.0/layout.json","contentVersion":"3.0","layout":{"name":"<X>","guid":"2dcd1674-5e34-4d98-b493-c75747027376","caption":"<Caption>","viewType":"Dashboard","pageType":"Responsive","namespace":"Ice.UIDbd.<X>","navigation":{"pageCaption":"","tabId":"","enable":false,"parentPage":null,"epBinding":"","epBindingLevel":0,"epBindingPeerOrder":0,"dataSetId":"%datasetId%"},"components":[ <filter card per D.5.2 with columnsWide/layoutData>, <metafx-panel-card-grid: model {id,guid,title,expanded:true,autoFillContainer:false, gridModel:{height:600,scrollable:"virtual",pageSize:100,sortable:true,resizable:true,editable:true, providerModel:{description:"<BAQ>: Summary",isDefault:true,serverPaging:true,epBinding:"<GV>",baqId:"<BAQ>",baqOptions:{where:"",whereList:[gate + ??{} filters]},columns:[full list]}, columns:[full list]}, actionData:[{id:"btn_Update_<GV>",description:"Update",icon:"mdi mdi-content-save",showInToolBar:true}], headerComponents:[],expandedHeaderComponents:[],fullScreenButtonVisible:true}> ]}}`. With `serverPaging:true` the columns list must be COMPLETE; per column `{field,title,sortable,filterable,resizable,editable,groupable,hidden,visibleIndex}`; whereList string tokens quoted `"'??{<TV>.Col}'"`, dates/numerics unquoted, numerics may carry `emptyValue:"0"`. Generated apps also emit `honorNull:false,emptyValue:null` on whereList items — tolerated there; the minimal `{column,condition,value}` form also works and is preferred when hand-authoring.

**events.jsonc** (v5.0, imports shared UIDashboards events): `search_initialize_<TV>` (data-clear + row-add per D.5.2, optionally with console-write traces), `btn_reset_page_search_<TV>` (Control onClick → event-next init), `btn_run_search_onClick` (D.5.3 gate open + `event-next refresh_<GV>`), `btn_Update_<GV>` (D.5.4), `refresh_<GV>` = `{"type":"property-set","param":{"component":"<gridCardGUID>","props":[{"prop":"invalidated","value":"true"}]}}` (**THE grid-refresh idiom** for BAQ provider grids), `window` (`Window onLoad` → event-next init), `executeRefreshAll` (event-next each refresh), `EnableDebug` (D.6 wedge, chaining event-next init so preview works).

**patch.jsonc**: `{"patch":[{"id":"svc","value":"Ice.BO.DynamicQuerySvc"},{"id":"param","value":""},{"id":"paramModel","value":""},{"id":"maintProgram","value":""}]}` (+ schema/contentVersion 2.0). **rules.jsonc / strings.jsonc / tools.jsonc**: empty arrays/objects + the matching `../shared/imports/UIDashboards/base/*` import (versions 3.0/3.0/2.0). **Import item KEYS are per-file and exact (VERIFIED vs schema + a real generated dashboard): `rules`/`tools` match the file name, but `strings.jsonc` uses `default`** (`{"default":{"$ref":"../shared/imports/UIDashboards/base/strings.jsonc#/strings"}}`). A guessed key (e.g. `strings`) passes preview but 500s every real menu launch (`InvalidCastException JArray→JObject` in `Translation.MergeWithGeneratedString` during `GetApp`). If there's no shared content to merge, `"imports": []` is equally valid — never invent import shapes (lessons-learned.md §23, uplift-and-debugging.md §3).

**Optional slider tracker** (generated style, if not building inline): `Pages\<TV>.layout.jsonc` with `viewType:"page"`, `navigation.parentPage:"<X>"`, `width:"500px"`, prompt fields in row/col wrappers + `btn_reset_page_search_<TV>`; opened via `{"type":"slider-open","param":{"page":"<TV>"}}` from a grid actionData search (magnify) button.

## D.8 Canonical dashboard uplift workflow

1. **Classic inventory** (write it down): pull the dashboard definition; per query record BAQ, caption, primary, pub/sub links, Grid flags + ViewButtons→action IDs, Grid-prompt (=editable) columns, Tracker prompts + CriteriaRequired; pull the customization (or confirm the 400-not-found); pull each BAQ (custom actions, `Updatable` fields, parameters); for updatable ones pull the UBAQ BPMs; harvest helper BAQs (D.1.4).
2. **Base app**: `GetNativeKineticApp("Ice.UIDbd.<ID>")`. Files populated → verify against inventory, layer on top. `Files:{}` → either a user opens it once in Kinetic/App Studio (auto-convert), or **generate the base yourself** (D.7) and import (D.4.1). Keep the BASE classic-faithful: native tracker prompts (inline, per the classic dock layout), gate, grid columns/editability. Put the classic CUSTOMIZATION in the LAYER.
3. **Layer**: bootstrap per D.4.2 (blank create → download → fill), then build: mass-update panels, selection+iterate+save, extra buttons/events, cosmetics, explicit Move ordering. `MCPToolsKinetic-Commit` with a clear comment around every import. **Company scope applies here too** — the once-per-session Current Company / All Companies / other pre-ask from SKILL.md round-trip step 7 (`InCompany` on `MCPToolsKinetic-ImportLayer`; lens-mcp-tools.md).
4. **Test loop**: user opens preview (remember `autoload=false` — onInit-chained init is mandatory) or a menu item with the console open; ship the debug wedge during development; on issues consult D.6; fix → **re-download** → patch → import → commit. Quiet trace writes when stable.
5. **Call out deferred items**: classic native-form launches (e.g. DynAttrValue/PA_1 attribute editors) have no clean MetaFX equivalent — defer with user sign-off; local-file `Process.Start` flows → downloads/EFX; one classic dashboard may map to several Kinetic apps with different names — always confirm the target app id.
