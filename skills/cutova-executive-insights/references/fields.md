# Executive Insight field cookbook

Exact column names and worked OData patterns for the seven tools. Column names are stable, but if
a call rejects a field, run `describe_baq_fields` on that tool to reconcile. Dates are strings in
ISO form, so date filters use string comparison (`ge '2026-01-01'`). `orderby` takes ` desc` for
descending. Always cap with `top`, and use `count: true` with `top: 1` for a pure count.

## zEI-Receivables (open posted AR)

Columns: `Customer_CustID`, `Customer_Name`, `InvcHead_InvoiceNum`, `InvcHead_InvoiceDate`,
`InvcHead_DueDate`, `InvcHead_InvoiceAmt`, `InvcHead_InvoiceBal`, `InvcHead_TermsCode`,
`InvcHead_FiscalYear`, `InvcHead_FiscalPeriod`, `InvcHead_CreditMemo`, `InvcHead_UnappliedCash`,
`Calculated_DocType` (Invoice / Credit Memo / Unapplied Cash), `Calculated_DaysPastDue`,
`Calculated_AgingBucket` (Current / 1-30 / 31-60 / 61-90 / 90+).

- Total open items: `count: true`, `top: 1`.
- Overdue count: `filter: Calculated_DaysPastDue gt 0`, `count: true`, `top: 1`.
- 90+ count: `filter: Calculated_DaysPastDue gt 90`, `count: true`, `top: 1`. Do not filter the 90+
  tier as `Calculated_AgingBucket eq '90+'`: the `+` does not match server-side and returns zero.
  The other buckets (`Current`, `1-30`, `31-60`, `61-90`) match with `eq` fine.
- Top debtors: `orderby: InvcHead_InvoiceBal desc`, `top: 10`, `select: Customer_CustID,Customer_Name,InvcHead_InvoiceBal,Calculated_DaysPastDue,Calculated_AgingBucket`.
- One customer: `filter: Customer_CustID eq '<CustID>'`.
- True invoices only (exclude credit memos and unapplied cash): `filter: Calculated_DocType eq 'Invoice'`.

## zEI-SalesOrders (open order book, release level)

Columns: `OrderHed_OrderNum`, `Customer_CustID`, `Customer_Name`, `OrderDtl_OrderLine`,
`OrderDtl_PartNum`, `OrderDtl_LineDesc`, `OrderDtl_ProdCode`, `OrderRel_OrderRelNum`,
`OrderHed_OrderDate`, `OrderRel_ReqDate`, `OrderRel_NeedByDate`, `OrderRel_OurReqQty`,
`OrderDtl_UnitPrice`, `OrderDtl_PricePerCode`, `OrderHed_OrderHeld`, `Customer_CreditHold`,
`Calculated_OpenValue` (price-per adjusted), `Calculated_ShipDatePastDue`,
`Calculated_RiskFlag` (OK / Hold / Past Due).

- Backlog lines: `count: true`, `top: 1`.
- At risk: `filter: Calculated_RiskFlag ne 'OK'`, `orderby: Calculated_OpenValue desc`, `top: 15`.
- Past-due ships only: `filter: Calculated_RiskFlag eq 'Past Due'`.
- On hold only: `filter: Calculated_RiskFlag eq 'Hold'`.
- Biggest open orders: `orderby: Calculated_OpenValue desc`, `top: 10`.

## zEI-Jobs (open production and maintenance jobs)

Columns: `JobHead_JobNum`, `JobHead_JobType` (MFG / MNT), `JobHead_PartNum`,
`JobHead_PartDescription`, `JobHead_ProdCode`, `JobHead_ProdQty`, `JobHead_StartDate`,
`JobHead_DueDate`, `JobHead_ReqDueDate`, `JobHead_JobFirm`, `JobHead_JobReleased`,
`JobHead_JobComplete`, `Calculated_LateDays`, `Calculated_RiskFlag` (On Track / Due Soon / Late / Complete).

- Open jobs: `count: true`, `top: 1`.
- Late: `filter: Calculated_RiskFlag eq 'Late'`, `orderby: Calculated_LateDays desc`, `top: 15`.
- Due soon: `filter: Calculated_RiskFlag eq 'Due Soon'`.
- Maintenance only: `filter: JobHead_JobType eq 'MNT'`.

## zEI-APInvoices (open posted payables)

Columns: `Vendor_VendorID`, `Vendor_Name`, `APInvHed_InvoiceNum`, `APInvHed_InvoiceDate`,
`APInvHed_DueDate`, `APInvHed_InvoiceAmt`, `APInvHed_InvoiceBal`, `APInvHed_REFPONum`,
`APInvHed_DebitMemo`, `APInvHed_DiscountAmt`, `APInvHed_DiscountDate`,
`Calculated_SourceType` (PO-Based / Misc), `Calculated_DocType` (Invoice / Debit Memo),
`Calculated_DaysToDue`, `Calculated_AgingBucket`, `Calculated_DiscountStatus` (None / Available / At Risk / Lost),
`Calculated_DiscountDaysLeft`.

- Open payables: `count: true`, `top: 1`.
- Discounts at risk: `filter: Calculated_DiscountStatus eq 'At Risk'`, `orderby: Calculated_DiscountDaysLeft`, `top: 15`.
- Cash plan by due date: `orderby: APInvHed_DueDate`, `top: 20`, `select: Vendor_Name,APInvHed_InvoiceBal,APInvHed_DueDate,Calculated_DaysToDue`.
- Misc (non-PO) invoices: `filter: Calculated_SourceType eq 'Misc'`.

## zEI-InvoicedSales (posted revenue)

Columns: `Customer_CustID`, `Customer_Name`, `InvcHead_InvoiceNum`, `InvcHead_InvoiceDate`,
`InvcHead_FiscalYear`, `InvcHead_FiscalPeriod`, `InvcDtl_InvoiceLine`, `InvcDtl_PartNum`,
`InvcDtl_ProdCode`, `InvcDtl_LineDesc`, `InvcDtl_SellingShipQty`, `InvcDtl_ExtPrice` (revenue),
`Calculated_DocType` (Invoice / Credit Memo).

- Top customers this year: `filter: InvcHead_FiscalYear eq 2026`, `orderby: InvcDtl_ExtPrice desc`, `top: 20`.
- Top products: same filter, `select: InvcDtl_PartNum,InvcDtl_ProdCode,InvcDtl_ExtPrice`, ranked by ExtPrice.
- A period: `filter: InvcHead_FiscalYear eq 2026 and InvcHead_FiscalPeriod eq 6`.
- Revenue is `InvcDtl_ExtPrice`. Credit memos are negative and net against revenue; keep them in a
  revenue total, split them out for a gross-vs-net view.

## zEI-POOutlier and zEI-APInvoiceOutlier (cost anomalies)

Parameters (all required): `MinObs` (default 5), `IQR_K` (1.5), `ModZThreshold` (3.5),
`LookbackDays` (365). The tool already filters to flagged open lines, so you do not need to filter
`IsOutlier`; just rank.

PO columns: `Calculated_Company`, `Calculated_VendorNum`, `Calculated_PartNum`, `Calculated_PONum`,
`Calculated_POLine`, `Calculated_ExtCost`, `Calculated_OrderDate`, `Calculated_DueDate`,
`Calculated_NHist`, `Calculated_Med`, `Calculated_P25`, `Calculated_P75`, `Calculated_MAD`,
`Calculated_IQR`, `Calculated_LoFence`, `Calculated_HiFence`, `Calculated_ModZ`, `Calculated_IsOpen`,
`Calculated_IsOutlier`.

AP columns are the same, with `Calculated_InvoiceNum`, `Calculated_InvoiceLine`,
`Calculated_InvoiceDate` in place of the PO number, line, and order date.

- Worst anomalies: `orderby: Calculated_ModZ desc`, `top: 10`,
  `select: Calculated_PartNum,Calculated_VendorNum,Calculated_PONum,Calculated_ExtCost,Calculated_Med,Calculated_NHist,Calculated_ModZ`.
- One vendor: `filter: Calculated_VendorNum eq <VendorNum>`.
- Only well-supported flags: raise `MinObs`, for example `MinObs: 12`.
- Only the most extreme: raise `ModZThreshold`, for example `ModZThreshold: 6`.

## Chart specs (render_chart)

- AR aging: bar, labels = the five buckets, one series = count per bucket (five cheap counts).
- Top debtors: horizontal bar, labels = customer names, series = `InvcHead_InvoiceBal` (top 10).
- Cost anomalies: horizontal bar, labels = part or PO, series = `Calculated_ModZ` (top 10), or a
  paired bar of `Calculated_ExtCost` versus `Calculated_Med`.
- Revenue trend needs a per-period sum. Pull `InvcHead_FiscalPeriod` and `InvcDtl_ExtPrice` with no
  `top`, then roll up with `scripts/aggregate.py --group InvcHead_FiscalPeriod --sum InvcDtl_ExtPrice`
  (see the skill's "Totals, roll-ups, and trends"). Chart the returned period totals.
