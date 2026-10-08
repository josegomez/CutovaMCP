#!/usr/bin/env python3
"""
aggregate.py - roll up a large BAQ tool result without pulling it into the model.

Executive Insight detail tools (zEI-Receivables, zEI-InvoicedSales, ...) return raw rows and do
not sum server-side. When a result is large the host spills it to a file instead of the model
context. This script reads that file, groups by one column, sums another, and prints a small
table. Only the summary reaches the answer, so a 30,000-row ledger costs a few hundred tokens.

It parses both shapes a tool result can take:
  - TOON: a `value[N]{f1,f2,...}:` header followed by indented comma-separated rows.
  - JSON: `{"value":[ {..}, .. ]}` (OData) or a bare list of objects.

Usage:
  python aggregate.py <result_file> --group <field> --sum <field> [--where F=V ...]
                      [--top N] [--count] [--max <field>]

Examples:
  # Top 15 customers by total open invoice balance (exclude credit memos / unapplied cash)
  python aggregate.py ar.txt --group Customer_Name --sum InvcHead_InvoiceBal \
      --where Calculated_DocType=Invoice --top 15 --count --max Calculated_DaysPastDue

  # Revenue by fiscal period (build a trend to chart)
  python aggregate.py rev.txt --group InvcHead_FiscalPeriod --sum InvcDtl_ExtPrice --top 24
"""
import sys, csv, io, re, json, argparse
from collections import defaultdict


def load_rows(path):
    text = open(path, encoding="utf-8").read()
    # JSON shapes first
    stripped = text.lstrip()
    if stripped[:1] in "{[":
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "value" in data:
                return data["value"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    # TOON shape
    lines = text.splitlines()
    hdr_i = next((i for i, l in enumerate(lines) if re.match(r"\s*value\[\d+\]\{", l)), None)
    if hdr_i is None:
        sys.exit("Could not find a TOON `value[..]{..}:` header or JSON `value` array in the file.")
    fields = re.search(r"\{([^}]*)\}", lines[hdr_i]).group(1).split(",")
    out = []
    for r in lines[hdr_i + 1:]:
        if not r.strip():
            continue
        rec = next(csv.reader(io.StringIO(r.strip())))
        if len(rec) < len(fields):
            continue
        out.append(dict(zip(fields, rec)))
    return out


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--group", required=True)
    ap.add_argument("--sum", required=True)
    ap.add_argument("--where", action="append", default=[], help="FIELD=VALUE equality filter")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--count", action="store_true", help="also show row count per group")
    ap.add_argument("--max", help="also show the max of this field per group")
    a = ap.parse_args()

    rows = load_rows(a.file)
    wf = [w.split("=", 1) for w in a.where]
    total = defaultdict(float)
    cnt = defaultdict(int)
    mx = defaultdict(float)
    grand = 0.0
    kept = 0
    for row in rows:
        if any(str(row.get(k, "")) != v for k, v in wf):
            continue
        val = num(row.get(a.sum))
        if val is None:
            continue
        g = str(row.get(a.group, ""))
        total[g] += val
        cnt[g] += 1
        if a.max:
            m = num(row.get(a.max))
            if m is not None:
                mx[g] = max(mx[g], m)
        grand += val
        kept += 1

    ranked = sorted(total.items(), key=lambda kv: -kv[1])[: a.top]
    print(f"rows parsed: {len(rows)}, rows kept after filter: {kept}")
    print(f"grand total {a.sum}: {grand:,.2f} across {len(total)} groups")
    hdr = f"{a.group:40} {a.sum:>18}"
    if a.count:
        hdr += f"{'count':>8}"
    if a.max:
        hdr += f"{'max ' + a.max:>16}"
    print(hdr)
    for g, v in ranked:
        line = f"{g[:38]:40} {v:>18,.2f}"
        if a.count:
            line += f"{cnt[g]:>8}"
        if a.max:
            line += f"{mx[g]:>16,.0f}"
        print(line)


if __name__ == "__main__":
    main()
