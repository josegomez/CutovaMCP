# Kinetic Searches, BAQ, and Server I/O — Reference

Derived from observed runtime behavior and App Studio output. Layer JSON shapes reflect the keys
the App Studio designer writes into the event JSON and the keys the runtime reads. Where the runtime
and the existing reference/lessons disagree, it is flagged inline and summarized in §9.

---

## 1. THE SEARCH SYSTEM (`search-show` + `search-value-set`)

### 1.1 Action envelope

The `search-show` runtime reads `args.metaFxEventAction.param as IUxpSearchDialog` and then
`searchDialog.searchOptions` — i.e. the options are **nested under `param.searchOptions`**:

```jsonc
{
  "type": "search-show",
  "param": {
    "searchOptions": {
      "like": "Project.ProjectID",
      "searchForm": "default",
      "selectMode": "SingleSelect",
      "sortByColumn": "ProjectID"
    }
  },
  "onSuccess": [ /* runs after OK with >=1 row selected */ ],
  "onError":   [ /* silent-search: no rows found */ ],
  "onEmpty":   [ /* silent-search only: trigger fired with empty value */ ]
}
```

The param object is run through `eventParamService.parseObject({...searchOptions}, ['validateFilter'])`
— every string property gets token evaluation (`{View.Col}`, `%...%`,
`#_ _#`) **except** `validateFilter`, which is deliberately left raw so the where-clause builder can
evaluate it at query time.

### 1.2 The full `searchOptions` interface

Canonical interface: `ISearchOptions` (same shape as `IUxpSearchOptions`; the App Studio editor
for `search-show` exposes the same keys).

| Property | Type | Meaning |
|---|---|---|
| `like` | `string` **required** | `Table.Column` search key, e.g. `"ABCCode.ABCCode1"`, `"Part.PartNum"`, `"Project.ProjectID"`. Drives which search definition is fetched (§1.3). Missing `like` crashes: `getSearchPanelId` calls `searchType.replace(...)` on it. |
| `searchForm` | `string?` | Which search form to load, e.g. `"default"`. Cache key is `` `${like}.${searchForm}` ``. Framework internal paths (sliding search, grid-cell search) default it to `'Default'` when absent. |
| `selectMode` | `'MultiSelect' \| 'SingleSelect'` | Whether the results grid allows multiple selection. Grid-cell default search hard-codes `SingleSelect`. |
| `show` | `boolean?` | **Not normally authored.** `undefined` → treated as `true` = show the sliding panel. `show:false` = **silent search** (§1.5). |
| `owner` | `string?` | Id of the event/control that triggered the search (bookkeeping only). |
| `preLoadSearchFilter` | `string \| {whereClauseTable, whereClause}[]` | Filter always applied. String form is appended to the where clause (token-parsed); array form emits one `whereClause<Table>` request field per entry (§1.6). |
| `sortByColumn` | `string?` | Picks the matching entry from the search metadata's `sortBy[]`; falls back to `sortBy[0]`. Sort emits `BY <column> [desc]` appended to the where clause string. |
| `disableColumns` | `string[]?` | Column names to disable in the results grid. |
| `pageSize` | `number?` | Overrides `searchMetadata.pageSize`. |
| `useGetRows` | `boolean?` | `true` → use `searchMetadata.requestOptionsGetRows` (the BO's `GetRows`); default → `requestOptions` (usually `GetList`). Changes result table naming and where-clause parameter routing (§1.6, §1.7). |
| `AlternateSearchMethod` | `string?` | Overrides `requestOptions.svcPath` — call a different method on the same service. |
| `CustomArgs` | `{field, value}[]?` | Extra request-body fields appended verbatim to the search request (value is token-parsed), e.g. `includeCompany=false`, `groupId=8009`. |
| `valueIn` | `{id, value}[]?` | Default values for the search prompt controls; `id` matches the criteria item id (silent search: sets `item.default`; quick search: matches `CriteriaField`). |
| `subPanelResponse` | `{epBinding, column}[]?` | Maps result columns to bindings when the search is hosted as an inner/sub panel. |
| `validation` | `{validateFilter?, errorMessage?}` | Silent search only: `validateFilter` is appended to the where clause; `errorMessage` replaces the stock "record not found" warning. |
| `overrides` | `{type:'getRowsParam', name, value}[]?` | Overrides `requestOptionsGetRows.params[name].whereClause` before the request. Only `type:'getRowsParam'` exists. |
| `returnMultipleTables` | `boolean?` | `true` → response is kept as a multi-table result (`IUxpSearchResult.table[]` gets one entry per returned table; first/primary = `requestOptions.dataTable`). |
| `launchSearchType` | `string?` | Which panel the sliding search opens on: `''` (Basic), `"Quick Search"`, `"BAQ Search"` (enum in properties: `{Basic:'', Quick, BAQ}` — the value stored is the localized string constant; internally maps to `ErpSearchActivityMode` = `BasicSearch/QuickSearch/BaqSearch/dataTagsSearch/personalSearch`). |
| `launchSearchName` | `string?` | The Quick Search ID / BAQ QueryID / named-search name to preselect when launching. |
| `hideOkButton` | `boolean?` | Suppresses the OK button (used by read-only grid-cell searches). |
| `calledFrom` | `string?` | Set automatically to the current app view id. |

> **Flag vs existing reference:** there is **no `whereClause`, `searchName`, or `gridColumns`
> property** on `searchOptions`. Pre-filtering is `preLoadSearchFilter`;
> the "named" search is `launchSearchType`/`launchSearchName`; result grid columns come from the
> server-side search definition, not the action.

### 1.3 How `like` resolves — the GetSearch pipeline

1. `search-show` → `ErpSearchShowEventService.executeSearchEventAction`.
2. Panel/silent both end up firing activity `GetUxpSearchPanelModel` → handled by the ERP search
   activity handler, which caches per `` `${like}.${searchForm}` `` and delegates to activity
   `GetUxpSearchViewModel`.
3. `GetUxpSearchViewModel` is handled by the MetaFX search activity handler
   (`handleGetSearchView`), which calls **REST `Ice.Lib.MetaFXSvc/GetSearch`** with request model:
   ```jsonc
   { "like": "<Table.Column>",
     "properties": { "searchForm": "<form>", "deviceType": "Desktop", "layers": [], "mode": "" } }
   ```
4. The response is a mini MetaFX app (**search.json**): `{ SearchMetadata, DataViews, Events, Rules }`.
   It is transformed into an `IUxpSearchViewModel`; a result dataview named
   `` `${DataViews[0].id}Result` `` is appended, with `serverTable` =
   `requestOptionsGetRows.dataTable` (if `useGetRows`) else `requestOptions.dataTable`.
5. `searchOptions` overrides are then stamped onto the metadata: `preLoadSearchFilter`,
   `AlternateSearchMethod` → `requestOptions.svcPath`, `pageSize`.

`SearchMetadata` (aka `IUxpSearchMetadata`) fields used by the client:
`requestOptions {svc, svcPath, dataTable}`, `requestOptionsGetRows {svc, svcPath, dataTable, params[{name, primary, whereClause}]}`,
`criteria.and[]` (prompt conditions), `sortBy[] {column, desc, getRowsParamName, whereClauseTable}`,
`pageSize`, `preLoadSearchFilter`.

This is exactly what the `GetSearches` MCP tool surfaces: BAQ column `Calculated_Like` = the `like`
value, `Calculated_SearchForm` = the `searchForm` value (lessons §7 mapping — consistent with runtime behavior).

### 1.4 Sliding search (interactive) path

`executeSlidingSearch`:

- Clears/initializes the **`actionResult` dataview**: `actionResult.searchCancelled=false`,
  `actionResult.searchResult=undefined` (`setActionResultCancelStatus`). On cancel:
  `searchCancelled=true`. Events can branch on `{actionResult.searchCancelled}` after the action.
- Builds `IUxpSearchPanelModel` `{id, option: {...searchOptions, calledFrom}, width: Medium, hideOkButton}`
  and shows `ErpMetaFxSlidingSearchComponent` in the shell slide panel.
- On **OK with ≥1 row**: fires activity `ProcessUxpSearchShowResponse`; on cancel/no rows it just
  completes (onSuccess chain is *not* invoked with rows).
- `ProcessUxpSearchShowResponse` is handled back in the MetaFX search activity handler
  (`handleSearchShowActionResponse`):
  it iterates the action's **`onSuccess` array itself** and executes each entry —
  `value-set` (obsolete; logs a warning, use `search-value-set`), `function`, stop on
  `return`/`return-error`/`exit`, everything else via the normal action executor. So the selected
  rows are available to those actions through the **`searchResult` transaction dataview**
  (populated by the OK handler before the response is processed — both the grid-cell and sliding
  variants are routed via the same activity).
- Return shape from the dialog (`SearchDialogResult`):
  `{ selectMode, dialogResult, owner, data: Object | Object[] }` — `data` is an array of the selected
  result rows when `MultiSelect`.

### 1.5 Silent search (`show:false`)

`executeSilentSearch`:

- Only runs when the triggering column-change has a value
  (`args.eventExecuteData.dataColumnChangeEventArgs.value`); otherwise the response is the action's
  **`onEmpty`** branch. (So `search-show` supports `onSuccess` / `onError` / `onEmpty`.)
- Applies `valueIn` defaults onto `criteria.and[]`, builds the where clause (§1.6), and runs
  `performSearchRequest` directly (no UI).
- **≥1 row** → rows copied into the `searchResult` dataview
  (`epEventTransactionService.clear('searchResult')` + `addRows('searchResult', rows)`), then
  `onSuccess` with `shouldCallNextAction:true`.
- **0 rows** → warning slideout (`validation.errorMessage` or stock "record not found"), then
  `onError`.

### 1.6 Where-clause construction (`ErpWhereClauseBuilderService`)

Produces `whereClauseData`, a flat object merged into the request body:

- **preLoadSearchFilter (array form)**: each `{whereClauseTable:'X', whereClause:'...'}` →
  request field `whereClauseX = '...'`.
- **Prompt conditions** (`criteria.and[]`, each an `IUxpSearchCondition` with
  `column`, `condition`, `exclude`, `whereClauseTable`, `whereClauseOnTrue/False`,
  `getRowsParamName`, `paramName`, `component`): value comes from the prompt control's binding.
  Condition transforms: `LIKE` → `col LIKE '%v%'`, `CONTAINS` → `CONTAINS(col,'v')`,
  `LIKE%` → `col LIKE 'v%'`, `IN` → `col IN (v)`, default → `col <op> v` (strings quoted).
  Empty/space string, numeric 0, or `exclude:true` → skipped.
- **preLoadSearchFilter (string form)** and **`validation.validateFilter`** (silent search only)
  are token-parsed and ANDed in when no custom whereClauseTable was used.
- **Sort**: `BY <col> [desc]` appended to the main string or to the `whereClause<Table>` field.
- **GetList (default)**: final string lands in request field **`whereClause`**.
- **GetRows** (`useGetRows:true`): each `requestOptionsGetRows.params[]` gets its own field —
  the `primary:true` param receives the built string; others get their static `whereClause`
  (possibly overridden via `searchOptions.overrides`), plus anything routed via a condition's
  `getRowsParamName`.

### 1.7 Request execution (`ErpSearchPanelService.performSearchRequest`)

- Picks `requestOptions` vs `requestOptionsGetRows` per `useGetRows`.
- Request data = `{ morePages:false, ...whereClauseData, ...CustomArgs }`.
- Executes through `ErpRestDataProvider` (`{svc, svcPath, restParams, tableName, skipAutoload:true}`)
  so required BO parameters get defaulted.
- Primary result table id: for `svcPath === 'GetList'` it is `dataTable.slice(0, -4)` (strips the
  `"List"` suffix, e.g. `ProjectList` → `Project`); otherwise `dataTable` as-is.
- `returnMultipleTables:true` → every table in the response is added to `result.table[]`
  (`primary:false` for the extras).

### 1.8 `search-value-set` — writing the picked value back

Action id `search-value-set`, category *Components*. Reads the
**`searchResult`** dataview populated by §1.4/§1.5.

Top-level action properties (all directly on the action object):

| Key | Type | Notes |
|---|---|---|
| `epBinding` | binding | Target `View.Column` to receive the value (token-parsed). |
| `value` | string | **Backward-compatible simple mode**: `"searchResult.<ColName>"` — only the part after the first `.` is used as the result-column name (`valueParam.split('.')` → `colName`; the prefix is ignored). |
| `param` | object | Advanced/multi-column mode (below). When present and non-empty, `value` is ignored. |

`param` shape (`MetaFxSearchValueSetEventParamProperties`):

| Key | Type | Meaning |
|---|---|---|
| `columns` | `string[]` (json) | Result column(s) to read. Multiple columns per row are joined with `fieldDelimiter`. |
| `multiFieldBindings` | `string[]` (json) | Parallel array of bindings — `multiFieldBindings[i]` receives `columns[i]` from the result rows. |
| `display` | `string` | Dual/chip mode: the result column used as chip display text; fires `CHIP_SELECTION` broadcast with `{epBinding, data:[{chipId,chipDisplayText}]}` and writes the id values to `epBinding`. |
| `rowDelimiter` | `string` | Default `"~"`. Joins multiple selected rows. |
| `fieldDelimiter` | `string` | Default `` "`" ``. Joins multiple columns within a row. |

Behavior details:
- Simple mode, single row → `transactionService.set(epBinding, row[colName], 'string')`.
- Simple mode, multi-select → values joined with `~` into one string.
- "Auto" search mode (search chips): values are *appended* to the existing binding value with
  duplicate suppression.
- **Column suppression is not part of this action** — re-entrancy protection is done by wrapping the
  write in `event-column-disable`/`event-column-enable` (§8, and see the contradiction flag there).

### 1.9 The field search icon — native wiring, confirmed

The magnifier on `erp-text-box`/`erp-numeric-box` (also `erp-part-rev-desc`,
`erp-foreign-lang-desc-text-box`):

- `model.enableSearch: true` renders the icon (icon class defaults `mdi-file-find`, override with
  `model.searchIconClass`; tooltip `model.searchTitle`; `model.searchOnly` disables the input
  leaving only the icon; icon hidden for `type='password'`). Enter key with `enableSearch` also
  blurs/refocuses.
- Click → `epTextBoxSearchClick` → component event **`epOnSearchBarClick`**.
- `epOnSearchBarClick` is bound to the plugin-event system by **`EpSearchButtonEvent`**,
  exposed in App Studio as the **"On Search Bar Click" / "On Search Click"** property via
  `ErpSearchButtonClickExtension`.
- **Candidate triggers for the icon click** (`getComponentTriggers`):
  1. `{type:'EpBinding', hook:'onClick',  target:<epBinding>}`
  2. `{type:'EpBinding', hook:'onSearch', target:<epBinding>}`
  `handleButtonClick` **reverses** the list and takes the first trigger that has events,
  i.e. it checks `EpBinding/onSearch` first, then `EpBinding/onClick`.
- **When App Studio creates a new event from "On Search Click"** it emits
  `getNewTriggeredEventForComponent` → id `` `${epBinding}_onClick` `` with trigger
  **`{type:'EpBinding', hook:'onClick', target:<epBinding>}`**.

**This confirms lessons §3y exactly**: the correct custom wiring for a field search icon is

```jsonc
"trigger": { "type": "EpBinding", "hook": "onClick", "target": "OrderHed.ProjectID_c" }
```

Additional notes:
- `EpBinding/onSearch` *would also* be picked up by the icon (checked first), but EpBinding triggers
  are additionally registered as column-change listeners elsewhere in the trigger handler, which is
  why lessons §3x saw the `onSearch`-hooked event firing on typing. `onClick` is the safe hook and
  is what App Studio itself generates.
- `Control`-type triggers (`{type:'Control',hook:'onClick',target:<id>}`) are **not** in the search
  icon's candidate list — they never fire from the icon (explains lessons §3v failures).
- **If no event exists for either trigger**, `handleButtonClick`'s `mergeMap` returns `null`,
  producing the RxJS error `TypeError: You provided 'null' where a stream was expected`.
  This is the §3v header error: base bindings
  "work natively" only because the **base app JSON already contains an
  `EpBinding/onClick` event** on that binding (e.g. `OrderDtl.ProjectID`); a custom `_c` binding has
  none, so the click resolves to nothing → null stream. There is no framework-level fallback field
  search — "native search" = base-app-supplied events.
- Do **not** add a second search event on a base binding that already has one — the icon fires the
  first trigger-with-events found; two events on the same trigger double-fire `search-show`
  (lessons §3y, consistent with this resolution logic).

**Grid cell search** is different: activity `GridCellSearchEvent` first checks
`hasEpBindingEvent(undefined, args.targetId)` — if a layer event exists on the cell's binding it is
fired (`performEpBindingComponentClick`); otherwise the framework opens its **default sliding
search** with `{like: args.like, searchForm: args.searchForm || 'Default', selectMode:'SingleSelect',
preLoadSearchFilter, useGetRows, hideOkButton: gridDisabledOrNonEditable}`, and on OK copies rows to
`searchResult` and fires `CallLogSearchResult`. Availability of a default is probed by activity
`IsGridCellSearchAvailable` → `hasDefaultSearchForm` = does `GetSearch(like, 'default')` return a
model.

### 1.10 Quick Search / BAQ Search / Named (Personal) Search infrastructure

- **GetSearchOptions**: POST `Ice.BO.KineticErpSvc/GetSearchOptions` with
  `{context: {likeTableName, likeFieldName, calledFrom, searchName: searchForm || 'default'}}`.
  Response (`IErpSearchOptions`) carries:
  - `baqSearches.DynamicQueryList[]` (`QueryID`, `Description`) — BAQ searches for this like.
  - `quickSearches.QuickSearch[]` (`ExportID` = the underlying BAQ), `QuickSearchCriteria[]`
    (`QuickSearchID`, `CriteriaField`, `Seq`, `CriteriaType` = `prompt|constant|radioset`,
    `CompOp`, `CriteriaValue`, `FilterOnNull`, `DataType`), `QuickSearchValueList[]` (radioset values).
  - Cached per `SearchOptions_<table>~<field>`; all referenced BAQ metadata is pre-initialized.
- **Quick search prompts** are bound to the transient **`QuickSearch` dataview**, column name =
  `CriteriaField + Seq` (e.g. `QuickSearch.CustID1`). Criteria values: `constant` → `CriteriaValue`,
  else read from `QuickSearch.<CriteriaField><Seq>`. `valueIn` ids match `CriteriaField`.
- **BAQ search**: results provider is a BAQ data provider bound to view **`ErpSearchResults`**;
  the value returned to the caller comes from the BAQ column flagged `UseLike` whose
  `LikeDataFieldTableID`/`LikeDataFieldName` match the `like` — its `Alias` is the `returnField`;
  fallback `"<Table>_<Field>"` flattened name.
- **Basic search** (the GetList/GetRows form) resolves a provider with
  `svcPath = servicePath || (datasetMode==='list' ? 'GetList' : 'GetRows')`, bound to
  `ErpSearchResults_Basic`.
- **Named/personal searches**: `Ice.BO.NamedSearchSvc` (`ErpBusinessObjects.NamedSearch`);
  update = delete (`DeleteByID`) + re-create; rows carry `SearchForm`, `NSId`, `CalledFrom`.
  Activities `UpdatePersonalSearch` / `DeletePersonalSearch`.
- The sliding panel's initial tab/search is driven by `launchSearchType`/`launchSearchName`.

---

## 2. `erp-baq` EVENT ACTION + BAQ SERVICES

### 2.1 Action shape — properties are TOP-LEVEL on the action

The `erp-baq` runtime reads `args.metaFxEventAction.baqId`,
`.mode`, `.alias`, `.executeOptions`, `.baqParams`, `.updateOptions` **directly off the action
object** (there is no `param` wrapper; `getActionData` clones the whole action).

```jsonc
// GET (execute) mode
{
  "type": "erp-baq",
  "baqId": "OrderAvailableInventory",
  "alias": "AvailInv",                    // dataview name to fill; presence => populateDataView
  "mode": "get",                          // 'get' (default) | 'update'
  "executeOptions": {
    "pageNumber": 1,
    "pageSize": 50,
    "select": ["PartDtl_PartNum","PartDtl_Qty"],   // string[] OR comma-separated string (auto-split)
    "where": "PartDtl_PartNum = '{OrderDtl.PartNum}'",
    "orderBy": ["PartDtl_PartNum"],                // string[] or comma string
    "groupBy": [],
    "having": "",
    "aggregate": [ { "column": "PartDtl_Qty", "type": "sum" } ]   // ErpBaqAggregateType: sum|avg|min|max|count
  },
  "baqParams": [                          // BAQ ExecutionParameters
    { "field": "MyParam", "value": "{OrderHed.OrderNum}", "type": "int", "isEmpty": false,
      "epBinding": "OrderHed.OrderNum" }  // if epBinding set, its live view value wins over 'value'
  ],
  "onSuccess": [], "onError": []
}
```

```jsonc
// UPDATE (uBAQ) mode
{
  "type": "erp-baq",
  "baqId": "MyUpdatableBaq",
  "alias": "MyView",
  "mode": "update",
  "updateOptions": {
    "operation": "UpdateBaq",     // see enum below
    "actionID": "",               // required for UpdateBaqCustomAction
    "allRows": false,             // Update/CustomAction: true = send all rows, false = current row
    "rollbackOnError": false,     // Update only: rollback the dataview on server error
    "fieldName": "",              // FieldUpdate/FieldValidate
    "fieldValue": ""              // FieldValidate
  },
  "onSuccess": [], "onError": []
}
```

Runtime details:
- `populateDataView = !!alias` — results land in dataview `alias` (else `baqId`).
- `baqParams[]` → `executeOptions.parameters[]` as
  `{ParameterID: field, ParameterValue: value, ValueType: type||'string', IsEmpty: isEmpty||false}`;
  when `epBinding` is set, `ParameterValue` is read live from `view.get(column)`.
- `select`/`orderBy`/`groupBy` given as strings are split on `,`.
- Update mode routes to `kineticErpBaqUpdate`; row payload
  (`getDataRowsForUpdate`): `getNew` → none; `fieldValidate`/`fieldUpdate` or `allRows!==true` →
  current row only; else all rows of the view. Update result `cancel:true` → `onError`, else `onSuccess`.
- Get mode success → `{success:true}` (no explicit onError branch on the get path; REST errors
  surface as thrown errors).

`ErpBaqUpdateOperation`:

| Enum key | Wire value (= method on `Ice.BO.KineticErpSvc`) |
|---|---|
| `update` | `UpdateBaq` |
| `fieldUpdate` | `UpdateBaqFieldUpdate` |
| `fieldValidate` | `UpdateBaqFieldValidate` |
| `customAction` | `UpdateBaqCustomAction` |
| `getNew` | `UpdateBaqGetNew` |

### 2.2 BAQ REST paths

| Operation | HTTP | Path | Payload |
|---|---|---|---|
| Execute BAQ (event get mode) | POST | `Ice.BO.KineticErpSvc/ExecuteBaq` | `{queryID, executionParams: [IErpBaqExecutionParams, ...virtualizations]}` (params composed from pageSize/pageNumber/select/where/orderBy/groupBy/having/aggregate/skipBpm) |
| uBAQ update ops | POST | `Ice.BO.KineticErpSvc/<operation>` (`UpdateBaq`, `UpdateBaqFieldUpdate`, `UpdateBaqFieldValidate`, `UpdateBaqCustomAction`) | `{queryID, ...updateOptions, queryResultDataset: {Results: [rows]}}` |
| uBAQ GetNew | GET | `BaqSvc/{queryID}/GetNew` | — (also used for `UpdateBaqGetNew`) |
| Simple get (OData) | GET | `BaqSvc/{queryID}` | OData query options |
| Legacy update | PATCH | `BaqSvc/{queryID}` | single row (`updateBaq`) — delete NOT supported (`deleteBaq` throws) |
| BAQ list | GET/POST | `Ice.BO.BAQDesignerSvc/BAQDesigners` (OData) or `.../GetRows` when the filter is too long | — |
| Designer def | POST | `Ice.BO.BAQDesignerSvc/GetByID` | `{queryID}` |
| Runtime query/metadata | POST | `Ice.BO.DynamicQuerySvc/GetByID` / `GetByIDsTranslated` | `{queryID}` / `{queryIDList}` |
| Search options | POST | `Ice.BO.KineticErpSvc/GetSearchOptions` | `{context:{likeTableName, likeFieldName, calledFrom, searchName}}` |

Update result digest: `fieldValidate` sets
`result.cancel = !parameters.isValid`; server `returnObj.Errors[]` → exception slideout (+ optional
`rollbackOnError` view rollback); otherwise `returnObj.Results[]` rows are merged back into the
view **matched by `SysRowID`** (replace or add; `fieldUpdate` rows re-marked `RowMod:'U'`).

Alias syntax: BAQ ids can be registered as `'baqID:alias'` in `initBaqMetadata`.

### 2.3 Grid `baqOptions` + `whereList` (BAQ-bound grids)

Panel-card-grid provider keys: `provider.baqId`, `provider.baqOptions`; runtime: the ERP BAQ data
provider.

```jsonc
"provider": {
  "baqId": "MyBaq",
  "baqOptions": {
    "pageNumber": "1",
    "pageSize": "50",
    "where": "Part_PartNum = ?{OrderDtl.PartNum}",
    "whereList": [
      { "column": "OrderHed_OrderNum",
        "condition": "=",                 // any SQL op; 'like' supported
        "value": "?{OrderHed.OrderNum}",
        "honorNull": false,               // only honored for = and <> ; empty value => 'col is null' clause
        "emptyValue": "" }                // value treated as empty; '' becomes literal ''
    ]
  },
  "autoLoadGrid": true, "pagePaddingSize": 0
}
```

- `where` and every `whereList[].value` are ANDed together (`prepareWhereFilter`).
- Empty values: a where item whose resolved value is empty (`''`, the `emptyValue`, or `'%'`/`'%%'`
  for `like`) is **dropped from the filter** unless `honorNull:true`, which emits
  `(col is null [OR col <cond> emptyValue])` for `=` or `col <> value` for `<>`.

**FIELD-PROVEN warning: emit each whereList item with EXACTLY three keys —
`{"column","condition","value"}`.** Although the interface declares `honorNull`/`emptyValue`
(above), including a **boolean** `honorNull:false` on a panel-card-grid provider made the client
where-clause builder call `.replace` on the boolean and throw

```
TypeError: t.replace is not a function
  at L.processValue → getCriteria → processCriteriaItem → getProcessedWhereClause
```

This error is NOT the BAQ, not paging, not a gate token — it is the extra boolean property on the
whereList item. Strip items to the three keys; only reach for `honorNull` if you genuinely need the
is-null clause, and expect to have to verify it on the live version.

### 2.3b Server paging drops sort/key columns from the Select (FIELD-PROVEN)

Symptom: with `providerModel.serverPaging:true`, the grid's `ExecuteBaq` `Select` omits some
columns (e.g. `UD103_Key2/Key3/Key4`). Sorting breaks and any event that reads those columns from
the result view (e.g. an OK button mapping `KeyFields.Key2/3/4` from `SearchResult`) gets nothing.

Cause:
- The BAQ has a `QuerySortBy` (ORDER BY) on those columns.
- Under server paging, `ExecuteBaq` projects ONLY the grid's columns. With `autoLoadColumns:true`,
  the auto Select = the BAQ's *display* fields, which may EXCLUDE the key/sort columns (they're in
  the query for joins/keys/sort but not flagged display).
- So the paged query is ordered by columns it isn't projecting → the sort has nothing to sort on,
  and the rows don't carry those values.
- (Client paging hides this because it sorts the full in-memory set.)

Fix: make the sort/key columns real grid columns so they land in the Select — `hidden:true`
(retrieved, not shown).

**Column-config rules that bite here:** `autoLoadColumns:true` + a PARTIAL `columns` array is NOT a
valid combo. App Studio always writes `autoLoadColumns:false` and the COMPLETE column list when any
column is customized; a partial array under `autoLoadColumns:true` may be ignored (the fix doesn't
take) or blank the grid. So set `autoLoadColumns:false` and provide the FULL list:

```jsonc
{ "id":"grdSearchResults", "epBinding":"SearchResult",
  "autoLoadColumns": false,
  "providerModel": { "baqId":"MyOrderSearchBAQ", "serverPaging": true, "baqOptions": { "whereList":[...] } },
  "columns": [
    { "field":"UD103_Key2", "hidden":true },   // sort + nav, retrieved not shown
    { "field":"UD103_Key3", "hidden":true },
    { "field":"UD103_Key4", "hidden":true },
    { "field":"Customer_CustID" }, { "field":"Customer_Name" }, ...  // the visible display columns
  ] }
```

Rule of thumb: any column referenced by the BAQ's `QuerySortBy`, OR by an event reading the result
dataview, MUST be a grid column (visible or hidden) so it's in the server-paged Select.

### 2.3c How the provider actually builds the `Select` (call chain)

Investigated after §2.3b's fix "didn't take" — grid columns feed the Select only
indirectly, and several things silently drop them:

1. **Bridge init** — the grid/provider bridge's `setProviderModel()`: calls
   `erpGridService.updateFieldMetadata(grid.model, provider.fieldMetadata)` and assigns the returned
   `fieldList` to the provider (`dataProvider.fieldList = fieldList`).
2. **`updateFieldMetadata`** — the two ways columns get dropped:
   - If `model.columns` is **EMPTY** at provider-init time, it auto-generates columns from the BAQ
     metadata = **exactly the BAQ's display columns**. A Select that equals the display-column list
     is the FINGERPRINT of this branch — the runtime grid model had no columns at all.
   - Otherwise it iterates `model.columns` and **skips any column with no `erpInternal`**
     (`if (!column.erpInternal) return;`). `erpInternal` is stamped by `buildColumn` during the
     grid's own `prepareColumns` — only columns that actually reached the LIVE grid model count.
     `hidden:true` columns DO count (only image columns are excluded).
3. **BAQ data provider `fieldList` setter** — brackets each name (`[UD103_Key2]`).
4. **BAQ data provider `setSelect`** — the whole story:
   `select = union(providerModel.baqOptions.select || [], this.fields)`.
   **`providerModel.columns` is NEVER read by the Select path** — putting columns there does nothing.
5. **`addOuterSortingFields`** auto-adds `[TableID_FieldName]` for the BAQ's
   `QuerySortBy` rows — but ONLY when there is no client sort and no grouping, and only if the sort
   rows surface in `baqMetadata.query.data.QuerySortBy` (subquery-level sorts may not).
6. The BAQ execution-params builder joins the list into the `Select` ExecutionSetting.

**The direct lever: `providerModel.baqOptions.select`** — unioned into the Select verbatim, no
grid-column machinery involved, works even with `autoLoadColumns:true` and no `columns` array:

```jsonc
"providerModel": {
  "baqId": "MyOrderSearchBAQ",
  "serverPaging": true,
  "baqOptions": {
    "select": ["[UD103_Key2]", "[UD103_Key3]", "[UD103_Key4]"],   // bracketed, to dedupe vs grid fields
    "whereList": [ ... ]
  }
}
```

This is usually a BETTER fix than §2.3b's full-columns approach: you keep auto-loaded columns and
just force the extra key/sort fields into the projection.

**Debugging: "my hardcoded columns aren't in the Select"** — if the emitted Select is exactly the
BAQ's display columns, the live grid model had NO columns when the provider initialized. Check, in
order: (1) the App Studio DRAFT block (`SysCharacter03`) still carries the old grid and the preview
renders it (lens-mcp-tools.md "two content blocks"); (2) the columns were put under
`providerModel.columns` (dead — see step 4); (3) the grid component diff didn't apply (wrapper
shape/wrong page section); (4) saved grid personalization/layout state (`stateInView`/savedLayout)
overriding the model.

### 2.3d RESOLVED: newer client builds SILENTLY DROP updatable (UBAQ) fields from the Select — fix = explicit `baqOptions.select`

**FULLY VERIFIED (live captures).**

Symptom: on a `providerModel.baqId` grid with `serverPaging:true` over an UPDATABLE BAQ, some
columns never arrive — the `ExecuteBaq` "Select" ExecutionSetting omits them, regardless of
`gridModel.columns` vs `providerModel.columns`, `autoLoadColumns`, `editable:false`, or
`sourceType`. Toggling the field's **Updatable** flag in the BAQ makes it appear/disappear.

**Mechanism — plain English:**
1. On current client builds, the grid's field enumeration (which feeds the Select) SKIPS every
   BAQ field marked Updatable. Columns still render but their data is never requested — blank.
   Older builds fetched everything; the gate arrived with a client upgrade (support-case
   candidate).
2. The client then re-appends the BAQ's `QuerySortBy` fields at the END of the Select (needed
   for paged ordering) — an accidental band-aid that masks #1 when the missing fields happen to
   be sort fields.
3. A saved personal sort or grouping on the grid disables that band-aid entirely
   (`addOuterSortingFields` early-returns on `hasClientSort`/`hasGroups`).
4. Fix: declare the fetch list yourself via `baqOptions.select` — unioned in FIRST,
   unconditionally, immune to #1–#3.

**Mechanism — observed detail.** On older client builds the Updatable flag only affected
editability; every non-image column was pushed into `fieldList`. On current builds the push is
gated: a column is enumerated ONLY when a BAQ metadata column is found for it AND that column is
not updatable.

So on current builds every `QueryField.Updatable=true` column — **and any column with no BAQ
metadata match** — is EXCLUDED from the enumerated Select. (This supersedes the earlier §2.3c
claim that a metadata-less explicit column still lands in fieldList: true on old builds only.)
Empirical confirmations: flipping Updatable adds/removes the field from the captured Select; an
independent "working" layer had its two sort-coincident updatable fields re-appended AT THE END
of its Select by `addOuterSortingFields` while its other two updatable fields were silently
missing.

Consequences:
- A grid over a UBAQ "works" only when its dropped updatable fields ⊆ the BAQ's sort columns AND
  nothing suppresses the sort-append. Coincidence, not configuration.
- Saved grid-layout sorts persist per grid GUID across layer re-imports → the breakage looks
  immune to every layer edit. `pageable:true` + `preloadOptions` can also carry sort state.

**THE FIX — declare the Select explicitly.** `baqOptions.select` is layer-JSON only (NOT exposed
in App Studio — same family as `skipAutoload`). Unioned first in `setSelect`, so immune to the
updatable-drop, the sort-append skip, and saved-layout state:

```jsonc
"providerModel": {
  "baqId": "MyOrderSearchBAQCP",
  "serverPaging": true,
  "baqOptions": {
    "select": [ "[UD103_Key2]", "[UD103_Key3]", "[UD103_Key4]", "...every result column, bracketed..." ],
    "whereList": [ ... ]
  }
}
```

Rules of thumb:
- Grid over an UPDATABLE BAQ + serverPaging → **ALWAYS set `baqOptions.select`** (full bracketed
  column list). Auto-enumeration WILL drop the updatable fields.
- Fragile front-end-only alternatives: make the fields non-updatable in the BAQ, or ensure
  `QuerySortBy` covers the fields you need restored.
- Avoid `pageable:true`/`preloadOptions` on such grids; clear saved grid layouts when debugging
  (a personal sort survives every import and disables the sort-append).
- Debug tell-tales in the captured ExecuteBaq payload: missing columns == updatable fields;
  restored columns appear AT THE END of the Select (sort-append fingerprint); an `OrderBy`
  ExecutionSetting == client sort state (the append will be skipped).
- Display and fetch are independent on this path: `gridModel.columns` still governs
  order/titles/hidden; `baqOptions.select` governs what's fetched.

### 2.4 `?{View.Col}` / `??{View.Col}` binding tokens (provider filters)

Token pattern: `/(\?{1,2}){(?:([\w\.]*)(?:,\s*(\S*)\s*)*)}/g`.

| Token | Meaning |
|---|---|
| `?{View.Col}` | **Required** binding. If the view value is empty/undefined, `validateFilter` fails and the provider **does not run the query** (master-with-no-row case). |
| `??{View.Col}` | Optional binding. Empty resolves to `''` (query still runs). |
| `?{View.Col,'dflt'}` | Default value when the binding is empty. |
| Exception | `Constant.*` bindings are never treated as blocking. |

The provider auto-subscribes to `RowChanged` and column changes of every referenced view and
re-fires the filter — this is the mechanism behind grids refreshing on row change,
and behind the transient-null storms during Refresh (lessons §3z: guard event-driven BAQ calls; note
that **event** `executeOptions.where` uses curly `{View.Col}` tokens parsed at event time, while
**grid provider** filters use `?{}`/`??{}` tokens parsed at query time — two different token systems).

**Quoting (FIELD-PROVEN): `?{}`/`??{}` do NOT auto-quote string BAQ columns** — wrap the token in
single quotes yourself:

- string `=`    → `"'??{SearchFilter.Key2}'"`
- string `like` → `"'??{SearchFilter.CustName}%'"` or `"'%??{SearchFilter.PartNum}%'"`
- required gate on a string col → `"'?{SearchFilter.Company}'"`

Numeric/date columns stay unquoted (dates need special handling — consider leaving date prompts out
of the whereList).

### 2.4b The GATE pattern — block a provider grid's query until a filter is entered (FIELD-PROVEN)

Goal: grid is empty on open; the moment ANY search prompt is typed, the grid queries with whatever
filters are filled. Mechanism = one **required** `?{}` token on a dedicated gate column, compared so
it never actually restricts once set:

1. A client "filter" dataview (`additionalColumns`, `datatype:"string"` — NOT `"nvarchar"`, which
   silently drops the view on import; see rules-and-dataviews.md) holds the prompts. Reuse one of
   its columns as the gate (e.g. `Company`).
2. The gate whereList item uses the **required** token with an always-true comparison:
   `{ "column":"UD103_Company", "condition":"<>", "value":"'?{SearchFilter.Company}'" }`
   - Gate empty → required `?{}` fails `validateFilter` → **query blocked** (blank grid).
   - Gate set to `'XXX'` → `UD103_Company <> 'XXX'` is always true → doesn't restrict, just unblocks.
3. All real filters use **optional** `??{}` tokens so empty ones drop out.
4. A gate-setter event flips the gate on any prompt change — trigger
   `{"type":"DataTable","target":"SearchFilterTbl","hook":"columnChanged","columns":[...all prompt cols...]}`
   with a `row-update` writing `SearchFilter.Company = "XXX"`. **The trigger `target` is the TABLE
   id (`SearchFilterTbl`), NOT the dataview id — targeting the view id means the event never
   fires** (events.md §2.4).
5. The "open" event seeds the gate column blank (grid blank on open); a Clear button resets it blank.

The grid itself: `epBinding` to a `schema:"baq"` dataview — which needs the full required property
set `{id, schema:"baq", data, table, tools, mode}` (no `tools` → view disappears on import; no
`table` → not in the Data View picker; rules-and-dataviews.md §B12) — `providerModel.baqId`,
`autoLoadColumns: true`, **no `columns` array** (a columns array emits a restrictive dynamic Select that can throw
"Invalid column name" on complex multi-subquery BAQs — components.md §3.7), whereList items with
exactly `{column, condition, value}` (§2.3). Exception: under `serverPaging:true` you MUST flip to
`autoLoadColumns:false` + a COMPLETE `columns` list (hidden key/sort columns included) — §2.3b.
Full worked example in lessons-learned.md §16.

### 2.5 BAQ virtualizations

`IErpBaqOptions.virtualizations[] {mode: recordCount|groupByDetails|pageCount, select, orderBy, groupBy}`;
each adds an extra entry to `executionParams` and yields an extra results table. Record count now
comes from `ExecutionInfo.TotalRows` (NeedTotal) rather than a second query.

---

## 3. `rest-erp` — DEEP DIVE

### 3.1 Action shape

Action id `rest-erp`, category *Rest*. Everything lives under **`param`**:

```jsonc
{
  "type": "rest-erp",
  "param": {
    "svc": "Erp.BO.SalesOrderSvc",
    "svcPath": "MasterUpdate",
    "requestMethod": "POST",                          // HTTP verb; designer default 'POST'
    "erpRequestMethod": "ErpPostWithDataViewProcessing", // designer default; see 3.2
    "methodParameters": [ /* IParams[], see 3.4 */ ],
    "erpRestPostArgs": { /* see 3.5 */ },
    "options": {                                      // IEpRestCallOptions extras
      "suppressException": false,                     // don't surface HTTP errors as slideouts
      "apiKey": "",                                   // efx only
      "efxLibrary": ""                                // efx only (marks response as function-style)
    }
  },
  "onSuccess": [], "onError": []
}
```

At execution: integer methodParameters with no value/epBinding are
defaulted to `0`; the whole `param` is token-parsed (`parseObject`); deep-link / paste contexts
auto-set `options.suppressException = true`. Success ⇒ `onSuccess`, failure ⇒ `onError`
(`lastResultSuccessValue` also set for `condition` actions).

Runtime request record (`IErpREST`):
`{svc, svcPath, erpRequestMethod, methodParameters?, erpRestPostArgs?, erpBaqArgs?, options?, dataView?, dirtyRows?}`.

UI locking: `erpPostWithDataviewProcessing` broadcasts `EpUIThreadStart/End` of type
`ProcessingRest` around the call — the standard "screen busy" lock.
To keep the UI interactive during an event chain, set **`disableUiLocking: true` on the event's
trigger** (IMetaFxEventTrigger). There is no per-action progress option on
rest-erp itself (BAQ options have `showProgress`).

### 3.2 `erpRequestMethod` — ALL values

`ErpRequestMethod` values, as dispatched by the ERP REST activity handler:

| Value | Behavior |
|---|---|
| `GET` | `erpRestService.get(svc, path, options)` |
| `POST` | `post(svc, path, data)` — `data` = flattened `methodParameters` |
| `PUT`, `OPTIONS`, `HEAD` | enum values exist; **no dispatch entry** (unusable at runtime) |
| `PATCH` | `patch(svc, path, data)` |
| `DELETE` | `delete(svc, path)` |
| `GetAndFillEpDataview` | GET + populate an EpDataView (view id = entity metadata id, e.g. `Erp.Customer`, or `options.alias`) |
| `PatchFromEpDataView` | PATCH using the current row of `dataView` |
| `PostFromEpDataview` | POST current row of `dataView`; response updates that row |
| `PostWithCustomMethod` | `dtCustomPost` — custom method returning data tables |
| `UpdateAndPostDataTable` | `dtUpdatePost` — post update with existing tables/dataviews (`basePath` default `'ds'`) |
| `ErpPostWithDataViewProcessing` | **the standard BO update path** — web equivalent of CopyDatasetToTableset (request) + CopyTablesetToDataset (response), with RowMod tracking. **This is the fallback default when neither requestMethod nor erpRequestMethod is set**. |

If `erpRequestMethod` is a **BAQ method** (`ErpBaqRequestMethod`, see §3.6) the call is routed to the
BAQ activity handler instead and **requires `erpBaqArgs`** (missing → error result).

### 3.3 `ErpPostWithDataViewProcessing` flow

1. `validateDatasetParamArgs` sanity-checks both param-arg arrays.
2. `processErpPostArgs` resolves each `requestParamArgs` entry into concrete table mappings —
   dataset-form args are expanded to one arg per dataset table (viewName per table).
3. The request **dataset is generated from the dataviews** named by `requestParamArgs`
   (`helper.generateDataSet`): the `ds` parameter contains each table's rows filtered per
   `methodParamModifier` and decorated with `RowMod`. Explicit `methodParameters` are merged in as
   scalar parameters.
4. `BeforeErpDataViewPost` activity gives consumers a chance to cancel or mutate the payload.
5. POST — except **GetList/GetRows (non-BOReader) and `Ice.Lib.MetaFxSvc/GetApp` are silently
   converted to GET** when the querystring fits (falls back to POST on 405).
6. Response → `helper.processErpPostResponse` (§3.5).

### 3.4 `methodParameters` (`IParams`)

Array items keyed by `field`; each becomes a request-body property.

| Key | Meaning |
|---|---|
| `field` | Parameter name in the request body (**required**). |
| `value` | Static value; token-parsed (`{View.Col}`, `%session.*%`, `#_ js _#`). Type-aware editor (`restParam`). |
| `epBinding` | Read the live value from this binding instead of `value`. |
| `model` | Send an entire dataview's data as the value (view name). |
| `interpolation` | `{str, args:[{epBinding|session|script}]}` — .NET-style `{0}` string composition. |
| `rowMode` | Adds `RowMod` decoration to model rows. |
| `isArray` | Value is an array. |
| `onlyWhenHasChanges` | Include the model only if it has pending changes. |
| `session` | `%session.<path>%` value, e.g. company. |
| `params` | Nested `IParams[]` for structured objects. |

The rest-erp designer auto-fills `methodParameters` (name+type) from the service's Swagger
(`fillMethodArgs`).

### 3.5 `erpRestPostArgs` — request vs response semantics

Property model `ErpRestPostArgs`:

```jsonc
"erpRestPostArgs": {
  "processResponse": true,          // master switch; nothing merges when false
  "responsePath": "",               // action-level default response location override
  "requestParamArgs": [
    { "paramName": "ds",            // BO parameter name that receives the dataset
      "paramPath": "",              // path prefix inside the request (basePath)
      "viewName": "OrderHed",       // dataview whose rows are sent  (viewName XOR dataset)
      "dataset": { "systemCode": "ERP", "datasetId": "SalesOrder", "serverDataset": "" },
      "dirtyRow": "",               // marker column/state for dirty-row detection
      "methodParamModifier": "default" }   // default | ExcludeBeforeImage | SendAllRows
  ],
  "responseParamArgs": [
    { "paramName": "ds",
      "viewName": "OrderHed",       // dataview that receives the response rows
      "dataset": { "systemCode": "ERP", "datasetId": "SalesOrder" },
      "responsePath": "returnObj",  // where in the response the data lives (per-arg override)
      "mergeBehavior": "replace" }  // 'replace' (default: view cleared first) | 'merge'
  ],
  "fillExtendedProps": {            // optional: dynamic attribute class metadata fill
    "useDefaultValues": true,       // => paramName 'ds', responsePath 'parameters'
    "paramName": "", "responsePath": "",
    "dynamicAttributeClassId": "View.Column"
  }
}
```

- **`requestParamArgs` = what gets SENT.** Each arg names a dataview (or whole dataset by
  `datasetId` — expanded to all of its tables/views) whose rows are packaged into the named BO
  parameter (typically `ds`). `methodParamModifier`:
  - `default` ≈ ref: sends before-image row (`RowMod:''`) + updated row (`RowMod:'U'`), or `'A'` rows;
  - `ExcludeBeforeImage`: only the `'U'`/`'A'` rows;
  - `SendAllRows` ≈ none: everything regardless of RowMod.
- **`responseParamArgs` = how the response merges back.** For each arg the helper locates the
  target dataview; `mergeBehavior` unset or `replace` → the view is **cleared** first (with current
  row/keys saved and restored afterwards — Refresh keeps grid positions); `merge` → rows merged in place. Response rows are read from:
  per-arg `responsePath`, else action-level `erpRestPostArgs.responsePath`, else
  **`parameters/<basePath>`**, then `/<paramName>` (getResponsePath). Dataset-form
  args are expanded per response table (datasetId ↔ table → viewName routing).
- When only `requestParamArgs` are given, the response is merged back into the *request* views using
  the request-row RowMod bookkeeping (`processErpResponseFromRequestParams`).

### 3.6 BAQ over rest-erp (`erpBaqArgs`)

Set `erpRequestMethod` to a value of `ErpBaqRequestMethod` and provide
`erpBaqArgs {baqId, options, data}`; handled by the ERP BAQ activity handler:

| erpRequestMethod | Service call |
|---|---|
| `InitializeBaqMetadata` | `initBaqMetadata([baqId...])` |
| `GetBaqList` | `getBAQList(baqId, options.top)` |
| `GetBaqData` | `getBaq` (GET `BaqSvc/{id}`) |
| `GetBaqMetadata` | `getBaqMetadata` |
| `GetBaqDataAndFillEpDataview` | `dvGetBaq` (fills dataview) |
| `UpdateBaqData` | `updateBaq` (PATCH `BaqSvc/{id}`) |
| `GetNewBaqData` | `newBaq` (GET `BaqSvc/{id}/GetNew`) |
| `GetBaqDesignerData` | `getDesigner` (BAQDesigner GetByID) |
| `GetBaqRuntimeQueryData` | `getRuntimeQuery` (DynamicQuery GetByID) |
| `BaqExecute` | `executeBaq` (KineticErp ExecuteBaq) |
| `UpdateBaq` / `UpdateBaqFieldUpdate` / `UpdateBaqFieldValidate` / `UpdateBaqCustomAction` / `UpdateBaqGetNew` | `kineticErpBaqUpdate` (KineticErp uBAQ wrappers / BaqSvc GetNew) |

### 3.7 Response processing & error handling (`MetaFxRestErpEventService`)

- `result.parameters.*` (non-object values) → **`actionResult.<key>`** columns. So BO output params
  are read in later actions as `{actionResult.<paramName>}`.
  Exception: `parameters.errorsOccurred` → `sysGlobalVariable.errorsOccurred`.
- Scalar `result.returnObj` → `actionResult.returnObj` (null → set to null).
- efx function responses (`options.efxLibrary` set): **every** key of the result →
  `actionResult.<key>`.
- Error detection: a string `result.message` marks the call failed; if
  `result.response.error.ErrorMessage` exists, all `error.*` keys are copied to `actionResult.*`
  (e.g. `actionResult.ErrorMessage`). Failure ⇒ the action's `onError` chain runs. HTTP-level
  exceptions also surface as Kinetic exception slideouts unless `options.suppressException:true`.

---

## 4. `erp-function` (Epicor Functions / EFX)

Properties are **top-level on the action** (no `param`):

```jsonc
{
  "type": "erp-function",
  "efxLibrary": "MyLibrary",           // function library id
  "efxPath": "MyFunction",             // function name
  "apiKey": "",                        // optional API key header
  "methodParameters": [                // same IParams shape as rest-erp (§3.4)
    { "field": "orderNum", "value": "{OrderHed.OrderNum}", "type": "int" }
  ],
  "responseParamArgs": [               // same shape as rest-erp responseParamArgs (§3.5)
    { "responsePath": "MyTableset", "paramName": "MyTable", "viewName": "MyTableset_MyTable" }
  ],
  "onSuccess": [], "onError": []
}
```

Internally it is rewritten to a rest-erp request:
`{svcPath: efxPath, erpRequestMethod: 'ErpPostWithDataViewProcessing',
methodParameters, erpRestPostArgs: {responseParamArgs, processResponse:true},
options: {efxLibrary, apiKey}}` and executed by `MetaFxRestErpEventService`. Because
`options.efxLibrary` is set, **all top-level keys of the function response are copied into
`actionResult.*`** (§3.7) — scalar function outputs are read as `{actionResult.<outputName>}`;
tableset outputs are routed by `responseParamArgs` (the designer auto-generates
`{responsePath: <tablesetParam>, paramName: <tableName>, viewName: '<tablesetParam>_<tableName>'}`
from the library's Swagger).

---

## 5. OTHER SERVER-I/O ACTIONS

### 5.1 `rest` (generic, non-ERP)

Shape:

```jsonc
{
  "type": "rest",
  "param": {
    "request": {
      "svc": "Ice.BO.SomethingSvc",
      "svcPath": "SomeMethod",
      "method": "get|post|...",
      "model": "MyView",                     // dataview used as the request model
      "addFullModelToRequest": false,
      "ignoreIfEmptyDataSet": false,
      "successOnlyIfConditionsAreMet": false,
      "params": [                            // IParams[] (full §3.4 shape incl. interpolation, nested params)
        { "field": "whereClause", "epBinding": "TransView.Filter", "value": null }
      ]
    },
    "response": {
      "model": "MyView",                     // dataview to fill from the response
      "hasMultipleModel": false,             // response has several tables
      "preserveOldData": false,              // don't clear the view first
      "returnObject": "returnObj",           // path of the payload in the response
      "fileType": "",                        // treat response as a file download
      "mergeRow": false,                     // merge into current row instead of load
      "replace": { }                         // JSON find/replace map applied to the response
    }
  },
  "onSuccess": [], "onError": []
}
```

### 5.2 `file-transfer-erp`

Under `param`:

| Key | Type | Notes |
|---|---|---|
| `transferType` | `'download' \| 'upload'` | |
| `specialFolder` | `ErpSpecialFolder` enum (numeric): `Report=0, WebDeployment=1, ReportDefinition=2, CustomReportDefinition=3, UserData=4, CompanyData=5, EWADeployment=6, Attachment=7` | required |
| `serverPath` | string | required. Upload: suffix `_Directory` uploads into a directory (each file becomes `<basePath>\<name>_Directory`). |
| `clientPath` | string | download target name |
| `company` | string | download only |
| `erpFileBoxID` | string | upload only — component id of an `erp-file-box`; its `model.files` are uploaded via `Ice.Lib.FileTransferSvc`. |

All values are token-parsed. Upload with no files, or unknown file box ⇒ nothing happens (logged).
Both paths return `onSuccess` (errors are swallowed by `catchError` into the stream).

### 5.3 `download-attachment-erp`

Under `param` (token-parsed):

```jsonc
{ "type": "download-attachment-erp",
  "param": {
    "docTypeID": "{XFileRef.DocTypeID}",
    "xFileRefNum": "{XFileRef.XFileRefNum}",   // number
    "fileName": "{XFileRef.XFileName}",
    "relatedToSchemaName": "Erp",
    "relatedToFile": "OrderHed"
  },
  "onSuccess": [], "onError": [] }
```

Missing param/service ⇒ `onError`.

### 5.4 `process-import-service`

Under `param`:

| Key | Type | Notes |
|---|---|---|
| `filesCacheKey` | string | key of the client-side cached upload files |
| `bindingServerFile` | epBinding | binding receiving the server file name |
| `specialFolder` | `ErpSpecialFolder` | target folder |

Fires generic activity `ProcessImportUploadFiles`; success = the activity result reports
`status.fileNames.length !== 0` ⇒ `onSuccess`, else `onError`.

---

## 6. TOKENS AVAILABLE IN SERVER-I/O PARAMS

Useful in `where`, `methodParameters.value`, search filters, etc. (all parsed by
`eventParamService.parseValue`/`parseObject` at event execution):

| Token | Meaning |
|---|---|
| `{View.Column}` | current value from a dataview binding |
| `%value%`, `%oldValue%`, `%row%`, `%column%`, `%current%`, `%previous%`, `%readOnly%`, `%currentDataView%`, `%previousDataView%` | trigger-context values (column-change events) |
| `%session.<path>%` | session values, e.g. `%session.context.company%` |
| `%<view>.row%` / `%<view>.count%` / `%<view>.hasRow%` / `%<view>.hasChanges%` | dataview state (rewritten to `#_trans.dataView('<view>')..._#`) |
| `%dataset.<DatasetId>.hasChanges%` | dataset-level dirty check |
| `#_ <js> _#` | raw JS (double-evaluated — wrap string results in quotes, lessons §5) |
| `~_Control.property_~` | live component model property |
| `?{View.Col}` / `??{View.Col}` / `?{View.Col,'dflt'}` | **provider-filter-only** binding tokens (§2.4) — NOT parsed in event params |

---

## 7. `searchResult` / `actionResult` QUICK REFERENCE

| Dataview | Written by | Contents |
|---|---|---|
| `searchResult` | search-show OK (sliding), silent search hit, grid-cell search OK | the selected/found result rows (all columns of the search's result table, flattened names for BAQ) |
| `actionResult.searchCancelled` | search-show (sliding) | `false` on open, `true` on cancel |
| `actionResult.searchResult` | search-show (sliding) | cleared (`undefined`) on open |
| `actionResult.<param>` | rest-erp / erp-function | BO output parameters / function outputs / error fields |
| `actionResult.returnObj` | rest-erp | scalar returnObj |
| `sysGlobalVariable.errorsOccurred` | rest-erp | BPM/BL errorsOccurred flag |

---

## 8. `event-column-disable` / `event-column-enable` — EXACT SHAPE (contradiction found)

The runtime reads the ACTION OBJECT itself: if it has a top-level `dataTable`, column-change
events are disabled for that dataview only; otherwise they are disabled for ALL dataviews.

`IColumnChangeParam` = `{ param?: {columns: string[]}, dataTable?: string }`,
and the App Studio property model (`MetaFxDataTableEventProperties`) writes **`dataTable` at the top
level of the action**. Canonical shape:

```jsonc
{ "type": "event-column-disable", "dataTable": "OrderHed" }
...
{ "type": "event-column-enable",  "dataTable": "OrderHed" }
```

**Flag vs lessons §3w:** the lessons record `{"type":"event-column-disable","param":{"dataTable":"OrderHed"}}`
as "the working shape" and a top-level `dataview` key as a no-op. In fact the runtime reads
**only top-level `dataTable`**. A `param.dataTable` value is never read — that variant falls into
the else-branch and disables column events on **ALL dataviews**, which does stop a feedback loop
(hence it "worked") but with a much wider blast radius; and `dataview` was a no-op simply because the
key name is wrong, not because top-level placement is wrong. Prefer top-level `dataTable`.

---

## 9. CONTRADICTIONS / CORRECTIONS SUMMARY

1. **`event-column-disable` shape** — the runtime reads top-level `dataTable`;
   `param.dataTable` (lessons §3w "working form") is ignored and silently degrades to
   disable-ALL-views. Correct: `{"type":"event-column-disable","dataTable":"<Table>"}` (§8).
2. **Search icon trigger** — lessons §3y CONFIRMED: App Studio's "On Search Click" =
   `epOnSearchBarClick` → `EpSearchButtonEvent`, and the generated event trigger is
   `{type:'EpBinding', hook:'onClick', target:<binding>}` (§1.9). The earlier reference-table claim
   that the icon hook is `onSearch` is wrong as authored guidance (though `EpBinding/onSearch` is
   *also* consulted by the click handler — first, in fact — it doubles as a column-change listener,
   which is the §3x loop). Any `Control`-type trigger never binds to the icon.
3. **"Native field search"** is not a framework fallback: with `enableSearch:true` and *no* event on
   the binding, the click handler returns a null stream (the `'null' where a stream was expected`
   error, §1.9). Base fields work because the base app ships `EpBinding/onClick` events.
4. **`searchOptions` has no `whereClause` / `searchName` / `gridColumns` properties** — if the
   existing reference lists them, remove; use `preLoadSearchFilter`, `searchForm`,
   `launchSearchType`/`launchSearchName` (§1.2).
5. **`searchForm` casing** — internal defaults use both `'default'` (GetSearchOptions context,
   hasDefaultSearchForm) and `'Default'` (grid-cell + sliding panel). Client cache key
   `${like}.${searchForm}` is case-sensitive; be consistent (base apps typically use `"default"`).
6. **`erp-baq` event action keys are top-level on the action** (no `param` wrapper) — matches how
   the lessons file used it; worth stating explicitly since search-show/rest-erp DO nest under `param`.
7. **`ErpRequestMethod.PUT/OPTIONS/HEAD`** exist in the enum but have no dispatch entry — do not use.
8. **GetList/GetRows POSTs are auto-converted to GETs** when small enough (§3.3) — explains GETs in
   network traces despite `requestMethod:"POST"` in the layer.
