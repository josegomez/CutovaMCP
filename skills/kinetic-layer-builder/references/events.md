# MetaFX Event Engine — Reference

Derived from observed runtime behavior and App Studio output.

## 0. Master list of registered action types

Each action is identified by its `type` string in the layer JSON:

**Flow control:** `condition`, `switch`, `split`, `event-next`, `event-complete`, `event-cancel`, `return`, `return-error`, `exit`
**Data/transaction:** `data-commit`, `data-clear`, `data-rollback`, `global-variable-set`, `session-set`
**DataView:** `dataview-clear`, `dataview-condition`, `dataview-copy`, `dataview-filter-set`, `dataview-set-current`, `event-view-disable`, `event-view-enable`, `event-column-disable`, `event-column-enable`, `event-row-disable`, `event-row-enable`
**Row:** `row-add`, `row-copy`, `row-current-set`, `row-delete`, `row-find`, `row-update`
**Grid/control:** `grid-refresh`, `grid-schema-invalidate`, `grid-sort-get`, `grid-sort-set`, `combo-refill`, `control-focus-set`, `property-set`, `search-value-set`, `title-set`
**Tree:** `select-tree-node`, `set-tree-node-state`, `refresh-tree`, `datatree-bindings-set`
**REST/server:** `rest-erp`, `rest`, `erp-function`, `erp-baq` (ERP-only), `function`, `calculation`, `execute-csharp`, `process-import-service`, `erp-message-handler`
**ERP-only:** `search-show`, `file-transfer-erp`, `download-attachment-erp`, `crystal-custom-report`, `serial-read`, `usb-read`
**Dialog/UI:** `dialog-show`, `dialog-show-system`, `dialog-result-set`, `slider-open`, `slider-close`, `dynamic-panel-open`, `credit-card-entry`, `expression-editor`, `kbmax-configurator-open`, `pdf-viewer-action`, `configurator-property-set`
**Navigation/app:** `app-open`, `app-close`, `page-navigate-to`, `url-open`, `apps-communicator-broadcast`, `apps-communicator-publish`
**Misc:** `console-write`, `dashboard-timer-set`, `dashboard-timer-clear`

Notes:
- `value-set` and `image-set` appear in the `MetaFxEventType` union but have **no registered action class**. `value-set` is only interpreted inside the search flow (actions of type `value-set` inside a search-show's event are consumed by the search handler, not the action registry). `image-set` has no implementation found — treat as obsolete.
- `external-component` is marked Obsolete in the union.

(Sections 1-4 filled in below.)


## 1. Action catalog

The complete registered action catalog follows. Each entry gives the type string, param interface, continuation branches, and a JSON example. Actions are grouped roughly as flow-control, data/dataview/row, grid/control, tree, REST/server, dialog/UI, navigation, and misc.

### `condition`
Evaluates `param.expression` as a JavaScript expression: the string is first run through `eventParamService.parseValue` with `getParseOptions(expression)` plus `options.sanitizeJSExpression = true` (token substitution such as `{DataView.Field}` applies, with JS-safe quoting), then evaluated by `MetaFxDynamicFunctionService.evaluate`, which builds `Function('context', 'trans', 'user', 'return <expr>')` — so `context` (app-communicator context data), `trans` (MetaFxTransactionService) and `user` (current user) are available inside the expression. Truthy result routes to `param.onSuccess`, falsy to `param.onFailure`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `expression` | string | yes | — | Boolean JS expression, e.g. `"{OrderDtl.PartNum}" === "TSHIRT"`. Parsed via `parseValue` with `sanitizeJSExpression: true`. |
| `shapeLabel` | string | no | — | (designer-only) label shown on the diagram shape; never read in `execute()`. |
| `onSuccess` | action[] | no | — | The **True** branch (designer caption "True", connector name `onSuccess`) — note it lives INSIDE `param`, not on the action object. |
| `onFailure` | action[] | no | — | The **False** branch (designer caption "False", connector name `onFailure`) — inside `param`. |

Continuations: does NOT read `metaFxEventAction.onSuccess`/`onError` (the designer explicitly hides action-level `onSuccess`/`onError`). Branching is `param.onSuccess` (true) / `param.onFailure` (false). Response: `{ successOrError: <chosen branch array>, lastResultSuccessValue: <raw eval result> }`.
```json
{
  "type": "condition",
  "param": {
    "expression": "\"{OrderHed.OpenOrder}\" === \"true\"",
    "onSuccess": [ { "type": "console-write", "value": "order is open" } ],
    "onFailure": [ { "type": "console-write", "value": "order is closed" } ]
  }
}
```

### `switch`
The value to switch on is the ACTION-level `value` property (not in `param`), run through `eventParamService.parseValue` (token substitution applies). It is compared against each `param.cases[].value` with three equality attempts: strict `===` string match, numeric match (`Number(case.value) === value` when case value is numeric), and boolean-string match (`'true'`/`'false'` case-insensitive vs `value.toString()`). The matched case's `actions` array is executed inline via `eventExecuteData.executeNextActions(...)`; if no case matches, the case with `default: true` runs; if none, returns `{ success: true }`.

| property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (on ACTION, not param) | string | yes (designer required) | — | Expression/binding whose parsed value is matched against the cases. |
| `param.cases` | array | yes (designer required) | `[]` | Array of case objects. |
| `param.cases[].value` | string \| number | no | — | Match value; ignored (hidden) when `default` is true. Designer blocks duplicate values. |
| `param.cases[].default` | boolean | no | `false` | Marks the default case; only one allowed (designer enforces). |
| `param.cases[].actions` | action[] | no | — | Actions executed when this case matches (designer connector name `onCaseAction`). |

Continuations: does not read `onSuccess`/`onError`/`onEmpty` (designer hides them). The chosen case's `actions` are executed directly inside `execute()` and its response is returned; no-match-no-default returns `{ success: true }`.
```json
{
  "type": "switch",
  "value": "{TransView.Mode}",
  "param": {
    "cases": [
      { "value": "Add", "actions": [ { "type": "console-write", "value": "adding" } ] },
      { "value": "Update", "actions": [ { "type": "console-write", "value": "updating" } ] },
      { "default": true, "actions": [ { "type": "console-write", "value": "other" } ] }
    ]
  }
}
```

### `split`
Splits a delimited string into columns of a dataview. Whole `param` goes through `eventParamService.parseObject`, then `param.value` additionally through `parseValue`. If the value contains the `columnDelimiter`, it is treated as name`value pairs per row (split rows by `rowDelimiter`, each row split by `columnDelimiter` into column name + value); otherwise each `rowDelimiter`-separated item becomes `<columnPrefix>01`, `<columnPrefix>02`, ... Each result is written via `eventTransactionService.set('<dataView>.<column>', value, type)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `value` | string | yes | — | Delimited string; parsed via `parseValue` (tokens apply). |
| `rowDelimiter` | string | no | `~` | Delimiter between items/rows. |
| `columnDelimiter` | string | no | `` ` `` | Delimiter between column name and value (its presence toggles the name/value mode). |
| `dataView` | string | yes (used in binding) | — | Target dataview for the generated columns. |
| `columnPrefix` | string | no | `SplitOutput` | Prefix for generated column names in single-row mode. |
| `dataTypes` | `{index?, column?, type?}`[] | no | — | Overrides type (`'bool' \| 'number' \| 'string'`) per `column` (name/value mode) or per 1-based `index` (single-row mode). Default type `string`. |

Continuations: none read; always returns `{ success: true }`.
```json
{
  "type": "split",
  "param": {
    "value": "{CallContextBpmData.Character01}",
    "rowDelimiter": "~",
    "columnDelimiter": "`",
    "dataView": "SplitView",
    "columnPrefix": "SplitOutput",
    "dataTypes": [ { "index": 2, "type": "number", "column": "Qty" } ]
  }
}
```

### `event-next`
Invokes another named event and WAITS for it. The target event id is the ACTION-level `value` (parsed via `parseValue`). The ACTION-level `param` object is run through `parseObject` and stored into the `SysVariable` dataview keyed by the child's unique event id via `eventActionHandler.setSysVariable(...)` — that is how parameters flow to the called event (readable there as `{sysVariable.X}` / event params). A legacy path exists when the action has a `condition` string property (logged as invalid, evaluated via `MetaFxDynamicFunctionService`, then the event runs without param passing). Extra flags `IsSysRefresh`/`IsSysDelete` are auto-merged into param when triggered from `SysRefresh`/`SysDelete`; `value === 'Refresh'` also triggers a CloseGridEditors activity. After the child event finishes, `sysVariable` is cleared (unless exit or skipClear).

| property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (on ACTION) | string | yes | `''` | Id of the event to execute. `parseValue` applies. |
| `param` (on ACTION) | object | no | — | JSON object passed to the target event via SysVariable. `parseObject` applies (tokens substituted in values). |
| `condition` (on ACTION) | string | no | — | Legacy/deprecated path; when present, evaluated as JS and event runs via simple path. |

Continuations: reads `args.metaFxEventAction.onSuccess` and, when the child executed a `return-error`, `args.metaFxEventAction.onError`. Response: `{ successOrError, lastResultSuccessValue: <last child response success or false>, shouldCallNextAction: !(successOrError === undefined && returnErrorExecuted) }` — i.e. an unhandled return-error stops the chain.
```json
{
  "type": "event-next",
  "value": "MyCustomEvent",
  "param": { "PartNum": "{OrderDtl.PartNum}", "Mode": "validate" },
  "onSuccess": [ { "type": "console-write", "value": "child event ok" } ],
  "onError": [ { "type": "console-write", "value": "child returned error" } ]
}
```

### `event-complete`
Unlike `event-next` (synchronous call-and-wait), this DEFERS an event to run after the current trigger's action chain completes: `param` is parsed via `parseObject`, `param.nextEvent` via `parseValue`; if `param.param` is present it is parsed and stored into SysVariable for the next event (same `setSysVariable` mechanism as event-next), then `eventResultService.deferEventCompleteActions(nextActionId, completeParam)` registers the deferred completion against the current trigger.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `nextEvent` | string | yes | — | Event id to trigger on completion. `parseValue` applies. |
| `param` | object \| object[] | no | — | Parameters for `nextEvent`, delivered via SysVariable (`parseObject` applies). |

Continuations: reads `args.metaFxEventAction.onSuccess` and always returns it: `{ success: true, successOrError: <action.onSuccess>, value: <nextEvent> }`.
```json
{
  "type": "event-complete",
  "param": { "nextEvent": "RefreshGrid", "param": { "RowNum": "{GridView.RowNum}" } },
  "onSuccess": []
}
```

### `event-cancel`
Sets `eventResultService.cancelEvent = true`, signaling the framework to cancel the in-flight event/trigger processing. Reads no `param` at all.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| (none) | — | — | — | `execute()` reads nothing from the action. |

Continuations: none read; returns `{ success: true }`.
```json
{ "type": "event-cancel" }
```

### `return`
Returns a value from a called (child) event back to its caller. The ACTION-level `param` (a free-form JSON object; `IReturnParam` is just `{ param?: object }` at the model level but execute() treats the whole `action.param` as the return payload) is parsed via `parseObject`, written to SysVariable for the current event, registered via `eventResultService.setReturnValue(uniqueEventId, parentUniqueEventId, false /* not error */, action.param)`, and MERGED into the parent's entry in `MetaFxEventParamService.eventParams` — so the CALLING event (the one that ran `event-next`) sees the returned properties as its own event params/tokens after the call returns.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param` (on ACTION, free-form object) | object | no | — | Whole object is the return payload; `parseObject` applies (tokens in values substituted). Keys become params on the parent event. |

Continuations: none read; returns `{ success: true }`.
```json
{
  "type": "return",
  "param": { "Result": "{TransView.CalcTotal}", "IsValid": "true" }
}
```

### `return-error`
Identical mechanics to `return` (param deep-cloned then `parseObject`, written to SysVariable, merged into parent's eventParams) except `setReturnValue(..., true, param)` marks the return as an ERROR. The calling `event-next` detects this via `eventResultService.isReturnErrorExecuted(...)` and routes to its `onError` branch (or halts the chain if the caller has no `onError`, because `shouldCallNextAction` becomes false).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param` (on ACTION, free-form object) | object | no | — | Error payload returned to the caller; `parseObject` applies. |

Continuations: none read on this action; returns `{ success: true }`. The branch effect happens in the CALLER's `event-next` (`onError`).
```json
{
  "type": "return-error",
  "param": { "ErrorMessage": "Part {OrderDtl.PartNum} is inactive" }
}
```

### `exit`
Sets `eventResultService.exitEvent = true` to abort the entire event chain (a parent `event-next` seeing `exitEvent` restores the parent's SysVariable param instead of clearing). Reads no param.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| (none) | — | — | — | `execute()` reads nothing from the action. |

Continuations: none read; returns `{ success: true, successOrError: null, shouldCallNextAction: false }` — explicitly stops further sibling actions.
```json
{ "type": "exit" }
```

### `function`
Executes a built-in CLIENT-SIDE custom function via `MetaFxCustomFunctionService.exec()`. NOTE: the configuration lives on the ACTION-level `option` property, NOT `param`. Only three function names are implemented: `join` (concatenates dataview rows/columns into a delimited string), `slice` (splits a delimited string from an epBinding by `args[2]`, takes index `args[1]`, writes to `output`), and `convertDelimitedListToSQL`. `option.output` is run through `parseValue`; other args are used as-is by the service (which itself resolves bindings via the transaction service).

| property (on `action.option`) | type | required? | default | notes |
|---|---|---|---|---|
| `name` | string | yes | — | One of `join`, `slice`, `convertDelimitedListToSQL`; anything else is a no-op. |
| `args` | string[] | yes | `[]` | Positional arguments; meaning depends on function (e.g. slice: `[epBinding, index, delimiter]`). |
| `output` | string | yes | — | epBinding (`View.Column`) where the result is written. `parseValue` applies. |
| `dataType` | string | no | — | Data type used when setting the output value. |

Continuations: none read; always returns `{ success: true }`.
```json
{
  "type": "function",
  "option": {
    "name": "slice",
    "args": ["TransView.DelimitedIds", "0", "~"],
    "output": "TransView.FirstId",
    "dataType": "string"
  }
}
```

### `calculation`
Sequentially applies arithmetic operations to a starting value and writes the result to a binding. `param` is parsed via `parseObject`; `initialValue`, each `operand` and each `operator` additionally go through `parseValue` (so all can be tokens like `{View.Col}`). Supported operators: `+`, `*`, `-`, `/` (applied in array order, no precedence). Result written via `eventTransactionService.set(param.epBinding, result)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `epBinding` | string | yes | — | `View.Column` target for the result. |
| `initialValue` | string | yes | — | Starting value; `parseValue` applies, coerced to number. |
| `operations` | `{operator, operand}`[] | no | — | Each operand coerced with unary `+`; unsupported operator produces `{ success: false }` (inside forEach — note the return is effectively swallowed). |

Continuations: none read; returns `{ success: true }`.
```json
{
  "type": "calculation",
  "param": {
    "epBinding": "TransView.Total",
    "initialValue": "{OrderDtl.UnitPrice}",
    "operations": [
      { "operator": "*", "operand": "{OrderDtl.OrderQty}" },
      { "operator": "-", "operand": "{OrderDtl.Discount}" }
    ]
  }
}
```

### `execute-csharp`
CONFIGURATOR-ONLY action (hidden from the toolbox unless the view id starts with the configurator prefix — `MetaFxExecuteCSharpService.hide()`). Loads the C# WASM runtime (`WasmService.loadWasm()`) and executes a compiled configurator method. `param` is deep-cloned after `parseObject`. If `param.type` is empty, the generic path runs `wasmService.executeMethod(param.method, param.inputs)`; the JSON result array is mapped through `param.outputs` (match `result.key` to `outputs[].name`, write to `outputs[].value` binding; a key without a `.` is treated as a dataview: cleared then `addRows`). If `param.type` is set (configurator expression type codes: `dynamicList`, `pageReadOnly`, `readOnly`, `dynamicListUserDefined`, `validate`, `changed`, `leave`, `load`, `loaded`, `configuratorLoaded`, `configuratorComplete`), a configurator transaction is initialized and the method executes as `configurator_<method>` with type-specific result handling (set combo data / read-only flags / outputs).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `method` | string | yes | — | C# method name (prefixed `configurator_` in typed/most paths). |
| `inputs` | `{name, type?, value?, columns?}`[] | no | — | Inputs; `type` one of `'epBinding' \| 'dataview' \| 'number' \| 'string' \| 'boolean'`; `columns` lists dataview columns to send. |
| `outputs` | `{name, value?}`[] | no | — | Maps result keys (`name`) to target bindings (`value`). For `dynamicList` type, every output binding gets the whole response. |
| `type` | string | no | — | Configurator expression type code; empty means plain method execution. |
| `control` | string | no | — | Target control id for `readOnly`/`pageReadOnly`/`dynamicListUserDefined` types. |
| `returnType` | string | no | — | (declared in `IExecuteCsharpParam` but never read in `execute()` — designer-only). |

Continuations: none read; all paths resolve to `{ success: true }`.
```json
{
  "type": "execute-csharp",
  "param": {
    "method": "UD_CalcPrice",
    "inputs": [ { "name": "qty", "type": "epBinding", "value": "Inputs.QtyInput" } ],
    "outputs": [ { "name": "price", "value": "Inputs.PriceInput" } ]
  }
}
```

### `global-variable-set`
Sets a column in the special `sysGlobalVariable` dataview. Reads ACTION-level `variable` and `value` (no `param` object); both go through `eventParamService.parseValue` (tokens apply). Executes `eventTransactionService.set('sysGlobalVariable.<variable>', <value>)`; skipped entirely when `variable` is falsy.

| property | type | required? | default | notes |
|---|---|---|---|---|
| `variable` (on ACTION) | string | yes (no-op if missing) | — | Column name in `sysGlobalVariable`. `parseValue` applies. |
| `value` (on ACTION) | any | no | — | Value to store. `parseValue` applies. |

Continuations: none read; returns `{ success: true }`.
```json
{
  "type": "global-variable-set",
  "variable": "LastOrderNum",
  "value": "{OrderHed.OrderNum}"
}
```

### `session-set`
Sets a session variable via `MetaFxSessionSetEventService.executeRequest`. `param` is parsed via `parseObject`. The service switches on `param.variable.toLowerCase()` and ONLY supports `employeeid` (anything else throws `"<variable> not supported by session set."`). Empty `value` = MES logout path (SetEmployeeIDSession activity); non-empty runs MES menu security, then either sets the employee id (→ `onSuccess`) or prompts a user change (KhpLoginPrompt; success → `onSuccess`, failure → `onError`).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `variable` | string | yes | — | Only `EmployeeId` (case-insensitive) is supported. |
| `value` | string | yes | — | Employee id; empty string means clear/logout. |

Continuations: reads `metaFxEventAction.onSuccess` and `metaFxEventAction.onError` (inside the service). Missing/null `param` returns `{ successOrError: action.onError }`. Responses set only `successOrError`.
```json
{
  "type": "session-set",
  "param": { "variable": "EmployeeId", "value": "{MESView.EmpID}" },
  "onSuccess": [ { "type": "event-next", "value": "LoadMenu" } ],
  "onError": [ { "type": "console-write", "value": "login failed" } ]
}
```

### `data-commit`
Commits pending (uncommitted) dataview transaction changes so they become the dataview's real values: `param` parsed via `parseObject`; with `param.dataview` set, commits only that dataview (`eventTransactionService.commit(param.dataview)`); with no param or no dataview, commits ALL pending changes (`commit()`).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `dataview` | string | no | (all views) | Name of the single dataview to commit. `parseObject` token substitution applies. |

Continuations: none read; returns `{ success: true }`.
```json
{ "type": "data-commit", "param": { "dataview": "TransView" } }
```

### `data-clear`
Clears data by scope. `param` parsed via `parseObject`, `param.value` additionally via `parseValue`. If `param` is missing entirely, calls `eventTransactionService.clearAll()`. Otherwise `type` must be exactly `dataview`, `table`, or `dataset` (string enum values from `MetaFxDataClearEventStrings`) or it THROWS `invalid type : <type>`; then calls `clearView`, `clearTable`, or `clearDataset` with `param.value`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `type` | `'dataview' \| 'table' \| 'dataset'` | yes (when param present) | — | Literal strings; anything else throws. |
| `value` | string | yes (when param present) | — | Id of the dataview/table/dataset to clear. `parseValue` applies. |

Continuations: none read; returns `{ success: true }`.
```json
{ "type": "data-clear", "param": { "type": "dataview", "value": "TransView" } }
```

### `data-rollback`
Discards uncommitted transaction changes. `param` is read RAW (no `parseObject`), but the individual `dataview`/`dataset` values go through `parseValue`. `dataview` wins if both set: `eventTransactionService.rollback(<name>, 'dataview')`; else `rollback(<name>, 'dataset')`. If neither is set, nothing happens.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `dataview` | string | no | — | Dataview to roll back. `parseValue` applies. Takes precedence over `dataset`. |
| `dataset` | string | no | — | Dataset to roll back. `parseValue` applies. |

Continuations: none read; returns `{ success: true }`.
```json
{ "type": "data-rollback", "param": { "dataview": "TransView" } }
```

### `console-write`
Logs a message to the MetaFX event logger (dev console/event log). Quirk: it runs the ENTIRE action object through `eventParamService.parseObject`, then reads the ACTION-level `value` (not `param`), re-parses it via `parseValue`, and calls `eventLoggerService.log(value)`. Nothing logged if `value` is falsy.

| property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (on ACTION) | string | yes (no-op if missing) | — | Message; token substitution applies (e.g. `"PartNum is {OrderDtl.PartNum}"`). |

Continuations: none read; returns `{ success: true }`.
```json
{ "type": "console-write", "value": "current customer: {OrderHed.CustNum}" }
```

### `dashboard-timer-set`
Starts a repeating `setInterval` that executes the named event every `param.interval` milliseconds via `eventActionHandler.executeEvent(args, param.event)`. `param` is read RAW (no parseObject); `param.event` is run through `parseValue` on EACH tick; `param.interval` is used as-is (no token substitution). The interval handle is stored in the STATIC `MetaFxDashboardTimerSetEvent.timerHandler` — there is only one global slot, so setting a second timer orphans the first handle.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `interval` | number | yes | — | Milliseconds between ticks; raw number, no parsing. |
| `event` | string | yes | — | Event id to execute per tick; `parseValue` applied each tick. |

Continuations: none read; returns `{ success: true }` immediately (timer keeps running).
```json
{ "type": "dashboard-timer-set", "param": { "interval": 30000, "event": "RefreshDashboardData" } }
```

### `dashboard-timer-clear`
Clears the single global timer created by `dashboard-timer-set` (`clearInterval(MetaFxDashboardTimerSetEvent.timerHandler)`) and resets the static handle to 0. Reads no param.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| (none) | — | — | — | `execute()` reads nothing from the action. |

Continuations: reads `metaFxEventAction.onSuccess`; returns `{ successOrError: action.onSuccess }` (note: no `success` field set).
```json
{ "type": "dashboard-timer-clear", "onSuccess": [ { "type": "console-write", "value": "timer stopped" } ] }
```
### General notes (apply to all actions below)

- "parseValue" = `eventParamService.parseValue()` — substitutes tokens such as `{View.Column}`, `{Constant.X}` etc. "parseObject" = `eventParamService.parseObject()` — runs parseValue over the string members of the object. A column marked "no parse" is passed to the service raw.
- Most actions return `{ success: true }` without reading any continuation array themselves; the shared event handler then follows the action's `onSuccess` / `onError` arrays. Actions that explicitly read `metaFxEventAction.onSuccess`/`onError` (or param-level connectors) are called out per action.
- Shared designer props on every action (`MetaFxEventActionProperties`): `id`, `onSuccess`, `onError`, `onEmpty`, `comments` (all designer-declared; `onEmpty`/`comments` are designer-only for the actions in this file).

---

### `dataview-clear`
Removes (clears) a data view: parses the top-level `value` as the view name and calls `eventTransactionService.clearView(value)`. Logs a deprecation-style warning on every execution.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (TOP-LEVEL on action, not inside `param`) | string | yes | — | data view id to clear; passes through parseValue |

Continuations: execute() reads none; returns `{success:true}` (framework follows `onSuccess`).
```json
{ "type": "dataview-clear", "value": "MyTempView", "onSuccess": [] }
```

---

### `dataview-condition`
Filters rows of a source data view with a row-match expression via `eventTransactionService.addSnapshotFrom(result, dataview, expression)` — the matching rows become a snapshot data view named `param.result` — then branches on match count, or iterates the matches running `param.iterativeEvent` once per row (setting `result` view's current row to each index first). **Difference vs plain `condition`**: `condition` evaluates one JS expression with `MetaFxDynamicFunctionService.evaluate()` and branches `param.onSuccess`/`param.onFailure`; `dataview-condition` is row-set matching against a data view with 3-way count branching and an optional per-row loop.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.dataview` | string | yes | — | source data view; parseValue |
| `param.result` | string | yes | — | target snapshot view holding the matches; parseValue |
| `param.expression` | string | yes | — | row match expression; parseValue |
| `param.iterativeEvent` | string | no | — | event id to execute once per matched row (loop mode); no parse |
| `param.onNoMatch` / `param.onSingleMatch` / `param.onMultipleMatch` | action[] | no | — | continuation arrays INSIDE param (non-loop mode) |

Continuations: non-loop — `response.successOrError` = `param.onNoMatch` (0 rows) / `param.onSingleMatch` (1) / `param.onMultipleMatch` (>1), with `lastResultSuccessValue:true`. Loop mode — `successOrError = metaFxEventAction.onSuccess`, `success` false if any iteration failed, `shouldCallNextAction:true`. Designer also declares `onOk/onCancel/onYes/onNo/onRetry/onNone/onAbort/onIgnore` connectors (designer-only; never read by execute()).
```json
{
  "type": "dataview-condition",
  "param": {
    "dataview": "OrderDtl",
    "result": "OpenLines",
    "expression": "OpenLine = true",
    "onNoMatch": [], "onSingleMatch": [], "onMultipleMatch": []
  }
}
```

---

### `dataview-copy`
Copies all data from one data view to another via `eventTransactionService.copyData(fromDataView, toDataView, setCurrentRow, mergeBehavior)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.fromDataView` | string | yes | — | parseObject (parsed) |
| `param.toDataView` | string | yes | — | parseObject (parsed) |
| `param.setCurrentRow` | boolean | no | `true` | only overridden when `!== undefined` |
| `param.mergeBehavior` | string (`EpDataViewCopyMergeBehavior`) | no | — | extra parseValue applied |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "dataview-copy", "param": { "fromDataView": "OrderHed", "toDataView": "OrderHedCopy", "setCurrentRow": true }, "onSuccess": [] }
```

---

### `dataview-filter-set`
Sets a persistent row filter on a data view: `eventTransactionService.dataView(param.dataview).filter.set(parsedFilter)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.dataview` | string | yes | — | parseObject (parsed) |
| `param.filter` | string | yes | — | filter expression string, e.g. `Company = '{CallContextClientData.CurrentCompany}'`; parseObject then an extra parseValue |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "dataview-filter-set", "param": { "dataview": "PartView", "filter": "ClassID = '{TransView.ClassID}'" } }
```

---

### `dataview-set-current`
Makes a view the app's *current* binding context: parses top-level `value` (a binding string, parsed with `EpBindingService.parseBinding`) and, if the current binding's view differs, calls `MetaFxTransactionService.setCurrentBinding(epb, null, null, true)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (TOP-LEVEL) | string | yes | — | binding string `ViewName.ColumnName` (view part is what matters); parseValue |

Continuations: sets `successOrError: metaFxEventAction.onSuccess` in both branches.
```json
{ "type": "dataview-set-current", "value": "OrderDtl.OrderLine", "onSuccess": [] }
```

---

### `event-view-disable` / `event-view-enable`
Globally suppresses (or re-enables) **view-change events** for the whole transaction. **execute() reads NO parameters at all** — not `param`, not a view name, nothing. It simply calls `disableOnViewChange(true)` (or `false` for enable) on the transaction-event service, which sets `disableViewChangeEvents` on `MetaFxTransactionService` — the flag applies to all views. Nothing visual is disabled; only the firing of viewChanged events is suppressed. The designer property model (`MetaFxDataViewEventProperties`) declares a `dataview` property, but it is **designer-only / ignored** for these two actions.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| — | — | — | — | no params read; any `dataview` in the JSON is ignored |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "event-view-disable" }
```

---

### `event-column-disable` / `event-column-enable`
Suppresses (or re-enables) **columnChanged/columnChanging event firing** for one data TABLE, or for all tables when no table is given. **VERIFIED param shape: execute() treats the whole action object as `IColumnChangeParam` and reads `dataTable` as a TOP-LEVEL property of the action object — it does NOT read `param.dataTable`, `param.dataView`, or `param.columns`.** When `dataTable` is present it is run through `parseValue` and column-change events are disabled for that table only; when it is absent, column-change events are disabled for ALL data views.
`IColumnChangeParam` also *declares* `param?: { columns: string[] }`, but execute() never reads it — a per-column list is dead/designer-cruft here. **Where the state is stored / what is disabled**: `disableOnColumnChange(disable, table?)` iterates `metaFxTransactionService.dataViews()` and for each view whose `d.table.id` matches (or all when no table) calls `d.table.disableColumnChangeEvents(disable)` — the flag lives on each `EpDataTable`. Nothing is visually disabled (no controls, no grid columns become read-only); it only stops columnChanged events (and thus columnChanged-triggered MetaFX events / server notifications) from firing. Note the identifier is the **table id** (`edv.table.id`), which several views may share — the designer combo (`MetaFxDataTableEventProperties.getDataTables()`) is populated with table ids, not view ids.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `dataTable` (TOP-LEVEL on action) | string | no | (omit = ALL tables) | table id; passes through parseValue |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "event-column-disable", "dataTable": "OrderHed" }
{ "type": "event-column-enable", "dataTable": "OrderHed" }
```

---

### `event-row-disable` / `event-row-enable`
Suppresses (or re-enables) **rowChanged event firing** for one data view, or all views when none given. **VERIFIED: `dataview` is a TOP-LEVEL property of the action (whole action passed to parseObject), not inside `param`.** When `dataview` is present, row-change events are disabled for that view only; otherwise for all views.
Storage/effect: `disableOnRowChange(disable, dataView?)` iterates all data views and calls `d.disableRowChangeEvents(disable)` on each matching `EpDataView` (flag on the view object; view id match this time, not table id). On **re-enable**, it additionally fires `metaFxAppPublishEventService.onAfterRowChanged(d.id)` once. Nothing visual is disabled.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `dataview` (TOP-LEVEL on action) | string | no | (omit = ALL views) | data view id; parsed by parseObject on the action |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "event-row-disable", "dataview": "OrderDtl" }
{ "type": "event-row-enable", "dataview": "OrderDtl" }
```

---

### `row-add`
Adds a new row to a data view via `eventTransactionService.addRow(param.dataview, row)`, where `row` is built from the optional `values` map (each value individually parseValue'd).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.dataview` | string | yes | — | parseValue |
| `param.values` | object (columnName → value) | no | `{}` | each value parseValue'd |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "row-add", "param": { "dataview": "UD01View", "values": { "Key1": "{OrderHed.OrderNum}", "Character01": "New" } } }
```

---

### `row-copy`
Copies the current row from one view to another via `eventTransactionService.copyRow(fromDataView, toDataView, setCurrentRow, loadData)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.fromDataView` | string | yes | — | parseValue |
| `param.toDataView` | string | yes | — | parseValue |
| `param["row-current-set"]` | boolean | no | `true` | NOTE the literal hyphenated key; parseValue'd, then used as setCurrentRow flag |
| `param.loadData` | any | no | — | passed raw to copyRow |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "row-copy", "param": { "fromDataView": "OrderDtl", "toDataView": "TempLine", "row-current-set": true } }
```

---

### `row-current-set`
Sets the current row pointer of a data view: `position:'last'` → `lastRowIndex`, `position:'first'` → 0, otherwise numeric `row` (extra parseValue + `+` coercion).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.dataview` | string | yes | — | parseObject |
| `param.row` | number/string | no | — | used when no `position`; parseValue then coerced to number |
| `param.position` | `'first'` \| `'last'` | no | — | wins over `row` |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "row-current-set", "param": { "dataview": "OrderDtl", "position": "last" } }
```

---

### `row-delete`
Deletes the CURRENT row of the named view: `eventTransactionService.deleteCurrentRow(viewId)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `dataview` (TOP-LEVEL on action) | string | yes | — | parseValue; no `param` object |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "row-delete", "dataview": "TempRows" }
```

---

### `row-find`
Searches a data view with a match expression and writes the result into a binding via `eventTransactionService.setAsync(epBinding, value)`. Modes: `Exists` (default) → boolean `rows.length > 0`; `Count` → number of matches; `RowIndex` → `eventTransactionService.rowIndex(dataview, expression)`. Invalid mode just logs an error.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.dataview` | string | yes | — | parseValue |
| `param.expression` | string | yes | — | match/criteria expression, e.g. `PartNum = '{TransView.PartNum}'`; parseValue |
| `param.epBinding` | string | yes | — | `View.Column` that receives the result; parseValue |
| `param.mode` | `'Exists'` \| `'Count'` \| `'RowIndex'` | no | `'Exists'` | |

Continuations: **there are NO `onFound`/`onNotFound` branches** — execute() reads no continuation arrays and returns `{success:true}` after the setAsync; branch afterwards with a `condition` action on the epBinding value.
```json
{
  "type": "row-find",
  "param": { "dataview": "OrderDtl", "expression": "PartNum = '{TransView.PartNum}'", "epBinding": "TransView.FoundRowIndex", "mode": "RowIndex" },
  "onSuccess": []
}
```

---

### `row-update`
Sets column values on the CURRENT row of the view(s) named inside each `epBinding`. `param` is an **array** of row objects, each with a `columns` array; every column is applied sequentially (rxjs `concat`) via `eventTransactionService.setAsync(epBinding, val, dataType)`.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param` | `IUpdateRow[]` = `[{ columns: [...] }]` | yes | — | **No `viewName` property exists** — the target view is the view part of each column's `epBinding` |
| `param[].columns[].epBinding` | string | yes | — | `View.Column`; parseValue |
| `param[].columns[].value` | any | see notes | — | used only when `expression` absent; parseValue (token substitution) |
| `param[].columns[].expression` | string | no | — | **expression WINS over value** when present. Parsed with `sanitizeJSExpression:true`, then **every backslash is doubled** (`parsedExpression.replace(/\\/g, '\\\\')`) before `MetaFxDynamicFunctionService.evaluate()` — so backslashes in layer JSON end up quadruple-escaped by the time you write them |
| `param[].columns[].dataType` | string | no | — | passed to setAsync (e.g. `'string'`, `'number'`, `'boolean'`) |
| `param[].columns[].options` | IParseOptions | no | — | declared on interface; execute uses `getParseOptions(expression)` internally, not this field |

Continuations: response is `{ successOrError: metaFxEventAction.onSuccess, shouldCallNextAction: result }`.
```json
{
  "type": "row-update",
  "param": [ { "columns": [
    { "epBinding": "OrderHed.OrderComment_c", "value": "{TransView.NewComment}", "dataType": "string" },
    { "epBinding": "TransView.Total", "expression": "{OrderDtl.OrderQty} * {OrderDtl.UnitPrice}", "dataType": "number" }
  ] } ],
  "onSuccess": []
}
```

---

### `grid-refresh`
Finds all `metafx-panel-card-grid` components, filters them by `option`/`target`, sets `gridModel.refreshOnChange = true` on each provider-backed grid and performs the `GridRefreshEvent` generic activity with `{type:'Control', target: gridModel.id}`; the matching erp-grid then re-runs its data provider (`refreshData()`) and fires `GridRefreshEventCompleted`. **If `param` is missing entirely, nothing is refreshed** (the loop is inside `if (param)`).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.option` | `'All'` \| `'Includes'` \| `'Excludes'` | yes (designer `required:true`) | behaves as All when neither Includes/Excludes | |
| `param.target` | string[] (grid model ids, i.e. `gridModel.id`) | when option ≠ All | — | matched with `indexOf`; parseObject applied to param |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "grid-refresh", "param": { "option": "Includes", "target": ["MyGrid"] } }
```

---

### `grid-schema-invalidate`
Performs the `GridInvalidateEvent` generic activity; the grid whose `model.epBinding` (type `'epBinding'`) or `model.id`/panel-card id (type `'Control'`) matches `target` calls `invalidateGrid()` (rebuilds columns/schema).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.type` | `'Control'` \| `'epBinding'` | yes | — | parseObject |
| `param.target` | string | yes | — | grid id or grid epBinding; extra parseValue |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "grid-schema-invalidate", "param": { "type": "Control", "target": "MyGrid" } }
```

---

### `grid-sort-get`
Broadcasts `ErpGridSortEvents.GridSortGet`; the grid whose `model.epBinding === param.epBinding` writes its current sort field into `sortColumnBinding` and direction into `sortDirectionBinding` (empty strings when unsorted).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.epBinding` | string | yes | — | the grid's epBinding; parseObject |
| `param.sortColumnBinding` | string | yes | — | `View.Column` receiving the sort field |
| `param.sortDirectionBinding` | string | yes | — | `View.Column` receiving `'asc'`/`'desc'` |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "grid-sort-get", "param": { "epBinding": "OrderDtl", "sortColumnBinding": "TransView.SortCol", "sortDirectionBinding": "TransView.SortDir" } }
```

---

### `grid-sort-set`
Broadcasts `ErpGridSortEvents.GridSortSet`; the grid whose `model.epBinding` matches applies `[{field: sortColumn, dir: sortDirection}]` (console error if the grid is not sortable).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.epBinding` | string | yes | — | grid epBinding; parseObject |
| `param.sortColumn` | string | yes | — | field/column name |
| `param.sortDirection` | `'asc'` \| `'desc'` | no | `'asc'` | defaulted in execute() |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "grid-sort-set", "param": { "epBinding": "OrderDtl", "sortColumn": "PartNum", "sortDirection": "desc" } }
```

---

### `combo-refill`
Broadcasts `IceEventType.COMBO_REFILL` with the parsed top-level `value` (the target combo's **epBinding**). The kinetic component whose `epBinding` matches calls `controlInstance.invalidate()` — i.e., the combo discards its cached list and re-runs its data/BAQ query on next open.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (TOP-LEVEL) | string | yes | — | epBinding of the combo control; whole action goes through parseObject |

Continuations: unusual — if `onSuccess` OR `onError` is present it returns `{ successOrError: onSuccess || onError, lastResultSuccessValue: !!onSuccess }` (i.e. onError array is followed only when onSuccess is absent); otherwise `{success:true}`.
```json
{ "type": "combo-refill", "value": "OrderHed.ShipViaCode", "onSuccess": [] }
```

---

### `control-focus-set`
Broadcasts `IceEventType.FOCUS` with the parsed top-level `epBinding`; the bound control receives keyboard focus.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `epBinding` (TOP-LEVEL) | string | yes | — | binding of the control to focus; parseObject on whole action |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "control-focus-set", "epBinding": "OrderHed.PONum" }
```

---

### `property-set`
Clones `param`, parses `component` and each `props[].value` (arrays element-wise), then `MetaFxComponentService.setProperty(param)` pushes on an internal `prop$` Subject. **Resolution**: every rendered component subscribes via `propertyChanged(epBinding, uniqueName, guid, modelID)` which filters `p.component === epBinding || uniqueName || guid || modelID` — so `param.component` may be the control's id (uniqueName/model id), its epBinding, or its guid; the separate `guid` field declared by the designer is NOT used for matching.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.component` | string | yes | — | control id / epBinding / guid / model id; parseValue |
| `param.guid` | string | no (designer-only) | — | declared in designer model; not read for matching |
| `param.props` | `[{ prop: string, value: any, prevValue?: any }]` | yes | — | `prop` = property name on the component model (e.g. `hidden`, `disabled`, `labelText`); each `value` parseValue'd (arrays element-wise) |

Continuations: none read; returns `{success:true}`.
```json
{
  "type": "property-set",
  "param": { "component": "btnCalc", "props": [ { "prop": "disabled", "value": false }, { "prop": "labelText", "value": "Recalculate" } ] },
  "onSuccess": []
}
```

---

### `search-value-set`
Takes rows from the system `searchResult` data view (populated by a preceding search) and writes them into binding(s), joining multiple rows/fields with delimiters. Behavior depends on the session search mode (`Auto` = chip-style append with duplicate check, else replace) and which param fields are present: `display` → dual-mode chip selection (broadcasts `CHIP_SELECTION` with `{chipId: row[columns[0]], chipDisplayText: row[display]}` items and sets the joined value); `multiFieldBindings` → writes `columns[i]` of the row(s) into `multiFieldBindings[i]`; `columns` only → concatenates the listed columns of each row into the top-level `epBinding`. If `param` is empty/missing, legacy mode: top-level `value` is split as `Table.Column` and that column of the searchResult rows is written to `epBinding` (multi-row joined by `~`).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `epBinding` (TOP-LEVEL) | string | yes | — | target binding; parseValue |
| `value` (TOP-LEVEL) | string | legacy mode only | — | `Table.Column` naming the searchResult column; parseValue |
| `param.columns` | string[] | for column modes | — | searchResult column names |
| `param.multiFieldBindings` | string[] | no | — | per-column target bindings (paired index-wise with `columns`) |
| `param.display` | string | no | — | searchResult column used as chip display text (dual mode) |
| `param.rowDelimiter` | string | no | `'~'` | joins rows |
| `param.fieldDelimiter` | string | no | `` '`' `` | joins fields within a row |

Continuations: none read; returns `{success:true}`.
```json
{
  "type": "search-value-set",
  "epBinding": "TransView.SelectedParts",
  "param": { "columns": ["PartNum"], "rowDelimiter": "~" }
}
```

---

### `title-set`
Broadcasts `IceEventType.SET_EP_VIEW_TITLE` with `{ title, customTitle: true }`; the app view/browser tab title component updates.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `value` (TOP-LEVEL) | string \| number | yes | — | new title; parseValue |

Continuations: none read; returns `{success:true}`.
```json
{ "type": "title-set", "value": "Order {OrderHed.OrderNum}" }
```

---

### `select-tree-node`
Calls `EpTreeViewActivityService.onSelectNode({component, sysRowID})`. **Node addressing**: the tree is identified by its component id and the node by the `SysRowID` of its underlying data row.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.component` | string | yes | — | the tree component id; no parse |
| `param.sysRowID` | string | yes | — | SysRowID of the node's row; parseValue |

Continuations: result truthy → `successOrError: onSuccess`; falsy (node missing or a viewChanging/rowChanging veto) → `successOrError: onError`.
```json
{ "type": "select-tree-node", "param": { "component": "MainTree", "sysRowID": "{OrderDtl.SysRowID}" }, "onSuccess": [], "onError": [] }
```

---

### `set-tree-node-state`
Calls `EpTreeViewActivityService.onSetNodeState(...)` to expand/collapse a node (same SysRowID addressing).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.component` | string | yes | — | tree id; no parse |
| `param.sysRowID` | string | yes | — | node's SysRowID; parseValue |
| `param.isExpanded` | boolean | yes | — | expanded vs collapsed; no parse |
| `param.childFolderEntityType` | string | no | — | entity type of the child folder to target under that SysRowID |

Continuations: always returns `successOrError: onSuccess` (result ignored).
```json
{ "type": "set-tree-node-state", "param": { "component": "MainTree", "sysRowID": "{OrderHed.SysRowID}", "isExpanded": true }, "onSuccess": [] }
```

---

### `refresh-tree`
Calls `EpTreeViewActivityService.onRefresh(param)` to rebuild the tree. Param is passed RAW — no parseValue/parseObject.

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.component` | string | yes | — | tree id; no parse |
| `param.preserveState` | boolean | yes | — | keep expanded/selected node state across refresh |

Continuations: result truthy → `onSuccess`, else → `onError` (both via `successOrError`).
```json
{ "type": "refresh-tree", "param": { "component": "MainTree", "preserveState": true }, "onSuccess": [], "onError": [] }
```

---

### `datatree-bindings-set`
Replaces a data tree's `treeBindings` definition at runtime: `EpTreeViewActivityService.onTreeBindingsSet({modelId, epBinding})`, where `epBinding` names a `View.Column` whose cell contains the JSON of the new treeBindings node. Param passed RAW (no parse).

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `param.modelId` | string | yes | — | id on the tree's model whose treeBindings get replaced |
| `param.epBinding` | string | yes | — | `View.Column` holding the JSON for the new treeBindings node |

Continuations: result truthy → `onSuccess`, else → `onError` (via `successOrError`).
```json
{ "type": "datatree-bindings-set", "param": { "modelId": "MainTree", "epBinding": "TransView.TreeJson" }, "onSuccess": [], "onError": [] }
```
### `rest-erp`

The most important action in the system. `execute()` first defaults any `methodParameters` entry of `type:'integer'` with no `epBinding` and empty/undefined `value` to `0`, then runs the ENTIRE `action.param` through `eventParamService.parseObject()` (so every string property supports `%binding%` / token substitution). If executing in a deep-link route load or Paste-Insert/Update context it forces `options.suppressException = true`. It then dispatches an `IErpRestActivityData` through `EpRestActivityService.onRestCall` to the ERP plugin layer, and maps the boolean outcome to `onSuccess`/`onError`.

**`param` shape as read by execute()/service (IErpREST):**

| param property | type | required? | default | notes |
|---|---|---|---|---|
| `svc` | string | yes | – | e.g. `"Erp.BO.SalesOrderSvc"`. Designer fills combo from `GetRestServicesList` activity. |
| `svcPath` | string | yes | – | Method/operation, e.g. `"Update"`, `"GetByID"`. Designer combo built from swagger keys ending `_output`. |
| `erpRequestMethod` | ErpRequestMethod | no | `'ErpPostWithDataViewProcessing'` (designer default; handler also defaults to it when both `erpRequestMethod` and `requestMethod` are missing) | One of `GET,POST,PUT,DELETE,OPTIONS,HEAD,PATCH,GetAndFillEpDataview,PatchFromEpDataView,PostFromEpDataview,PostWithCustomMethod,UpdateAndPostDataTable,ErpPostWithDataViewProcessing`. Designer also stores legacy `requestMethod:'POST'`. BAQ-style methods are routed to `ErpBaqActivityHandlerService` and require `erpBaqArgs` (error if missing). |
| `methodParameters` | IParams[] | no | – | POST body scalars. Each: `field` (name, required), `value` (static; goes through parseValue via `requestParam`), `epBinding`, `model` (send whole dataview model), `interpolation`, `rowMode`, `isArray`, `onlyWhenHasChanges`, `session` (e.g. `%session.CompanyId%`), nested `params`. Built into request `data` by `epEventParamService.requestParam(params, data, null)`. |
| `erpRestPostArgs` | object | no | – | See sub-table below. Only used by `ErpPostWithDataViewProcessing`. |
| `erpBaqArgs` | object | no | – | Only for BAQ request methods (legacy path; the `erp-baq` action is preferred). |
| `options` | IErpRestCallOptions | no | – | Designer exposes `suppressException`, `apiKey`, `efxLibrary`. Runtime also honors `rollbackOnError`, `closeDialogsOnError`, `convertTypesToJson/FromJson`, `alias`, `populateDataView`, `resultPath`, `updateEntity`, `tableMapping`, `filterRowMods`, `ignoreContextHeader`, `addDataCollectionLicense`, `addECCWebServiceLicense`. NOTE: there is NO `headers`, `showProgress`, `blockUi`, `callProperty`, pagination, or asynchronous/queue option for this action. |
| `dataView` | EpDataView | no | – | Used only by `PatchFromEpDataView` / `PostFromEpDataview` methods. |
| `dirtyRows` | IErpRestDirtyRowsArgs[] | no | – | `{view: 'tableId' or 'tableId:viewId'}`; forces the current row of that view into the payload with `RowMod:'U'` (or `'A'`), marking it modified. |

**`erpRestPostArgs` sub-shape:**

| property | type | default | notes |
|---|---|---|---|
| `processResponse` | boolean | `true` (set to true by `processErpPostArgs` when null/undefined) | When false the response is NOT merged into dataviews. |
| `responsePath` | string | – | Global override of where response tables live in the JSON (default `parameters/<basePath>`; basePath default `'ds'`). |
| `requestParamArgs` | array | – | Each: `dataset {systemCode (default 'Erp'), datasetId (required), serverDataset}` OR `viewName`; plus `paramPath`, `paramName`, `dirtyRow`, `methodParamModifier` (`default`\|`ExcludeBeforeImage`\|`SendAllRows`). Defines which dataviews are serialized into the posted `ds`. |
| `responseParamArgs` | array | – | Each: `dataset {...}` OR `viewName`; plus `paramPath`, `paramName`, `responsePath`, `mergeBehavior` (`merge`\|`replace`). Defines how response tables map back to dataviews. |
| `fillExtendedProps` | object | – | `{useDefaultValues, paramName, responsePath, dynamicAttributeClassId(epBinding)}`. When `useDefaultValues` true, uses `paramName='ds'`, `responsePath='parameters'`; fetches the ds and calls the dynamic-attribute (extended UD props) service. |

**Request payload engine (`ErpPostWithDataViewProcessing`)** — web equivalent of classic `CopyDatasetToTableset`:
1. `ErpDatasetMappingService.processErpPostArgs`: every `requestParamArgs` entry with a `viewName` becomes an `opts.tableMapping` entry `{name: paramName, data: dataview, methodParamArg}`. Entries with a `dataset` are EXPANDED into one arg per table of the dataset (viewName/tableId/datatableKeys resolved from the cached route DataViews + dataset metadata fetched via REST); a missing dataview yields an empty array on `methodParameters[tableId]`.
2. `ErpRestHelperService.generateDataSet` builds `{ <basePath|'ds'>: { <TableName>: rows[] } }`. Rows chosen per `methodParamModifier`: `default`/null = before-image row (`RowMod:''`) + updated row (`RowMod:'U'`), or added row (`RowMod:'A'`), plus deleted rows; `ExcludeBeforeImage` = only `'U'`/`'A'` rows; `SendAllRows` = every row regardless of RowMod. `dirtyRow`/action `dirtyRows` force the current row in as `'U'`.
3. An `onBeforeActivity` (`BeforeErpDataViewPost`) lets consumers cancel or mutate the payload (cancel yields `ErpPostCancelled` error).
4. `GetList`/`GetRows` (and `Ice.Lib.MetaFxSvc/GetApp`) are transparently switched from POST to GET when the query string is short enough; 405 falls back to POST.

**Response mapping engine (`processErpPostResponse`)** — runs only when `erpRestPostArgs.processResponse`:
- **From requestParamArgs** (round-trip merge): views ordered hierarchically (parents first). For each view: response rows read from `"<responsePath | erpRestPostArgs.responsePath | parameters/<basePath>>/<paramName>"` (slash-delimited path into the response JSON). Client table commits deleted+modified, then `loadBatchDataRows` merges server rows by key sets (`datatableKeys` first, then `['SysRowID']`); rows with `RowMod:'D'` are deleted+committed; a single unmatched added client row gets its PK values inferred from the unmatched server row (order-entry style key assignment); extra added client rows are rejected.
- **From responseParamArgs** (fill/refresh): for each view — `mergeBehavior` missing or `replace` ⇒ `dataview.clear()` first (with current-row save/restore when context mode is Refresh/Delete so grids keep position); `merge` ⇒ upsert only. Response rows resolved the same way; each row upserted by keys, `'D'` rows deleted, and `dataview.commit()` when nothing dirty remains. `includeSysRowId===false` skips SysRowID batching.
- `fillExtendedProps` then fires the dynamic-attributes fetch.

**Scalar/return handling (metafx side, `processRestResponse`)**: `result.parameters.errorsOccurred` ⇒ `sysGlobalVariable.errorsOccurred`; otherwise every NON-object parameter ⇒ `actionResult.<key>`. `returnObj` null ⇒ `actionResult.returnObj = null`; scalar `returnObj` ⇒ `actionResult.returnObj`. If `options.efxLibrary` present (function call), EVERY key of the result is copied to `actionResult.<key>`.

**Errors & continuations**: HTTP and business errors are caught in the ERP activity handler (`catchError` puts the error object into `args.result`), so the metafx service sees `result.message` as a string ⇒ sets `actionResult.<ErrorMessage/…>` from `result.response.error`, logs, and returns `success=false`. `execute()` chooses `onSuccess` when success, `onError` otherwise; response is `{ success, successOrError, lastResultSuccessValue: success }` (no `shouldCallNextAction`). There is NO separate onFailure and no distinction between HTTP-status and BPM/business errors at the branch level — both land on `onError`. Unless `options.suppressException===true`, the ERP layer first shows the exception slideout (`showExceptionSlideout`); `closeDialogsOnError` closes all dialogs; `rollbackOnError` rolls back deleted rows in the requestParamArgs views; RowMods set by `dirtyRow` are reset on error.

```json
{
  "type": "rest-erp",
  "param": {
    "svc": "Erp.BO.SalesOrderSvc",
    "svcPath": "Update",
    "erpRequestMethod": "ErpPostWithDataViewProcessing",
    "methodParameters": [{ "field": "ds", "value": "" }],
    "erpRestPostArgs": {
      "processResponse": true,
      "requestParamArgs": [
        { "dataset": { "systemCode": "Erp", "datasetId": "SalesOrder" }, "paramName": "ds", "methodParamModifier": "default" }
      ],
      "responseParamArgs": [
        { "paramName": "OrderHed", "viewName": "OrderHed", "mergeBehavior": "replace" },
        { "paramName": "OrderDtl", "viewName": "OrderDtl", "mergeBehavior": "merge", "responsePath": "parameters/ds" }
      ]
    },
    "options": { "suppressException": false }
  },
  "onSuccess": [{ "type": "erp-message-handler", "param": { "type": "toast", "level": "information", "message": "Order saved" } }],
  "onError": [{ "type": "console-write", "param": { "message": "{actionResult.ErrorMessage}" } }]
}
```

---

### `erp-function`
Shares the `rest-erp` request pipeline.

Calls an Epicor Function (EFx) library operation. `execute()` builds an `IErpREST` internally: `svcPath = action.efxPath`, `erpRequestMethod = 'ErpPostWithDataViewProcessing'`, `methodParameters = action.methodParameters`, `erpRestPostArgs = { responseParamArgs: action.responseParamArgs, processResponse: true }`, `options = { efxLibrary: action.efxLibrary, apiKey: action.apiKey }`. All properties live DIRECTLY ON THE ACTION (not under `param`). Because `options.efxLibrary` is set, the whole function response object is flattened into `actionResult.<key>` (see rest-erp `processFunctionResponse`); response dataset tables can additionally be mapped to dataviews via `responseParamArgs` (designer auto-suggests `viewName` = `<responsePath>_<tableName>`).

| action property | type | required? | default | notes |
|---|---|---|---|---|
| `efxLibrary` | string | yes (practically) | – | Library id; designer combo from `GetEfxLibraryList` activity. |
| `efxPath` | string | yes | – | Function name; combo from swagger keys ending `Output`. |
| `apiKey` | string | no | – | Sent as x-api-key. |
| `methodParameters` | array | no | – | Same `{field, value/epBinding,...}` shape as rest-erp (types from `<fn>Input` swagger; `date-time` format maps to `datetime`). |
| `responseParamArgs` | array | no | – | Same shape as rest-erp responseParamArgs (`paramName`, `viewName`, `responsePath`, `mergeBehavior`, `dataset`...). |

Continuations: `onSuccess` / `onError`; response `{ success, successOrError, lastResultSuccessValue: success }`.

```json
{
  "type": "erp-function",
  "efxLibrary": "MyLibrary",
  "efxPath": "GetCustomerCredit",
  "apiKey": "",
  "methodParameters": [{ "field": "custNum", "epBinding": "Customer.CustNum" }],
  "responseParamArgs": [{ "responsePath": "creditData", "paramName": "CreditTable", "viewName": "creditData_CreditTable" }],
  "onSuccess": [{ "type": "row-update", "param": { "epBinding": "TransView.CreditOk", "value": "{actionResult.creditOk}" } }],
  "onError": []
}
```

---

### `rest`

Generic (ICE-style) REST call, NOT the ERP dataview engine. `param` = `{ request, response }`. `request.svc`/`request.svcPath` go through `parseValue`. Only `GET` and `POST` are handled (anything else returns undefined!). POST body: if `request.addFullModelToRequest`, the current row of dataview `request.model` is copied (all values converted to string), then `request.params` (IParams[]) are appended via `requestParam`.

| param property | type | required? | notes |
|---|---|---|---|
| `request.svc` | string | yes | service |
| `request.svcPath` | string | yes | path |
| `request.method` | 'GET'\|'POST' | yes | others ignored |
| `request.model` | string | no | dataview id for full-model POST |
| `request.addFullModelToRequest` | boolean | no | send whole current row |
| `request.ignoreIfEmptyDataSet` | boolean | no | declared on interface (not read in this service) |
| `request.params` | IParams[] | no | appended to body |
| `response.model` | string | no | target dataview: array data → `addRows` (or `mergeRow` per row when `response.mergeRow`), object → `addRow` |
| `response.hasMultipleModel` | boolean | no | walk the object found at `response.returnObject`; every property whose name matches an existing dataview gets `addRows` (empty arrays only when listed in `response.replace`) |
| `response.preserveOldData` | boolean | default false | declared; normalized in handler |
| `response.returnObject` | string | no | deep-scan key to locate payload in complex responses |
| `response.mergeRow` | boolean | no | merge rows by key instead of add |
| `response.replace` | string[] | no | dataviews allowed to update even when response array empty |

Scalars: every non-`ds` key of `response['parameters']` ⇒ `actionResult.<key>`; scalar `returnObj` ⇒ `actionResult.returnObj`.
Continuations: none are branched — `execute()` always returns `{ success: true }` (errors propagate as observable errors to the framework). No `onSuccess`/`onError` read.

```json
{
  "type": "rest",
  "param": {
    "request": { "svc": "Ice.BO.UserFileSvc", "svcPath": "GetRows", "method": "POST",
      "params": [{ "field": "whereClause", "value": "UserID = '{sysSession.UserId}'" }] },
    "response": { "model": "UserFile", "hasMultipleModel": false, "preserveOldData": false, "mergeRow": false, "replace": [] }
  }
}
```

---

### `erp-baq`

Executes or updates a BAQ. All properties are ON THE ACTION (no `param`), and the whole action object is run through `eventParamService.parseObject` (token substitution everywhere). `populateDataView` is auto-set when `alias` is non-empty (results land in the dataview named by `alias`). `baqParams` are converted to `executeOptions.parameters` as `{ParameterID, ParameterValue, ValueType, IsEmpty}`; an entry's `epBinding` ('View.Column') is resolved live against the dataview model. `executeOptions.select/orderBy/groupBy` accept comma-separated strings (split into arrays).

| action property | type | required? | default | notes |
|---|---|---|---|---|
| `baqId` | string | yes | – | Query ID; designer combo from `getBAQList`. |
| `mode` | 'get'\|'update' | no | `'get'` | |
| `alias` | string(epBinding) | no | – | Target dataview name for results / source rows for update. |
| `executeOptions` | object | no (get mode) | – | `pageNumber`, `pageSize`, `select`(csv/array), `where` (interpolatable), `orderBy`, `groupBy`, `having`, `aggregate[{column,type}]`, plus auto-filled `parameters`. |
| `baqParams` | array | no (get mode) | auto-filled from BAQ definition | `{field, value, type, isEmpty, epBinding}`. |
| `updateOptions` | object | update mode | – | `operation` (`UpdateBaq`\|`UpdateBaqFieldUpdate`\|`UpdateBaqFieldValidate`\|`UpdateBaqCustomAction`\|`UpdateBaqGetNew`), `actionID` (customAction), `allRows`, `rollbackOnError`, `fieldName`, `fieldValue`. `viewName` is forced to `alias` at runtime. |

Rows sent for update: `getNew` ⇒ none; `fieldValidate`/`fieldUpdate` or `allRows!==true` ⇒ current row of `alias` view; otherwise all rows.
Continuations: **update mode** — `result.cancel===true` ⇒ `onError`, else `onSuccess` (`{successOrError}` only, no lastResultSuccessValue). **get mode** — always `{ success: true }` (no branch; errors propagate to framework).

```json
{
  "type": "erp-baq",
  "baqId": "zCustomer01",
  "mode": "get",
  "alias": "MyBaqResults",
  "executeOptions": { "pageSize": 100, "where": "CustID = '{OrderHed.CustID}'", "orderBy": "Customer_Name" },
  "baqParams": [{ "field": "pCompany", "epBinding": "sysSession.CompanyID", "type": "string", "isEmpty": false }],
  "onSuccess": [], "onError": []
}
```

---

### `erp-message-handler`

The standard message/dialog action (successor of `dialog-show`). Deep-clones `param`, runs `parseObject`, then `parseValue` on `message` (with `placeholderValues` token array), `title`, `buttons`, `result`, `level`, `type`; attaches the current data context; fires the `HandleMessage` generic activity (`EpGenericActivityId.HandleMessage`) — this is how BPM-style/user messages are surfaced (toast, slideout dialog, log, etc. depending on `type`).

| param property | type | required? | notes |
|---|---|---|---|
| `type` | EpMessageType | yes | e.g. Slideout (dialog), toast, etc. Only Slideout results are branched. |
| `level` | EpMessageLogLevel | yes | info/warning/error... |
| `message` | string | yes | epBindingInterpolate; `{0},{1}` placeholders filled from `placeholderValues`. |
| `buttons` | EpMessagePanelButtons | no | which buttons the slideout shows (okCancel, yesNo, ok, ...). |
| `result` | EpMessagePanelResult | no | default result. |
| `title` | string | no | |
| `placeholderValues` | array of `{placeholderValue}` | no | substitution values (each parsed). |

Continuations (ACTION-level, not in param): if the activity result `type === Slideout`, dialog result maps `'Ok'→onOk`, `'Yes'→onYes`, `'No'→onNo`, `'Cancel'→onCancel`; any other value ⇒ `{success:false, value:'<x> - not supported'}`. Branch response is `{ successOrError, lastResultSuccessValue: true }`. Non-slideout messages ⇒ `{ success: true }`. Designer-only extras: `epBinding`, `dataview`, `dataTable`, `condition`, `option {name,args,output,dataType}`, `variable`.

```json
{
  "type": "erp-message-handler",
  "param": { "type": "Slideout", "level": "warning", "title": "Confirm",
    "message": "Delete order {0}?", "buttons": "yesNo",
    "placeholderValues": [{ "placeholderValue": "{OrderHed.OrderNum}" }] },
  "onYes": [{ "type": "row-delete", "param": { "dataView": "OrderHed" } }],
  "onNo": []
}
```

---

### `process-import-service`

Uploads cached files to the server via the `ProcessImportUploadFiles` generic activity (`data.activityId` is forced to `UxpGenericActivityId.ProcessImportUploadFiles`). `bindingCacheKey`, `bindingServerFile`, `filesCacheKey` are `parseValue`d.

| param property | type | required? | notes |
|---|---|---|---|
| `filesCacheKey` | string | no | key of the uploaded-files cache. |
| `bindingServerFile` | epBinding | no | binding that receives/holds server file name. |
| `specialFolder` | ErpSpecialFolder enum | no | server special folder. |
| `bindingCacheKey` | string | no | read by execute(); NOT in designer model (designer-only omission). |

Continuations: activity result with matching activityId and non-empty `status.fileNames` ⇒ `onSuccess`, else `onError` (plain `{successOrError}`).

```json
{ "type": "process-import-service",
  "param": { "filesCacheKey": "importFiles", "bindingServerFile": "ImportView.ServerFile", "specialFolder": 3 },
  "onSuccess": [], "onError": [] }
```

---

### `file-transfer-erp`

Uploads files from an ErpFileBox component or downloads a server file, via `ErpFileTransferService`. `specialFolder` (toNumber), `transferType`, `serverPath`, `clientPath`, and (upload) `erpFileBoxID` / (download) `company` all go through `parseValue`.

| param property | type | required? | notes |
|---|---|---|---|
| `specialFolder` | ErpSpecialFolder (number) | yes | server special folder enum. |
| `serverPath` | string | yes | upload: `\path\file` (a trailing `_Directory` suffix marks directory mode); download: server file path. |
| `clientPath` | string | no | download target name. |
| `company` | string | no | download only. |
| `transferType` | 'download'\|'upload' | yes | |
| `erpFileBoxID` | string | upload | objectId of the ErpFileBox component; its model's `files` are uploaded (one merged observable per file). |

Continuations: only `onSuccess` is ever used (`successOrError = onSuccess` even after catchError; `onError` never referenced). Upload with a bad `erpFileBoxID` just logs and returns undefined.

```json
{ "type": "file-transfer-erp",
  "param": { "transferType": "upload", "specialFolder": 3, "serverPath": "\\Uploads\\{sysSession.UserId}", "erpFileBoxID": "myFileBox" },
  "onSuccess": [] }
```

---

### `download-attachment-erp`

Downloads an XFileRef attachment to the client. `param` is `parseObject`'d; the service first resolves doc types for the related table (`getCombinedDocTypes` with `schema: relatedToSchemaName`, `tableId: relatedToFile`) and then calls `downloadFileToClient({docTypeID, fileName, xFileRefNum})`.

| param property | type | required? | notes |
|---|---|---|---|
| `docTypeID` | string | no | document type. |
| `xFileRefNum` | number | yes | attachment reference number. |
| `fileName` | string | yes | file name (also used as save name). |
| `relatedToSchemaName` | string | yes | e.g. `Erp`. |
| `relatedToFile` | string | yes | related table, e.g. `OrderHed`. |

Continuations: doc-type fetch error ⇒ `onError`; download result truthy ⇒ `onSuccess` else `onError`. Missing param/service ⇒ `onError`.

```json
{ "type": "download-attachment-erp",
  "param": { "docTypeID": "", "xFileRefNum": "{Attachments.XFileRefNum}", "fileName": "{Attachments.FileName}",
    "relatedToSchemaName": "Erp", "relatedToFile": "OrderHed" },
  "onSuccess": [], "onError": [] }
```

---

### `search-show`

Opens the standard Kinetic search panel (or runs a silent search). `param = { searchOptions: {...} }`; `searchOptions` is `parseObject`'d (excluding key `validateFilter`). `searchOptions.show` defaults to `true`. **show=false (silent)**: only runs when the triggering column-change has a value, otherwise branches `onEmpty`; builds the where clause from search metadata + `valueIn` defaults + `sortByColumn`, executes `performSearchRequest`; rows found ⇒ the **`searchResult` dataview is cleared and filled with the result rows** and `onSuccess` fires with `shouldCallNextAction: true`; no rows ⇒ warning toast (`validation.errorMessage` or default) then `onError` with `shouldCallNextAction: true, success:false`. **show=true (sliding)**: sets `actionResult.searchCancelled=false` and clears `actionResult.searchResult`; opens `ErpMetaFxSlidingSearchComponent`; OK with rows ⇒ fires `ProcessUxpSearchShowResponse` activity (which applies rows/`subPanelResponse` bindings) then `onSuccess` with `shouldCallNextAction: false`; Cancel/empty ⇒ sets `actionResult.searchCancelled=true` and still returns `onSuccess` with `shouldCallNextAction:false` (typically followed by `search-value-set` child actions which are skipped because shouldCallNextAction is false).

| `param.searchOptions` property | type | notes |
|---|---|---|
| `like` | string, required | search target `Table.Column` (e.g. `Customer.CustID`); also keys the saved panel layout. |
| `show` | boolean, default true | false = silent search. |
| `selectMode` | 'MultiSelect'\|'SingleSelect' | multi-select support. |
| `owner` | string | owning component. |
| `searchForm` | string | override search form. |
| `launchSearchType` | ''(Basic)\|'quick'\|'BAQ' | which search type to open. |
| `launchSearchName` | string | quick-search/BAQ-search id. |
| `preLoadSearchFilter` | json | preload criteria. |
| `validation` | json | `{errorMessage}` used on empty silent result. |
| `sortByColumn` | string | initial sort. |
| `disableColumns` | json | columns disabled in the panel. |
| `pageSize` | number | page size. |
| `CustomArgs` | array `{field,value}` | passed to `performSearchRequest`. |
| `AlternateSearchMethod` | string | alternate BO method. |
| `subPanelResponse` | array `{epBinding,column}` | result-column→binding mapping applied on OK. |
| `valueIn` | array `{id,value}` | default criteria values (silent search). |
| `useGetRows` | boolean | use GetRows instead of GetList. |
| `overrides` | array `{type,name,value}` | metadata overrides. |
| `returnMultipleTables` | boolean | return all tables. |
| `hideOkButton` | boolean | runtime-read; hides OK on the panel. |

Continuations: `onSuccess`, `onError`, `onEmpty` (silent, no trigger value). Uses `shouldCallNextAction` (true for silent results, false for sliding panel). Result context: `searchResult` dataview (silent), `actionResult.searchCancelled` / `actionResult.searchResult`.

```json
{ "type": "search-show",
  "param": { "searchOptions": { "like": "Customer.CustID", "show": true, "selectMode": "SingleSelect",
    "launchSearchType": "", "pageSize": 100,
    "subPanelResponse": [{ "epBinding": "OrderHed.CustID", "column": "CustID" }] } },
  "onSuccess": [{ "type": "search-value-set", "param": { "columns": ["CustID"] } }],
  "onError": [], "onEmpty": [] }
```

---

### `dialog-show` — OBSOLETE

Logs "obsolete, use erp-message-handler". Maps `param.type` to buttons (`alert`/`okCancel` ⇒ okCancel, `yesNo` ⇒ yesNo, `yesNoCancel` falls back to yesNo) and fires `HandleMessage` as a Slideout with `message` parsed against `placeholderValues`.

| param property | type | notes |
|---|---|---|
| `type` | 'yesNo'\|'okCancel'\|'alert'\|'yesNoCancel' | button set. |
| `message` | string | `{0}` placeholders via `placeholderValues`. |
| `placeholderValues` | string[] | substitutions. |
| `view`, `childView` | string | declared on IModelDialog; NOT read by execute() (legacy/designer-only). |
| `onYes`/`onNo`/`onOk`/`onCancel` | action[] | **inside param** — branch arrays. |

Continuations: dialog result `'Ok'→param.onOk`, `'Yes'→param.onYes`, `'No'→param.onNo`, `'Cancel'→param.onCancel`; response `{successOrError, lastResultSuccessValue:true}`; non-slideout ⇒ `action.onSuccess`.

```json
{ "type": "dialog-show",
  "param": { "type": "yesNo", "message": "Continue with {0}?", "placeholderValues": ["{OrderHed.OrderNum}"],
    "onYes": [], "onNo": [] } }
```

---

### `dialog-show-system`

Shows the SYSTEM confirmation dialog (save/delete/undo confirmations) via the `ShowSystemDialog` generic activity. `dialogMessage`, `dialogTitle`, `uiFormFullName`, `uiFormEventType` are `parseValue`d (token substitution in message/title). The ERP handler may SUPPRESS the dialog based on user dialog-confirmation options for the `uiFormEventType`/form, auto-answering Yes/No.

| param property | type | required? | notes |
|---|---|---|---|
| `uiFormEventType` | ErpFormEventType | yes | e.g. `UpdateOnSaveButton`, `DeleteOnDeleteButton`, `UndoOnClearButton`, `PrintDialog`, `None` — drives suppression rules. |
| `uiFormFullName` | string | no | classic form full name for per-form confirm options. |
| `forceConfirm` | boolean | no | force showing. |
| `dialogTitle` | string | no | |
| `dialogMessage` | string | no | |
| `dialogButtons` | EpDialogButtons | no | |
| `dialogStatus` | EpDialogStatus | no | |
| `onSuccess` | action[] | no | **inside param** — runs when result === 'Yes'. |
| `onFailure` | action[] | no | **inside param** — any other result (No). |
| `objectKind/objectId/objectName/objectCreationDate/configKey` | – | designer-only metadata fields. |

Continuations: result string `'Yes'` ⇒ `param.onSuccess`, else `param.onFailure` (`{successOrError}` only). Action-level `id/onSuccess/onError` are hidden by designer row rules.

```json
{ "type": "dialog-show-system",
  "param": { "uiFormEventType": "DeleteOnDeleteButton", "dialogTitle": "Delete",
    "dialogMessage": "Delete record {OrderHed.OrderNum}?",
    "onSuccess": [{ "type": "rest-erp", "param": { "svc": "Erp.BO.SalesOrderSvc", "svcPath": "Update" } }],
    "onFailure": [] } }
```

---

### `dialog-result-set`

Sets the pending dialog result string used by slider/app close flows. Reads ACTION-level `value` (through `parseValue`) and stores it via `MetaFxDialogResultSetEventService`; `slider-open`'s `onAfterClosed` and `app-close` consume it (e.g. set 'OK' before closing a slider so `slider-open.onOk` fires).

| action property | type | required? | notes |
|---|---|---|---|
| `value` | string | yes | e.g. `OK`, `Cancel`, `Yes`, `No`, `Abort`, `Retry`, `Ignore`, `None`. |

Continuations: none branched (service returns its own response; no onSuccess/onError read in execute).

```json
{ "type": "dialog-result-set", "value": "OK" }
```

---

### `slider-open`

Opens one of the CURRENT VIEW's pages (`view.Pages`, by page `name`) in a sliding panel. Wires the page's `slidingPanel.buttons`/`actionData` to their onClick events; honors page `width`, `slidingPanel.collapseOnOutsideClick`, page ONCLOSING (can `preventDefault` via `sysVariable`) and ONCLOSED events; refreshes `navigation.pageCaption` via parseValue. When the panel closes, the captured dialog result (button `dialogResult` or the value set by `dialog-result-set`) picks the branch.

| param property | type | required? | notes |
|---|---|---|---|
| `page` | string | yes | page name within the current app view (only property on IOpenSliderParam). |

Continuations (ACTION-level): `'OK'/'Ok'→onOk`, `'Cancel'/'Close'→onCancel`, `'None'→onNone`, `'Abort'→onAbort`, `'Retry'→onRetry`, `'Ignore'→onIgnore`, `'Yes'→onYes`, `'No'→onNo`; unknown ⇒ `{success:false, value:'invalid open-view response <x>'}`. Branch response `{successOrError, lastResultSuccessValue:true}`.

```json
{ "type": "slider-open", "param": { "page": "CustomerDetailPanel" },
  "onOk": [{ "type": "rest-erp", "param": { "svc": "Erp.BO.CustomerSvc", "svcPath": "Update" } }],
  "onCancel": [] }
```

---

### `slider-close`

Pops the last sliding panel (`EpShellService.popSlidePanel('last')`). No params read. Always returns `{ success: true }`; no continuation arrays read. (Pair with `dialog-result-set` first so the owning `slider-open` branches correctly.)

```json
{ "type": "slider-close" }
```

---

### `dynamic-panel-open`

Builds a dynamic sliding panel from ACTION-level properties and fires the `ShowDynamicPanel` generic activity.

| action property | type | notes |
|---|---|---|
| `title` | string | parseValue'd panel title. |
| `width` | number/string | panel width. |
| `epBindingComponents` | array | bound components model. |
| `components` | array | component defs, `parseObject`'d. |

Continuations: activity result with `closeData` (OK pressed, data returned) ⇒ `onOk`, else ⇒ `onCancel`; `{successOrError, lastResultSuccessValue:true}`.

```json
{ "type": "dynamic-panel-open", "title": "Enter Reason", "width": 400,
  "components": [{ "id": "reasonText", "type": "textbox", "epBinding": "TransView.Reason" }],
  "onOk": [], "onCancel": [] }
```

---

### `app-open`

Opens another Kinetic app. `param.view` parseValue'd; `valueIn`/`launchOptions` parseObject'd (mutually exclusive — valueIn wins). **`slideOut: true`**: opens the child app in a slider (iframe): width from `width` ('Custom' + `customWidth`, or a `UxpSlidingPanelWidthTypes` key, default Medium); then WAITS for `EXECUTE_DIALOG_RESULT` from the child close — the child's `app-close` `valueOut` object is written to a fresh `actionResult` row, its `dataviews` payload is copied back into the parent dataviews (with UI-thread notifications), and `closeParam.result` picks the branch. **`slideOut` false/absent**: broadcasts `OPEN_VIEW` (shell navigation) and immediately returns `onSuccess`.

| param property | type | required? | notes |
|---|---|---|---|
| `view` | string | yes | target app/view id (e.g. `Erp.UI.CustomerEntry`). |
| `menuId` | string | no | menu id of the view. |
| `layer` | string | no | layer applied to the child view. |
| `whoLaunched` | string | no | sender id. |
| `valueIn` | object | no | KeyValue args to the child (parseObject). |
| `launchOptions` | `{options, type}` | no | LFO-style launch options (parseObject/parseValue); cleared if valueIn present. |
| `slideOut` | boolean | no | open in slider and wait for result. |
| `page` | string | no | open specific page of the child app. |
| `width` | number\|string | no | slider width type or 'Custom'. |
| `customWidth` | number | no | used when width==='Custom'. |
| `openInDesignMode`, `inAppstudioPreview`, `mode` | – | designer/studio flags (not used in this execute path). |
| `onOk/onCancel/onNone/onAbort/onRetry/onIgnore/onYes/onNo` | action[] | no | **inside param** — branch by child's close result. |

Continuations: slideOut result maps `OK→param.onOk`, `Cancel→param.onCancel`, `None→param.onNone`, `Abort→param.onAbort`, `Retry→param.onRetry`, `Ignore→param.onIgnore`, `Yes→param.onYes`, `No→param.onNo`; unknown ⇒ `{success:false,...}`; matched ⇒ `{successOrError, lastResultSuccessValue:true}`. Non-slideOut ⇒ ACTION-level `onSuccess`. Child return data: `closeParam.valueOut` ⇒ `actionResult` row; `closeParam.dataviews` rows replace parent dataview data.

```json
{ "type": "app-open",
  "param": { "view": "Erp.UI.CustomerEntry", "slideOut": true, "width": "Medium",
    "valueIn": { "CustID": "{OrderHed.CustID}" },
    "onOk": [{ "type": "rest-erp", "param": { "svc": "Erp.BO.SalesOrderSvc", "svcPath": "GetByID" } }],
    "onCancel": [] } }
```

---

### `app-close`

Closes the current app when running inside an iframe/slider: `param` parseObject'd; if `param.result` empty it uses the stored `dialog-result-set` value; posts `REQUEST_OUTPUT_DATAVIEW` to the host (which then emits `EXECUTE_DIALOG_RESULT` back to the parent's `app-open`). Outside an iframe it just collapses the sliding panel. Always `{success:true}`; no branches.

| param property | type | notes |
|---|---|---|
| `result` | DialogResultType string | 'OK','Cancel','Yes','No',... — drives parent's app-open branch. |
| `dataviews` | `{source,destination}[]` | dataviews copied back to the parent. |
| `valueOut` | object | scalars returned to the parent's `actionResult`. |

```json
{ "type": "app-close",
  "param": { "result": "OK", "valueOut": { "selectedCust": "{Customer.CustID}" },
    "dataviews": [{ "source": "Customer", "destination": "Customer" }] } }
```

---

### `page-navigate-to`

Broadcasts `NAVIGATE_PAGE` with the parsed param. No result waiting.

| param property | type | required? | notes |
|---|---|---|---|
| `page` | string | yes | target page name in the current app (only property). |

Continuations: none; always `{ success: true }`.

```json
{ "type": "page-navigate-to", "param": { "page": "LandingPage" } }
```

---

### `url-open`

Opens a URL through `MetaFxAppCommunicatorService.launchWebForm(URL, title, external, otacSupport)`. `URL` is parseValue'd (supports `{0}` style bound urls). With `useAppCommunicator: true` an app-communicator channel is created and `&channelid=<id>` appended.

| param property | type | notes |
|---|---|---|
| `URL` | string, required | target url. |
| `title` | string | window/tab title. |
| `external` | boolean | open external browser window. |
| `otacSupport` | boolean | append one-time access code auth. |
| `useAppCommunicator` | boolean | create comm channel and pass channelid. |

Continuations: none; always `{ success: true }`.

```json
{ "type": "url-open", "param": { "URL": "https://maps.google.com/?q={Customer.City}", "external": true } }
```

---

### `apps-communicator-broadcast`

Broadcasts an `IActionMessage` to all connected apps via `MetaFxAppCommunicatorService.broadcastErpEvent`. Param parseObject'd.

| param property | type | required? | notes |
|---|---|---|---|
| `action` | string | yes | action/message name (shown as shape text). |
| `args` | json object | yes | payload. |

Continuations: none; always `{ success: true }`.

```json
{ "type": "apps-communicator-broadcast", "param": { "action": "refreshOrders", "args": { "orderNum": "{OrderHed.OrderNum}" } } }
```

---

### `apps-communicator-publish`

Publishes an `IPublishData` payload on the app-communicator channel (`publishData`). Param parseObject'd.

| param property | type | required? | notes |
|---|---|---|---|
| `whoPublished` | string | yes | publisher key subscribers listen for. |
| `args` | array `{key, value}` | no | value is epBindingInterpolate (token-substituted). arrayIndexer `key`. |

Continuations: if ACTION `onSuccess` is defined it is returned as `{successOrError: onSuccess}`, else `{ success: true }`. No onError.

```json
{ "type": "apps-communicator-publish",
  "param": { "whoPublished": "orderContext", "args": [{ "key": "OrderNum", "value": "{OrderHed.OrderNum}" }] },
  "onSuccess": [] }
```

---

### `credit-card-entry`

Fires the `CreditCardEntry` generic activity with an `IUxpCreditCardActivityModel` (param parseObject'd; `hostAddress`, `hostNamespace`, `publicKey` additionally parseValue'd — typically bound to company payment-gateway settings).

| param property | type | notes |
|---|---|---|
| `hostAddress` | string | gateway host. |
| `hostNamespace` | string | gateway namespace. |
| `publicKey` | string | gateway public key. |
| (other IUxpCreditCardActivityModel fields) | – | passed through untouched. |

Continuations: activity returned a result ⇒ `actionResult.creditCardStatus` is set and `{success:true}` (onSuccess NOT branched explicitly); no result ⇒ `onError` with `lastResultSuccessValue:false`.

```json
{ "type": "credit-card-entry",
  "param": { "hostAddress": "{CompanyCC.HostAddress}", "hostNamespace": "{CompanyCC.Namespace}", "publicKey": "{CompanyCC.PublicKey}" },
  "onError": [] }
```

---

### `kbmax-configurator-open`

Opens the KBMax (CPQ) configurator via `ShowKBMaxConfigurator` generic activity; `param` is parseObject'd and passed as the activity args (opaque model consumed by the KBMax activity handler). On result, the raw result object is JSON-stringified into `actionResult.response`.

| param property | type | notes |
|---|---|---|
| (opaque) | object | passed to ShowKBMaxConfigurator activity after parseObject. |

Continuations: non-empty activity result ⇒ `onSuccess` (after setting `actionResult.response`); empty/error (errors are swallowed to `[]`) ⇒ `onError`.

```json
{ "type": "kbmax-configurator-open", "param": { "configuratorId": 42, "quoteNum": "{QuoteHed.QuoteNum}" },
  "onSuccess": [], "onError": [] }
```

---

### `pdf-viewer-action`

Drives the embedded PDF viewer through generic activities: `download` ⇒ `GetCurrentDocumentAsBase64` (result stored in `actionResult.returnObj`); `focus-field` ⇒ `SetSelectedField(value)`; `set-page` ⇒ `SetCurrentPDFPage` where `value` is a number or `'first'|'next'|'previous'|'last'` (current/total page fetched via `GetCurrentPDFPage`/`GetTotalPDFPage`).

| param property | type | required? | notes |
|---|---|---|---|
| `type` | 'download'\|'focus-field'\|'set-page' | yes | |
| `value` | any | for focus-field/set-page | field name, page number or keyword. |
| `includeHeaders` | boolean | no | declared on interface; not read by this service. |

Continuations: QUIRK — the service returns `metaFxEventAction.onSuccess` / `onError` (the raw arrays) cast to `IEpPluginEventResponse` instead of wrapping them in `successOrError`; missing param/service ⇒ proper `{successOrError: onError}`.

```json
{ "type": "pdf-viewer-action", "param": { "type": "set-page", "value": "next" }, "onSuccess": [], "onError": [] }
```

---

### `expression-editor`

Opens the Monaco expression editor in a sliding panel. `param` is the `IEpExpressionEditorModel` (deep-cloned; `param.readonly` parseValue'd to boolean). The service registers check-syntax and tree-node activity handlers that execute the metafx events referenced by `param.onCheckSyntaxEvent` / tree-node event hooks.

| param property | type | notes |
|---|---|---|
| `readonly` | boolean | parsed to boolean. |
| `onCheckSyntaxEvent` | event ref | metafx event executed on syntax check. |
| `onOk` / `onCancel` | action[] | **inside param** — branch when the sliding panel closes with Ok/Cancel. |
| (other IEpExpressionEditorModel fields: expression, bindings, language, etc.) | – | passed to the editor component. |

Continuations: editor status `valid` ⇒ ACTION `onSuccess` else ACTION `onError`; but when the panel returns an explicit Ok/Cancel action, `param.onOk`/`param.onCancel` is used with `success:false`. Response `{success, successOrError, lastResultSuccessValue: status.valid}`.

```json
{ "type": "expression-editor",
  "param": { "readonly": false, "expression": "{TransView.Formula}", "onOk": [], "onCancel": [] },
  "onSuccess": [], "onError": [] }
```

---

### `configurator-property-set`

Hidden-from-toolbox action used by the product configurator runtime. Parses `param` (`IErpConfiguratorPropertySet`; `pageSeq` and `inputFieldName` additionally parseValue'd) and fires the `ConfiguratorPropertiesSet` generic activity (sets configurator input control properties). Wrapped in a CONFIGURATOR_LOAD profiler timer.

| param property | type | notes |
|---|---|---|
| `pageSeq` | string | configurator page sequence. |
| `inputFieldName` | string | target input name. |
| (other IErpConfiguratorPropertySet fields, e.g. properties to set) | – | passed through parseObject. |

Continuations: none; always `{ success: true }`. `hide: true` (not shown in designer toolbox).

```json
{ "type": "configurator-property-set", "param": { "pageSeq": "1", "inputFieldName": "Color", "props": [{ "prop": "visible", "value": true }] } }
```

---

### `crystal-custom-report`

Prints or previews a custom Crystal report through the Edge Agent (`ErpEdgeAgentService`). `param` parseObject'd. `print` additionally pulls printer name / page settings / printer settings from the report parameter dataview (`ErpReportingConstants.reportParamViewId`). If the Edge Agent is not available the work reports `success:false` (⇒ onError). Unsupported `reportAction` values throw (designer enum also lists `design`, which the service does NOT handle — it will throw).

| param property | type | required? | notes |
|---|---|---|---|
| `reportAction` | 'print'\|'preview' ('design' designer-only, unsupported) | yes | |
| `reportTitle` | string | no | |
| `reportPath` | epBinding/string | yes | path to .rpt. |
| `reportUserID` | string | no | crystal credentials. |
| `reportPassword` | epBinding/string | no | |

Continuations: `result.cancelled` ⇒ `onFailure`; `result.success` ⇒ `onSuccess`; else ⇒ `onError`.

```json
{ "type": "crystal-custom-report",
  "param": { "reportAction": "print", "reportPath": "{ReportParam.RptDefFile}", "reportTitle": "Pack Slip" },
  "onSuccess": [], "onError": [], "onFailure": [] }
```

---

### `serial-read`

Reads from a client COM port. Only `subType` `'scale'` is supported (anything else throws). Prefers the Edge Agent scale-read (`requestReadWeightFromScale` with `port: 'COM'+port`); otherwise falls back to the browser Web Serial API (prompting the user to pick a port; retries the inquire command). The weight read is written to **`actionResult.Weight`**.

| param property | type | notes |
|---|---|---|
| `subType` | string | must be 'scale'. |
| `port` | string | COM port number. |
| `baudRate` | epBinding/number | |
| `parity` | string | |
| `stopBits` | epBinding/number | |
| `dataBits` | epBinding/number | |
| `timeOut` | epBinding/number (ms) | |
| `appendCR` | boolean | append `\r` to inquire message. |
| `inquireMsg` | string | command written to the scale. |

Continuations: `cancelled` (user dismissed port picker) ⇒ `onFailure`; success ⇒ `onSuccess`; failure ⇒ `onError`. Result context: `actionResult.Weight`.

```json
{ "type": "serial-read",
  "param": { "subType": "scale", "port": "3", "baudRate": 9600, "parity": "none", "stopBits": 1, "dataBits": 8,
    "timeOut": 2000, "appendCR": true, "inquireMsg": "W" },
  "onSuccess": [{ "type": "row-update", "param": { "epBinding": "TransView.Weight", "value": "{actionResult.Weight}" } }],
  "onError": [], "onFailure": [] }
```

---

### `usb-read`

Reads from a client USB HID device (scale) — WebHID/agent based, mirroring `serial-read`. Weight lands in **`actionResult.Weight`**.

| param property | type | notes |
|---|---|---|
| `subType` | string | device subtype (scale). |
| `vendorId` | string | USB vendor id filter. |
| `productId` | string | USB product id filter. |
| `uom` | string | unit of measure interpretation. |
| `usagePage` | number | HID usage page. |

Continuations: `cancelled` ⇒ `onFailure`; success ⇒ `onSuccess`; failure ⇒ `onError` (same pattern as serial-read, including the `onFailure`/`onSuccess` branches and the `actionResult.Weight` write).

```json
{ "type": "usb-read",
  "param": { "subType": "scale", "vendorId": "0x0922", "productId": "0x8004", "uom": "KG", "usagePage": 141 },
  "onSuccess": [], "onError": [], "onFailure": [] }
```

---

## Cross-cutting notes (traced, not guessed)
- `eventParamService.parseObject(x, [exclusions])` recursively token-substitutes every string property (`{View.Column}`, `%session.*%`, etc.); `parseValue` does the same for a single value with optional placeholder array. Actions noted above call one or both explicitly.
- Standard response contract (`IEpPluginEventResponse`): `success` (default next chain), `successOrError` (explicit continuation array to run), `lastResultSuccessValue` (feeds `{lastResult}` condition checks), `shouldCallNextAction` (only `search-show` sets it in this set), `value` (failure message).
- `actionResult` is a transaction-scoped dataview: rest-erp/rest write scalar `parameters`/`returnObj` there; erp-function writes the whole function result; search-show writes `searchCancelled`; serial/usb write `Weight`; credit-card writes `creditCardStatus`; kbmax writes `response`; pdf download writes `returnObj`; app-open (slideOut) replaces it with the child's `valueOut`.
- rest-erp/erp-function have NO pagination, header, progress/blockUi, queue or async options — anything documented elsewhere claiming those has not been observed to work.

---

## 2. Trigger system

An event's `trigger` object decides *when* it runs: `{"type": <TriggerType>, "target": <id-or-binding>, "hook": <Hook>, "columns": [...]?}`.

### 2.1 Trigger types (`MetaFxEventHookType`)

`EpBinding`, `Control`, `Window`, `DataView`, `DataTable`, `Grid`, `Page`, `Tree`, `EventID`, `Event`.

### 2.2 Hooks (`MetaFxEventHook`)

`onClick`, `onBlur`, `onLoad`, `onInit`, `columnChanged`, `columnChanging`, `rowChanged`, `rowChanging`, `viewChanged`, `viewChanging`, `onEpPanelCardCollapsed`, `onEpPanelCardExpanded`, `onSearch`, `onDataDropDownClick`, `epOnClickAdd`, `onClosing`, `onClosed`, `onTreeNodeExpand`, `onTreeNodeSelectionChange`, `onTreeDropItem`, `onTreeDragEnter`, `onTreeBeforeExpandAll`, `onBroadcastData`, `before`, `after`, `override`.

### 2.3 Verified trigger combinations

| Purpose | Trigger |
|---|---|
| Button click | `{"type":"Control","target":"<componentId>","hook":"onClick"}` |
| Bound control / link click | `{"type":"EpBinding","hook":"onClick","target":"<binding>"}` (very common in base apps) |
| Field changed (one or more columns) | `{"type":"DataTable","target":"<TableName>","hook":"columnChanged","columns":["Col1","Col2"]}` (also `columnChanging`) |
| Row / view change | `{"type":"DataView","target":"<ViewId>","hook":"rowChanged\|rowChanging\|viewChanged\|viewChanging"}` |
| Component init | `{"type":"Control","hook":"onInit","target":"<id>"}` |
| App load (dashboards auto-run BAQ) | `{"type":"Window","hook":"onLoad"}` |
| Cross-app broadcast received | `{"type":"Window","hook":"onBroadcastData"}` (pairs with `apps-communicator-publish`) |
| Grid cell/row click (drill-in) | `{"type":"Grid","hook":"onClick","target":"<grid>"}` |
| Grid paste hooks | `{"type":"Grid","hook":"beforePaste"\|"afterPaste"}` |
| Dropdown-in-grid open | `{"type":"DataView","hook":"onDataDropDownClick"}` |
| Tree apps | `{"type":"Tree","hook":"onTreeNodeExpand"\|"onTreeNodeSelectionChange"\|"onTreeBeforeExpandAll"}` |
| Override a system event | `{"type":"Event","hook":"override","target":"AfterGetByID"}` |
| Run after a system event | `{"type":"Event","hook":"after","target":"<SystemEvent>"}` |

### 2.4 Critical trigger behaviors (VERIFIED on a live server — see lessons-learned.md)

- **`AfterGetByID`** is the canonical "record finished loading" hook. Base ships it with empty actions, so overriding it costs nothing.
- **There is NO `onChange` hook.** It fails silently — use `columnChanged`.
- **The field search icon (`enableSearch:true`) wiring is `{"type":"EpBinding","hook":"onClick","target":"<DataView.Column>"}`** — EpBinding type, `onClick` hook, target = the field's data binding. This is the confirmed-correct wiring after many wrong turns:
  - `Control/onSearch` and `Control/onClick` → do NOT attach to the search icon (no fire).
  - `EpBinding/onSearch` → attaches but fires on *every* column change (typing) and loops.
  - When wired correctly, App Studio shows an **ellipsis** on "On Search Click"; a **`+`** means nothing is attached.
- **When to add a custom search event at all:** a field bound to a *base searchable field* (e.g. `OrderDtl.ProjectID`) fires the framework's native `onClick` search automatically with just `enableSearch:true` — do NOT add a custom event (it double-fires). A field bound to a *custom `_c` field* with no native search needs both `enableSearch:true` and the custom `EpBinding/onClick` event running `search-show` + column-suppressed `search-value-set`.
- **An `EpBinding` trigger whose target is a data column acts as a column-change listener** — it fires on every change to that column, not just clicks. This is why writing back to the same binding an event watches causes re-entrancy; bracket the write with `event-column-disable`/`event-column-enable`.
- **A `DataTable` trigger's `target` is the TABLE id, not the dataview id** (FIELD-PROVEN): `{"type":"DataTable","target":"SearchFilterTbl","hook":"columnChanged",...}` fires; targeting the *view* id (`SearchFilter`) means the event **never fires** — silently. For a client filter dataview, that's the `table` property of the dataview definition, not its `id`. (Same table-vs-view distinction as `event-column-disable` below.)
- **`event-column-disable`/`event-column-enable` shape** — the runtime reads **`dataTable` as a TOP-LEVEL property of the action** (see the §1 catalog entry): `{"type":"event-column-disable","dataTable":"OrderHed"}` … `{"type":"event-column-enable","dataTable":"OrderHed"}`. `dataTable` = the view of the field being set. The lessons file records a `param.dataTable` wrapper as "working" — it is NOT actually read; it falls into the else-branch and disables column events on **ALL** dataviews (stops the loop, but with far wider blast radius). A top-level `dataview` key is a no-op (wrong key name). Prefer top-level `dataTable`.

## 3. Token / expression substitution engine

The engine substitutes tokens in action params before executing, then (for `condition`/`switch`) evaluates the result as JavaScript.

| Token | Meaning |
|---|---|
| `{View.Column}` | a dataview field value. **Curly braces, always**, for view fields. |
| `%value%`, `%oldValue%`, `%row%` | special values in column/row triggers |
| `%currentDataView%` | the view that fired the current event |
| `%dataset.<View>.hasChanges%` | dataset state |
| `%session.userId%`, `%session.companyId%`, `%session.company%` | session values |
| `%svc%`, `%systemCode%`, `%datasetId%`, `%tableName%`, `%serverDataset%`, `%keyFieldSearchName%`, `%keyFieldSearchForm%`, … | **patch constants** — app-level values defined in `patch.jsonc` |
| `{{strings.SomeKey}}` | a localized caption from `strings.jsonc` |
| `#_  raw JS  _#` | escape to raw JavaScript inside an expression |
| `searchResult.<Col>` | a column of the row the user picked in a `search-show`; valid inside that search's `onSuccess` (e.g. `search-value-set value:"searchResult.ProjectID"`) |
| `actionResult.<x>` | the result of the immediately preceding action (rest-erp writes `parameters`/`returnObj`; erp-function writes its result; search-show writes `searchCancelled`) |

Three families resolve `%...%`: fixed specials (`value`/`row`/`oldValue`/`currentDataView`), namespaced `session.*`/`dataset.*`, and **patch constants** (any `id` in `patch.jsonc`). `%View.Column%` (percent around a view field) is **none of these** → `Invalid session value`; use `{View.Column}` for view fields.

**Double-evaluation trap (VERIFIED):** the rule/event engine evaluates the *result* of a `#_ … _#` raw-JS expression a second time as code.
- A bare `#_ new Date().toISOString() _#` throws `SyntaxError: Invalid or unexpected token` (the returned date string is evaluated again). Fix: wrap in quotes so the second pass sees a string literal: `'#_ new Date().toISOString() _#'`.
- Toggling a boolean works: `#_ !{OrderHed.ReadyToCalc} _#`. After mutating a BO field via `row-update`, also set `RowMod = "U"` so the row is dirty for the next Save.

Inside `condition`/`switch` expressions the engine builds `Function('context','trans','user','return <expr>')`, so `context`, `trans` (transaction service) and `user` are in scope after substitution. The debug console prints the substituted expression literally, so mistakes are obvious.

## 4. Event object schema & chaining

```json
{"id":"MyEvent","mode":"A","customizable":true,"disable":false,"trigger":{...},"actions":[...]}
```

- **`"mode":"A"`** = a NEW event. `"mode":"U"` marks it an overlay of a base event → App Studio shows it **locked** and it behaves wrong. Always `"A"` for your own events. (`"D"` = deleted/removed overlay.)
- The disable key is **`disable`** on events, **not** `disabled` (rules use `disabled` — do not mix them up).
- **`customizable:true`** or you can't edit it in App Studio (it shows locked).
- Actions run in array order. Each action may carry continuation arrays: `onSuccess`, `onError`/`onFailure`, and dialog branches `onOk`/`onCancel`/`onYes`/`onNo`/`onNone`/`onAbort`/`onRetry`/`onIgnore`/`onEmpty`.
- **Chaining:** `event-next` (`{"type":"event-next","value":"OtherEvent"}`) chains to another event by id and continues; `event-complete` (`{"param":{"nextEvent":"X"}}`) completes the current event then runs the named one. Prefer chaining into an existing stock event (e.g. `Update`, `Refresh`, `GetNew`) over hand-rolling its effect.
- **Prefer calling existing events:** to auto-save, use `event-next` into the app's built-in Save/`Update` event rather than a bare `data-commit` (a stray `data-commit` in a custom event has broken Save). The toolbar Save event already handles the commit correctly.

## 5. Contradictions / corrections vs the old reference & lessons

- The `value-set` and `image-set` types appear in the `MetaFxEventType` union but have **no registered action class**. `value-set` is only interpreted inside the search flow (consumed by the search handler, not the action registry); `image-set` has no implementation — treat as obsolete. (The old reference listed `value-set`/`image-set` among "remaining action ids"; they are not general-purpose actions.)
- rest-erp/erp-function have **no** pagination, header, progress/blockUi, queue, or async options — anything claiming those has not been observed to work.
- `event-column-disable` reads a **top-level `dataTable`** on the action (not `param.dataTable`, and not `dataview`) — see §1 catalog and §2.4. The lessons file's `param.dataTable` is silently ignored and degrades to disabling ALL views.
- The search icon hook is `onClick` (EpBinding), not `onSearch` (see §2.4) — this corrects the old reference's §7.2 table which listed `EpBinding/onSearch` as "the search icon on a field."
