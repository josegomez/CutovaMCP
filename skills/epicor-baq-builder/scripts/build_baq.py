#!/usr/bin/env python3
"""
build_baq.py — build an importable Epicor .baq from the bundled BasicBAQ template.

Proven live on Kinetic 2025+ (simple joins, criteria, group-by, IN-lists, and a
recursive CTE). Usage: import the helpers, define rows, call build(). Two runnable
examples at the bottom: a simple join query and a recursive CTE.

Encodes every hard-won gotcha:
  - CRLF line endings + BOM in the template XML
  - XML escaping (the <> operator breaks the file if written raw)
  - element order per row type (matches the embedded xs:schema)
  - SQ (subquery-as-table) refs = BARE SubQueryID GUID, no dot
  - CTE references aliased with the CTE's exact Name; SQ table = child in joins
  - criteria collections: Seq/AndOr restart per table + per subquery; first row
    of each collection MUST have empty AndOr
"""
import re, zipfile, os, uuid, shutil
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

EOL = "\r\n"  # template uses CRLF


class Baq:
    """Loads the template and accumulates rows. All helpers take the SubQueryID
    (sq) explicitly so multi-subquery BAQs (CTEs, unions) are natural."""

    def __init__(self, template_baq, workdir, company="C001"):
        self.workdir = workdir
        os.makedirs(f"{workdir}/x", exist_ok=True)
        with zipfile.ZipFile(template_baq) as z:
            for i in z.infolist():
                open(f"{workdir}/x/{i.filename}", "wb").write(z.read(i.filename))
        self.xml = open(f"{workdir}/x/DynamicQuery", encoding="utf-8-sig", newline="").read()
        self.company = company
        self.qid = re.search(r"<QueryID>([^<]+)</QueryID>", self.xml).group(1)
        # the template's single TopLevel subquery id — reuse it for simple BAQs
        self.template_sq = re.search(r"<SubQueryID>([^<]+)</SubQueryID>", self.xml).group(1)
        self.rows = []

    # ------------------------------------------------------------ low level
    def _row(self, tag, vals):
        parts = [f"  <{tag}>"]
        for k, v in vals:
            v = escape(str(v))
            parts.append(f"    <{k}>{v}</{k}>" if v != "" else f"    <{k} />")
        parts.append(f"  </{tag}>")
        self.rows.append(EOL.join(parts))

    # ------------------------------------------------------------ structure
    def subquery(self, name, typ, seq, leftp="", rightp=""):
        """Add a subquery; returns its new SubQueryID GUID.
        typ: TopLevel | CTE | InnerSubQuery | Union | UnionAll | Intersect | Except.
        Seq order = set-operation chaining; LeftP='(' on the first member and
        RightP=')' on the last groups a union/recursive-CTE block.
        NOTE: when you add your own subqueries, also call calc_tt(sq) for each,
        and use strip_template(all_seed=True) so the template's TopLevel goes away."""
        sq = str(uuid.uuid4())
        self._row("QuerySubQueryDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("Name", name), ("Type", typ), ("Seq", seq), ("IsUnion", "false"),
            ("LeftP", leftp), ("RightP", rightp), ("SelectListClause", "All"),
            ("TopRowExpr", "0"), ("TopInPercent", "false"), ("TopWithTies", "false")])
        return sq

    def calc_tt(self, sq):
        """The mandatory 'Calculated' pseudo-table — one per subquery you create."""
        self._row("QueryTableDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", "Calculated"), ("Seq", "-1"), ("DBSchemaName", ""),
            ("DBTableName", ""), ("TableType", "TT"), ("IsSummaryTable", "false"),
            ("IsVisibleInDesigner", "false"), ("Modifiers", ""), ("SystemFlag", "false"),
            ("PivotFunction", ""), ("PivotDataType", ""), ("PivotFieldFormat", "")])

    def table(self, sq, tid, seq, schema, tbl):
        """Normal DB table. tid = alias (must be unique in the subquery)."""
        self._row("QueryTableDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", tid), ("Seq", seq), ("DBSchemaName", schema),
            ("DBTableName", tbl), ("TableType", "DB"), ("IsSummaryTable", "false"),
            ("IsVisibleInDesigner", "true"), ("Modifiers", ""), ("SystemFlag", "false"),
            ("PivotFunction", ""), ("PivotDataType", ""), ("PivotFieldFormat", "")])

    def sq_table(self, sq, alias, seq, target_sq):
        """Reference another subquery as a table. target_sq = its SubQueryID GUID
        (stored BARE — never add a dot). If the target is a CTE, alias MUST be the
        CTE's Name (mismatched aliases fail at execution, not import)."""
        self._row("QueryTableDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", alias), ("Seq", seq), ("DBSchemaName", ""),
            ("DBTableName", target_sq), ("TableType", "SQ"), ("IsSummaryTable", "false"),
            ("IsVisibleInDesigner", "true"), ("Modifiers", ""), ("SystemFlag", "false"),
            ("PivotFunction", ""), ("PivotDataType", ""), ("PivotFieldFormat", "")])

    # ------------------------------------------------------------ fields
    def _fld(self, sq, tid, fname, seq, dtype, fmt, label, schema, tbl, dbf, calc, formula, alias):
        self._row("QueryFieldDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", tid), ("FieldName", fname), ("Seq", seq),
            ("DBSchemaName", schema), ("DBTableName", tbl), ("DBFieldName", dbf),
            ("DataType", dtype), ("Description", ""), ("External", "false"),
            ("IsCalculated", calc), ("Formula", formula), ("FieldFormat", fmt),
            ("FieldLabel", label), ("LikeDataFieldTableID", ""), ("LikeDataFieldSeq", "0"),
            ("Aggregation", ""), ("IsGroupBy", "false"), ("UseLike", "false"),
            ("LikeDataFieldName", ""), ("Updatable", "false"), ("RaiseEvent", "false"),
            ("QuickSearchID", ""), ("DropDown", "false"), ("UpdInitExpression", ""),
            ("Alias", alias), ("IsRequired", "false"), ("IsReadOnly", "false"),
            ("DefaultValue", ""), ("SystemFlag", "false"),
            ("SubquerySet_Alias", ""), ("SubquerySet_DataType", "")])

    def field(self, sq, tid, fname, seq, dtype, fmt, label, schema="Erp", tbl=None):
        """Display a DB column. The server hydrates description/format/caption/Like
        from the data dictionary on import, so this minimum is enough.
        Seq must be UNIQUE across ALL fields of the subquery (regular AND
        calculated share one sequence). When adding fields to an EXISTING BAQ,
        scan its current QueryField Seq values and use max+1 — never reuse."""
        self._fld(sq, tid, fname, seq, dtype, fmt, label, schema, tbl or tid, fname,
                  "false", "", f"{tid}_{fname}")

    def calc_field(self, sq, fname, seq, dtype, fmt, label, formula):
        """Calculated field: formula is plain T-SQL; may use Constants.<Name>,
        {ScalarSubqueryName}, and <SQalias>.<inner Alias> references.
        A calc formula that is just '<SQalias>.<innerAlias>' passes an SQ column
        through as an output — the proven way to line up union-member columns."""
        self._fld(sq, "Calculated", fname, seq, dtype, fmt, label, "", "", "",
                  "true", formula, f"Calculated_{fname}")

    def sq_field(self, sq, sq_alias, inner_alias, seq, dtype, fmt, label, db_field):
        """Display a subquery table's column directly — NO calc field needed.
        inner_alias = the field's Alias inside the referenced subquery (e.g.
        'Company_Address1'); db_field = the original DB column ('Address1').
        Verified designer-native pattern (works at top level and in union members)."""
        self._fld(sq, sq_alias, inner_alias, seq, dtype, fmt, label, "", "", db_field,
                  "false", "", inner_alias)

    def ud_table(self, sq, base_alias, seq="101", schema="Erp", base_table=None):
        """MANDATORY whenever any _c field is used (displayed OR joined): add the
        hidden <Table>_UD extension + its FK join. Reference every _c field with
        TableID=<base>_UD afterwards. Referencing _c on the base table works in the
        BAQ Designer (it auto-attaches _UD) but FAILS at layer/grid runtime with
        'Invalid column name' — ExecuteBaq does not auto-attach. Returns the UD alias."""
        ud = f"{base_alias}_UD"
        self._row("QueryTableDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", ud), ("Seq", seq), ("DBSchemaName", schema),
            ("DBTableName", f"{base_table or base_alias}_UD"), ("TableType", "UD"),
            ("IsSummaryTable", "false"), ("IsVisibleInDesigner", "false"), ("Modifiers", ""),
            ("SystemFlag", "false"), ("PivotFunction", ""), ("PivotDataType", ""),
            ("PivotFieldFormat", "")])
        rid = self.relation(sq, base_alias, ud, "Inner", is_fk="true")
        self.relfield(sq, rid, "1", "SysRowID", "ForeignSysRowID",
                      "uniqueidentifier", "uniqueidentifier")
        return ud

    def pivot_sq_table(self, sq, alias, seq, target_sq, pivot_function, pivot_dtype, pivot_fmt):
        """Reference a subquery as a PIVOTED table (cross-tab). pivot_function =
        aggregate over the inner value alias, e.g. "sum(PORel_RelQty)" or
        "count( InvcHead1_InvoiceNum )". Pair with pivot_for() for the FOR clause,
        then display each pivot value via sq_field(..., inner_alias='<value>',
        db_field='<value>') — e.g. FieldName '1', DBFieldName '1'."""
        self._row("QueryTableDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", alias), ("Seq", seq), ("DBSchemaName", ""),
            ("DBTableName", target_sq), ("TableType", "SQ"), ("IsSummaryTable", "false"),
            ("IsVisibleInDesigner", "true"), ("Modifiers", "Pivot"), ("SystemFlag", "false"),
            ("PivotFunction", pivot_function), ("PivotDataType", pivot_dtype),
            ("PivotFieldFormat", pivot_fmt)])

    def pivot_for(self, sq, pivot_alias, spread_inner_alias, dtype, values, seq="1", andor=""):
        """The pivot FOR clause: an IN criterion (CriteriaType=3) on the pivoted SQ
        table listing the spreading column's values — each value becomes an output
        column. spread_inner_alias e.g. 'InvcHead1_FiscalPeriod'; values e.g.
        [str(n) for n in range(1,13)]."""
        vsid = self.new_valueset_id()
        self.where(sq, pivot_alias, seq, spread_inner_alias, dtype, "IN", andor,
                   rvalue=vsid, is_const="false", criteria_type="3")
        for v in values:
            self.valueset_item(vsid, v)

    # ------------------------------------------------------------ joins
    def relation(self, sq, parent, child, join_type="Inner", is_fk="false"):
        """Add a join, returns its RelationID for relfield(). Inner | LeftOuter.
        If one side is an SQ/CTE table, it goes on the CHILD side."""
        rid = str(uuid.uuid4())
        self._row("QueryRelationDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("RelationID", rid), ("IsFK", is_fk), ("ParentTableID", parent),
            ("ChildTableID", child), ("JoinType", join_type), ("OuterJoin", "false")])
        return rid

    def relfield(self, sq, rid, seq, pfield, cfield, pdt="nvarchar", cdt="nvarchar"):
        """One ON pair. Use zDataRelationships output when the dictionary knows the
        join. For SQ children, cfield = the inner field Alias (e.g. OrderHedA_Company)."""
        self._row("QueryRelationFieldDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("RelationID", rid), ("Seq", seq), ("ParentFieldName", pfield),
            ("ParentFieldDataType", pdt), ("ParentFieldIsExpr", "false"), ("ChildFieldName", cfield),
            ("ChildFieldDataType", cdt), ("ChildFieldIsExpr", "false"), ("AndOr", "And"),
            ("Neg", "false"), ("LeftP", ""), ("RightP", ""), ("CompOp", "=")])

    # ------------------------------------------------------------ criteria etc.
    def where(self, sq, tid, seq, fname, dtype, op, andor, *, rvalue="", to_table="",
              to_field="", to_dtype="", is_const="true", criteria_type="2", use_having="false"):
        """One criterion. criteria_type: '2'=Table Criteria (normal WHERE on a table
        field — the default), '0'=SubQuery Criteria (REQUIRED for calculated fields
        and cross-table OR), '1'=HAVING (with use_having='true').
        Seq/AndOr restart per collection (per table AND per subquery tab): the FIRST
        criterion of each collection must have andor='' or the designer breaks.
        Value shapes: const -> rvalue='literal'; param -> rvalue='@Param';
        field -> is_const='false' + to_*; IN-list -> op='IN', is_const='false',
        rvalue=valueset id from new_valueset_id() + valueset_item() rows."""
        self._row("QueryWhereItemDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", tid), ("CriteriaID", str(uuid.uuid4())), ("Seq", seq),
            ("FieldName", fname), ("DataType", dtype), ("CompOp", op), ("AndOr", andor),
            ("Neg", "false"), ("LeftP", ""), ("RightP", ""), ("IsConst", is_const),
            ("CriteriaType", criteria_type), ("UseHaving", use_having), ("ToTableID", to_table),
            ("ToFieldName", to_field), ("ToDataType", to_dtype), ("RValue", rvalue),
            ("ExtSecurity", "false")])

    def new_valueset_id(self):
        return "_where-" + str(uuid.uuid4().int % 10**19)

    def valueset_item(self, vsid, value):
        self._row("QueryValueSetItemsDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("ValueSetID", vsid), ("ItemValue", value)])

    def groupby(self, sq, expression, seq):
        self._row("QueryGroupByDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("GroupByID", str(uuid.uuid4())), ("Expression", expression),
            ("Seq", seq), ("SystemFlag", "false")])

    def sortby(self, sq, tid, fname, seq, asc="true"):
        self._row("QuerySortByDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("SubQueryID", sq), ("TableID", tid), ("FieldName", fname), ("Seq", seq),
            ("IsAsc", asc), ("DisplayName", "")])

    def parameter(self, pid, ptype, fmt, seq="1", skip_if_empty="false", label="",
                  mandatory="false", default="", control_type="Standard"):
        """Declare a parameter AND its prompt control together. A parameter needs
        BOTH rows — QueryParameterDesigner (declaration, incl. ParameterLabel) and
        QueryCtrlDesigner (the runtime prompt; without it the parameter prompt does
        not render and the query fails to collect the value). The designer always
        creates both. fmt = display format for the prompt, e.g. 'x(8)' or '{date}';
        seq = prompt order. Reference in criteria as rvalue='@<pid>'.
        control_type: Standard | DropDown (add ctrl_value rows) | ItemList (IN @pid)."""
        self._row("QueryParameterDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("ParameterID", pid), ("ParameterType", ptype), ("ParameterLabel", label),
            ("SkipIfEmpty", skip_if_empty)])
        cid = str(uuid.uuid4())
        self._row("QueryCtrlDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("ControlID", cid), ("DataSource", pid), ("DataType", ptype),
            ("FieldFormat", fmt), ("IsMandatory", mandatory), ("DefaultValue", default),
            ("ControlType", control_type), ("SourceType", "1"), ("ListSource", ""),
            ("DisplayColumn", ""), ("ValueColumn", ""), ("Seq", seq)])
        return cid

    def ctrl_value(self, control_id, stored_value, display_text, seq):
        """One dropdown option for a ControlType='DropDown' parameter control."""
        self._row("QueryCtrlValuesDesigner", [("Company", self.company), ("QueryID", self.qid),
            ("ControlID", control_id), ("ID", stored_value), ("Val", display_text), ("Seq", seq)])

    # ------------------------------------------------------------ build
    def strip_template(self, all_seed=False):
        """Remove the template's seed rows. all_seed=True also removes the template
        TopLevel subquery + its table rows (incl. the Calculated row) - do this when
        you created your own subqueries; otherwise keep them and reuse template_sq."""
        x = self.xml
        if all_seed:
            x = re.sub(r"  <QuerySubQueryDesigner>.*?</QuerySubQueryDesigner>\r?\n", "", x, flags=re.S)
            x = re.sub(r"  <QueryTableDesigner>.*?</QueryTableDesigner>\r?\n", "", x, flags=re.S)
        else:
            x = re.sub(r"  <QueryTableDesigner>(?:(?!</QueryTableDesigner>).)*?<TableID>Company</TableID>"
                       r".*?</QueryTableDesigner>\r?\n", "", x, flags=re.S)
        x = re.sub(r"  <QueryFieldDesigner>.*?</QueryFieldDesigner>\r?\n", "", x, flags=re.S)
        assert "<TableID>Company</TableID>" not in x, "template seed rows not removed"
        self.xml = x

    def _validate_seqs(self, xml_text):
        """QueryField.Seq must be UNIQUE per subquery (regular + calculated fields
        share ONE sequence space — it is the display order the designer edits by).
        Duplicates import without error but corrupt the field grid in the
        Calculated Field Editor / designer (seen live: two fields both Seq 13).
        Same check for QueryTable.Seq per subquery (Calculated -1 exempt only once)."""
        import xml.etree.ElementTree as _ET
        from collections import Counter
        r = _ET.fromstring(xml_text)
        strip = lambda t: t.split('}')[-1]
        for tag, what in (("QueryFieldDesigner", "QueryField"), ("QueryTableDesigner", "QueryTable")):
            seqs = Counter()
            for c in r:
                if strip(c.tag) != tag:
                    continue
                d = {strip(e.tag): (e.text or '') for e in c}
                seqs[(d.get('SubQueryID'), d.get('Seq'))] += 1
            dups = {k: v for k, v in seqs.items() if v > 1}
            assert not dups, f"DUPLICATE {what}.Seq per subquery — would corrupt designer ordering: {dups}"

    def build(self, description, out_path):
        x = self.xml.replace("<Description>Basic BAQ Template</Description>",
                             f"<Description>{escape(description)}</Description>")
        x = x.replace("</BAQDesignerDataSet>", EOL.join(self.rows) + EOL + "</BAQDesignerDataSet>")
        self._validate_seqs(x)
        open(f"{self.workdir}/x/DynamicQuery", "w", encoding="utf-8", newline="").write(x)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in ["BAQVersion", "DynamicQuery", "DynamicQueryDesign", "QueryDependencies"]:
                z.write(f"{self.workdir}/x/{f}", f)
        ET.parse(f"{self.workdir}/x/DynamicQuery")  # well-formedness check
        print(f"built {out_path} ({os.path.getsize(out_path)} bytes)")
        # then: request_file_upload -> curl PUT -> ImportBAQ(BAQID=<name>) ->
        # GetBAQDefinition, and for subquery/CTE queries have the user EXECUTE it.


# ==================== Example 1: simple two-table join ====================
def example_simple():
    b = Baq("../assets/BasicBAQ_template.baq", "/tmp/baq1")
    sq = b.template_sq          # reuse the template's TopLevel subquery
    b.strip_template()          # keep TopLevel + Calculated row, drop seed table/field
    b.table(sq, "OrderHed", "1", "Erp", "OrderHed")
    b.table(sq, "OrderDtl", "2", "Erp", "OrderDtl")
    r = b.relation(sq, "OrderHed", "OrderDtl", "Inner", "true")
    b.relfield(sq, r, "1", "Company", "Company")
    b.relfield(sq, r, "2", "OrderNum", "OrderNum", "int", "int")
    b.field(sq, "OrderHed", "OrderNum", "1", "int", "->>,>>>,>>9", "Order")
    b.field(sq, "OrderDtl", "PartNum", "2", "nvarchar", "x(50)", "Part")
    b.calc_field(sq, "DaysOld", "3", "int", "->>,>>>,>>9", "Days Old",
                 "datediff(day, OrderHed.OrderDate, Constants.Today)")
    b.where(sq, "OrderHed", "1", "OpenOrder", "bit", "=", "", rvalue="true")
    b.sortby(sq, "OrderHed", "OrderNum", "1")
    b.build("Open orders demo", "/tmp/baq1/OpenOrdersDemo.baq")


# ============ Example 2: recursive CTE (explode a delimited list) ============
# Proven pattern incl. the three execution-time rules: bare GUID SQ refs,
# CTE reference aliased with the CTE's exact Name, SQ table as join CHILD.
def example_recursive_cte():
    b = Baq("../assets/BasicBAQ_template.baq", "/tmp/baq2")
    cte = b.subquery("RepList", "CTE", "1", leftp="(")            # anchor
    rec = b.subquery("RepListNext", "UnionAll", "2", rightp=")")  # recursive member
    tlq = b.subquery("TopLevelQuery", "TopLevel", "3")
    b.strip_template(all_seed=True)
    for s in (cte, rec, tlq):
        b.calc_tt(s)
    # anchor: first entry of each list
    b.table(cte, "OrderHedA", "1", "Erp", "OrderHed")
    b.field(cte, "OrderHedA", "Company", "1", "nvarchar", "x(8)", "Company", tbl="OrderHed")
    b.field(cte, "OrderHedA", "OrderNum", "2", "int", "->>>>>>>>9", "Order", tbl="OrderHed")
    b.field(cte, "OrderHedA", "SalesRepList", "3", "nvarchar", "x(200)", "Reps", tbl="OrderHed")
    b.calc_field(cte, "Idx", "4", "int", ">>9", "Idx", "1")
    b.calc_field(cte, "RepCode", "5", "nvarchar", "x(8)", "Rep",
                 "[Ice].entry(1, OrderHedA.SalesRepList, '~')")
    b.where(cte, "OrderHedA", "1", "SalesRepList", "nvarchar", "<>", "", rvalue="")
    # recursive member: references the CTE itself; columns align with anchor by Seq
    b.sq_table(rec, "CTELoop", "1", cte)
    b.calc_field(rec, "Company", "1", "nvarchar", "x(8)", "Company", "CTELoop.OrderHedA_Company")
    b.calc_field(rec, "OrderNum", "2", "int", "->>>>>>>>9", "Order", "CTELoop.OrderHedA_OrderNum")
    b.calc_field(rec, "SalesRepList", "3", "nvarchar", "x(200)", "Reps",
                 "CTELoop.OrderHedA_SalesRepList")
    b.calc_field(rec, "Idx", "4", "int", ">>9", "Idx", "CTELoop.Calculated_Idx + 1")
    b.calc_field(rec, "RepCode", "5", "nvarchar", "x(8)", "Rep",
                 "[Ice].entry(CTELoop.Calculated_Idx + 1, CTELoop.OrderHedA_SalesRepList, '~')")
    b.where(rec, "Calculated", "1", "RepCode", "nvarchar", "<>", "", rvalue="",
            criteria_type="0")  # terminates recursion; calc field => subquery criteria
    # top level: CTE ref MUST be aliased with the CTE's Name and be the join CHILD
    b.table(tlq, "OrderHed", "1", "Erp", "OrderHed")
    b.sq_table(tlq, "RepList", "2", cte)
    r = b.relation(tlq, "OrderHed", "RepList")
    b.relfield(tlq, r, "1", "OrderNum", "OrderHedA_OrderNum", "int", "int")
    b.relfield(tlq, r, "2", "Company", "OrderHedA_Company")
    b.field(tlq, "OrderHed", "OrderNum", "1", "int", "->>>>>>>>9", "Order")
    b.calc_field(tlq, "RepCode", "2", "nvarchar", "x(8)", "Sales Rep", "RepList.Calculated_RepCode")
    b.field(tlq, "OrderHed", "DocTotalCharges", "3", "decimal", "->>,>>>,>>9.99", "Order Total")
    b.calc_field(tlq, "RepAmount", "4", "decimal", "->>,>>>,>>9.99", "Rep Amount",
                 "OrderHed.DocTotalCharges * (CASE RepList.Calculated_Idx"
                 " WHEN 1 THEN OrderHed.RepSplit1 WHEN 2 THEN OrderHed.RepSplit2"
                 " WHEN 3 THEN OrderHed.RepSplit3 WHEN 4 THEN OrderHed.RepSplit4"
                 " WHEN 5 THEN OrderHed.RepSplit5 ELSE 0 END) / 100.0")
    b.build("Rep split allocation demo", "/tmp/baq2/RepSplitDemo.baq")


if __name__ == "__main__":
    example_simple()
