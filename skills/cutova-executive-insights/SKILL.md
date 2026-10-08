---
name: cutova-executive-insights
description: >
  Cutova Executive Insights, a Cutova product, turns Epicor Kinetic into a live executive
  briefing and lets the user drill in. Use this skill whenever someone asks how the business is
  doing, for a status or exec briefing or morning numbers, or about revenue, sales, cash,
  collections, AR, receivables, who owes us, AP, payables, what we owe, early-pay discounts,
  backlog, open orders, orders at risk, jobs at risk, WIP, cost anomalies, outliers, overbilling,
  weird invoices or POs, top customers, top vendors, or top products, even when they do not name a
  tool or a report. It runs the Cutova Executive Insights tools (zEI-*) against Epicor through
  Cutova, answers plain-language questions by routing to the right tool and slice, and renders
  charts. Prefer this skill over ad-hoc BAQ building for any executive or finance question about
  the company's own Epicor data.
---

# Cutova Executive Insights

Cutova Executive Insights is a Cutova product: a curated pack of seven read-only Epicor Kinetic
tools, delivered through Cutova, that answer the questions an executive actually asks. This skill
does three jobs: it opens with a **status briefing** that makes someone go "show me more", it
lets them **drill in** on anything (outliers, things at risk, aging, revenue), and it answers
**plain-language questions** about the business. Every tool runs as the signed-in user, so
results already respect that user's Epicor permissions.

## The one rule that makes this work: never pull a whole table

These are operational tables. Open AR alone can be tens of thousands of rows. Pulling a table
into the conversation is slow, expensive, and usually answers nothing. Three cheap moves cover
almost every question:

- **A total or a volume** → `count: true` with `top: 1`. You get the count without the rows.
  `count` alone still returns every row, so always cap it with `top: 1`.
- **A ranking ("top", "biggest", "worst")** → `orderby` the measure descending with `top: 10`.
- **A slice ("overdue", "at risk", "on hold")** → `filter` on the flag, then count or rank it.

Call `describe_baq_fields` on a tool the first time you filter or sort it, to get the exact
column names. The columns are also listed in `references/fields.md`. Guessing a field name wastes
a round trip; the columns are not the raw Epicor names (they are prefixed, for example
`InvcHead_InvoiceBal` and `Calculated_AgingBucket`).

## The status briefing

When someone asks how the business is doing, for a briefing, or for "the numbers", produce one
compact briefing from cheap queries, then offer to drill in. Do not narrate each call. Run this
set, then write the briefing:

1. **Cash in** — `zEI-Receivables` `count:true top:1` for total open AR items; again with
   `filter: Calculated_DaysPastDue gt 0` for the overdue count; again with
   `filter: Calculated_DaysPastDue gt 90` for the 90+ count. Filter the 90+ tier by days, not by
   `Calculated_AgingBucket eq '90+'`: the `+` does not match server-side and returns zero. Then top debtors:
   `orderby: InvcHead_InvoiceBal desc`, `top: 10`, select the customer, balance, days past due,
   aging bucket.
2. **Cash out** — `zEI-APInvoices` `count:true top:1` for open payables; again with
   `filter: Calculated_DiscountStatus eq 'At Risk'` for discounts about to expire.
3. **Backlog and risk** — `zEI-SalesOrders` `count:true top:1` for open lines; again with
   `filter: Calculated_RiskFlag ne 'OK'` for orders at risk. `zEI-Jobs` `count:true top:1`; again
   with `filter: Calculated_RiskFlag eq 'Late'` for late jobs.
4. **Anomalies** — `zEI-POOutlier` and `zEI-APInvoiceOutlier` with the default parameters
   (`MinObs 5`, `IQR_K 1.5`, `ModZThreshold 3.5`, `LookbackDays 365`), `orderby: Calculated_ModZ desc`,
   `top: 5`. These are the "money on the floor" lines.

Then write a briefing that leads with the headline, not a wall of numbers:

```
# Executive briefing — <company>, as of <date>
## Cash
- Open AR: <n> items, <overdue n> overdue, <90+ n> in the 90+ bucket.
- Biggest exposures: <top 3 debtors with balance and days past due>.
- Open AP: <n> items. Early-pay discounts at risk: <n>.
## Backlog and production
- Open order lines: <n>, <n> at risk (past-due ship or credit hold).
- Open jobs: <n>, <n> late.
## Anomalies worth a look
- <top 2-3 PO/AP outliers: part, vendor, this cost vs the vendor-and-part norm, x-times>.
## Where do you want to go? Collections, orders at risk, cost anomalies, or revenue trend.
```

Keep it to one screen. The close matters: name the drill-downs so the user picks one. That is the
"WOW, now show me" moment.

**Chart the briefing** when the client renders charts. Use the `render_chart` tool for a small
set that carries the story: AR aging as a bar chart (bucket counts), top debtors as a horizontal
bar, and the top outliers by modified z-score. `render_chart` is the native in-chat visual; when
it is not available, fall back to a compact markdown table. Do not chart everything, chart the
two or three visuals an executive would screenshot.

## Drilling in

Match the ask to the smallest tool set. Full field lists and more filters are in
`references/fields.md`.

- **Collections / who owes us** — `zEI-Receivables`. Rank by `InvcHead_InvoiceBal desc`. Slice by
  `Calculated_AgingBucket`, `Calculated_DaysPastDue`, or `Calculated_DocType`
  (Invoice / Credit Memo / Unapplied Cash). Credit memos carry a negative balance and are money
  owed back to the customer, so separate them, do not net them into "who owes us" silently.
- **Orders at risk** — `zEI-SalesOrders` `filter: Calculated_RiskFlag ne 'OK'`, ranked by
  `Calculated_OpenValue desc`. `RiskFlag` is `Hold` (order or customer credit hold) or `Past Due`
  (ship date passed). `OpenValue` is already adjusted for the price-per code, so it is a real
  dollar figure.
- **Jobs at risk** — `zEI-Jobs` `filter: Calculated_RiskFlag eq 'Late'`, ranked by
  `Calculated_LateDays desc`. This tool holds production and maintenance jobs only.
- **What we owe / discounts** — `zEI-APInvoices`. For a cash plan, rank by `APInvHed_DueDate`.
  For discounts, `filter: Calculated_DiscountStatus eq 'At Risk'` and pay those first to capture
  the discount. `Calculated_SourceType` separates PO-based from misc invoices.
- **Revenue** — `zEI-InvoicedSales`. Revenue is `InvcDtl_ExtPrice`, which already folds in quantity
  and the price-per code. For "top customers" or "top products this year",
  `filter: InvcHead_FiscalYear eq <year>`, `orderby: InvcDtl_ExtPrice desc`, `top: 20`. For an
  exact dollar total or a period-over-period trend, sum the raw rows with code, see "Totals,
  roll-ups, and trends" below.
- **Cost anomalies** — `zEI-POOutlier` and `zEI-APInvoiceOutlier`. See the next section.

## Reading an outlier, for an executive audience

The outlier tools already do the statistics. Your job is to say what a flagged line means in the
language of accounting, production, and the front office, not the language of a data scientist.
The audience is a controller, a plant manager, a CFO. Never put "modified z-score", "IQR", or the
parameter names (`MinObs`, `IQR_K`, `ModZThreshold`, `LookbackDays`) in front of the user. Turn each
flagged line into a plain, factual sentence about money:

> PO 100123, part WIDGET-10 from Acme Supply: this order pays **$12,400**. The usual cost for that part
> from that vendor is about **$310**, based on the last **15 purchases**. That is roughly **40 times
> higher**, about **$12,090 over the norm** — worth checking the unit price or quantity before it is
> paid.

Build that from `Calculated_ExtCost` (what this line pays), `Calculated_Med` (the usual cost), and
`Calculated_NHist` (how many past purchases back that "usual"). Rank the list with
`Calculated_ModZ desc` so the most extreme come first, but describe the gap in **dollars and
multiples** ("40 times higher", "$25,200 over the usual"), never as a z-score or a fence. For a
finance audience lead with the dollar exposure; for production lead with the part and the PO.

The comparison is against that vendor and that part's own history, so a flag means "unusual for this
supplier", not "this supplier is expensive versus others". If someone asks the cross-vendor question,
say that is a different view the current tool does not do.

The tools compare each line against its vendor-and-part buying history and stay silent when there is
too little history to judge. A quiet result means "nothing stands out against a solid track record",
not "nothing was checked". When someone wants to widen or narrow what counts as unusual ("only the
clear-cut ones", "look back two years", "flag even small oddities"), translate that into the tool
parameters yourself and report what you did in plain terms ("I looked back two years and kept only
the clearest cases"). Do not make the user learn the knobs. The objective, quantitative anchors an
executive will accept are the ones to show: the dollars, the multiple, and how many past purchases
the "usual" is based on.

## Answering questions

Route a plain question to the tool that owns the fact, then slice.

| The user asks about | Tool | How |
|---|---|---|
| who owes us, overdue, DSO, aging | zEI-Receivables | rank by balance, slice by aging/days |
| a specific customer's exposure | zEI-Receivables | `filter: Customer_CustID eq '<id>'` |
| what we owe, cash out, discounts | zEI-APInvoices | rank by due date, slice by discount status |
| backlog, orders at risk, on hold | zEI-SalesOrders | slice by RiskFlag, rank by OpenValue |
| jobs late, WIP | zEI-Jobs | slice by RiskFlag, rank by LateDays |
| revenue, top customers/products | zEI-InvoicedSales | filter the period, rank by ExtPrice |
| weird PO costs, overpaying a vendor | zEI-POOutlier | default params, rank by ModZ |
| abnormal supplier invoices | zEI-APInvoiceOutlier | default params, rank by ModZ |

When a question spans tools ("give me the whole picture on customer X"), pull that customer's AR,
their open orders, and their invoiced sales, and synthesize. Do not dump three tables, answer the
question.

## Totals, roll-ups, and trends: sum the raw rows with code

The detail tools return raw rows and do not sum server-side. That is deliberate: raw tools stay
broad and reusable, and the skill does the math. When a question needs an exact dollar total, a
per-customer or per-vendor roll-up, or a per-period trend, do not sum in your head and do not read
the rows into the answer. Instead:

1. Pull only the columns the roll-up needs with `select` (the group key and the measure), with no
   `top` so every row is included.
2. A large result lands in a file rather than your context. Run the bundled `scripts/aggregate.py`
   on that file to group and sum. Only the small summary comes back, so a 30,000-row ledger costs
   a few hundred tokens.

Top customers by total owed (money owed to us, so exclude credit memos and unapplied cash):

```
python scripts/aggregate.py <result_file> --group Customer_Name --sum InvcHead_InvoiceBal \
    --where Calculated_DocType=Invoice --top 15 --count --max Calculated_DaysPastDue
```

Revenue by fiscal period, a trend to chart:

```
python scripts/aggregate.py <result_file> --group InvcHead_FiscalPeriod --sum InvcDtl_ExtPrice --top 24
```

This is why "which customers owe the most" is a real answer and not a top-invoice proxy: a customer
with 500 mid-size invoices only outranks one big invoice when you sum per customer.

Two conditions and a fallback. This needs a client that can run a code step (bash or Python) and
that spills or streams a large result to a file; Cowork and Claude with an analysis tool do both.
In a plain MCP client with no code step, fall back to the cheap proxies (counts, the aging mix, and
top-N by single balance) and say plainly that the exact roll-up needs a code-capable client. A
server-side path also exists and needs no new tools: exposing OData `$apply` on the BAQ tools would
let any client request a grouped sum. That is a platform change, not a pack change.

## Guardrails

- State the basis of every number: the as-of date, the fiscal calendar, and the currency. A
  figure with no basis is a figure someone will misread in a meeting.
- Results are already scoped to the signed-in user by Epicor impersonation. Do not imply the
  answer sees more than that user may see.
- Free tenants enable five tools at once. If a needed tool is not enabled, say which five to turn
  on for the question. The loadouts are Cash and Risk, Revenue, and Anomaly; see the pack README.
- Never invent a number. If a query returns nothing, say so plainly and check whether a filter
  was too tight before concluding "none".
