# BAQ Anatomy — the complete object reference

This documents every part of a BAQ definition, written for someone who has never built one. All facts here were observed in real exports from a live Kinetic 2025+ system and verified by successful re-imports.

## Table of contents

1. [Mental model](#1-mental-model)
2. [The header: DynamicQuery(Designer)](#2-the-header)
3. [Subqueries: QuerySubQuery](#3-subqueries)
4. [Tables: QueryTable](#4-tables)
5. [Fields: QueryField](#5-fields)
6. [Joins: QueryRelation + QueryRelationField](#6-joins)
7. [Criteria: QueryWhereItem (+ QueryValueSetItems)](#7-criteria)
8. [Parameters: QueryParameter + QueryCtrl (+ QueryCtrlValues)](#8-parameters)
9. [Group by: QueryGroupBy](#9-group-by)
10. [Sorting: QuerySortBy](#10-sorting)
11. [Field attributes: QueryFieldAttribute](#11-field-attributes)
12. [Execution settings: QueryExecuteSetting](#12-execution-settings)
13. [Subquery patterns: scalar subselects, joined subqueries, CTEs, unions](#13-subquery-patterns)
14. [Updatable BAQs (UBAQ) and BPM](#14-updatable-baqs)
15. [External BAQs](#15-external-baqs)
16. [What the server fixes/fills on import](#16-server-behavior-on-import)

---

## 1. Mental model

A BAQ is a SQL SELECT statement stored as relational rows instead of text. Each concept in SQL maps to a row type:

| SQL concept | BAQ row type (XML element in DynamicQuery) |
|---|---|
| the query itself | `DynamicQueryDesigner` (1 row) |
| each SELECT block (main query, subquery, CTE, union member) | `QuerySubQueryDesigner` |
| FROM / JOIN table | `QueryTableDesigner` |
| JOIN ... ON | `QueryRelationDesigner` (the join) + `QueryRelationFieldDesigner` (each ON pair) |
| SELECT column | `QueryFieldDesigner` |
| WHERE / HAVING condition | `QueryWhereItemDesigner` |
| IN ('a','b','c') constant list | `QueryValueSetItemsDesigner` |
| GROUP BY expression | `QueryGroupByDesigner` |
| ORDER BY | `QuerySortByDesigner` |
| @parameter | `QueryParameterDesigner` + `QueryCtrlDesigner` (prompt UI) |
| column display metadata | `QueryFieldAttributeDesigner` |
| OPTION(...) / timeout | `QueryExecuteSettingDesigner` |

Keys that tie rows together: every row carries `QueryID` (the BAQ) and `SubQueryID` (a GUID identifying which SELECT block it belongs to). Fields belong to tables via `TableID`. Join conditions belong to joins via `RelationID`. Criteria are identified by `CriteriaID`.

Note: in the export XML the element names carry a `Designer` suffix (`QueryTableDesigner`); GetBAQDefinition returns the same data without the suffix (`QueryTable`). Same columns either way.

## 2. The header

One `DynamicQueryDesigner` row. Fields that matter:

- `QueryID` — the BAQ ID. You never need to edit this for a rename; ImportBAQ's BAQID parameter rewrites it everywhere.
- `AuthorID`, `Company` — set to the importing user/company on import.
- `Description` — display name in the BAQ list. Do edit this.
- `DisplayPhrase` — a generated SQL preview with Epicor's own disclaimer. Informational; ignore it, never parse it, it goes stale harmlessly.
- `IsShared` (visible to others), `SecCode` (security code, e.g. `BAQDEFAULT`), `AllCompanies`, `XCompany`, `GlbCompany`.
- `Updatable` — true for UBAQs.
- `ExtQuery` + `ExtDatasourceName` — external BAQ markers (see §15).
- `Version` — the Kinetic version the BAQ was authored on; the server bumps it.

## 3. Subqueries

Every BAQ has at least one `QuerySubQueryDesigner` row: the top level.

- `SubQueryID` — GUID; all child rows reference it. When copying from the template you can reuse its existing GUID.
- `Name` — designer display name; also how scalar subselects are referenced in formulas (`{Name}`).
- `Type` — one of: `TopLevel`, `Union`, `UnionAll`, `Intersect`, `Except`, `CTE`, `InnerSubQuery`.
- `Seq` — order. **Seq order defines set-operation chaining**: a `Union`/`UnionAll`/`Intersect`/`Except` row combines with the *previous* member in Seq order.
- `LeftP` / `RightP` — literal `(` and `)` that group a chain of union members so the group can be referenced as a single unit.
- `SelectListClause` — `All` or `Top` (with `TopRowExpr`, `TopInPercent`, `TopWithTies`).
- `OrderByOffSet` / `OrderByFetch` — OFFSET/FETCH paging.

## 4. Tables

One `QueryTableDesigner` row per FROM/JOIN source.

- `TableID` — the **alias**. The same DB table can appear many times under different TableIDs (e.g. `Customer_BILL`, `Customer_W0`).
- `DBSchemaName` + `DBTableName` — the real table, e.g. `Erp` + `Customer`, or `Ice` + `SysUserFile`.
- `Seq` — 1..n for regular tables. UD tables use 101+. The `Calculated` pseudo-table uses -1.
- `Modifiers`/`PivotFunction`/`PivotDataType`/`PivotFieldFormat` — used only on pivoted SQ references (section 13, Pivots); empty otherwise.
- `TableType`:
  - `DB` — normal database table
  - `TT` — the `Calculated` pseudo-table (see below)
  - `SQ` — a subquery used as a table: `DBSchemaName=''`, `DBTableName='<SubQueryID GUID>'` of the referenced subquery. **The bare GUID, NO leading dot** — a dot (or any decoration) breaks SQL generation: the designer emits raw GUIDs into the SQL and execution fails with "Incorrect syntax near..." even though the import succeeds. (Some display tools print SQ tables as `.guid` because they concatenate the empty schema + `.` + name — that dot is a formatting artifact, not file content.)
  - `UD` — an explicitly joined `<Table>_UD` extension table holding the user-defined `_c` columns. **Required whenever the query touches any `_c` field** (see the UD rule in section 5); carried hidden: `Seq=101+`, `IsVisibleInDesigner=false`.
  - `EX` — external datasource table (external BAQs only)

**The Calculated pseudo-table**: every subquery that exists in the designer carries one row `TableID=Calculated`, `TableType=TT`, `Seq=-1`, empty schema/table, `IsVisibleInDesigner=false`. It is the container for calculated fields. The template already has it — keep it even if you add no calculated fields.

## 5. Fields

One `QueryFieldDesigner` row per displayed column.

Essential values for a normal database field:

```
TableID        = table alias, e.g. OrderHed
FieldName      = column name, e.g. OrderNum
Seq            = display order (1, 2, 3...) — UNIQUE per subquery, see warning below
DBSchemaName   = Erp / Ice
DBTableName    = physical table
DBFieldName    = column name again
DataType       = nvarchar / int / decimal / bit / date / datetime ...  (get from zDataFields)
FieldFormat    = x(50) / ->>,>>>,>>9 / {date} / yes/no ...             (get from zDataFields)
FieldLabel     = display caption
Alias          = conventionally TableID_FieldName, e.g. OrderHed_OrderNum
IsCalculated   = false, Formula = ''
External       = false; all the flag fields (IsGroupBy, UseLike, Updatable, RaiseEvent,
                 DropDown, IsRequired, IsReadOnly, SystemFlag) = false; Aggregation = ''
```

**Seq integrity — do not corrupt it.** All fields of a subquery — regular AND calculated — share ONE Seq sequence, and it must be unique (1..n). The import does NOT enforce this: duplicate Seq values load "successfully" and then corrupt the field ordering in the designer and Calculated Field Editor (observed live: two calc fields both at Seq 13, two at 14). When ADDING a field to an existing BAQ, first collect every existing QueryField Seq in that subquery (don't forget calculated fields) and assign max+1; when reordering, renumber the whole set 1..n with no gaps-by-accident duplicates. `build_baq.py` validates this automatically at build time.

For a **calculated field**: `TableID=Calculated`, `IsCalculated=true`, empty DBSchema/DBTable/DBField, `Formula` = the expression (see `formula-language.md`), `DataType` = the result type you declare. Alias convention `Calculated_<FieldName>`.

**User-defined (UD) fields — the `_UD` table is MANDATORY.** Columns ending `_c` physically live in `<Table>_UD` (look them up with `zDataFields` on e.g. `SalesRep_UD`). Referencing `_c` directly on the base table LOOKS fine — it imports, the server even adds `UserDefinedColumn` attributes, and Analyze/Execute in the BAQ Designer works because the designer auto-attaches the `_UD` extension interactively. But the runtime `ExecuteBaq`/dynamic-Select path used by Kinetic layers and grid BAQ providers does NOT auto-attach it: the compiled SQL references bare `_c` names against the base table and fails with `SqlException 207 — Invalid column name 'X_c'` (including `_c` fields used only in joins, never displayed). The correct form, matching Epicor-delivered BAQs:

- `QueryTableDesigner` row for the extension: `TableID=<Table>_UD`, `TableType=UD`, `IsVisibleInDesigner=false`, `Seq=101` (102, 103... for more), `DBSchemaName=<same schema>`, `DBTableName=<Table>_UD`.
- FK relation to the base table: `ParentTableID=<Table>`, `ChildTableID=<Table>_UD`, `JoinType=Inner`, `IsFK=true`, ONE relation field: `SysRowID = ForeignSysRowID` (both `uniqueidentifier`).
- EVERY `_c` reference goes through the extension: display fields with `TableID=<Table>_UD`, and join conditions with `ParentFieldName`/`ChildFieldName` on the `_UD` table — never on the base table.
- For clean result aliases set the field `Alias` to `<Table>_<field>_c` (e.g. `UD103_CustomerPO_c`) instead of the default `<Table>_UD_<field>_c`.

Verify by exporting after import: the `_UD` QueryTable row must exist with `TableType=UD` + `IsVisibleInDesigner=false`, and `_c` fields/joins must carry `TableID=<Table>_UD`. Designer Analyze alone does NOT prove a layer/grid will run it — test through the actual runtime path.

Supply the minimum: Description, precise formats, captions, Like references etc. are all hydrated from the data dictionary on import (§16).

## 6. Joins

A join = one `QueryRelationDesigner` row + one `QueryRelationFieldDesigner` row per ON condition.

`QueryRelationDesigner`:
- `RelationID` — new GUID you generate.
- `ParentTableID` → `ChildTableID` — table aliases being joined.
- `JoinType` — `Inner` or `LeftOuter` (parent LEFT OUTER JOIN child keeps all parent rows).
- `IsFK` — true when taken from the dictionary relationship; informational.
- `OuterJoin` — legacy flag, false.

`QueryRelationFieldDesigner` (one per field pair):
- `RelationID` (same GUID), `Seq` (1, 2, ...)
- `ParentFieldName` `CompOp` `ChildFieldName` — e.g. Company = Company, OrderNum = OrderNum
- `ParentFieldDataType` / `ChildFieldDataType`
- `ParentFieldIsExpr` / `ChildFieldIsExpr` — set true to use an expression instead of a field name
- `AndOr` ('' on first pair, then 'And'), `Neg`, `LeftP`/`RightP` — condition chaining

Get the correct field pairs from `zDataRelationships` — its output (ParentFieldName, CompOp, ChildFieldName, Seq per row) maps 1:1 onto these rows. For joins the dictionary doesn't know (e.g. `UserComp.DcdUserID = SysUserFile.UserID`), write the pairs yourself.

Epicor almost always joins on `Company` first plus the business keys.

## 7. Criteria

One `QueryWhereItemDesigner` row per condition.

**CriteriaType — decoded, this matters.** The designer has two homes for criteria and `CriteriaType` says which:

- `CriteriaType=2` → **Table Criteria** (the criteria grid attached to one table). Use this for normal WHERE conditions on a table's own fields — the overwhelmingly common case.
- `CriteriaType=0` → **SubQuery Criteria** (the subquery-level WHERE/HAVING tab). Required for criteria on **calculated fields** (they have no table grid) and for cross-table OR logic.
- `CriteriaType=1` → SubQuery Criteria with `UseHaving=true` (a HAVING condition).
- `CriteriaType=3` → the **PIVOT FOR clause** (an IN criterion on a pivoted SQ table whose value list defines the pivot columns — see section 13, Pivots).

**`Seq` and `AndOr` restart within each collection** — each table's criteria set and the subquery criteria set are separate chains. The first row of EACH collection must have `AndOr=''` (empty); later rows `And`/`Or`. Getting this wrong (e.g. a lone subquery criterion with `AndOr=And`) produces a broken condition in the designer even though the import succeeds — verified the hard way.

Row anatomy:

- `TableID` + `FieldName` — the left side. Calculated field: `TableID=Calculated`, `FieldName=<calc name>` (and CriteriaType=0).
- `CriteriaID` — new GUID. `Neg` for NOT; `LeftP`/`RightP` for parentheses.
- `CompOp` — `=`, `<>`, `>`, `>=`, `<`, `<=`, `LIKE`, `IN`, `ISNULL` (null test, empty RValue).
- `DataType` — of the left field.

The right side is one of four shapes (copy these exactly):

| Shape | IsConst | RValue | To* fields |
|---|---|---|---|
| constant | `true` | the literal: `true`, `false`, `0`, `web` etc. Empty string allowed (`<RValue />`) | empty |
| parameter | `true` | `@ParamName` | empty |
| another field | `false` | empty | `ToTableID`, `ToFieldName`, `ToDataType` point at the other field (also how correlated subqueries bind to the outer query) |
| constant IN-list | `false` | a ValueSetID like `_where-4981263407492039803` | empty |

**Constant IN-lists**: the where row's RValue holds a made-up unique `ValueSetID` (convention: `_where-<long number>`); the list items are separate `QueryValueSetItemsDesigner` rows: `(Company, QueryID, ValueSetID, ItemValue)` — one per value. An IN against a *parameter* instead uses `RValue=@Param` with an ItemList control (§8).

Bit fields compare against `true`/`false`. Int UD fields compared "<> ''" in loose SQL mean `<> 0`.

## 8. Parameters

**A working parameter requires TWO rows** — the declaration AND its prompt control. The designer always creates both; hand-built BAQs that only add `QueryParameterDesigner` don't prompt correctly. Verified shapes from production BAQs:

`QueryParameterDesigner` (element order: ParameterID, ParameterType, ParameterLabel, SkipIfEmpty):

```
ParameterID   = Site            -- the name used as @Site
ParameterType = nvarchar        -- nvarchar / int / date / decimal / bit
ParameterLabel = ''             -- optional prompt label override
SkipIfEmpty   = false           -- true = criteria using it are skipped when blank ("optional filter")
```

`QueryCtrlDesigner` — the prompt control (order: ControlID, DataSource, DataType, FieldFormat, IsMandatory, DefaultValue, ControlType, SourceType, ListSource, DisplayColumn, ValueColumn, Seq):

```
ControlID    = <new GUID>
DataSource   = Site             -- the ParameterID it prompts for
DataType     = nvarchar         -- match the parameter
FieldFormat  = x(8)             -- prompt display format ({date}, ->>,>>>,>>9, ...)
IsMandatory  = false
DefaultValue = ''               -- e.g. '%'
ControlType  = Standard         -- Standard | DropDown | ItemList
SourceType   = 1
ListSource / DisplayColumn / ValueColumn = ''   -- used when a dropdown is fed by a BAQ/list source
Seq          = 1                -- prompt order
```

- Reference the parameter in criteria as `IsConst=true`, `RValue='@Site'`, `CriteriaType=2` (normal table criterion; `1` when HAVING).
- `ControlType=DropDown` → fixed options live in `QueryCtrlValuesDesigner` rows (`ControlID`, `ID`=stored value, `Val`=display text, `Seq`).
- `ControlType=ItemList` → multi-value list parameter, paired with an `IN @Param` criterion.
- `QueryParameterBindingDesigner` was empty in every specimen (likely dashboard/BAQ-reference bindings).

## 9. Group by

`QueryGroupByDesigner`: one row per GROUP BY expression — `GroupByID` (new GUID), `Expression` (free text: `Table.Field`, `Alias.Calculated_Field`, or a calc field name), `Seq`. Aggregates (SUM/MAX/COUNT...) go inside calculated-field formulas; the QueryField `Aggregation` column exists but the formula approach is the pattern proven here. To emulate "pick one row per group", use `Row_Number() over (partition by ... order by ...)` in a calc field of a subquery, then filter `= 1` outside.

## 10. Sorting

`QuerySortByDesigner`: `TableID`, `FieldName`, `Seq`, `IsAsc`. Straightforward.

## 11. Field attributes

`QueryFieldAttributeDesigner` rows override column metadata: `AttributeName` ∈ Caption, Format, Like, Required, BizType (Email/Phone/URL/quantity), LinkedColumn/UomColumn, UserDefinedColumn, IsHidden... with `Value` and `IsOverriden`. **You rarely write these** — the server generates them from the dictionary on import. Only add one to deliberately override a caption/format.

## 12. Execution settings

`QueryExecuteSettingDesigner` rows, one per setting: `SettingID=QueryOption, SettingValue=recompile` → OPTION(RECOMPILE); `SettingID=QueryTimeOut, SettingValue=500` → timeout seconds.

## 13. Subquery patterns

**Scalar subselect** (a subquery returning one value, used inside a formula):
- Add a `QuerySubQueryDesigner` row `Type=InnerSubQuery` with its own Name and GUID.
- Give it tables, one calculated field (its return value), and criteria.
- Correlate to the outer query with where rows using the field-comparison shape: `IsConst=false`, `ToTableID`/`ToFieldName` = the OUTER query's table.field.
- Consume it in an outer calc-field formula as `{Name}`, e.g. `ISNULL({OnHandTotal},0)`.

**Subquery joined as a table**:
- Same `InnerSubQuery` (or a parenthesized union group), but referenced by a `QueryTableDesigner` row in the consuming subquery: `TableType=SQ`, `DBTableName='<that SubQueryID GUID>'` (bare GUID, no dot!), `TableID=<alias>`.
- **When the referenced subquery is a CTE, make the alias (TableID) equal the CTE's Name.** Confirmed by a live failure/fix cycle: a top-level reference aliased differently produced "name does not exist" style errors, and renaming the alias to the CTE's Name fixed execution. (One production BAQ does use a divergent alias, so it may work in some paths — but matching the name is the proven-safe rule.)
- **In joins, the SQ table is always the CHILD** and the DB table the parent (`ParentTableID=OrderHed, ChildTableID=RepList`) — every working specimen follows this; an SQ-as-parent relation was part of a query that failed to execute.
- Its columns are referenced as `<alias>.<inner field Alias>` — calculated fields surface as `<alias>.Calculated_<name>`.
- On the SQ side of relation fields, the field name is the **inner field Alias** (e.g. `ChildFieldName=OrderHedA_Company`).
- **Displaying a subquery's field directly (pass-through)** — you do NOT need a calculated field to surface an SQ table's column. Add a regular QueryField row (designer-native, verified from a designer-authored example): `TableID=<SQ alias>`, `FieldName=<the inner field's Alias>` (e.g. `Company_Address1`), `DBFieldName=<the original DB column>` (e.g. `Address1`), `DBSchemaName`/`DBTableName` empty, `IsCalculated=false`, no Formula, `Alias` typically kept equal to the inner Alias, DataType/FieldFormat from the original column. Works at the top level and in union members alike (union members use it to line columns up by Seq). A calc field whose formula is just `<alias>.<innerAlias>` also works but is unnecessary — reserve calc fields for actual expressions.

**CTE**:
- `Type=CTE` subquery, low Seq (CTEs come first). Non-recursive CTEs need no parens.
- Consume by TableType=SQ reference, exactly like above.
- **Recursive CTE**: pair the CTE with a following `Type=UnionAll` member wrapped in parens (`LeftP='('` on the CTE, `RightP=')'` on the union member); the union member references the CTE's own SubQueryID as an SQ table. Union members' output columns align by field `Seq` and must have matching DataTypes.
- Proven authoring example (authored, imported, executed live after one fix cycle): explode a `~`-delimited `SalesRepList` into one row per rep. Anchor (`RepList`, Type=CTE, `(`): OrderHed keys + `Idx=1` + `[Ice].entry(1, SalesRepList, '~')`, criteria `SalesRepList <> ''`. Recursive member (Type=UnionAll, `)`): SQ table ref to the CTE's own SubQueryID (alias may differ here, e.g. `CTELoop`), calc pass-throughs `CTELoop.OrderHedA_Company` etc., `Idx+1`, `entry(Idx+1, ...)`, terminated by ONE subquery criterion `RepCode <> ''` (CriteriaType=0) — no extra Idx guard needed. Top level: SQ ref aliased **exactly `RepList`** (=CTE name), joined as CHILD of OrderHed on the inner aliases, positional `CASE RepList.Calculated_Idx WHEN 1 THEN OrderHed.RepSplit1 ... END` for the per-rep split.

**Unions**: members are consecutive-Seq subqueries; the first member is `InnerSubQuery` (or TopLevel), each following member has `Type=Union`/`UnionAll`/`Intersect`/`Except`. Columns line up by field Seq. Wrap a chain in LeftP/RightP to reference the whole thing as one SQ table. Additional facts from production BAQs: the **top level itself can be unioned** (TopLevel Seq n followed by a `Union` member, no parens needed — e.g. an Invoices + Payments result set); a single-member (non-recursive) CTE needs no parens; union chains with 3-4 members are common (tag each member's origin with a literal calc field like `'inventory'` / `'staged'`); and **TopLevel does not have to be the last Seq** — it can be Seq 1 with the inner subqueries after it.

**PIVOT (cross-tab)** — decoded from three production BAQs (a per-branch invoice count, a commission tracker, and an inbound-shipments report):

A pivot turns rows into columns (e.g. one column per fiscal period). Everything hangs off the SQ table reference in the consuming subquery:

1. **Build the pivot source** as an inner subquery outputting exactly: the key columns you want per output row, the *spreading* column (whose values become column headers, e.g. FiscalPeriod), and the *value* column to aggregate (e.g. InvoiceNum, RelQty).
2. **Reference it as a pivoted SQ table**: normal `TableType=SQ` row plus `Modifiers='Pivot'`, `PivotFunction='<agg>(<inner value alias>)'` (real examples: `count( InvcHead1_InvoiceNum )`, `sum(PORel_RelQty)`, `sum(Calculated_PeriodAmt)`), `PivotDataType` and `PivotFieldFormat` = the type/format of every generated pivot column. (`Modifiers='No'` appears on non-pivoted SQ refs that once carried pivot metadata — harmless.)
3. **The FOR clause is a criterion**: a `QueryWhereItemDesigner` row on that SQ table with `CompOp=IN`, **`CriteriaType=3`**, `IsConst=false`, `FieldName=<inner alias of the spreading column>` (e.g. `InvcHead1_FiscalPeriod`), `RValue=<ValueSetID>`, and one `QueryValueSetItemsDesigner` row per pivot value (`'1'..'12'`, `'MON'..'FRI'`...). **Each value becomes an output column** — pivot columns are always a fixed, enumerated list.
4. **Display the pivot columns** as pass-through field rows on the SQ alias where `FieldName` and `DBFieldName` are the *value itself*: `TableID=SubQuery2, FieldName='1', DBFieldName='1', DataType=<PivotDataType>, Alias=SubQuery2_1`. Non-spread key columns are displayed as normal pass-throughs and act as the implicit GROUP BY (standard T-SQL PIVOT semantics).
5. Calculated fields can reference pivot columns directly: `isnull(BranchTotals.1,0) + isnull(BranchTotals.2,0) + ...` for row totals.

## 14. Updatable BAQs

Header `Updatable=true` plus `QueryUpdateSettingsDesigner` (AllowAddNew, SupportMDR, `UpdatableType`: A = advanced/BPM) and per-field `Updatable`/`RaiseEvent`/`UpdInitExpression` on QueryField rows (`UpdInitExpression` can use `Constants.*`).

**Custom actions**: `QueryCustomActionDesigner` rows — just `ActionID` + `ActionLabel` (e.g. `Ship`/"Ship", `StageAsync`/"Stage Async", `FillQty`/"Fill Qty"). They appear as buttons in dashboards/apps; the behavior is implemented by a BPM directive on the UBAQ's `RunCustomAction` method that switches on `actionID`.

UBAQ exports carry two extra ZIP entries: `version` and `BpMethodDataset` — the BPM layer travels with the file. `BpMethodDataset` contains `BpMethod` rows (GetList/GetNew/Update/FieldUpdate/FieldValidate/RunCustomAction), `BpArgument` rows (signatures), and `BpDirective` rows (the directive bodies). Method codes embed `<Company>/<BAQID>` — the import rename fixes these automatically.

## 15. External BAQs

Header: `ExtQuery=true`, `ExtDatasourceName=<configured external datasource>`. All tables get `TableType=EX` with the external schema (`dbo.OrderHed`, custom views, `_UD` replicas joined explicitly). Everything else works the same. External exports may lack the `QueryDependencies` entry entirely — the ZIP entry list is variable.

## 16. Server behavior on import

Verified by diffing exports against post-import GetBAQDefinition:

- Regenerates ALL `SysRowID`/`SysRevID` — omit them in rows you write.
- Rewrites `QueryID` everywhere from the `BAQID` parameter, including UBAQ BPM method codes.
- Sets `Company`, `AuthorID` (importing user), `GlbCompany`, dates; clears `SystemFlag`; bumps `Version`.
- **Hydrates from the data dictionary**: field Descriptions, exact FieldFormats, FieldLabels/Captions, Like references, Required/BizType/UOM attributes, UserDefinedColumn attributes — all appear even if you supplied none. Non-overridden QueryFieldAttribute rows are rebuilt wholesale.
- The stale `DisplayPhrase` is imported as-is (harmless; the designer regenerates it when opened).
