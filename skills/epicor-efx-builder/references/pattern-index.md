<!-- Pattern & widget decision guide — part of the epicor-efx-builder skill. Self-contained: it names no libraries. -->

# Pattern and widget decision guide

Use this to pick the function kind and the construction pattern from the task itself. Every pattern named here has a written template in one of the other reference files — you never need a live library to copy from. (You *may* still export a live function as an optional sanity check, but it is not a prerequisite.)

## Choose the function kind

| The task… | Build it as | Why |
|---|---|---|
| runs logic, calls one or more BOs, reads/writes data, integrates externally, branches, loops | **Kind 2 custom code** | Fully templated in [§5](custom-code-functions.md); most flexible; branching/looping are trivial in C#. |
| must be maintained by a non-developer in the designer, or the shop standard is visual | **Kind 1 visual** | Templated in [§6](visual-functions.md); but it is XAML-prefix-sensitive — prefer the scaffold or clone a live node, and prove it with a Testing import. |
| is mostly one BO call or a couple of designer steps | **Kind 1 visual** with `InvokeBOMethodAction2` | Matches the four proven widgets in [§6.3](visual-functions.md). |
| needs branching/looping but must stay "visual" | **Kind 1 with a `CustomCodeAction` widget** | Keeps the graph shell but does the logic in C#; avoids unproven Decision-widget XML. |

## Pick the custom-code pattern (Kind 2 — see [§5](custom-code-functions.md))

| Intent | Pattern | Key refs to add |
|---|---|---|
| Create/update/delete an Epicor record with business rules | `CallService<...SvcContract>` + `GetNew`/`GetByID` → set → `Update` | type-2 BO (and/or type-0 dll) |
| Read Epicor data, no writes | LINQ over `Db.<Table>` scoped by `Session.CompanyID` | type-1 table(s); `DirectDBAccess` ≥ 1 |
| Set a UD/flag field the BO won't let you set | `Db` write inside `IceContext.CreateDefaultTransactionScope()` + `SaveChanges()` | type-1 table `Updatable:true`; `DirectDBAccess:2` |
| Reuse another function's logic | `this.ThisLib.<Fn>` (same lib) / `this.EfxLib.<Lib>.<Fn>` (other lib) | type-3 for `EfxLib` only |
| Call an external system | `HttpClient` + `HttpRequestMessage` + Newtonsoft JSON | type-0 `Newtonsoft.Json.dll` |
| Run a BAQ / UBAQ | `CallService<Ice.Contracts.DynamicQuerySvcContract>` → `ExecuteByID`/`GetListByID` | type-2 `ICE:BO:DynamicQuery` |
| Produce a report PDF | report `SvcContract` → `GetNewParameters` → `RunDirect`/`SubmitToAgent` | type-2 report + `ICE.SysRptLst`/`ICE.SysTask` |
| Long / deferred work | enqueue via `ScheduledFunctionSvcContract.SubmitToAgent` | type-2 `ICE:Proc:ScheduledFunction` |
| Surface a business error | throw `Ice.BLException("…")` | none |

Never use raw ADO.NET / `SqlCommand` — see the prohibited-SQL rule in [§5.9](custom-code-functions.md).

## Pick the visual widget (Kind 1 — see [§6](visual-functions.md))

| Intent | Widget | Notes |
|---|---|---|
| Call a BO method | `ilbma:InvokeBOMethodAction2` | Bind params to a signature arg (`VariableBindingTarget`) or an expression; result to a directive variable. |
| Arbitrary C# in the graph | `ilbma:CustomCodeAction` | Needs `AllowCustomCodeWidgets:true`; usings in `AdditionalUsings`. |
| Set an output/variable | `ilbma:SetArgumentAction` | Expression via `ExpressionDefinition Text="…"`. |
| Bulk-set columns on queried rows | `ilbma:UpdateTableByQueryAction` | Intricate `QueryDefinition` — clone a live one. |
| Branch / condition, send mail, raise exception, invoke another EFX, fill table, etc. | *not templated here* | Do it in a `CustomCodeAction`/Kind 2 function, or clone the exact node XML from a live function and prove by Testing import. |

## Reliability ladder (most to least certain to compile)

1. Kind 2 custom code assembled from [§5](custom-code-functions.md) — self-sufficient from this skill.
2. Kind 1 from `scripts/efx_package.py scaffold --kind 1`, extended with the four proven widgets — validate, then Testing import.
3. Kind 1 using a widget cloned from a live function's exact XML — Testing import.
4. Hand-authored exotic widget XML — avoid; use option 1 or 3 instead.
