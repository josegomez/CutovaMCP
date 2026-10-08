<!-- Custom-code (Kind 2) functions — part of the epicor-efx-builder skill. Section numbers match SKILL.md. -->

## 5. Custom-code (Kind 2) functions

Parse the string `Body` as JSON to get `{ "Code", "Usings" }`; edit each independently, reserialize once, assign back to `Body`. Prefer a narrow edit over reformatting a whole method. Preserve line endings, unrelated text, error handling, transaction boundaries, and disposal patterns unless the request targets them.

### 5.1 Signature binding

Every argument is a field: read inputs as `this.<InputArg>` (the `this.` is optional), assign outputs as `this.<OutputArg> = ...`. Outputs are pre-initialized to defaults (`false`/`0`/`null`/`""`); `return;` ends the function returning whatever is assigned so far.

```csharp
// inputs: iKey (Int32); outputs: oSuccess (Boolean), oMessage (String)
this.oSuccess = false;
if (iKey <= 0) { oMessage = "invalid key"; return; }
try { /* work */ oSuccess = true; }
catch (Exception ex) { oMessage = ex.Message; }
```

`System.Data.DataSet` in/out: read `InDS.Tables["<T>"].Rows`; build outputs with `new DataSet()` + `new DataTable("<T>")` + `Columns.Add("<Col>", typeof(...))` + rows + `Tables.Add(t)` + `t.AcceptChanges()`, `DBNull.Value` for nulls. Typed tableset in: `this.<Arg>.<Table>.FirstOrDefault()`; out: `this.oTS = svc.GetByID(key)`.

### 5.2 The `Usings` field

A **single string** of `using X;` lines joined by `\r\n` (CRLF); empty string when none.

Implicitly available (never listed): `System`, `System.Linq`, `System.Data`, `System.Collections.Generic`, `Ice`, `Ice.Common` (`BLException`), `Ice.Tablesets`, `Ice.Contracts`, `Erp`, and the Function runtime (`Session`, `Db`, `CallService`, `ThisLib`, `EfxLib`, `callContextClient`, `BufferCopy`, `IceRowState`, `IceContext`, `ErpContext`).

Must be listed (or fully qualified) — each with the assembly reference it implies (§7):

| You use | Add using | Assembly ref (type 0) |
|---|---|---|
| `StringBuilder`, `Encoding` | `System.Text` | — |
| `Regex` | `System.Text.RegularExpressions` | — |
| `File`, `Path`, `Stream`, `MemoryStream` | `System.IO` | — |
| `Thread.Sleep` | `System.Threading` | — |
| `CultureInfo`, `NumberStyles` | `System.Globalization` | — |
| `HttpClient`, `HttpRequestMessage`, `StringContent` | `System.Net.Http` (+ `System.Net.Http.Headers`) | — |
| `JsonConvert`, `JsonSerializerSettings` | `Newtonsoft.Json` | `Newtonsoft.Json.dll` |
| `JObject`, `JArray`, `JToken` | `Newtonsoft.Json.Linq` | `Newtonsoft.Json.dll` |
| `<X>Tableset` / `<X>Row` from Erp | `Erp.Tablesets` | BO contract ref (§7) |
| `EventLog`, `TraceEventType` | `System.Diagnostics` | `System.Diagnostics.EventLog.dll` (EventLog only) |
| `WriteTaskLog` | `Ice.Core` | `Ice.Core.TaskBase.dll` |

### 5.3 Calling a Business Object

```csharp
this.CallService<Erp.Contracts.<BO>SvcContract>(svc =>
{
  var ts = new Erp.Tablesets.<BO>Tableset();          // or: var ts = svc.GetByID(key);
  svc.GetNew<Table>(ref ts /*, parent keys */);        // adds a row with RowMod "A"
  var row = ts.<Table>.FirstOrDefault(r => r.Added()); // or ts.<Table>[0]
  row.<Field> = value;
  svc.OnChange<Field>(ref ts);                          // "change" methods re-default dependents; call in UI order
  // row.RowMod = "U";  // only on rows you edit AFTER a GetByID; GetNew rows are already "A"
  svc.Update(ref ts);
  this.oKey = row.<GeneratedKey>;                       // read back after Update
});
```

- **Contract naming**: `Erp.Contracts.<BO>SvcContract` / `Ice.Contracts.<BO>SvcContract`. UD BOs use the `_c` suffix (`Erp.Contracts.<Name>_cSvcContract`, tableset `Erp.Tablesets.<Name>_cTableset`). Reports: `Erp.Contracts.<Rpt>SvcContract`.
- The lambda parameter is the service proxy; `CallService` disposes it — no explicit `Dispose()`. Nesting `CallService` is fine.
- **Row state**: `RowMod` `"A"`/`"U"`/`"D"`/`""`; helpers `row.Added()/Updated()/Deleted()/Unchanged()`, `row.SetRowState(IceRowState.Added|Deleted)`.
- **UD (`_c`) fields**: on a typed tableset row use the indexer or helpers — `row["Flag_c"] = true;` / `row.SetUDField<bool>("Flag_c", true);` / `(bool)row.UDField<bool>("Flag_c")` (a direct `row.Flag_c` property may not exist on the base tableset). On a `Db` entity, UD columns are plain properties (`dbRow.Flag_c`).
- **Delete**: `var ts=svc.GetByID(key); ts.<Head>.FirstOrDefault().SetRowState(IceRowState.Deleted); svc.Update(ref ts);`
- **Buffer-copy idiom** — needed only for BOs that validate an old-vs-new row pair (order/quote/task-style transactional BOs, e.g. SalesOrder, Quote, JobEntry, Task). For most maintenance BOs the plain path (`GetByID` → set field → `RowMod="U"` → `Update`) is correct. When unsure which a BO needs, use the plain path and confirm by a **Testing import + a live call**; if `Update` throws a "record has been changed"/row-not-found style error, switch to buffer-copy:
  ```csharp
  var ts = svc.GetByID(key);
  var live = ts.<Table>.FirstOrDefault();
  var copy = new Erp.Tablesets.<Table>Row(); BufferCopy.Copy(live, copy); ts.<Table>.Add(copy);
  live.<Field> = value; live.RowMod = "U"; svc.Update(ref ts);
  ```
- **Change company/plant**: `using (CallContext.Current.TemporarySessionCreator.SetCompanyID(c).SetPlantID(p).Create()) { ... }`.
- **References**: a type-2 service ref `ERP:BO:<BO>` / `ICE:BO:<BO>` (or `ERP:UD:<Name>_c`, `ERP:Rpt:<Rpt>`, `ICE:Proc:<Proc>`) and/or the type-0 dll `Erp.Contracts.BO.<BO>.dll`. Add the type-2 service ref and also the type-0 dll when you name tableset/row types.

### 5.4 Cross-library calls

```csharp
var r1 = this.ThisLib.<Fn>(a, b);            // same library (public or private function) — no reference needed
var r2 = this.EfxLib.<LibraryID>.<Fn>(a, b); // another library — needs a type-3 reference; target lib Published, function Public
```

Arguments are positional in the request-param `Order`. Return shape: one output → returned directly; two+ outputs → an object with a property per output name (`r.oSuccess`); zero outputs → void.

### 5.5 Direct data reads (LINQ over `Db`)

```csharp
var head = Db.<Table>.Where(x => x.Company == Session.CompanyID && x.<Key> == iKey).FirstOrDefault();
bool exists = Db.<Table>.Any(x => x.Company == Session.CompanyID && x.<Key> == iKey);
var q = (from a in Db.<A>
         join b in Db.<B> on new { a.Company, a.Key1 } equals new { b.Company, b.Key1 } into bg
         from b in bg.DefaultIfEmpty()                       // left join
         where a.Company == Session.CompanyID
         select new { a.Key1, Name = b != null ? b.<Col> : "" }).ToList();
```

- **Always scope by company** (`Session.CompanyID`, or `callContextClient.CurrentCompany`). Also available: `Session.UserID`, `Session.PlantID`, `Session.EmployeeID`.
- Each `Db.<Table>` needs a **type-1** reference `ERP.<Table>` / `ICE.<Table>` (`Updatable:false` for reads); library `DirectDBAccess` ≥ 1.
- **Direct writes** (only for UD/flag fields the BO fights): set `Updatable:true`, `DirectDBAccess:2`, and
  ```csharp
  using (var tx = IceContext.CreateDefaultTransactionScope())
  { var row = Db.<Table>.Single(...); row.<Field_c> = v; Db.SaveChanges(); tx.Complete(); }
  ```
- **Fresh contexts** for helper libs: `Ice.Services.ContextFactory.CreateContext<ErpContext>()` / `<IceContext>()`.

### 5.6 External REST integration

Usings: `System.Net.Http`, `System.Net.Http.Headers`, `System.Text`, `Newtonsoft.Json`, `Newtonsoft.Json.Linq`. Ref: `Newtonsoft.Json.dll`.

```csharp
Func<Exception,string> describe = ex => {           // .Result wraps failures in AggregateException
  var agg = ex as AggregateException;
  return agg != null
    ? string.Join(" | ", agg.Flatten().InnerExceptions.Select(i => i.GetType().Name + ": " + i.Message))
    : ex.GetType().Name + ": " + ex.Message; };
try {
  string raw;
  using (var client = new HttpClient())
  {
    client.Timeout = TimeSpan.FromSeconds(60);
    using (var req = new HttpRequestMessage(HttpMethod.Post, "<url>"))
    {
      req.Headers.Add("<header-name>", "<header-value>");
      req.Content = new StringContent(JsonConvert.SerializeObject(new { a = this.iA }), Encoding.UTF8, "application/json");
      var resp = client.SendAsync(req).Result;
      raw = resp.Content.ReadAsStringAsync().Result;
      if (!resp.IsSuccessStatusCode)
        throw new Exception(string.Format("call failed {0} {1}", (int)resp.StatusCode, resp.ReasonPhrase));
    }
  }
  var root = JToken.Parse(raw ?? "{}");
  if (root.Type == JTokenType.String) root = JToken.Parse(root.ToString()); // double-encoded payloads
  var obj = root as JObject;
  string v = obj?["<prop>"]?.ToString();
  this.oSuccess = true;
}
catch (Exception e) { this.oSuccess = false; this.oMessage = describe(e); }
```

Functions are synchronous — use `.Result`. Two-step login-then-call (first POST returns a token, second request adds it as a header) is common. Keep URL/credentials in a config table or a separate function, never inline.

### 5.7 Transactions and errors

- `RequireTransaction` is almost always `false`; set `true` only when several BO `Update`s must be atomic and you are not managing scope yourself (a function under `RequireTransaction` should not call REST/sleep while holding locks). `SingleRowMode` stays `false` for code functions (it matters only for UBAQ/dashboard row actions).
- Canonical output pattern: an `oSuccess`-style `bool` + an `oMessage`-style `string` + optional `oInfo`-style output. All output names must begin with `o`, matching §4. Throw `Ice.BLException("<msg>")` (a.k.a. `BusinessLayerException`) for a user-facing business error; `throw;` to rethrow from an inner lambda. Accumulate multi-step messages with `StringBuilder` and assign once.
- Logging: `Ice.Diagnostics.Log.WriteEntry(msg)` (server log, no refs). A shared logging library is typically called via `this.EfxLib.<LoggingLib>.<Fn>(...)` wrapped in `#if DEBUG … #endif`. Never log secrets, auth headers, or full external responses.

### 5.8 BAQ / report / scheduling (from code)

Run a BAQ — refs `ICE:BO:DynamicQuery` and/or `Ice.Contracts.BO.DynamicQuery.dll`:

```csharp
this.CallService<Ice.Contracts.DynamicQuerySvcContract>(dq =>
{
  var qets = dq.GetQueryExecutionParametersByID("<BAQID>");
  var p = qets.ExecutionParameter.FirstOrDefault(x => x.ParameterID == "<ParamID>");
  if (p != null) p.ParameterValue = iValue.ToString();
  var ds = dq.ExecuteByID("<BAQID>", qets);   // UBAQ: dq.GetListByID("<BAQID>", qets, 0, 0, out bool more)
  foreach (System.Data.DataRow r in ds.Tables["Results"].Rows) { var v = r["<Alias>"]; }
});
```

Report to PDF: `CallService<Erp.Contracts.<Rpt>SvcContract>` → `GetNewParameters()` → set `<Rpt>Param[0]` (`AgentID`, `ReportStyleNum`, `SSRSRenderFormat`, key, and a `TaskNote` GUID token) → `RunDirect(ts)` (sync) or `SubmitToAgent(...)` (async); read bytes back by joining `Db.SysRptLst`/`Db.SysTask` on the `TaskNote` token (type-1 refs `ICE.SysRptLst`, `ICE.SysTask`). Schedule another function via `Ice.Contracts.ScheduledFunctionSvcContract` (ref `ICE:Proc:ScheduledFunction`) with `ParameterValues = JsonConvert.SerializeObject(dict)` then `SubmitToAgent`.

### 5.9 Prohibited: direct SQL

Never create, extend, copy, or recommend a function that executes SQL through `SqlCommand`, `SqlConnection`, `DbCommand`, `IDbCommand`, provider-specific command/connection classes, `CreateCommand`, `ExecuteSqlCommand`, or any raw ADO.NET execution — even if a live function (especially in an `Internals`-style library) shows a working example. Use a BO service (business rules/updates), a BAQ/DynamicQuery (query-shaped reads), or Epicor's supported `Db`/LINQ context. If an unrelated edit encounters legacy direct SQL, preserve it exactly, flag the risk without revealing values, and keep the change outside that code.

---
