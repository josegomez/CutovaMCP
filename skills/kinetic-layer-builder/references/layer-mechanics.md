# App Studio & Layer/Diff Mechanics — Reference

Derived from observed runtime behavior and App Studio output. Where this refines the existing `kinetic-layer-reference.md` or `lessons_learned.md`, it is flagged inline with **⚠ CONTRADICTION** or **✔ CONFIRMS**.

Scope note: the diff/merge engine itself is **server-side** (`Ice.LIB.MetaFXSvc`). The client side exposes the complete *contract*: the `Difference`/`DiffOperation` types, the compare/revert engine that re-applies diffs in the designer, the save/publish pipeline, and every runtime model the diffs target. Those are documented exhaustively here.

---

## 1. Architecture: where layers are merged and diffed

### 1.1 The server does ALL merging and ALL diff generation

- **Runtime load**: the client calls `Application/GetApp` (service `Ice.LIB.MetaFXSvc`, or `Erp.BO.ErpMetaFxSvc` for configurators) with `{id, mode, deviceType, pageName, layers[], layerType, debug, segments, ...}` and receives a **fully merged** `MetaFxView` (Layout, Pages, Events, Rules, DataViews, Toolbar…). The client never applies layer diffs at runtime.
  - Service names: `Ice.LIB.MetaFXSvc` and `Erp.BO.ErpMetaFxSvc`.
- **Designer save**: App Studio does **not** compute the layer diff. `SaveApp` is posted the **entire current application** (`application: {DataViews, Events, Layout, Pages, Rules, Toolbar}`) plus `layerInfo` (`layerType, layerName, parentLayers, WIP, isNew, publishParentLayers, deviceType`). **The server diffs it against the base (or the parent-layer-merged result) and stores the `{Id, Path, Value, Operation, Index}` diffs.**
  - Save request shape (`EpMetaFxSaveRequest`): `layout, pages, orphans, rules, tools, events, dataviews, layerInfo, serializedEvents, viewType, applicationType, uxAppVersion, properties, configuratorInfo`.
- **Consequence (⚠ refines the mental model in the existing reference §1):** "App Studio emits a Move cascade when you drag" is really "*the server* emits the Move cascade" — App Studio just posts the re-ordered full components array and the server serializes the difference. That is also why **physical array order of the diffs is authoritative**: the server writes diffs in document order and re-applies them in order (see §2.5).
- The only client-side JSON diffing is `jsondiffpatch` (dirty checking, undo, `hasChanges()`), unrelated to the layer format: `hasChanges()/hasEventChanges()/hasRowRuleChanges()/hasDataViewChanges()` all use it.
- Before SaveApp the client **trims properties that equal designer defaults**, so a saved layer only carries meaningful values.

### 1.2 Server endpoints (client-visible contract)

| Endpoint (svc/svcPath) | Purpose | Key payload fields |
|---|---|---|
| `Application/GetApp` | load merged app (base + layers [+ personalization]) | `id, mode ('' runtime / 'AppStudio'), deviceType, layers[], layerType, pageName, debug, segments` |
| `Application/SaveApp` | save base draft **or** save a layer (draft or publish, per `layerInfo.WIP`) | full application + `appStudio{serializedEvents, viewType, deviceType}` + optional `layerInfo` |
| `Application/Publish` | publish a **base app** | `{id, segments}` |
| `Application/GetList` | list apps (+ their layers) | returns `hasDraftContent`, `systemFlag`, `subType`, `publishStatus`, `layers[]` |
| `Application/GetSystemApplicationStatus` | `{CreatedBy, SystemFlag, CanAccessBase}` | |
| `ApplicationLayer/GetList` | list layers for an app | `{id, layerType, deviceType, includeDraftContent}` |
| `ApplicationLayer/GetByID` | one layer | `{id, layerType, layerName, deviceType, parentLayers}` |
| `ApplicationLayer/Delete` | delete a layer | `{layerType, layerName, deviceType, parentLayers, id, segments{Company,CGCCode}}` |
| `ApplicationLayer/BulkPublishLayers` | publish many layers | `{layers[], validateBeforePublish}` |
| `ApplicationHistory/GetList` | audit/version log | `{id, layerName, historyType, segments}` |
| (designer) `GetAppDifference` | version compare — returns `{left, right, diff[], hasDraft, hasPreviousBase}` | |

All are served by `Ice.LIB.MetaFXSvc` (or the UX platform path equivalent).

### 1.3 The GetApp request model (every field)

`EpMetaFxViewRequestProperty`:

| Field | Meaning |
|---|---|
| `layers: string[]` | layer names to apply, e.g. `["CSF-India", "CUS-NoPurchaseContacts"]` — **applied in array order** |
| `deviceType` | `'Desktop' | 'Phone' | 'Tablet'` |
| `mode` | `''` (runtime) or `'AppStudio'` (returns Draft* collections too) |
| `pageName` | optional page scope |
| `layerType` | `KNTCCustLayer` / `KNTCPersLayer` |
| `debug`, `checkDuplicateIds` | debug logging / dup-id validation |
| `applicationType` | `'view' | 'component'` |
| `applicationSubType` | `Configurator | Report | Process | Dashboard | Apps | Shared` |
| `baseAppVersion`, `layerVersion` | load a specific version (version history) |
| `ignorePersonalization` | **skip the user's personalization layer** (used by the personalization editor when loading the clean state) |
| `additionalContext` | `{menuId, inPreviewMode, ...}` |
| `includeWasm`, `comment` | configurator / save comment |

Route → request wiring: the `layerNames` query param is split on `,`, plus `baseAppVersion`/`layerVersion` query params.

### 1.4 What GetApp returns — `MetaFxView`

| Field | Notes |
|---|---|
| `Layout` | `MetaFxLayoutSchema` — the app envelope (§5.1) |
| `Pages[]` | one `MetaFxLayoutSchema` per page |
| `Orphans[]`, `HasOrphans` | pages/components orphaned by layer upgrades (shown in App Studio's Orphans panel) |
| `Events[]`, `Rules[]`, `DataViews[]`, `ToolBar[]` | merged behavior sections |
| `DraftLayout/DraftEvents/DraftRules/DraftDataViews` | **only in `mode:'AppStudio'`** — the unpublished draft copies |
| `PatchInfo[]`, `PatchTokens` | patch bookkeeping (§10) |
| `Properties[]` | exposed public properties of components |
| `References[]` | external JS/WASM deps |
| `IsLayerDisabled`, `AllowVersions`, `Wasm`, `ConfiguratorInfo` | flags |
| `ServerErrorCode`, `ServerErrors[]` | e.g. `PERSONALIZATION_LOAD_ERROR` → client offers to delete the broken personalization layer |

Runtime toolbar entries get `parentId: 'epview'` stamped client-side, and items with `mode:'D'` are filtered out of Events/Rules/DataViews/ToolBar before use (§4).

---

## 2. The diff wrapper — exact semantics

### 2.1 The `Difference` type

This is the wire type the server uses for `GetAppDifference`, and the superset of what a layer `.jsonc` diff entry carries:

```jsonc
// Difference
{
  "FullPath":  "string",  // compare-only: absolute path incl. category, e.g. "Pages/Details/pcOrderDetail/model/hidden"
  "Id":        "string",  // the target object's id (component id, event id, rule id, ...)
  "Index":     0,         // ordinal; -1 marks the halves of a Move pair in compare payloads
  "Operation": "Add",     // DiffOperation
  "Path":      "string",  // relative path: "", "components", "/model/hidden", "/navigation/epBinding", ...
  "Value":     null,      // the payload (full object for Add/Replace-of-object; scalar for property diffs; null for Move)
  "PreValue":  null,      // compare-only (optional): the previous value (for revert display)
  "reverted":  null       // compare-only (optional): RevertOption
}

// DiffOperation
//   Remove  = 0
//   Add     = 1
//   Replace = 2
//   Move    = 3
```

**Facts this settles:**

- **All four Operations exist**: `Remove`, `Add`, `Replace`, `Move`. The enum name is **`Remove`, not `Delete`**. In layer `.jsonc` files Operation is serialized as the enum **name string** (`"Add"`, `"Replace"`, `"Move"`, `"Remove"`); the numeric values above are the server enum ordinals. **✔ CONFIRMS** lessons §9/§10 that `Move` is real; **⚠ CONTRADICTION** with the old reference §2 diff-grammar table which listed only `Add|Replace`.
- A layer `.jsonc` diff entry is the same shape minus the compare-only fields (`FullPath`, `PreValue`, `reverted`) — matching the verified wrapper `{Id, Path, Value, Operation, Index}` (**✔ CONFIRMS** lessons §3p that all five keys are required; a bare `{Operation, Value}` is malformed).

### 2.2 Legal `Path` values (grammar)

| Path form | Meaning |
|---|---|
| `""` (empty) | the diff targets a **whole top-level item** in a flat section (event, rule, dataview, tool): `Value` = the entire object, `Id` = its `id` (lessons §3p wrapper; compare maps such diffs by `Id` when `FullPath` is empty) |
| `"components"` | the diff targets a **component node** in a page's flat components list: Add (Value = full component), Replace (Value = full component), Move (Value = null). Nodes are matched by `model.guid`/`id`; synthesized new-page child diffs get `Path: 'components'` |
| `"/model/<prop>"` | **property diff**: replace/add one model property (e.g. `/model/hidden`). Revert walks the `/`-separated segments and restores `PreValue`; version history strips `'/model/'` when mapping property diffs to the property panel |
| `"/navigation/<prop>"` | **page-level property diff** (e.g. `/navigation/epBinding`, `/navigation/parentPage`, `/navigation/dataSetId`, `/navigation/pageCaption`). Version history explicitly looks for `Path === '/navigation/parentPage'` |
| `"/<prop>"` | page/layout scalar property diff (e.g. `/caption`, `/name`). Same path-walking revert; `name` is special-cased to fix `navigation.parentPage` references on other pages |
| tool property path e.g. `"/text"` | on ToolBar diffs, `Path.split('/').join('')` is used as the tool property key |
| internal/system paths | `'/layoutData'` (Add), `'/layoutData/hostId'`, `'/mode'` — machine noise, filtered from the compare UI |

`FullPath` (compare payload only) is `<Category>/<...>`: categories are `Layout`, `Pages` (then page name), `Events`, `Rules`, `DataViews`, `ToolBar`, `Orphans` (`NodeCategory` enum). Path traversal skips a literal `model` segment when walking component trees.

**Property-path diff vs full-component Replace:** both are legal on components. A property diff (`Path:"/model/hidden"`, `Value:true`) touches exactly one property; a full Replace (`Path:"components"`, `Value:{...full component...}`) swaps the whole node — the revert engine handles these as distinct cases. **✔ CONFIRMS** lessons §10 ("hide a card with a `/model/hidden` property diff") and §3o (Replace-with-full-component for a base control).

### 2.3 How Replace/Add/Remove resolve targets by `Id`

Node matching in the compare engine (which mirrors the server's application logic) resolves in this priority order:

1. component: `model.guid` equality, then `id`, then `Path`, then `Name`/`name`;
2. pages: by `guid`;
3. Events/Rules/DataViews/ToolBar items: by `id`.

So a `Replace` on `Path:"components"` finds the component whose `id` (or `model.guid`) equals the diff's `Id` and substitutes `Value` wholesale. `Add` inserts `Value` (new node); `Remove` deletes the node with that `Id`. For flat sections (events etc.) the same by-`id` resolution applies.

### 2.4 `Move` semantics

- In the compare payload a Move appears as a **pair of diffs with the same `Id`, opposite `Operation`s (`Add`+`Remove`), each with `Index === -1`**; the UI hides them (the compare view filters `Operation === Move`, and pairs halves via `Index === -1 && same Id && opposite Operation`).
- In a **layer `.jsonc`** a Move is a single entry `{"Id":"<compId>","Path":"components","Value":null,"Operation":"Move","Index":<n>}` (**✔ CONFIRMS** lessons §10 verified shape; the client never constructs these — the server emits them when the saved array order differs from base).

### 2.5 `Index` vs physical array order

- **Nothing client-side sorts or positions anything by the diff `Index`.** It is used only as: (a) the `-1` sentinel marking Move pairs in compare payloads (§2.4); (b) `Index: 0` on client-synthesized diffs for new-page children.
- The merge happens server-side; the empirically **VERIFIED** behavior (lessons §3a/§10, App Studio drag round-trip) is that **sibling render order = the physical order of the diff objects in the section's `Diffs` array**, with `Index` cosmetic/bookkeeping. Nothing observed contradicts that; the compare view treating `Index` purely as a marker **✔ CONFIRMS** it is not an ordering key.
- Practical rule stands: to reposition a component, physically move its diff within the `Diffs` array (and keep `Index` ascending for hygiene); an `Index`-only edit is a no-op.

### 2.6 New pages as diffs

A brand-new page appears in the compare stream as a single `Add` at `FullPath: "Pages/<PageName>"` whose `Value` is the **entire page object**. When the designer needs per-child diffs for display it synthesizes them by walking `Value`. **✔ CONFIRMS** the reference §2 table: a new page = its own manifest section with one `{Id:null, Path:null, Value:<entire page>, Operation:"Add"}` diff (section-level `Operation:"Add"`), and explains why page-level nav diffs have no component `Id` (lessons §3aa methodology trap).

### 2.7 The manifest section wrapper `{Name, Version, Diffs, Operation}`

The section wrapper and its `Version` strings (`layout/pages 3.0, events 5.0, rules 3.0, tools 2.0, dataviews 4.0, config 2.0`) are a **server/storage format** — `contentVersion` and those version literals are not used client-side. The client never validates them; validation/rejection happens in `Ice.LIB.MetaFXSvc`. Keep treating the version numbers and the section-level `Operation: "Add"` (new page) / implicit `"Modify"` as **empirically verified** (lessons §9, reference §2).

Similarly, the **layer zip format** (`Layers/<App>/<Layer>.jsonc`), `TypeCode KNTCCustLayer` record with `Key1=layer, Key2=app, Key3=Desktop`, and the `SysCharacter03` (import) vs `Content` (published export) storage split are server-side facts — the client only knows `TypeCode` strings (§3.1) and an opaque `ILayer.Content` dictionary (`IContent`). **Nothing client-side contradicts lessons §3i.**

---

## 3. Layer records, types, parents, precedence

### 3.1 Type codes and delimiters

| Constant | Value | Notes |
|---|---|---|
| Customization layer TypeCode | `'KNTCCustLayer'` | |
| Personalization layer TypeCode | `'KNTCPersLayer'` | |
| Layers delimiter | `','` | multiple layer names in the route query param `layerNames` |
| Layer-names delimiter | `'^'` | inside a personalization LayerName: `"<user>^<parent-layer-info>"` — UI shows `split('^')[0]` |

### 3.2 The `ILayer` record (client view of a layer)

| Field | Meaning |
|---|---|
| `TypeCode` | `KNTCCustLayer` / `KNTCPersLayer` |
| `ViewId` | app id (e.g. `Erp.UI.SalesOrderEntry`) |
| `LayerName` | layer name; is the user name in Personalization |
| `ParentLayers: string[]` | if parent layers exist, the diff is applied based on the parent-layer JSON; otherwise it is applied to the base JSON — i.e. a layer's diffs are computed & applied against base+parents, giving the precedence chain |
| `WIP: boolean` | work-in-progress flag → **draft vs published** (§3.4) |
| `HasDraftContent` | there is unpublished draft content (**✔ CONFIRMS** lessons §3h) |
| `UpgradeStatus`, `UpgradeError` | layer upgrade state after base-app version changes |
| `CGCCode` | Country-Specific-Functionality group code (CSF layers); only one CGC customization layer allowed per code (enforced at save) |
| `Company` | company scope ('' = all) |
| `PublishParentLayers` | publish parents together with this layer |
| `IsNew`, `SystemFlag`, `CreatedBy/On`, `LastUpdatedBy/On`, `CommentText`, `DeviceType` | bookkeeping |

`ILayerAndView` (app-list rows) adds `IsPublished`, `PublishError`, `IsLayerDisabled`, `StatusType (Published|Upgrade|Deleted|Success)`.

### 3.3 Precedence order

Effective order for a running app: **base app → customization layer chain (each layer diffed/applied on top of its `ParentLayers` result, in the `layers[]` array order of the GetApp request) → the user's personalization layer** (applied automatically server-side per user unless `ignorePersonalization: true`).

Evidence:
- `ParentLayers` semantics (§3.2).
- The runtime request sends only customization layer names; personalization is not in `layers[]` yet applies (the personalization editor must pass `ignorePersonalization` to see the pre-personalization state).
- Personalization save posts `ParentLayers = <active customization layer names>` (§3.5), so each customization-layer combination gets its own personalization record.
- Dependent-layer computation walks `ParentLayers` recursively; deleting/editing a layer warns about dependents including personalizations.

### 3.4 Draft vs published — the `WIP` flag

- **Save** (toolbar Save in App Studio, layers enabled): SaveApp with `layerInfo.WIP = true` → content goes to the **draft** track; `HasDraftContent` becomes true.
- **Publish**: same SaveApp endpoint with `WIP=false` → **publishes**. If any parent layer has draft content, the user is asked whether to `PublishParentLayers` (the parent chain is walked to detect draft content).
- Base apps (no layers) use `saveDraft` then the separate `Application/Publish` endpoint with a "not reversible" warning.
- Bulk publish: `ApplicationLayer/BulkPublishLayers` (permission gates: `canPublishLayer` for `KNTCCustLayer`, `canPublishDashboard` for SubType `Dashboard`, `canPublishBase` otherwise).

**✔ CONFIRMS** lessons §3h: published and draft are separate tracks; a published-layer export won't include draft work; `IncludeUnpublishedLayers`/`includeDraftContent` on `ApplicationLayer/GetList` surfaces `HasDraftContent`.

### 3.5 Personalization layers (KNTCPersLayer)

- **Personalization saves ONLY layout + pages.** The save request hardcodes `events: [], rules: [], dataviews: [], tools: []` and `LayerName: ''` (the server keys it to the current user), `IsNew: true`, `ParentLayers = <active customization layers>`. The same shape is used both from the personalization panel and from App Studio's layer-selection save path.
- Personalization can be **promoted** to a customization layer, optionally merging standalone **KineticGridLayout** grid personalizations (compressed with `lz-string`, fetched via `Ice.BO.KineticErpSvc/GetSpecificUserSettingsForView`) into the panel-card-grid models first.
- Broken personalization on load: server returns `ServerErrorCode = PERSONALIZATION_LOAD_ERROR`; client offers Yes/No delete of the personalization layer (delete request carries `parentLayers` + `pageName`).
- Toolbar tool ids overridable by host apps: `'personalization'`, `'customization'`.

### 3.6 App Studio launch / preview

- App Studio (layers mode) is entered with query params `layerNames` (comma-joined) + `layerType`; these are parsed and all layers are loaded with `IncludeUnpublishedLayers: true`.
- **Preview** opens the real app in a new tab with `{preview:'true', layerNames, layerType, layerVersion, baseAppVersion, autoload}`. Preview shows the **draft** content (server resolves WIP for the requesting session).
- Version history/compare: `GetAppDifference` returns `{left, right, diff, hasDraft, hasPreviousBase}`; the dropdowns offer *Current Base / Previous Base* vs *Draft Version*. Draft comparison is only offered when `HasDraftContent`.

---

## 4. Item lifecycle: `mode`, `customizable`, locking

### 4.1 `mode: 'A' | 'U' | 'D'`

Present on events, rules, dataviews, tools (e.g. `IMetaFxEvent.mode`, `MetaFxDataView.mode`). Semantics:

| Value | Meaning |
|---|---|
| `'A'` | item **added** by this layer (a brand-new item). The designer treats an event as new when `mode === 'A'` and no existing item has that id; a dataview counts as changed when `mode === 'A' || mode === 'U'` |
| `'U'` | item is an **update/overlay of an existing (base or parent-layer) item**. The designer force-sets `mode='U'` the moment you edit an existing item. **The id cannot be changed on a 'U' item**; the dataview id field is disabled when `mode==='U'` |
| `'D'` | item **deleted** by this layer. Runtime filters `mode !== 'D'` everywhere: events, rules, dataviews (the view is never created), tools |

**✔ CONFIRMS + refines** lessons/reference §7.1: `"mode":"A"` for your own new items is correct; `"U"` isn't just "shows locked" — it is the marker for *overlay of an existing item* and freezes the id. A `"D"` entry is how a layer deletes a base event/rule/dataview/tool without a Remove component diff.

### 4.2 `customizable` / `personalizable` — locked items

- **Runtime designer lock**: an item with `customizable !== true` while editing a **layer** (`useLayers`) is read-only and gets a **lock badge** (`mdi-lock`, text "locked"):
  - events: an event is read-only when `customizable !== true` and layers are in use, and shows the lock badge. `baseModified` adds a "modified base event" badge.
  - components: read-only when `comp.model.referencedControlId` is set (shared/referenced controls) **or** (`customizable === false` **and** layers enabled). `customizable === undefined` defaults to **true** (editable). The layout designer and property designer both honor this (the property panel goes read-only).
- **Property-panel behavior** (common designer property rules):
  - `updateCanCustomizeRule`: when `customizable = false` → the `personalizable` checkbox is disabled **and forced to false** (not-customizable implies not-personalizable).
  - `hideCustomizable`: when `useLayers` is true → the `customizable` checkbox itself is **Invisible**. **⇒ You cannot flip `customizable` from inside a layer in App Studio** — it is a base-app author's switch; layer authors must set it in JSON. (**✔ CONFIRMS** lessons §3e practice of always emitting `customizable:true` in generated items.)
- Every designer property model defaults `customizable: true, personalizable: true` (e.g. toolbar and row-navigator property models).

---

## 5. Layout, pages & navigation model

### 5.1 `MetaFxLayoutSchema` — every field (layout.jsonc / pages/*.layout.jsonc payload)

| Field | Type / values | Notes |
|---|---|---|
| `name`, `namespace`, `caption`, `guid` | | `namespace` only on the app layout (e.g. `App.AbcCodeEntry.AbcCodeForm`) |
| `viewType` | app: `'Apps'`, `'Dashboard'` (also TRACKERS/ENTRY/MAINTENANCE/REPORT/PROCESS template keys); pages: `'Page' | 'Peek' | 'TabPage' | 'Tab' | 'VirtualPage' | 'SlidingPanel' | 'Configurator'` (`PageViewType` enum) | **⚠ DISCREPANCY**: the existing reference §2.2 documents slide-out pages as `viewType:"Slideout"`. The client enum value is **`'SlidingPanel'`** and runtime filters check `viewType !== 'SlidingPanel'`. If shipped apps show `"Slideout"`, verify per-app — the client only special-cases `SlidingPanel`, `Tab`, `TabPage`, `VirtualPage`. |
| `pageType` | `'Responsive' | 'Absolute' | ''` | `Absolute`/empty ⇒ legacy/unpublished |
| `width`, `height`, `enableFullWidth`, `flexLayout`, `disableUiLocking`, `maxItemsInToolBar` | | `maxItemsInToolBar` default 6 |
| `components[]` | flat list of `{id, sourceTypeId, parentId, model, components?}` | |
| `titleBadgeModel`, `heroBar` | | hero bar (status strip) |
| `navigation` | see §5.2 | |
| `navigationTabTree` | custom tree template for a tab | registered per `navigation.tabId` |
| `slidingPanel` | `{status, hideClose, collapseOnOutsideClick, showButtons, showTitle, buttons[{...IEpButtonModel, dialogResult}], actionData[], hideTools}` | slide-out page chrome |
| `pageSeq`, `readOnly`, `reversedPrimaryButtons` | | |
| `skipOnLeaveOPE/OPL`, `skipPageNoInputs`, `isConfigurator` | configurator paging | |
| `isVisibleInLegacyTree`, `parentCardStackId`, `virtualPageType`, `isOrphanPage`, `fitToPageMode` | virtual-page / orphan metadata | |

### 5.2 The `navigation` object (page & app level)

```jsonc
"navigation": {
  "dataSetId": "",            // dataset for the page
  "entityType": "",
  "enable": false,            // on the 'Tab' page: enables the whole nav system (sysPages/sysTabs are built only then)
  "parentPage": "",
  "epBinding": "",            // "View.Column" (may be comma-separated multi-key: "OrderHed.OrderNum,OrderHed.OrderDate")
  "pageCaption": "",          // caption template with {View.Column} tokens
  "epBindingLevel": 0,
  "epBindingPeerOrder": 0,    // sibling sort order — App Studio sorts Pages by this
  "tabId": "",
  "topRowTemplate": [],       // IEpCreateComponentActivityData[]
  "extendedProps": { "disableCallLog": false, "disableMemos": false, "disableChangeLog": false, "disableAttachments": false, "disableBPMHoldBadge": false },
  "expandInNavigation": 0,
  "expandNavigationLevels": 0
}
// all properties optional
```

### 5.3 sysPages / sysTabs and the crumb bar — why null `epBinding` crashes

- If a page with `viewType === 'Tab'` exists **and** `tab.navigation.enable`, the runtime builds two system dataviews: `sysTabs` (from the Tab page's `metafx-tabstrip` component: `{tabId, tabName, page, defaultTab, epBinding}`) and `sysPages` (rows: `{pageId, parentPageId, epBinding, pageCaption, itemCaption, dataSetId, tabId, epBindingLevel, epBindingPeerOrder, ...extendedProps}`) — one row per app layout + each page except `Tab`/`SlidingPanel`. A page missing `dataSetId` inherits the layout's (`p.navigation.dataSetId || layout.navigation.dataSetId`). **Note: `epBinding` is NOT defaulted** — a null page epBinding flows into the sysPages row as null.
- **Crumb bar crash corroboration (lessons §3aa):** the crumb bar calls `.split(',')` on the sysPages row's `epBinding` in at least four hot paths with **no null guard**:
  - `loadDropDownItems()`: `const bindings: string[] = dataItem.epBinding.split(',')` — hit from `reLoadCrumb()` during `ngOnInit` → the on-load crash;
  - `setCrumbBarItemSelected()`: `this.dataView.dataRow().epBinding.split(',')` — hit from view-event subscriptions (RowChanged/ViewLoaded during **Refresh**) → the refresh spam;
  - binding registration (`parseBinding(...epBinding)` / `navDataItems[0].epBinding.split(',')`).
  So a `Replace` diff nulling `/navigation/epBinding` on any nav-visible page produces exactly the `TypeError: Cannot read properties of null (reading 'split')` in `reLoadCrumb → loadDropDownItems / setCrumbBarItemSelected`. **✔ CONFIRMS lessons §3aa root cause.** Fix remains: never null a page's `/navigation/epBinding` / `/navigation/dataSetId`; either omit the diff (base value stands) or set real values.
- `pageCaption` templating: `\{([^}]+)\}` tokens are extracted, each parsed as `View.Column`, the value read from the live dataview (date-formatting via extended properties), and the shell title set. Multi-binding `epBinding` values are joined with `' - '` for crumb descriptions.
- App Studio's **new page defaults**: `viewType` = `TabPage` (if current page is Tab/TabPage) else `Page`; `navigation = {enable:false, parentPage:<current>, epBinding:'', dataSetId:'', pageCaption:'', epBindingPeerOrder:<next>, tabId:<current tab>}` — note **empty strings, not null**.

### 5.4 Virtual pages (panel cards as nav nodes)

Every non-hidden panel card / panel-card-grid / card-stack / GL control panel on a `TabPage` becomes a **VirtualPage** sysPages row: `name` = card's model id (suffixed `-card` on collision with a real page), `epBinding` = the card grid's `gridModel.epBinding` (or the page binding), `virtualPageType` = Card/CardStack/List, plus a recursive `fields[]` index used by app search. Full-screen-visible legacy-tree membership: `fullScreenButtonVisible` or is-grid, and not hidden.

### 5.5 Auto-fix on load

If a page has exactly one root `metafx-panel-card` whose body contains a card/grid with `autoFillContainer: true`, the root card also gets `autoFillContainer = true`. (Context for the grid-height guidance in the reference §4.3.)

---

## 6. Tools (tools.jsonc model)

Tool object schema (designer template plus runtime usage):

```jsonc
{
  "id": "toolSave",
  "text": "Save",              // caption (designer alias: toolbartext)
  "icon": "mdi mdi-content-save",
  "imageUrl": "",
  "epBinding": "",             // optional binding handle (lets RULES target the tool)
  "shortCut": "",
  "sequence": 10,              // sort order
  "disabled": false,
  "showInToolBar": true,       // primary bar — mutually exclusive with:
  "showInSecondaryToolBar": false,
  "showInDataTree": false,
  "divider": false,
  "style": undefined,
  "sysType": undefined,        // 'personalization' | 'customization' for overridable system tools
  "parent": "",
  "parentId": "epview",        // runtime stamps this; designer filters by it
  "customizable": true,
  "personalizable": true,
  "mode": "A"                  // layer lifecycle flag (§4.1)
}
```

- `showInToolBar` / `showInSecondaryToolBar` are enforced mutually exclusive by designer rules.
- Runtime: `view.ToolBar.map(t => ({...t, parentId:'epview'}))`; tools with `mode:'D'` filtered; `sysTools` system dataview mirrors toolbar state so events/rules can drive tools.
- Rules can move controls into the toolbar: actions `SettingStyle.ShowInToolbar` / `SettingStyle.showInSecondaryToolBar` (§7) — note the **case difference** is real and verbatim.
- In version compare, ToolBar diffs are surfaced as **page properties** (`toolDiff`), keyed by tool `Id` with `Path` = `/`+property.

---

## 7. Rules (rules.jsonc) — full runtime contract

### 7.1 Rule object fields

```jsonc
{
  "id": "cr_RTPShapeGreen",
  "description": "...",
  "dataView": "TransView",          // scoping view (condition may reference other views)
  "condition": "OrderHed.ReadyToCalc = true",   // EpCriteria expression; EMPTY/absent ⇒ rule always applies
  "actions": [ { "action": "...", "epBinding": "...", ... } ],
  "disabled": false,                // note: rules use `disabled`, events use `disable`
  "mode": "A", "customizable": true,
  // dynamic (data-driven) rules:
  "listColumn": "RRColumn",         // column holding a delimited list of target columns
  "actionColumn": "RRAction",       // column holding delimited action names
  "targetDataView": "OrderHed",     // view the listed columns belong to
  "listDelimiter": "~",             // default '~'
  // delegate (function) rules:
  "function": "<js body or fn name>",
  "namespace": "<window global holding the fn>",
  "dependentFields": ["OrderHed.OpenOrder", ...]
}
```

- Disabled rules are skipped at runtime (`includeDisabled=false`) and `mode:'D'` rules removed.
- Rules with `listColumn`/`targetDataView` are **dynamic**: rebuilt whenever the listColumn/actionColumn value changes, targeting `${targetDataView}.${listedColumn}` per entry.
- Function rules: with `namespace`, resolves `window[namespace][function]`; without, `new Function(...dependentFields, function)` — a raw JS body in rules.jsonc. App Studio warns about performance.
- Conditions referencing sysPages get id rewriting (`pageId` → `realPageId`).

### 7.2 Complete action catalog

| `action` string | Effect | Params |
|---|---|---|
| `DisableColumns` | disable listed columns of the rule's dataview | `columns: ["Col1", ...]` (prefixed with dataview automatically) |
| `SettingStyle.Warning` / `.Ok` / `.Highlight` / `.Error` | field-level state color (Warning/Success/Info/Error) | `epBinding` |
| `SettingStyle.RowWarning` / `.RowOk` / `.RowHighlight` / `.RowError` | row-level state color | — |
| `SettingStyle.Disabled` | disable control(s) on binding | `epBinding` |
| `SettingStyle.ReadOnly` | read-only (maps to disableAction) | `epBinding` |
| `SettingStyle.Invisible` | hide control(s) on binding | `epBinding` |
| `SettingStyle.ShowInToolbar` / `SettingStyle.showInSecondaryToolBar` | surface the bound control/tool in the (secondary) toolbar | `epBinding` (exact casing as shown) |
| `SetColumnValue` | write `value` to the bound column | `epBinding`, `value` |
| `SetViewColumnValue` | write `value` to a view column (view-scope variant) | `epBinding`, `value` |
| `DisableRow` | disable the whole row/form except listed columns | `exceptTheseColumns: [...]` |
| `HidePage` | hide a page; **`executeOnFalseCondition = true`** (also runs to un-hide when condition is false) | `value` = page |
| `ChangeImage` | swap image on the bound control | `epBinding`, `value` |

**⚠ CONTRADICTION with lessons §4** ("Only SettingStyle.Disabled / Invisible / ReadOnly are valid setting styles"): the runtime accepts the **full list above** — 13 SettingStyle/misc actions plus DisableColumns/DisableRow/SetColumnValue/SetViewColumnValue/HidePage/ChangeImage. Unknown actions log `Action not implemented <name>` and are ignored — a misspelled action fails silently.

**✔ CONFIRMS** lessons §3c: rule actions resolve targets **by `epBinding`**, so every component sharing a binding is affected — bind custom controls to unique columns before ruling them.

---

## 8. Dataviews (dataviews.jsonc) — runtime model

`MetaFxDataView` (complete field list):

`id, description?, table?, staticFilter?, parent {parentDataview, parentColumns[], childColumns[]}, schema?, additionalColumns?, datasetId?, serverDataset?, serverTable?, memoTableName?, contextOverrideView?, isSystemView?, disableViewChangeEvents?, data? (BAQ id for schema:"baq"), tools? (IEpStdToolAction — new/delete tool config), sort? (IEpDataSort[]), columnProperties?, mode? ('A'|'U'|'D'), customizable?, confirmChanges? (defaults true for non-system views — MetaFxDataViewDefaults), attachInfo?`.

Runtime facts:
- **Dashboard difference:** if `Layout.viewType` equals `'Dashboard'` (case-insensitive), **every dataview gets `confirmChanges = false`** — no dirty-close prompt on dashboards.
- System dataviews auto-registered on every app load: `actionResult, searchResult, sysLicensedModules, sysTools, sysGlobalVariable, sysPages, sysTabs, CallContextBpmData, sysVariable, sysTreeNode, sysDragRows, sysGanttTasks, sysGanttSelectedRow, sysPublishedData, sysParams, sysDynamicReportParams`. Note `CallContextBpmData` is created as a **system** view here — the base app's use of its columns for status shapes (lessons §3c) sits on top of this. `TransView` is *not* in this list; it is an ordinary dataview shipped in ERP base apps.
- Deleted dataviews (`mode:'D'`) are never instantiated.
- Per-view data pushed to the ERP plugin layer includes `viewId, tableId, schema, datasetId, serverDataset, serverTable, memoTableName, data, tools, columnProperties, contextOverrideView, additionalColumns, attachInfo` — the full set of dataview keys the ERP side consumes.

---

## 9. Events (events.jsonc) — object model

- `IMetaFxEvent`: `{ id, description?, trigger?, actions[], mode? ('A'|'U'|'D'), customizable?, copyOfId?, baseModified?, disable? }`.
  - `disable` (not `disabled`) prevents execution (**✔ CONFIRMS** reference §7.1). `copyOfId` set when cloned; cleared on first open.
  - `baseModified` marks a modified base event (extra designer badge).
- `IMetaFxEventTrigger`: `{ type: MetaFxEventHookType, target?, hook: MetaFxEventHook, columns?, disableUiLocking? }` — `disableUiLocking: true` keeps the UI interactive during the event chain (not in the old reference).
- `IMetaFxEventAction`: `{ type, param?, value?, option?, epBinding?, dataview?, dataTable?, filter?, variable?, comments?, expression?, condition?(obsolete) }` + continuation arrays `onSuccess, onError, onFailure, onEmpty, onOk, onCancel, onYes, onNo, onNone, onAbort, onRetry, onIgnore` — the definitive slot list (**✔ CONFIRMS** reference §7.1 and adds `onEmpty` officially).
- System-event overrides: an event whose trigger is `{type:'Event', hook:'override', target:'<SystemEvent>'}`; the designer builds the overridden-list from exactly that filter, excluding `mode:'D'`.
- Action param interfaces worth noting for layer authoring: `ISwitchParam {cases[{value|default, actions}]}`, `IViewConditionParam {dataview, result, expression, onNoMatch/onSingleMatch/onMultipleMatch, iterativeEvent}` (richer than the reference's `dataview-condition` example), `ISplitParam {value, rowDelimiter='~', columnDelimiter='` + "`" + `', dataView, columnPrefix, dataTypes[]}`, `ICurrentRowParam {dataview, row?, position?('first'|'last')}`, `ISetTimerParam {interval, event}`, `IExecuteCsharpParam`, `ISessionSetParam`, `IDownloadAttachmentErpParam`, `ICloseViewParam {result, dataviews[{source,destination}], valueOut}`, `IOpenViewParam` (incl. `slideOut`, `page`, `layer`, `openInDesignMode`, dialog-result continuations).

---

## 10. Patch (patch.jsonc) — client-visible mechanics

```jsonc
// PatchInfo  — WHERE a patch was applied: target object Id, json Type, Property, patch Name, patch Value
{ "Id": "", "Type": "", "Property": "", "Name": "", "Value": "" }
// PatchToken — an available token: id (the %id%), op, token, value
{ "id": "", "op": "", "token": "", "value": "" }
// PatchTokens — catalog per section
{ "layout": [ /* PatchToken */ ], "events": [ /* PatchToken */ ], "rules": [ /* PatchToken */ ] }
```

- **Substitution of `%id%` patch constants happens server-side during GetApp merge.** The client receives, per view: `PatchInfo[]` (a record of applied patches — consumed by the designer property panel to show patched properties) and `PatchTokens` (the catalog of available tokens **per section: layout / events / rules**) used for designer autocomplete:
  - binding autocomplete offers `view.PatchTokens.layout.map(x => x.id)`;
  - the rule designer shows a patch chip when a rule value matches a `PatchTokens.rules` entry.
- So patch constants are **registered in patch.jsonc (server file), resolved at merge time, catalogued per section** — consistent with the reference §2.2/§7.3; the client adds the fact that tokens are sectioned (layout/events/rules) and surfaced read-only in App Studio.

---

## 11. Shared `$ref` resolution paths (designer-built)

- Shared combo (App Studio picks a combo type): `../shared/combo/<folder>/<subfolder>/combo.jsonc#/combo` from layout, `../../shared/combo/...` from a page — matches the reference §4.4 `$ref` pattern and explains the `../` depth difference.
- Shared/UDC component: `/shared/components/<id>/layout.jsonc#/layout/components`. Components carrying `referencedControlId` (instances of shared components) are **locked** in the designer (§4.2).

---

## 12. Dashboards & application sub-types

- `ApplicationSubType` enum: `Configurator, Report, Process, Dashboard, Apps, Shared`. Dashboards are ordinary MetaFX apps whose `Layout.viewType = 'Dashboard'` and app-list `SubType = 'Dashboard'`.
- Verified client-side differences for `viewType 'Dashboard'`:
  1. all dataviews forced `confirmChanges=false` (§8) — no unsaved-changes prompt;
  2. separate publish permission `canPublishDashboard`, with dashboard base apps publishable by their creator or `CanAccessBase` users even without full modify rights;
  3. page-parent pickers exclude `viewType 'Dashboard'` pages;
  4. new-app templates: TRACKERS/ENTRY/MAINTENANCE/APPS map to `PAGETEMPLATE`, REPORT/PROCESS → `TEMPLATE` (dashboards use the Apps page template family). A brand-new app defaults `viewType:'Apps', pageType:'Responsive', caption:'Apps'`.
- Everything else (layers, diffs, events, rules, tools) is **identical** to entry apps — a dashboard layer is a normal `KNTCCustLayer` on the dashboard's ViewId. (Data comes from `schema:"baq"` dataviews + `Window/onLoad` auto-run events, per the reference §15 — no client-side special-casing found beyond the four points above.)

---

## 13. App Studio designer behavior summary (what actually happens on each user action)

| User action | Client behavior | Server effect |
|---|---|---|
| Open App Studio on a layer | GetApp `mode:'AppStudio'`, `layers:[...]`, `layerType`, `IncludeUnpublishedLayers` layer list; Draft* collections populate the designers | merge base→parents→layer(draft) |
| Edit an existing event/rule/dataview | designer sets `mode='U'` on the item (id frozen) | on save, server stores overlay/Replace |
| Add new item | item created with `mode='A'` (`customizable:true` default) | server stores Add diff (`Path:""`, `Id`=item id) |
| Delete a base item | item marked `mode='D'` | server stores the deletion |
| Drag/reorder components | client mutates the page's `components` array order only | server computes the **Move cascade** (one Move per displaced sibling) on save |
| Change one property of a base control | property panel `set(component.model, prop, value)` | server emits a property diff (`/model/<prop>` Replace) or full-component Replace depending on its diffing granularity |
| Save | `SaveApp` full app + `layerInfo{WIP:true}` → **draft** (`HasDraftContent=true`) | server re-diffs whole app vs base+parents |
| Publish | `SaveApp` + `layerInfo{WIP:false, PublishParentLayers?}` | publishes layer (and optionally parents) |
| Preview | new tab `?preview=true&layerNames=...&layerType=...&layerVersion&baseAppVersion` | GetApp with draft resolution |
| Version compare / revert | `GetAppDifference` → `Difference[]`; revert re-applies `PreValue`s client-side then saves | new draft |

Key implication for hand-authored layers (**✔ CONFIRMS** lessons §3r/§3u): because save always re-diffs the **whole** document, importing a layer replaces everything; there is no server-side incremental merge of two layer versions.

---

## 14. Contradictions & corrections found (summary)

1. **Rule action catalog** — lessons §4 said only `SettingStyle.Disabled/Invisible/ReadOnly` are valid. **Wrong**: the runtime supports 19 actions (§7.2), including row-state colors, `SetColumnValue`, `HidePage`, `ChangeImage`, toolbar-placement styles. Unknown names fail silently with a console warn.
2. **DiffOperation set** — old reference §2 listed `Add|Replace` only. Actual: `Remove=0, Add=1, Replace=2, Move=3`. The delete operation is named **Remove**. Lessons §9/§10 (`Move` real) confirmed.
3. **`Index` is not an ordering key** — nothing client-side orders by it; it's a Move-pair sentinel (`-1`) / bookkeeping. Physical `Diffs` array order governs (empirically verified in lessons §3a/§10; nothing observed contradicts it).
4. **`Slideout` vs `SlidingPanel`** — the client's page-type enum and all runtime filters use **`SlidingPanel`**; the existing reference §2.2 says `viewType:"Slideout"` for slider pages. Treat `"Slideout"` as unverified; if it appears in shipped `.jsonc`, the server may normalize it — verify before relying on either string in new pages. (`slider-open` targets pages by name — `IOpenSliderParam {page}` — so the viewType string matters for nav filtering.)
5. **App Studio does not emit diffs** — it posts the complete app; the server generates all `{Id, Path, Value, Operation, Index}` entries, including Move cascades. "App Studio emits X" in prior docs should read "the server serializes X from App Studio's saved document."
6. **`customizable` is not editable inside a layer** — the checkbox is hidden when `useLayers` (designer rule `hideCustomizable`), and `customizable:false` also forces `personalizable:false`. `customizable: undefined` = editable (defaults true). Locked = lock badge + read-only property panel; also any component with `referencedControlId` is locked regardless.
7. **`mode:'U'` freezes the item id** and is auto-applied by the designer to any edited pre-existing item — reinforcing "always `mode:'A'` for your own new items" and explaining why hand-setting `'U'` makes items behave like locked base overlays.
8. **Personalization layers contain only layout + pages** — events/rules/dataviews/tools are hardcoded empty in every personalization save path. Personalizations key to the user (LayerName='' at save; `'^'`-delimited composite name in storage) and to the active customization-layer set via `ParentLayers`.
9. **Section `Version` numbers and the manifest wrapper are server-side** — not used or validated client-side; they remain empirical (lessons §9 values stand).
10. **Crumb-bar null-`epBinding` crash** — fully corroborated: four unguarded `.split(',')`/`parseBinding` call sites in the crumb bar on the sysPages row's `epBinding` (§5.3).
11. **Dashboard differences are minimal client-side** — `confirmChanges=false` on all views + publish permission gates; no other special layer behavior.
12. **`disableUiLocking`** exists on triggers (event-level UI lock suppression) and as a layout flag — not in the old reference's trigger schema.
13. **Orphans** — layers/upgrades can orphan pages/components; they surface in `MetaFxView.Orphans` + `HasOrphans` and App Studio's Orphans panel, and are part of the compare tree (`NodeCategory.Orphans`). Orphaned nodes are read-only in compare.

---

## 15. Quick-reference: verified JSON shapes for layer authors

Diff entries (all five keys always; Operation strings exactly as shown):

```jsonc
// Add a new component (position = physical position of this entry among the section's component diffs)
{"Id":"txtNew","Path":"components","Value":{ "id":"txtNew","sourceTypeId":"erp-text-box","parentId":"col0","model":{...} },"Operation":"Add","Index":1001}

// Replace (modify) an existing base component — full component in Value, resolved by Id/guid
{"Id":"chkReadyToCalc","Path":"components","Value":{ ...full component, "model":{...,"hidden":true} },"Operation":"Replace","Index":1002}

// Property-only diff on a component
{"Id":"pcOrderHedTax","Path":"/model/hidden","Value":true,"Operation":"Add","Index":1003}

// Page-navigation property diff (NEVER set these to null — crumb bar .split crash)
{"Id":null,"Path":"/navigation/epBinding","Value":"OrderHed.OrderNum","Operation":"Replace","Index":2}
{"Id":null,"Path":"/navigation/dataSetId","Value":"SalesOrder","Operation":"Replace","Index":3}

// Move an existing component (reposition = this entry's array position)
{"Id":"pcOrderHedComments","Path":"components","Value":null,"Operation":"Move","Index":1004}

// Remove a component
{"Id":"btnObsolete","Path":"components","Value":null,"Operation":"Remove","Index":1005}

// Add a whole event / rule / dataview / tool (flat sections)
{"Id":"ce_MyEvent","Path":"","Value":{"id":"ce_MyEvent","mode":"A","customizable":true,"disable":false,"trigger":{...},"actions":[...]},"Operation":"Add","Index":361}

// Delete a base event via lifecycle flag (alternative to Remove): ship it with mode "D"
{"Id":"BaseEventId","Path":"","Value":{"id":"BaseEventId","mode":"D"},"Operation":"Replace","Index":362}

// New page = its own manifest section: {"Name":"MyPage","Version":"3.0","Operation":"Add","Diffs":[
//   {"Id":null,"Path":null,"Value":{ <entire MetaFxLayoutSchema page> },"Operation":"Add","Index":0} ]}
```

Item lifecycle cheat sheet: `mode:"A"` new · `mode:"U"` overlay of existing (id frozen, shows locked-ish) · `mode:"D"` deleted · omit for untouched base. Events use `disable`; rules use `disabled`. Always `customizable:true` on generated items (the flag can't be flipped from App Studio inside a layer).
