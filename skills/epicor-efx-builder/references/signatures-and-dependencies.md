<!-- Signatures, data types, references, mappings — part of the epicor-efx-builder skill. Section numbers match SKILL.md. -->

## 4. Function signatures and data types

`FunctionSignature` is an array of parameter objects:

```jsonc
{"Response": false, "ParameterID": 1, "ArgumentName": "iKey", "Order": 1,
 "DataType": "System.Int32", "Optional": false, "Description": ""}
```

Rules:
- `Response`: `false` = request/input, `true` = response/output. Inputs and outputs have **independent** `ParameterID` and `Order` sequences (each usually starts at 1).
- **Naming is directional and required for newly built or renamed arguments:** every input starts with `i` (`iFoo`, `iBar`) and every output starts with `o` (`oTee`, `oTah`). This avoids collisions with generated members, reserved identifiers, and existing runtime properties. Update all body/widget bindings when renaming. Preserve an untouched legacy signature during an unrelated edit rather than expanding scope solely to rename it.
- **Allowed characters — letters and digits only.** An `ArgumentName` may contain only `a-z`, `A-Z`, and `0-9`. No underscores, spaces, hyphens, dots, or any other punctuation, and it must start with a letter (which, with the rule above, means `i` or `o`). Epicor rejects an input/output parameter whose name contains anything else. So `iCustNum` and `oOrderCount2` are valid; `i_CustNum`, `oOrder-Count`, `oOrder.Count`, and `o Order` are not.
- `ParameterID` and `Order` must be **unique within their direction**. Keep `Order` deterministic.
- `ArgumentName` is the code/widget argument name and becomes a field on the function (`this.<ArgumentName>`). Follow the required `i*`/`o*` direction prefix and the letters-and-digits-only rule above.
- `Optional` and `Description` are always present in current exports (`Description` may be `""`).
- A null `FunctionSignature` is **not** the same as an empty array; preserve the exported representation unless intentionally defining a signature.

**Scalar types**: `System.String`, `System.Boolean`, `System.Int32`, `System.Int64`, `System.Decimal`, `System.Guid`, `System.DateTime`, and the nullable forms `System.Int32?`, `System.Boolean?`, `System.Decimal?`, `System.DateTime?`, `System.Int64?`. Prefer nullable types for optional dates/numbers and use `.Value` / `??`.

**Complex types** (`System.Data.DataSet`, or a strongly-typed tableset such as `Erp.Tablesets.SalesOrderTableset`, `Ice.Tablesets.QueryExecutionTableset`) require a matching assembly/BO reference (§7) and add a `DataTypeInfo` field on the parameter — a **JSON-encoded string**:

```jsonc
"DataTypeInfo": "{\"wellknownType\":2,\"namespace\":\"Ice.Tablesets\",\"name\":\"QueryExecutionTableset\",\"assembly\":\"Ice.Contracts.BO.DynamicQuery\",\"options\":2}"
```

`wellknownType`: `1` = Basic scalar, `2` = Tableset (`0`/`Unknown` for a generic like `Dictionary<...>`). `options` mirrors it (`1` basic, `2` tableset/complex). The visual `ecm:TypeRefData` (§6.4) carries the same information but as **named** attributes (`WellknownType="Basic"|"Tableset"|"Unknown"`) rather than the numeric JSON form here.

When a name, direction, type, or order changes, update every code/widget binding that used it. Preserve untouched parameter objects byte-for-byte where practical; require unique IDs and orders.

---

## 7. References, mappings, and dependency reconciliation

### 7.1 `LibraryReferences`

Each entry: `{ "ReferenceType": <n>, "ReferenceID": "<id>" }` (type 1 also carries `"Updatable": <bool>`).

| Type | Meaning | `ReferenceID` shape |
|---|---|---|
| 0 | Assembly (DLL) | `Newtonsoft.Json.dll`, `Erp.Contracts.BO.SalesOrder.dll`, `Ice.Contracts.BO.DynamicQuery.dll` |
| 1 | Database table | `ERP.<Table>` / `ICE.<Table>` (+ `Updatable`) — UD tables `ERP.<Name>_c` |
| 2 | BO / report / proc / lib service | `ERP:BO:<BO>`, `ICE:BO:<BO>`, `ERP:Rpt:<Rpt>`, `ERP:UD:<Name>_c`, `ICE:Proc:<Proc>`, `ICE:Lib:<Lib>` |
| 3 | Epicor Function Library | `<LibraryID>` |

Add the narrowest required reference; avoid duplicates. Mark a table `Updatable:true` only when the code actually writes it via `Db`. Removing a reference requires proving no code, widget, type, or signature uses it.

### 7.2 `LibraryMappings`

Entries are `{ "Company": "<Company>", "Allowed": <bool> }` — which companies may run the library. Preserve all mappings on ordinary edits. When creating a library, derive mappings from the target environment and intended company availability; never copy a Production company mapping blindly into Testing or another tenant.

### 7.3 Reference checklist (derive from what you wrote)

| If the function contains | Add |
|---|---|
| `Db.<Table>` read | type 1 `ERP.<Table>`/`ICE.<Table>` (`Updatable:false`); `DirectDBAccess` ≥ 1 |
| `Db.<Table>` write + `Db.SaveChanges()` | same, `Updatable:true`; `DirectDBAccess:2` |
| `CallService<...SvcContract>` / `InvokeBOMethodAction2` | type 2 `ERP:BO:<BO>`/`ICE:BO:<BO>` (and/or type 0 dll) |
| UD BO `<Name>_cSvcContract` | type 2 `ERP:UD:<Name>_c` (+ type 0 dll) |
| Report contract | type 2 `ERP:Rpt:<Rpt>` / `ICE:Rpt:BAQReport` (+ type 0 dll) |
| `ScheduledFunctionSvcContract` / process set | type 2 `ICE:Proc:ScheduledFunction` / `ICE:Proc:SchedProcSet` (+ dll) |
| `this.EfxLib.<Lib>` | type 3 `<Lib>` (target Published, function Public) |
| `this.ThisLib` | nothing |
| `JsonConvert` / `JObject` / `JArray` | type 0 `Newtonsoft.Json.dll` |
| `Ice.Core.WriteTaskLog` | type 0 `Ice.Core.TaskBase.dll` + type 1 `ICE.SysTask` |
| `System.Diagnostics.EventLog` | type 0 `System.Diagnostics.EventLog.dll` |
| any Kind 2 function | library `AllowCustomCodeFunctions:true` |
| a Kind 0 visual function (standard widgets only) | nothing — `AllowCustomCodeWidgets` may stay false (verified by live import) |
| a Kind 1 visual function (contains a `CustomCodeAction`) | library `AllowCustomCodeWidgets:true`; the widget's usings go in `DirectiveDefinition2.AdditionalUsings`, assemblies in `AdditionalReferences` |
| `HttpClient`, `System.IO`, `System.Text`, LINQ, `Ice.Diagnostics.Log`, `Ice.Mail` | nothing extra (framework/runtime) |

Final sanity pass: every `Db.X` → a type-1 row; every `*SvcContract`/BO method → a type-2 (or type-0) row; every `EfxLib.X` → a type-3 row; every `Newtonsoft` → the dll; every non-implicit namespace → a `using` line joined with `\r\n`; no direct SQL; outputs assigned on every path; a `Company` predicate on every `Db` query.

---
