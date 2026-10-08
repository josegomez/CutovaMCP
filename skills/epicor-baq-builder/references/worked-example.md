# Worked example: SQL statement → imported BAQ

This is the exact translation performed and verified live (BAQ `GetSalesRepsTest2`). Follow the same steps for any SQL-to-BAQ request.

## The input

```sql
SELECT SysUserFile.EMailAddress, SalesRep.Territory_c, SysUserFile.Name
FROM dbo.SalesRep
INNER JOIN erp.SaleAuth  ON SalesRep.Company = SaleAuth.Company AND SalesRep.SalesRepCode = SaleAuth.SalesRepCode
INNER JOIN erp.UserComp  ON SaleAuth.Company = UserComp.Company AND SaleAuth.DcdUserID  = UserComp.DcdUserID
INNER JOIN ice.SysUserFile ON SysUserFile.userid = UserComp.DcdUserID
WHERE SalesRep.RoleCode IN ('SA','SM','DM') AND SalesRep.Inactive = 0 AND SalesRep.ExternalRepID_c <> ''
GROUP BY SysUserFile.EMailAddress, SalesRep.Territory_c, SysUserFile.Name
```

## Step 1 — Resolve every table and field against the dictionary

Do not trust the SQL's schemas, casing, or field names; users write loose SQL. Verify with the tools:

- `zDataTable filter: ZDataTable_DBTableName eq 'SysUserFile'` → physical table `Ice.SysUserFile`, dictionary DataTableID `UserFile`. (Dictionary IDs ≠ physical names sometimes; the QueryTable row uses the PHYSICAL schema/name: `Ice`/`SysUserFile`.)
- `zDataFields (ERP, SalesRep)` → `InActive` is bit (user wrote "Inactive"); `RoleCode`, `SalesRepCode` nvarchar. No Territory_c here...
- `zDataFields (ERP, SalesRep_UD)` → `Territory_c` nvarchar x(8), `ExternalRepID_c` **int** (so `<> ''` really means `<> 0`). CAVEAT (learned later): this example referenced `_c` fields on the base table, which the designer tolerates — but the layer/grid runtime does NOT. The correct form is a hidden `SalesRep_UD` extension table (TableType=UD, SysRowID=ForeignSysRowID FK) with every `_c` reference through it — see anatomy section 5 and the `ud_table()` helper.
- `zDataRelationships (ERP, SalesRep, child SaleAuth)` → join pairs Company=Company, SalesRepCode=SalesRepCode. The UserComp→SysUserFile join isn't in the dictionary — write `DcdUserID = UserID` manually.
- `dbo.` schema in user SQL on an internal BAQ = `Erp`/`Ice`.

## Step 2 — Map to rows

- 4 `QueryTableDesigner` rows: SalesRep(1), SaleAuth(2), UserComp(3) in `Erp`; SysUserFile(4) in `Ice`. (Plus the template's `Calculated` TT row, kept.)
- 3 `QueryRelationDesigner` + 5 `QueryRelationFieldDesigner` rows (2+2+1 ON pairs), each relation gets a new GUID.
- 3 `QueryFieldDesigner` rows, Seq 1-3, Alias `Table_Field`.
- 3 criteria on SalesRep, all **`CriteriaType=2` (Table Criteria)**, Seq 1/2/3, AndOr ''/And/And:
  1. `RoleCode IN` → `IsConst=false`, `RValue=_where-<unique number>` + 3 `QueryValueSetItemsDesigner` rows (SA/SM/DM)
  2. `InActive = false` (bit)
  3. `ExternalRepID_c <> 0` (int — `<>` must be XML-escaped as `&lt;&gt;`)
- 3 `QueryGroupByDesigner` rows: Expressions `SysUserFile.EMailAddress`, `SalesRep.Territory_c`, `SysUserFile.Name`, Seq 1-3, each a new GroupByID GUID.

Lesson learned live: the ExternalRepID_c criterion was first written with `CriteriaType=0`, which put it on the SubQuery Criteria tab starting with "And" — invalid in the designer even though the import succeeded. Normal table-field WHERE conditions are Table Criteria (`CriteriaType=2`).

## Step 3 — Build, import, verify

Run `scripts/build_baq.py` (adapt the `new_rows` list), which starts from `assets/BasicBAQ_template.baq`, strips the seed Company table/field, splices the rows, and re-zips. Then: `request_file_upload` → PUT → `ImportBAQ BAQID=GetSalesRepsTest` → `GetBAQDefinition` and check each section landed (tables 5, relations 3, relation fields 5, fields 3, criteria 3 all type 2, group-bys 3, value set 3 items).

If ImportBAQ returns `Success:false` with no message: the target likely exists and is open in a designer. Import under a new name or ask the user to close it. Remember fileRefs are single-use — re-request the upload for a retry.

---

# Worked example 2: recursive CTE — including the failure and the fix

Request: "OrderHed.SalesRepList is tilde-separated. Give me one row per sales rep, with the order total multiplied by that rep's split so I know how much each rep gets."

Design (three subqueries): CTE anchor `RepList` (first rep: `Idx=1`, `[Ice].entry(1, SalesRepList, '~')`), recursive UnionAll member (next rep: `Idx+1`, `entry(Idx+1, ...)`, referencing the CTE itself), TopLevel joining the CTE back to OrderHed with a positional `CASE Idx WHEN 1 THEN RepSplit1 ... END` for the split %. Full runnable code: `example_recursive_cte()` in `scripts/build_baq.py`.

## What went wrong on the first attempt — and why it matters

The first version **imported successfully and verified perfectly with GetBAQDefinition** — then failed at execution with "Incorrect syntax near the keyword 'where'/'inner'" and raw GUIDs visible in the generated SQL. Three causes, all invisible to the import:

1. **Dotted SQ reference.** The SQ table rows stored `DBTableName='.76fc7ad9-...'` (with a leading dot) instead of the bare GUID. The dot came from *misreading analysis output* that displayed `schema + "." + table` with an empty schema. The designer couldn't resolve the reference, so it emitted raw GUIDs into the SQL. Store the **bare SubQueryID GUID**.
2. **CTE reference aliased with a different name.** The top level aliased the CTE ref as `RepSplit` while the CTE's Name was `RepList` — the designer reported the alias as nonexistent. Alias CTE references with the CTE's **exact Name** and use that name in formulas (`RepList.Calculated_Idx`).
3. **SQ table as join parent.** The working fix (and every production specimen) has the DB table as parent and the SQ/CTE table as **child** in QueryRelation.

Also learned: a single subquery criterion `RepCode <> ''` (CriteriaType=0, it's a calc field) terminates the recursion — no extra `Idx < 5` guard needed; and calc-field pass-throughs (`CTELoop.OrderHedA_Company`) are a valid way to line up union-member columns.

## The takeaway that shapes the whole workflow

**GetBAQDefinition verifies structure, not executability.** Import success + definition check is NOT the finish line for anything with subquery/CTE/union references. Always have the user Analyze/execute the BAQ in the designer, and treat designer/SQL errors as a normal iteration step: export a working similar BAQ, diff row-by-row against yours, fix, re-import.
