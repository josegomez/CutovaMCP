# Calculated-field formula language

A calculated field's `Formula` is **plain SQL Server T-SQL** evaluated against the subquery's table aliases, plus two BAQ-specific extensions. The BAQ Designer's "Functions" menu only inserts T-SQL snippets — nothing proprietary is stored, so write standard SQL directly.

Verified examples from production BAQs:

```sql
isnull({AlwaysHide}, 0)                                   -- scalar subselect reference
Constants.LastDayOfMonth                                  -- BAQ constant
convert(varchar, PartTran.TranDate, 101)                  -- plain T-SQL
CASE WHEN PartLangDesc.Company IS NULL THEN Part.PartDescription ELSE PartLangDesc.Description END
SUM(PartBin.OnhandQty)                                    -- aggregate (pair with GROUP BY)
Row_Number() over (partition by PartMtl.PartNum order by AssembliesPossible)
[Ice].entry(1, Part_UD.Category_c, '~')     -- Epicor DB scalar function
datediff(day, OrderHed.OrderDate, Constants.Today)
```

## Extension 1: `{SubQueryName}`

References a scalar subselect (an `InnerSubQuery` returning one value). See baq-anatomy.md section 13.

## Extension 2: `Constants.<Name>`

Runtime-resolved BAQ constants. Full catalog:

CacheInvalidateTime, CompanyID, CompanyName, CountryCode, CountryGroupCode, CurComp, CurCompName, CurLangID, CurrentCompany, CurrentCompanyName, CurrentEmployeeID, CurrentLanguageID, CurrentPlant, CurrentTime, CurrentUserID, Day, DayOfWeek, DEC_COST, DEC_GENERAL, DEC_PRICE, DefaultUM, DefaultUOM, DefUM, DesignMode, EmployeeID, FirstDayOfMonth, FirstDayOfNextMonth, FirstDayOfNextWeek, FirstDayOfPrevMonth, FirstDayOfPrevWeek, FirstDayOfUserCultureWeek, FirstDayOfWeek, GlobalSecurityManager, IsMultiTenant, LanguageID, LastDayOfMonth, LastDayOfNextMonth, LastDayOfNextWeek, LastDayOfPrevMonth, LastDayOfPrevWeek, LastDayOfWeek, MobileConnect, Month, PlantID, ProductCode, ProductName, SecurityManager, Today, Tomorrow, UserID, VersionString, Week, WorkstationDescription, WorkstationID, Year, Yesterday.

Most useful: `Constants.Today`, `Constants.CurrentUserID` / `UserID`, `Constants.CompanyID`, `Constants.CurrentPlant`, the FirstDayOf/LastDayOf date family. `UpdInitExpression` on updatable fields accepts constants too (e.g. `Constants.CompanyID`).

## Designer function menu -> T-SQL equivalents

| Menu group | Functions (all plain T-SQL or trivial wrappers) |
|---|---|
| Aggregate | Avg, Count, Max, Min, Sum |
| Math | Abs, Sqrt, Power, Log, Log10, Modulo (x % y), Round, Truncate |
| String | Asc, Char, Len, Left-Trim (LTRIM), Trim, Right-Trim (RTRIM), Substitute, Substring, Replace, Upper, Lower |
| Date | Date(y,m,d), Year, Month, Day, WeekDay, Add-interval (DATEADD), Date-difference (DATEDIFF) |
| Conversion | DateToString/TimeToString/DecimalToString/IntToString (CONVERT), Integer, Decimal, StringToDate, IntToDateTime, Logical |
| Ranges | Lookup, Entry ([Ice].entry(n, str, delim) - 1-based token from a delimited string), Num-entries |
| Financial | FiscalYear, FiscalPeriod |

## Advanced patterns (mined from real production BAQs)

Windowing functions are fully supported and heavily used. All of these are real production formulas.

### Windowed aggregates

```sql
-- partition total (no ORDER BY = total over the whole partition)
sum(OrderRel.OurReqQty) over (partition by OrderRel.Company, OrderRel.OrderNum, OrderRel.OrderLine)
-- running total (ORDER BY = cumulative)
sum(PeriodAmt) over (partition by T.Company, T.FiscalYear order by T.FiscalPeriod)   -- YTD from period amounts
count(1) over (partition by Inventory.PkgControlHeader_PCID)                     -- rows per group, on every row
```

Note `sum(PeriodAmt) over (...)`: a windowed aggregate **over a sibling calculated field** (referenced by bare FieldName) — calc fields can reference other calc fields in the same subquery by name.

### Ranking

```sql
ROW_NUMBER() OVER (PARTITION BY X.Company, X.PartNum ORDER BY X.CustNum)
Rank()       over (partition by D.FiscalYear, D.FiscalPeriod order by Calculated_YTDAmt desc)  -- leaderboards
Dense_Rank() over (order by OrderRel.OrderNum, ShipName, Add1, City, State, Zip)           -- synthesize a grouping key (pack-slip grouping)
```

### The idioms these enable

- **Latest effective record**: `ROW_NUMBER() OVER (PARTITION BY Company, SalesRepCode ORDER BY EffectiveDate DESC, RateNumber DESC)` in a subquery, then criteria `Rank = 1` outside — the standard "current rate/price/revision" pattern.
- **Closest date match**: `row_Number() over (partition by ... order by abs(datediff(day, RateDate, PeriodEnd)) asc)` then `= 1`.
- **FirstOnly de-duplication** (avoid double-counting a header amount duplicated across joined detail rows): `InvoiceCount = ROW_NUMBER() OVER (PARTITION BY InvcHead.InvoiceNum ORDER BY InvcHead.InvoiceNum)`, then `FirstOnly = CASE InvoiceCount WHEN 1 THEN 1 ELSE 0 END`, then every header-level amount is `InvcHead.InvoiceAmt * FirstOnly` — sums stay correct.
- **Running-sum allocation**: `RunningSum = sum(ReqQty) over (partition by PartNum order by ...)` then `ShipIt = CASE WHEN RunningSum <= OnHandTotal THEN 1 ELSE 0 END` — "fill orders until stock runs out".

### String aggregation & misc

```sql
string_agg(ShipDtl.PackNum, ', ')                                        -- concatenated list per group
case when count(1) > 20 then 'Too Many To List'
     else string_agg(cast(ShipDtl.PackNum as nvarchar(MAX)), ', ') end   -- with a size guard (cast avoids the 8000-byte limit)
count(distinct ShipDtl.WarehouseCode)                                    -- distinct counts work
DATENAME(dw, OrderHed.OrderDate)                                         -- weekday-name tricks for workday math
CONCAT(CONVERT(varchar(2), MONTH(GETDATE())), '/', ...)                  -- date formatting
/* comments */ and -- comments                                           -- both allowed inside Formula text
'' or 'inventory'                                                        -- literal constants as columns (to tag union members with their source)
```

A memorable production example: local plant time computed as `CASE Plant.TimeZoneID WHEN 'Central Standard Time' THEN ... DATEADD(SECOND, Constants.CurrentTime - 3600, CAST('00:00:00' AS TIME)) ...` — constants, T-SQL, and business data mixed freely.

## Field format strings (`FieldFormat`)

`x(50)` text width; `>>>>>9` / `->>,>>>,>>9` / `>>>,>>>,>>9.99` numbers (- = sign, commas = separators); `{date}` date; `yes/no` bit. Get real formats from `zDataFields`; for calculated fields pick a sensible one — the designer only uses it for display.
