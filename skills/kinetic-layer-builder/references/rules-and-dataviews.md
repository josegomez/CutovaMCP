# Kinetic Rules Engine & DataView/Binding System — Reference

Derived from observed runtime behavior and App Studio output. This document is self-contained.

---

# PART A — THE RULES ENGINE

## A1. The rule object schema (`rules.jsonc` / `IMetaFxRowRule`)

Every field below is reconstructable from how the runtime interprets rules and how the App Studio
rule designer serializes them.

| Field | Type | Written by designer? | Semantics |
|---|---|---|---|
| `id` | string | yes (`rowRuleName`) | Unique rule id. Runtime replaces a rule with the same id when re-added (same-id rules are de-duplicated / replaced). Auto id `rule-auto-id-N` when omitted. |
| `description` | string | yes | Free text; only used in log/error messages. |
| `dataView` | string | yes | **The owning dataview.** The rule is attached to `EpDataView(dataView).rules` when that view is created. A rule whose `dataView` names a view that never gets created **never runs**. |
| `condition` | string | yes (Conditions mode) | Criteria expression string (grammar in §A5). **Empty/absent condition ⇒ criteria `true` ⇒ actions always apply** (`EpDataRowRules.rule(true, …)`). |
| `actions` | `IRowAction[]` | yes | Action list, §A2. One rule may hold many actions. |
| `disabled` | boolean | yes (`rowRuleDisable`) | **A rule with `disabled: true` is filtered out at load time and never even instantiated** — the load filter is `e.dataView === dataview && (includeDisabled \|\| !e.disabled)`, `includeDisabled` defaults to `false`. (Runtime code can later flip `rule.disabled`, which triggers re-evaluation — §A6.) |
| `mode` | `'A' \| 'U' \| 'D'` | yes | Designer writes `'A'` for "New Rule", `'U'` for an edit of an existing/base rule. Runtime **only checks for `'D'`** and skips those rules — `'D'` is how a layer deletes a base rule. `'A'` vs `'U'` matters only to the merge/designer, not the engine. |
| `customizable` | boolean | yes (always `true` from designer) | Locks/unlocks the rule in App Studio; not consumed by the runtime engine. |
| `function` | string | optional | Raw JS function **body** (delegate rule). Compiled with `new Function(...dependentFields, function)` and wrapped as an `fn` criteria. Mutually exclusive with `condition`. |
| `namespace` | string | optional | If set, `function` is instead a function **name** looked up on `window[namespace][function]` (external JS module). Missing ⇒ warn `Not Implemented` and rule dropped. |
| `dependentFields` | string[] | with `function` | Column names (may be `View.Column` or `View.$rowCount`) whose values are passed as arguments to the delegate; also drive re-evaluation subscriptions. Cross-view refs and `$rowCount` are resolved at evaluation. |
| `listColumn` | string | multiActionColumn mode | **Dynamic rule** (see below). Column on the rule's dataview whose *value* is a delimited list of target column names. |
| `actionColumn` | string | multiActionColumn mode | Column whose value is a delimited list of action names (e.g. `SettingStyle.Disabled~SettingStyle.Invisible`). |
| `targetDataView` | string | multiActionColumn mode | View against which the dynamic bindings `${targetDataView}.${listColumn-item}` are built. Defaults to the rule's `dataView`. |
| `listDelimiter` | string | multiActionColumn mode | Delimiter for the lists, default `'~'`. |

**Dynamic rules** (`listColumn`/`targetDataView` present) are excluded from the normal static rule
build and instead registered separately: the runtime subscribes to the owning view's
`table.onColumnChange()`, and whenever the `listColumn`/`actionColumn` value changes it removes and
re-adds the rule with freshly computed actions. This is the MetaUI pattern where the *server*
pushes a tilde-delimited list of columns to disable/hide into a row column.

**Rule loading pipeline:** when the view loads, the runtime registers the *entire merged* rules
list (base + layers). Then, as each dataview is created, it attaches the rules whose `dataView`
matches that view's id (`epDataView.rules.add(...)`). In App Studio designer mode all rules are
created with `disabled: true` and only enabled for preview.

## A2. Every rule ACTION type

### A2.1 The JSON action object (`IRowAction`)

| Field | Used by | Meaning |
|---|---|---|
| `action` | all | The action name string (table below). |
| `epBinding` | SettingStyle.\*, SetColumnValue, ChangeImage | Target binding `View.Column`. Designer always writes `${ruleDataView}.${field}` but the runtime parses it with `getColumnBinding(binding, '$current-view')` so **any** `View.Column` string works, including a view different from the rule's `dataView`. A bare column (no dot) resolves against the *executing* view at runtime (`$current-view` substitution). |
| `value` | SetColumnValue / SetViewColumnValue / ChangeImage / HidePage | Constant to set (number/bool/string, designer coerces it), or source binding for SetViewColumnValue, or image name for ChangeImage, or pageId for HidePage. |
| `columns` | DisableColumns | Array of **column names** (no view prefix); runtime prefixes each with the rule's `dataView` (`${dataview}.${col}`). |
| `exceptTheseColumns` | DisableRow | Array of column names exempted from the row disable. Designer writes `[]` when none selected. |

### A2.2 Complete action-name catalog

JSON `action` string → runtime construction:

| JSON action string | Runtime action | EpControlActionType / behavior |
|---|---|---|
| `SettingStyle.Disabled` | control action | `Disabled` → sets the bound components' `disabled` state |
| `SettingStyle.ReadOnly` | control action | **`Disabled`** via `EpDataRowRules.disableAction` — NOTE: the runtime maps `SettingStyle.ReadOnly` to the *disable* action, not to `EpControlActionType.ReadOnly`. (`EpDataRowRules.readOnlyAction` exists but the JSON rule translator doesn't call it — so a JSON `SettingStyle.ReadOnly` behaves identically to `SettingStyle.Disabled`.) |
| `SettingStyle.Invisible` | control action | `Invisible` → sets `hidden` state |
| `SettingStyle.Error` | control action | `Error` status (red highlight on control/grid cell) |
| `SettingStyle.Warning` | control action | `Warning` status |
| `SettingStyle.Ok` | control action | `Success` status |
| `SettingStyle.Highlight` | control action | `Info` status |
| `SettingStyle.RowError` / `RowWarning` / `RowOk` / `RowHighlight` | rows action | `EpDataRowRuleRowsActionType.Error/Warning/Success/Info` — CSS class per grid row: `ep-row-rule-error`, `ep-row-rule-warning`, `ep-row-rule-success`, `ep-row-rule-info`. Applies to *every row* whose data matches the condition (grid row styling/highlighting — this exists and is the row-highlight facility). |
| `SettingStyle.ShowInToolbar` | control action | `ShowInToolBar` |
| `SettingStyle.showInSecondaryToolBar` | control action | `showInSecondaryToolBar` (lower-case `s` is literal) |
| `SetColumnValue` | value action | Writes `value` into the target binding's view/column via `dv.set()` when the condition is true. |
| `SetViewColumnValue` | value action (binding mode) | `value` is itself a `View.Column`; the current value of that binding is copied into the target binding. Designer emits this automatically when the action value's `fieldDataType === 'field'`. |
| `DisableRow` | rows action (`disableRow` kind) | Disables every component bound to the rule's dataview except `exceptTheseColumns`; per-row in grids. Full semantics in §A2.3. |
| `DisableColumns` | control action | `Disabled` on each `${dataView}.${column}` binding — i.e. sugar for a multi-binding `SettingStyle.Disabled`. |
| `HidePage` | hide-page action | Sets `hide = <conditionResult>` on the `sysPages` row whose `pageId === value` and broadcasts `EpTreeNodeVisibleStatus` so the nav tree hides the page node. **`executeOnFalseCondition = true`** — it runs on both condition outcomes, so the page re-shows when the condition goes false. |
| `ChangeImage` | control image action | `ChangeImage` + `changeImage = value` (an image name; the designer offers ~80 stock names like `Approved`, `Warning`, `RedFolder`). Rendered per grid column. |
| *anything else* | — | `logger.warn("Action not implemented <action>")` and the action is dropped. |

Designer-only notes: the App Studio action dropdowns are
`SettingStyle: [Disabled, Invisible, ReadOnly, Status, RowStatus, ShowInToolbar, showInSecondaryToolBar, sequence]`,
`SetValue: [SetColumnValue]`, `Disable: [DisableColumns, DisableRow]`, `HidePage`, `ChangeImage`.
`SettingStyle.Status` + a status of Error/Highlight/Ok/Warning is *serialized* as
`SettingStyle.Error` etc. per selected column; `SettingStyle.RowStatus` serializes to
`SettingStyle.Row<Status>`.
**`SettingStyle.sequence` has no runtime case — it hits the "Action not implemented" branch.**

The full `EpControlActionType` enum (for completeness — includes members not reachable from JSON
rules: `Bold`, `OK`, `Highlight`, `Mandatory`, `ReadOnly`, `Required`, `LabelText`, `Status`):
`Bold, Error, Warning, Info, Success, OK, Highlight, Disabled, Mandatory, Invisible, ReadOnly,
Required, LabelText, Status, ShowInToolBar, showInSecondaryToolBar, ChangeImage`.
Code-built rules (base app code, not JSON) can use the extra members; JSON layers cannot.

### A2.3 `DisableRow` — exact semantics

Construction: `EpDataRowRules.disableRowAction(exceptColumns?)` creates an
`EpDataRowRuleRowsAction` with `EpDataRowRuleRowsActionType.Disabled` and
`dataActionKind = EpActionKind.disableRow`, `executeOnAllRows = true`.
`exceptTheseColumns` values are stored as `exceptBindings` (plain column names).

Application to **form controls**:

1. Whenever any executed rule set contains a disableRow action, the view recomputes a **global
   per-view state** from *all currently-true* rule results:
   - `disabledRow = (number of active DisableRow actions) > 0`
   - `disabledExceptColumns` = the **intersection** of the `exceptBindings` arrays of ALL active
     DisableRow actions. One active action ⇒ its own list; two active actions ⇒
     only columns excepted by *both* stay enabled; any active action with an empty list ⇒ nothing
     is excepted.
2. A rows-action event is broadcast with only the **view** set (no column) — every component whose
   binding *view* matches receives it.
3. Each bound component then sets its `disabled` state (priority `rowRuleDisableRow`) to
   `true` unless its own bound column is in `disabledExceptColumns`.

Consequences you can rely on:
- `DisableRow` disables **every component bound to any column of that view** — including status
  shapes bound to `View.XxxShape` columns (confirms lessons §3f). Exempt them by column name.
- It **is symmetric/reversible**: when the condition flips false, the per-view state is
  recomputed from the remaining true results and re-broadcasts `disabledRow=false` (confirms the
  §3l correction of §3k).
- **Two DisableRow rules on the same view compose as an OR**: the row stays disabled while *any*
  of them is true, and the effective exception list is the *intersection*. This is the precise
  explanation of lessons §3l ("two rules managing the same row's disable state don't
  compose"): a custom lock rule that is true keeps the row disabled even after the base
  `openOrderRule` goes false — not a bug, the documented any-true semantics.

Application to **grids**:
condition is executed per data row (`rules.executeRowsRuleCriteriaItems(dataRow)`);
`result.rowDisabled = true` if a matching rule has a disableRow action. **Grid quirk:** if any
matching row event's disableRow action has a *non-empty* `exceptBindings`, `rowDisabled` is forced
back to `false` — the grid then relies on per-cell disabling instead of the
whole-row disable. Grid row *state coloring* (`RowError` etc.): if multiple rows-actions match a
row, **the last one wins**. Results are cached per data row in
`dataRowRulesForAllRows.dataRowsResults` and reset when a rule's criteria columns change.

## A3. Condition grammar (the parser)

`EpCriteriaParser.parse()` tokenizes with ordered regex replacement passes (order is load-bearing):
dates → `like` → quoted strings → `{field}` tokens → booleans → `is not`/`is` → `not` →
**bindings** → identifiers → numbers → `in (…)` → `and`/`or` → compare operators → criteria
triples → parenthesized blocks. Then `parseGroup` builds an AND/OR tree (AND binds tighter; ORs are
gathered into one top group).

### A3.1 Operators

- Comparison: `=`, `<>`, `>`, `>=`, `<`, `<=`, `in (a,b,c)`, `contains`, `starts`, `ends`
  (mapped to `EpCriteria.eq/neq/gt/ge/lt/le/in/contains/starts/ends`).
- `is` ⇒ `=`, `is not` ⇒ `<>`.
- `like 'a%'` sugar: `'%x%'`⇒contains, `'x%'`⇒starts, `'%x'`⇒ends, `'x'`⇒`=`.
- Joins: `and`, `or` (case-insensitive), `not` (prefix, applies to the following criteria or
  `(...)` block), parentheses for grouping.
- If either side of a comparison is the literal-side, the parser swaps operands and reverses the
  operator so the column is always on the left.
- **A bare boolean column is valid criteria**: `Approved and Signed` — a lone column token becomes
  `column = true`.

### A3.2 Literals

- Strings: single quotes, escape a quote by doubling `''`.
- Numbers: int/float, up to 2 decimals in the regex `\d+(\.\d{1,2})?`.
- Booleans: bare `true`/`false`.
- Dates: `Date('2024-01-31')` or bare ISO `2024-01-31` / `'2024-01-31T00:00:00'`. Invalid dates
  push parse errors.
- `null` / `undefined` are recognized identifiers with special argument categories.
- String comparison is **case-insensitive** by default (values lowercased, unless
  `sensitiveCompare`).

### A3.3 Column references, cross-view references, `$rowCount`

Left side (the "argument" column) and right side (the "value") each accept:

| Form | Parsed as | Notes |
|---|---|---|
| `Column` | column on the **rule's own** `dataView` | evaluated against the current data row (row-by-row for grid actions). |
| `View.Column` (dotted) | cross-view binding | identifier regex allows dots; token with a `.` goes through `EpBindingService.parseBinding` and becomes `[View].[Column]`. |
| `[View].[Column]` (bracket) | cross-view binding | matched by the dedicated binding regex **before** identifiers. |
| `[View].[$rowCount]` | pseudo-column | The binding regex explicitly allows `$` in the column part (`[[$]*`). At evaluation, `column === '$rowCount'` returns `dv.count` (the target view's current row count). Works for the rule's own view or a cross view. |
| `{Column}` / `{View.Column}` as the **value** | value-column reference | `{X}` ⇒ compare against column X (same view unless dotted); `[view].[col]` also accepted as value. |
| `{$VariableName}` / `{$Rec.Name}` | data-filter variable | resolved via the filter's variables, then the view filter's variables, then the data model variables. `{$parent.Col}` is how parent/child filters are compiled (§B4). Variable-driven rules re-evaluate on the `EpBindingVariables` event. |

**`$rowCount` is the only pseudo-column.** There is no `$rowIndex`, `$hasChanges`, or any other
`$`-column in the evaluator — the only special-case is `'$rowCount'`. Dataset dirtiness is exposed
to *events* via `%dataset.<View>.hasChanges%` tokens, not to rule conditions.

**Cross-view resolution:** during pre-processing every dotted/bracketed reference becomes an
`IEpBinding`; at evaluation, if `epb.view !== thisView.id` the engine fetches the other view and
uses its **current row** (`dv.dataRow()`), not the row being iterated. If the cross view has **no
current row** and the column is not `$rowCount`, the criterion evaluates **false** — this is why
`OrderNum = 0` misses the empty state but `[View].[$rowCount] = 0` catches it (lessons §3o
rationale, confirmed). A referenced column that doesn't exist on the row pushes a
`column not found: <col>` execution error, logged once per rule build as
`Error in row rule id:[...] expression: ... errors: ...`.

**`sysPages.pageId` rewrite:** before parsing, the runtime rewrites `[sysPages].[pageId]` /
`sysPages.pageId` to `[sysPages].[realPageId]` so conditions match "virtual" card pages correctly.

**Parse failure mode (important):** parse errors are logged to console
(`Errors in criteria parser for expression: …`) and `parse()` returns an **empty expression**.
An empty expression means `hasConditions === false`, and `EpDataViewFilter.evaluate()` then
returns the input row unfiltered — i.e. **an unparseable condition degrades to "true whenever the
rule's own dataview has a current row"**. Watch the console for the parser error line; the visible
symptom is a rule that applies unconditionally.

> **FLAG — dotted `$rowCount` (`OrderHed.$rowCount = 0`) vs lessons §3o.** In the parser grammar
> the identifier regex is `[_a-zA-Z][_a-zA-Z0-9.]*` — `$` is NOT a legal identifier
> character — and the binding regex requires literal `]` characters, so the *dotted* form
> `View.$rowCount` cannot tokenize into a `$rowCount` binding; only the bracket form
> `[View].[$rowCount]` can. By the grammar, the dotted form should produce a parse error/degenerate
> condition (see failure mode above), which can *look* correct in some states. Lessons §3o reports
> the dotted form shipping and working on a live system; either a server-side normalization
> rewrites it before the client parses, or the field observation was the degenerate-condition
> coincidence. **Recommendation: always emit the bracket form `[View].[$rowCount]`** — it is what
> base-app rules use and is unambiguously supported by the parser. Dotted plain columns
> (`OrderHed.ReadyToCalc`) are fully supported; the caveat is only for `$rowCount`.

## A4. Rule evaluation: when and how rules (re-)evaluate

One `EpDataRowRuleBuilder` per dataview, exposed as `dataView.rules`.

**Build:** for each enabled rule, the criteria string is parsed into an `EpDataRowRuleFilter`
(an `EpDataViewFilter` bound to the owning view), pre-processed to extract:
- `bindings` — every column referenced on either side of every criterion (own-view columns become
  `thisView.column` bindings; cross-view stay as written),
- `views` — `[ownViewId] ∪ {binding views}`,
- `variables` — `{$var}` names.

**Subscriptions:** the builder subscribes to the global binding-event stream and re-evaluates when
an event's view is in ANY rule's `views` list and the event type is one of:

```
ValueChanged, RowChanged, ViewLoaded, ViewAdded, RowReplaced,
RowAdded, RowDeleted, Rollback, or any event with isRowCountChanged === true
```

- For `ValueChanged` (a column edit) the rule must reference **that exact binding** — unless the
  rule was built with `onAnyFieldChange` (a code-only option; JSON rules don't set it). So *typing
  in a field re-evaluates only rules whose condition mentions that column*.
- Row add/delete events that will be followed by a RowChanged are skipped to avoid evaluating
  against a half-updated state. A brand-new empty view (`ViewAdded`, 0 rows) does
  not trigger evaluation.
- **Cross-view conditions re-evaluate when the referenced view changes** — because the other
  view's id is in `views`, its RowChanged/ValueChanged/load events all pass the filter. This is
  why a rule with `dataView: TransView` and condition on `OrderHed.ReadyToCalc` re-fires on
  OrderHed edits (confirms lessons §3d).
- Variable-based conditions re-evaluate on `EpEventType.EpBindingVariables` broadcasts.
- Initial evaluation happens at rule build and again on `refresh()`.
- Rules also re-evaluate when a rule object is added/removed/disabled at runtime
  (change types `set/add/remove/clear/disabled/condition/criteria/refresh`).

**Result diffing:** the view stores the last boolean result per rule and only queues action
execution when some rule's result actually changed. Actions are then executed and translated into
binding events.

**Late-created components catch up:** when a component registers its binding it calls
`dv.getDataRowRuleEvents(view, column)` and applies the *current* rule results immediately.
External views that a rule touched are chained recursively (`externalDataViews`) — so a rule
on view A that styles a binding on view B is replayed when B's components initialize.

## A5. How rules target components — binding match, conflicts, `model.*` interplay

### A5.1 Targeting = binding equality, not component id

A control action emits one `IEpBindingEvent` per target binding, carrying `{view, column}`. Every
`EpBindingComponent` subscribes to the global stream filtered **only by view**, and applies a
control action only when `epb.column === event.column`. Comparison is case-insensitive.

**Therefore: a rule action hits EVERY component whose `model.epBinding` equals the target
`View.Column` — there is no component-id targeting.** This confirms lessons §3c (a rule on
`CallContextBpmData.Character19` swept in the base shapes sharing that binding) and §3n (give a
control a unique binding — the column need not exist in any dataview — to make it rule-targetable).

### A5.2 Multiple rules on the same binding/action — conflict resolution

Two mechanisms:

1. **Event filtering**: among events in one batch that share the same binding AND the same action
   *type* (same `dataActionKind` and same `EpControlActionType`, with all status colors counted as
   one type): **the last event with `result === true` wins**; if none is true, the last one wins.
   Losing events are discarded.
2. **True-rule re-append**: when a rule's condition (or enablement) flips to false, the builder
   searches all *other* still-true rules whose actions share a binding and action type with the
   false one and re-injects those actions into the batch. Net effect:
   `Rule1: if F1 then disable F10` and `Rule2: if F3 then disable F10` compose correctly — F10
   re-enables only when **both** are false.

So per-binding `SettingStyle` actions from multiple rules compose as an OR, exactly like the
DisableRow per-view state (§A2.3).

### A5.3 State-property priority stack and `model.hidden` defaults

Rule outcomes land in a per-component priority map, not directly on the model:

```
EpPropertyStatePriority: control=0 (the model property itself),
  extended=1, keyField=2, rowRuleDisableRow=3, rowRule=4
EpStateProperty: disabled, hidden, labeltext, readonly, required, status
```

Resolution for e.g. `hidden`: **if `model.hidden` differs from the default (`false`), the model
value wins outright**; otherwise priorities are walked ascending 1→4 and the first non-default
value wins. False values are removed from the map, so an inactive rule leaves no residue.

Practical consequences (all confirm lessons §3d):
- Author custom controls with `model.hidden:false` / `model.disabled:false` and let rules drive
  the state; a hard `model.hidden:true` **beats every rule** that wants the control visible.
- `keyField` (priority 2) is the built-in "no data ⇒ disabled" behavior: any non-key-field bound
  control is disabled whenever its view has no rows. It outranks rowRule (4) in the walk, so a rule
  cannot re-enable a control on an empty view.
- `rowRuleDisableRow` (3) is checked before `rowRule` (4): an active DisableRow keeps a control
  disabled even if a per-binding rule sets disabled=false.

### A5.4 Read-only vs disabled at the component

`EpControlActionType.ReadOnly` sets the `readonly` state, `Disabled` sets `disabled`, `Invisible`
sets `hidden`, and Error/Warning/Info/Success set `status`. But note §A2.2: JSON
`SettingStyle.ReadOnly` is translated by the runtime to the **Disabled** action, so from a layer
you effectively have Disabled / Invisible / the status colors / row actions / value actions /
HidePage / ChangeImage.

## A6. TransView and `SysReadOnly` — the framework read-only orchestration

- **TransView is NOT created by the framework.** The system views auto-created for every app are:
  `actionResult, searchResult, sysLicensedModules, sysTools, sysGlobalVariable, sysPages, sysTabs,
  CallContextBpmData, sysVariable, sysTreeNode, sysDragRows, sysGanttTasks, sysGanttSelectedRow,
  sysPublishedData, sysParams, sysDynamicReportParams` (each registered as a system view).
  `TransView` comes from the **base app's `dataviews.jsonc`** like any other view — it simply has
  no `schema`/`serverDataset`, so it is a pure client table (rows are plain JS objects; any column
  springs into existence on first write). ERP services *treat it as well-known*: e.g. the main menu
  ignores it, and the current-dataview monitor reads `TransView.SysPrimaryViewName`.
- **`TransView.SysReadOnly` framework consumers:**
  - Standard toolbar tool actions (New/Delete dropdowns etc.) are enabled only when
    `!transViewDv.get('SysReadOnly')` — flipping it true suppresses the standard tools.
  - The attachments component uses a code-built rule
    `EpCriteria.eq('[TransView].[SysReadOnly]', true) OR eq('[TransView].[SysEditableAttachments]', false)`
    to disable attachment editing.
  - Everything else that reacts to `SysReadOnly` is **app-level JSON rules** in each base app
    (e.g. Sales Order's `openOrderRule` DisableRow keyed on `[TransView].[SysReadOnly] = true`, and
    `hideToolsReadOnlyMode` which hides toolbar tools). `hideToolsReadOnlyMode` is **not** a
    framework built-in — it lives in the app's `rules.jsonc`, so its exact actions must be read
    from `GetNativeKineticApp` output per app.
- Other well-known TransView columns: `SysPrimaryViewName` (primary view for the
  toolbar/current-dataview monitor), `SysEditableAttachments`, `SysClientPrintingEnabled`,
  plus app-defined scratch columns.
- **The shipped read-only recipe** (lessons §3l): set `TransView.SysReadOnly` from an event
  (`row-update`); the base app's own DisableRow rules keyed on it lock/unlock every governed view,
  the standard toolbar tools are suppressed, and because rules on `[TransView].[SysReadOnly]` have
  TransView in their `views` list they re-evaluate the moment the flag changes (§A4). Do not add a
  second DisableRow on a view the base already governs — any-true composition (§A2.3) will hold
  the lock.

---

# PART B — DATAVIEWS AND BINDINGS

## B1. Dataview schema (`dataviews.jsonc` entries → `MetaFxDataView`)

All fields:

| Property | Type | Semantics / default |
|---|---|---|
| `id` | string | View id — what bindings/events/rules reference. Must not start with a digit and must avoid `` `!@#$%^&*()+-=[]{};':"\|,.<>/?~ `` (`EpBindingService.validateDataViewId`). |
| `description` | string? | Free text. |
| `table` | string? | Logical/client table id. **Views with the same `table` share one `EpDataTable`** — an existing table with that id is reused. This is how multiple filtered views over one dataset work. |
| `staticFilter` | string? | Criteria string (same grammar as rule conditions, §A3) applied as the view's filter. Defaulted to `''`. |
| `parent` | `EpIceParentDataView`? | `{parentDataview: string, parentColumns: string[], childColumns: string[]}` — §B4. |
| `schema` | string? | System code: `"Erp"`, `"Ice"`, or `"baq"` (§B9). Absent ⇒ pure client view (TransView-style). The rule designer treats schema-less views + `KeyFields/KeyFieldParams/LandingPage` as non-selectable auto-injected views. |
| `additionalColumns` | `EpAdditionalColumn[]`? | Client-only columns; entry shape `{columnName, caption, datatype}` (legacy: plain string array still tolerated). They surface in designer column lists and grid column pickers; they do not go to the BO. **`datatype` must be a KINETIC type token — `string`, `int`, `decimal`, `date`, `boolean`, `guid` — NEVER a SQL type. FIELD-PROVEN: `"nvarchar"` makes the whole dataview silently disappear on import. Full per-kind required-property sets: §B12.** |
| `datasetId` | string? | Client dataset alias grouping sibling views; the key for `requestParamArgs`/`responseParamArgs` dataset expansion (§B8) and for sibling-view lookup. |
| `serverDataset` | string? | Real server tableset name. When it differs from `datasetId`, `datasetId` is treated as an alias and `serverDataset` is used for the `GetDatasetTables` fetch. |
| `serverTable` | string? | Real server table name; falls back to `table`/`tableId` when absent. Copied onto the runtime view. |
| `memoTableName` | string? | Memo table for the memo feature (designer "Other settings"). |
| `contextOverrideView` | string? | View id whose context-menu metadata should be used instead. |
| `isSystemView` | boolean? | Internal flag; auto-created sys views get `true`. Default written by designer: `false`. Affects: `confirmChanges` default false, exclusion from view-change events (below), debug panel grouping. |
| `disableViewChangeEvents` | boolean? | Excludes the view from `viewChanged/viewChanging` plugin triggers. Effective default: `false` for normal views, `true` for system views when unset (`!!view.disableViewChangeEvents \|\| (!!view.isSystemView && view.disableViewChangeEvents === undefined)`). |
| `data` | any? | Free payload. For `schema:"baq"` views this holds the **BAQ id** (§B9). |
| `tools` | `IEpStdToolAction`? | `{new: {text?, hidden?}, delete: {text?, hidden?}}` — customizes/hides the standard New/Delete toolbar entries for this view (designer strips empty objects). |
| `sort` | `IEpDataSort[]`? | Sort descriptors passed straight into the view options. Shape `{column, descending}` (kendo SortDescriptor — wrong keys build `field: undefined` and crash kendo `orderBy`, per verified reference §6). |
| `columnProperties` | `IEpColContextProperties[]`? | Per-column context-menu overrides; entry keyed by `column`. |
| `mode` | `'A'\|'U'\|'D'`? | Layer merge mode. **`'D'` ⇒ the view is skipped entirely at load.** |
| `customizable` | boolean? | App Studio lock flag (designer-only). |
| `confirmChanges` | boolean? | Participate in the dirty-check "confirm leave" dialog. Default: `true` for non-system views, `false` for system views and for every view of a `viewType:"Dashboard"` app. |
| `attachInfo` | `EpAttachInfo`? | Attachment metadata. |
| `dataMode`, `name`, `viewId`, `tableId`, `openDesigner` | — | **Not on `MetaFxDataView`.** `dataMode:"rows"` is a *combo component* property, not a dataview property; `name/viewId/tableId` are echoes seen in exported JSON / `IEpViewDataItem` cache entries, not consumed from `dataviews.jsonc`. |

## B2. View creation pipeline

When the view loads, the runtime resets the transaction, registers rules (§A1), then creates every
`dataviews.jsonc` view (`inTransaction:true, isSysView:false`), then the 16 system views (§A6
list). Per view:

1. skip `mode:'D'`;
2. `trx.addFromTable(id, table, {filter: staticFilter, tableOptions:{rowMod:false}, sort})` —
   note **`rowMod:false`**: the underlying `EpDataTable` does *not* auto-maintain the `RowMod`
   column for MetaFX views (that's why events must set `RowMod:"U"` manually after `row-update`;
   §B11);
3. `setParent(...)` if `parent` present;
4. `epDataView.rules.add(...)` with the rules for that view id;
5. copy `isSystemView`, `serverTable`, resolve `confirmChanges`;
6. broadcast dataview-added (unless suppressed).

Ignore list (never removed on reset): `Constant, CallContextBpmData, CallContextClientData,
SysHistTasks, SysActiveTasks, SysReportDetail, SysRptLst, SysSchedTasks, SysTaskLogs, DebugLogData,
sysViewLockFlags, LayoutManager`. Attachment views may be created dynamically by the
dataset mapping service and are back-registered via the `ErpDatasetDvCreatedDataItem` event (§B8).

## B3. `EpDataView` runtime essentials

- `data` / `count` / `row` (current index, `-1` = none) / `dataRow(index?)` (undefined when no
  current row) / `hasData()`.
- `get(column, rowIndex?)` / `set(column, value, rowIndex?, context?)` — delegate to the shared
  `EpDataTable`. Rows are plain objects: **writing a column that doesn't exist simply creates the
  property** — this is the basis for "bind to a column that doesn't exist and it's
  created on the fly" (lessons §3n). Reading a missing column returns `undefined` (and rule
  evaluation logs `column not found` only when the property is absent via `hasOwnProperty`).
- Change tracking: `isDirty`, `hasModified/hasDeleted/hasAdded`, `hasChanges` (OR of the three),
  `modifiedRows()/addedRows()/deletedRows()/addModRows()`, `getOriginalDataRow`,
  `acceptDataRowChanges/rejectDataRowChanges`.
- `commit(options)` → table commit: rolls changes into originals and, when the table maintains
  RowMod, resets `RowMod` to `''`. `rollback()` restores.
- `rules` → the `EpDataRowRuleBuilder` (§A4); `filter` → the view's `EpDataViewFilter`
  (staticFilter + runtime `dataview-filter-set`).
- `addRow/deleteRow/replaceRow`, `findRow/findRowIndex/match/matchFirst` (criteria-based),
  `setRow/trySetRow` (row navigation with cancellable `rowChanging`).
- Every table change is translated into binding events by `createBindingEventFromTableChange`:
  `modify` ⇒ `ValueChanged` (with `column`, `value`, `oldValue`, `currentRow`),
  `load` ⇒ `ViewLoaded` (+row reset), `add/delete/replace/rollback/commit` ⇒ the corresponding
  `EpBindingEventType`, all carrying `rowCount/oldRowCount/isRowCountChanged`. These are exactly
  the events that drive rule re-evaluation (§A4) and component refresh (§B6). This function is the
  `processErpPostResponse → createBindingEventFromTableChange → broadcast` frame seen in the
  Refresh crash stack (lessons §3aa) — the crash itself is downstream in a subscriber (§B7).

`EpDataViewModelService` (the "transaction", `EpDataViewModelService.current`): registry of views
(`view(id)`, `items()`, `add/addFromTable/remove`), current/previous binding & data view, global
variables, commit/rollback across views.

## B4. Parent/child view relations

`dataviews.jsonc` `parent: {parentDataview, parentColumns[], childColumns[]}` → `EpDataView.setParent`:

- Compiles a parent filter: one criterion `childCol = {$parent.parentCol}` per column pair
  (`EpCriteria.eq(childColumn, '{$parent.' + parentColumn + '}')`);
  `parentColumn` defaults to `childColumn` when only one list is given. The `$parent` variable is
  populated with the parent's current row before each filter run.
- Subscribes to parent `RowChanged/RowDeleted/ViewLoaded/ViewAdded`; when the parent's current row
  actually changed, the child is refiltered, `ViewLoaded` is broadcast, and the child row is set
  to 0 (or −1 if empty).
- Deleting a parent row cascades to children when `allowRecursiveChildDelete` is enabled;
  `commitChildDataviews` commits all children of a view.
- Code-level `setParent` also accepts function links (custom `filter`/`preFilter`/`postFilter`
  callbacks) — not expressible from JSON.

## B5. Binding string parsing (`EpBindingService`)

`parseBinding(binding, isViewOnly=false)`:

- `null`/`undefined`/`''` → `{view:'', column:'', epBinding:''}` — **parseBinding itself is
  null-safe**; the notorious `Cannot read properties of null (reading 'split')` crashes come from
  raw `.split()` calls elsewhere (§B7).
- `[View].[Column]` → both parts extracted; `[View]` alone → view only.
- Otherwise `b.split('.')` → `view = parts[0]`, `column = parts[1]` (may be `undefined` for a bare
  view, or `''` for a trailing dot). Normalized `epBinding` output is always the bracket form
  `[View].[Column]`.
- Helpers: `getBinding(view, column)`, `parseBindingColumn` (column-or-view),
  `getColumnBinding(binding, defaultView)` (bare column ⇒ defaultView), `isViewEqual`,
  `isBindingEqual`, `isEventBindingEqual` — all case-insensitive comparisons.

## B6. Component binding lifecycle (`EpBindingComponent`)

On registration: parse `model.epBinding` → set the initial binding value → subscribe twice to the
global event stream: (a) all non-ValueChanged events for the binding's **view**; (b) debounced
ValueChanged for the exact view+column with `currentRow===true`.

Initial value: pulls the current column value if the view has data; reads column metadata
(`caption` → labelText, `isKeyField`); applies the **keyField rule** (non-key-field controls
disabled while the view is empty, priority `keyField`); then fetches and applies the current
rule-action events (§A4 catch-up). If the view doesn't exist at all, the control is simply
disabled at keyField priority — binding to a *nonexistent view* does not crash, it yields a
permanently disabled control until the view appears (`ViewAdded` re-runs initialization).

Event handling: `RowChanged/RowAdded/RowReplaced/RowDeleted/Rollback` reset the control's value
from the (new) current row and maintain the keyField disable from `rowCount`;
`ViewLoaded/ViewAdded` re-run full initialization; `RowRule` events go to `applyRowRules` (§A5).

## B7. Page-level navigation `epBinding`, the crumb bar, and the split-null crash

Each page's `navigation` block (`pages/<Name>.layout.jsonc`, or `/navigation/*` diffs in a layer)
contributes a row to the **`sysPages`** system view; `EpNavigationService` builds `navDataItems`
from those rows. A page-level `epBinding` may be a **comma-separated list** of bindings
(`View.Col1,View.Col2`).

- The navigation service splits it defensively:
  `item.epBinding ? item.epBinding.split(',') : []`.
- **The crumb bar does NOT guard:** it calls
  - `navDataItems[0].epBinding.split(',')` in its RowChanged/RowReplaced handler,
  - `dataItem.epBinding.split(',')` in `loadDropDownItems`, called from `reLoadCrumb` on init and
    reloads.

  If the landing page's `/navigation/epBinding` is null (e.g. a layer `Replace` diff blanked it),
  every crumb-bar reload throws `TypeError: Cannot read properties of null (reading 'split')` —
  once on record load (via `ngOnInit → reLoadCrumb → loadDropDownItems`), and repeatedly on
  Refresh because every RowChanged/RowReplaced broadcast re-enters the handler. This is the exact
  mechanism behind lessons §3aa; fix = restore the page's `epBinding` (e.g.
  `OrderHed.OrderNum`) and `dataSetId`. The crumb bar also reads `RowMod === 'A'` off the bound
  view's first row to suppress navigation while adding.

## B8. Dataset mapping — how `datasetId` expands `responseParamArgs`

When a `rest-erp` action carries a **dataset-form arg**
(`{dataset: {systemCode, datasetId}, responsePath | paramName/...}`) instead of per-view args:

1. The dataset mapping service collects the datasets from request+response args; `systemCode`
   defaults to `'Erp'`.
2. Alias resolution: if any cached view has `datasetId ≠ serverDataset`, the server name is taken
   from the view — this is why a dataview's free-form `datasetId` (e.g. `CustomerDS`) works as the
   arg key while `serverDataset` (`Customer`) is what goes to the server.
3. The table list for the dataset is fetched once via BO **`Ice.KineticErp/GetDatasetTables`** and
   cached.
4. The single dataset response arg is replaced with **one `IErpDataViewResponseParamArg` per
   dataset table that has a matching dataview in the app** — matching on schema +
   serverTable/tableId + datasetId + serverDataset, case-insensitive. Each expanded arg carries
   `{paramName: tableId, viewName, tableId, responsePath, mergeBehavior, datatableKeys, datasetId,
   serverDatasetId, schema}` — i.e. **every view sharing the `datasetId` gets loaded from the one
   response**. (Confirms reference §6 rule 4.)
5. The same is done for request args (adds `dirtyRow`, `methodParamModifier`); dataset tables
   with **no** matching view are sent as empty arrays in the method params.
6. Datasets defining child attachment tables get attachment dataviews cloned+created on the fly and
   parented via the dataset keys, then announced via `ErpDatasetDvCreatedDataItem`.

The actual response-to-view load (mergeBehavior `Replace|Merge` per
`EpDataViewCopyMergeBehavior`) happens in `processErpPostResponse`, which loads rows into each
named view — that load emits the `ViewLoaded`/`RowChanged` cascade of §B3.

## B9. BAQ-backed views (`schema: "baq"`)

- Declared as `{id, schema:"baq", data:"<BAQ id>", table, name, ...}` — the **BAQ id lives in
  `data`** (or `serverTable` when set): the table name resolves to `serverTable ?? data` for
  baq-schema views vs `serverTable ?? tableId` otherwise.
- All baq-schema views are registered with the ERP BAQ binding service during view init
  (filtered on `schema === 'baq'`).
- Column metadata for baq views is resolved differently, and the App Studio dataview designer has
  a dedicated BAQ schema entry.
- No `serverDataset` needed; `tools:{new:{hidden:true}}` + `confirmChanges:false` are the sane
  defaults for read-only BAQ views (matches reference §6 example).
- **FIELD-PROVEN: a BAQ view needs BOTH `table` AND `tools` or it breaks.**
  No `tools` → the view **disappears on import**. No `table` → it imports but does NOT register in
  App Studio's Data View picker (can't be selected as a grid source; inconsistent at runtime).
  Convention: `table` = same string as `id`. Required set: `{id, schema:"baq", data, table, tools,
  mode}` — see §B12.

## B10. Row lifecycle — RowMod, hasChanges, and the commit paths

- `RowMod` modes: `'A'` added, `'U'` updated, `'D'` deleted, `''` unchanged
  (`EpDataTableRowModes`).
- When a table runs with `rowMod: true`, edits maintain RowMod automatically (add ⇒ 'A', modify ⇒
  'U' unless already 'A'/'D', reverting all column changes ⇒ back to `''`) and `commit` resets to
  `''`.
  **MetaFX creates app views with `rowMod: false`** (§B2), so ERP flows set RowMod explicitly:
  `row-update` events must also set `View.RowMod = "U"` (lessons §5), and server responses carry
  their own RowMod.
- `hasChanges` = `hasModified || hasAdded || hasDeleted` (view level); the event
  token `%dataset.<View>.hasChanges%` surfaces it to event conditions.
- **`data-commit` is a client-side accept-changes, not a save**: the event action commits the
  dataview (`EpDataView.commit()`) → originals overwritten, dirty flags reset, `Commit` binding
  event broadcast. This is why a stray `data-commit` "breaks Save" (lessons §2): it wipes the
  change tracking the real server update (`rest-erp` `ErpPostWithDataViewProcessing`, e.g.
  `MasterUpdate`) relies on.
- The server save path is: `Update` event (top-level) → override checks → `MasterUpdate` →
  `rest-erp` with `erpRequestMethod: ErpPostWithDataViewProcessing` → dataset mapping (§B8) →
  response reloaded into the views (which re-fires rules per §A4).

## B11. `GetNativeKineticApp`-style base structures (how it all connects)

A base app export contains, per §B1/§A1 consumers: `DataViews` (this doc §B1), `Rules`
(§A1), `Events`, `Layout` + `Pages` (each page's `navigation.epBinding`/`dataSetId` feed `sysPages`
— §B7), `ToolBar`, `PatchInfo/PatchTokens` (the `%token%` constants), `Properties`
(component-property diffs) — the exact field list is the `MetaFxView` model:
`Layout, DraftLayout, ToolBar, DataViews, Pages, Orphans, Rules, DraftRules, References, Events,
PatchInfo, PatchTokens, Properties, IsLayerDisabled, ConfiguratorInfo, Wasm, AllowVersions,
ServerErrorCode, ServerErrors`.
Layer sections overlay these collections server-side before the client consumes the merged
result.

---

# CONTRADICTIONS / CORRECTIONS FLAGGED (vs existing reference & lessons)

1. **`SettingStyle.ReadOnly` ≠ readonly at runtime.** The runtime maps it to the
   *Disabled* control action, even though `EpControlActionType.ReadOnly` and a distinct readonly
   state exist. Layers should treat `SettingStyle.ReadOnly` and `SettingStyle.Disabled` as
   equivalent (both grey/disable).
   The existing reference's "Only SettingStyle.Disabled/Invisible/ReadOnly are valid" is also
   **incomplete** — status styles (`Error/Warning/Ok/Highlight`), row statuses (`RowError` etc.),
   `ShowInToolbar`, `showInSecondaryToolBar`, `SetColumnValue`, `SetViewColumnValue`,
   `DisableColumns`, `DisableRow`, `HidePage`, `ChangeImage` are all valid JSON actions (§A2.2).
2. **Dotted `View.$rowCount` is not supported by the parser** (identifier regex has no `$`; only
   the bracket binding regex allows `$`). This *contradicts lessons §3o*, which reports the dotted
   form shipping successfully. Given the parser's silent degrade-to-true failure mode, emit
   **`[View].[$rowCount]`** in generated layers (base apps use this form). Dotted plain columns
   are fine.
3. **`disabled: true` in rules.jsonc removes the rule entirely at load** (not "present but
   inactive") — it is filtered out before instantiation. The old note "Rules need disabled:false to
   be active" (lessons §4) is right but understated: a disabled rule cannot be re-enabled at
   runtime from JSON because it was never instantiated.
4. **Two DisableRow rules on one view DO compose — as any-true OR with intersected exceptions**
   (§A2.3). Lessons §3l's "two rules managing the same row's disable state don't compose" is the
   observable symptom (the row won't unlock until *every* true DisableRow goes false), but the
   engine behavior is deterministic, not undefined. The guidance (drive `TransView.SysReadOnly`
   instead of adding a duplicate DisableRow) stands.
5. **`SettingStyle.sequence` (offered by the App Studio designer UI) has no runtime
   implementation** — it logs `Action not implemented` and is dropped.
6. **`dataMode` is not a dataview property.** The existing reference §6 table lists `dataMode`
   under dataviews; it exists only on combo component models. Also `confirmChanges`
   default is `true` for non-system views but **forced `false` for every view of a Dashboard app**
   (§B1) — the reference lacks the dashboard carve-out.
7. **HidePage runs on false conditions too** (`executeOnFalseCondition = true`) — unlike every
   other action, which executes/broadcasts on both results but only *applies* effects per result.
   Practical effect: pages re-appear automatically; don't pair HidePage with a second "show" rule.
8. **`model.hidden`/`model.disabled` set to a non-default value beats all rules** — the
   model-vs-default check precedes the priority walk. And the keyField no-data disable
   (priority 2) outranks rule actions (priority 4): a rule cannot enable a control on an empty
   view.
9. **parseBinding is null-safe; the crumb bar is not.** The split-null crash of lessons §3aa is
   pinned to the crumb bar's unguarded `…epBinding.split(',')` calls, fed by the page's
   `/navigation/epBinding` via sysPages. The navigation service uses the guarded pattern the
   crumb bar lacks.
10. **Page `epBinding` may be a comma-separated list** of `View.Column` bindings — undocumented in
    the existing reference (relevant when setting `/navigation/epBinding` in layers).

## B12. FIELD-PROVEN dataview setup checklist — required properties per kind

Symptom: a dataview you added silently vanishes on import or doesn't function, while native views
(LinesView, Customer…) persist. Cause is almost always a wrong/incomplete property set.
Before importing ANY hand-built dataview, diff it against a native one of the SAME kind and match
the shape.

**Universal invariant — EVERY dataview, regardless of kind, must have `id`, `table`, `tools`,
`mode`.** If in doubt, give it a `table` — there is no reason a dataview should lack one, and a
missing `table` is what keeps a view out of the Data View picker / makes it behave inconsistently.

### B12.1 BO / server-bound view (`schema:"Erp"` or `"Ice"`)

```jsonc
{ "id":"LinesView", "schema":"Ice",
  "table":"UD103A", "serverTable":"UD103A",
  "datasetId":"UD103", "serverDataset":"UD103",
  "parent":{...}, "staticFilter":"...", "sort":"...",   // only if a child/filtered view
  "tools":{ "new":{"hidden":true}, "delete":{"hidden":true} },
  "mode":"U" }
```

Required: `id, schema, table, serverTable, datasetId, serverDataset, tools, mode`.

### B12.2 BAQ view (`schema:"baq"`)

Bound to a BAQ (`data` = BAQ id). **Both `table` AND `tools` are required.**
- No `tools` → the view **disappears on import**.
- No `table` → the view imports but does NOT register in App Studio's Data View picker (you can't
  select it as a grid source, and it can behave inconsistently at runtime). Give it a `table` name
  (convention: same string as `id`). Verified: adding `table` is exactly what made
  `OrderSearch`/`SearchResult`/`DepositBalance`/`RelatedViews` show up.

```jsonc
{ "id":"SearchResult", "schema":"baq", "data":"MyOrderSearchBAQ",
  "table":"SearchResult",                              // required in practice
  "confirmChanges":false,                                // optional
  "parent":{ "parentDataview":"UD103",
             "parentColumns":["Key1","Key2","Key3"],
             "childColumns":["UD1031_Key1","UD1031_Key2","UD1031_Key3"] },  // child views only
  "tools":{ "new":{"hidden":true}, "delete":{"hidden":true} },   // REQUIRED
  "mode":"U" }
```

Required: `id, schema:"baq", data, table, tools, mode`. BREAKS if bare `{id,schema,data,mode}`
(disappears without `tools`; won't register in the picker without `table`).

### B12.3 Client / in-memory view (no `schema`, has `additionalColumns`)

A layer-defined table (search filters, staging grids, etc.).

```jsonc
{ "id":"SearchFilter", "table":"SearchFilterTbl", "datasetId":"SearchFilterDS",
  "parent":{...},                                        // child views only
  "additionalColumns":[ { "columnName":"Key2", "caption":"Key2", "datatype":"string" }, ... ],
  "tools":{ "new":{"hidden":true}, "delete":{"hidden":true} },
  "mode":"U" }
```

Required: `id, table, datasetId, additionalColumns, tools, mode`.

### B12.4 Column `datatype` must be a KINETIC type token, never a SQL type

- Valid tokens: `string`, `int` (integer), `decimal` (numeric/money/qty), `date`, `boolean`, `guid`.
- **`nvarchar` (or any SQL type) makes the whole dataview disappear on import.** This was the
  original bug — text columns were `nvarchar`; the fix is `string`.
- Use the RIGHT token per column: text→`string`, numbers→`decimal`/`int`, dates→`date`,
  SysRowID/keys→`guid`.

### B12.5 Every kind needs

- `mode:"U"` (overlay) on views that overlay/extend; and
- a `tools` block `{ "new":{"hidden":true}, "delete":{"hidden":true} }` unless you want the
  add/delete toolbar buttons.

### B12.6 Audit habit

Enumerate `dataviews.Diffs`, classify each by kind, and confirm the required set above. A quick
check that catches almost all failures:
1. Every non-BO view has a `tools` block.
2. Every BAQ view has BOTH `table` and `tools` (no `table` = won't appear in the Data View picker).
3. Every client column uses a Kinetic type token (`string`/`int`/`decimal`/`date`/`guid`/`boolean`),
   never `nvarchar`.
