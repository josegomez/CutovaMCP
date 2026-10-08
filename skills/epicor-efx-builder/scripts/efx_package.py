#!/usr/bin/env python3
import argparse, hashlib, json, sys, uuid
import xml.etree.ElementTree as ET
from pathlib import Path

def load(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def has_bom(path):
    try: return Path(path).read_bytes()[:3] == b"\xef\xbb\xbf"
    except Exception: return False
def find_placeholders(doc):
    """Return governance-ish string values still holding an angle-bracket placeholder."""
    hits=[]
    def walk(o, p):
        if isinstance(o, dict):
            for k,v in o.items(): walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i,v in enumerate(o): walk(v, f"{p}[{i}]")
        elif isinstance(o, str) and "<" in o and ">" in o and any(t in o for t in ("<Company>","<UserID>","<LibId>","<guid>","<desc>","<Owner>","<...>")):
            hits.append(p)
    walk(doc, "$"); return hits
def dump(doc, path):
    # Epicor exports EFX JSON with a UTF-8 BOM and rejects a syntactically valid
    # package when that framing is removed.
    Path(path).write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8-sig")
def funcs(doc):
    value = doc.get("Library", {}).get("Functions")
    if not isinstance(value, list): raise ValueError("Library.Functions must be an array")
    return value
def parse_code_body(fn):
    value = fn.get("Body")
    if not isinstance(value, str): raise ValueError(f"{fn.get('FunctionID')}: Body must be a JSON string")
    body = json.loads(value)
    if not isinstance(body, dict): raise ValueError(f"{fn.get('FunctionID')}: Body JSON must be an object")
    return body
def validate_body(fn):
    value=fn.get("Body")
    if value is None: return
    if not isinstance(value,str): raise ValueError(f"{fn.get('FunctionID')}: Body must be a string or null")
    if fn.get("Kind") in (0,1):
        import re as _re
        xml=_re.sub(r'^\s*<\?xml[^>]*\?>', '', value)  # some exports carry a utf-16 declaration
        root=ET.fromstring(xml)
        if root.tag.rsplit('}',1)[-1]!="DirectiveDefinition2":
            raise ValueError(f"{fn.get('FunctionID')}: visual Body root must be DirectiveDefinition2")
    elif fn.get("Kind")==2:
        parse_code_body(fn)
def canon(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def validate(doc, library=None, count=None, target=None, path=None, enforce_io_prefixes=False):
    errors=[]
    if path is not None and not has_bom(path):
        errors.append("file is missing the UTF-8 BOM (Epicor's restore parser requires it)")
    for ph in find_placeholders(doc):
        errors.append(f"unresolved placeholder value at {ph} (replace <...> before import)")
    for key in ("Mode","Version","SystemCode","LibraryId","Library"):
        if key not in doc: errors.append(f"missing top-level {key}")
    lid=doc.get("LibraryId")
    if library and lid != library: errors.append(f"LibraryId is {lid!r}, expected {library!r}")
    try: items=funcs(doc)
    except ValueError as exc: errors.append(str(exc)); items=[]
    ids=[x.get("FunctionID") for x in items]
    if any(not isinstance(x,str) or not x for x in ids): errors.append("every function needs a non-empty FunctionID")
    if len(ids)!=len(set(ids)): errors.append("FunctionID values must be unique")
    if count is not None and len(items)!=count: errors.append(f"function count is {len(items)}, expected {count}")
    if target and ids.count(target)!=1: errors.append(f"target {target!r} occurs {ids.count(target)} times")
    lib=doc.get("Library",{})
    kinds={x.get("Kind") for x in items}
    if 1 in kinds and not lib.get("AllowCustomCodeWidgets"):
        errors.append("library has a Kind 1 (visual/widget) function but AllowCustomCodeWidgets is not true")
    if 2 in kinds and not lib.get("AllowCustomCodeFunctions"):
        errors.append("library has a Kind 2 (custom-code) function but AllowCustomCodeFunctions is not true")
    # signature: unique ParameterID/Order within each direction
    for fn in items:
        sig=fn.get("FunctionSignature")
        if isinstance(sig,list):
            for resp in (True,False):
                grp=[p for p in sig if bool(p.get("Response"))==resp]
                if len({p.get("ParameterID") for p in grp})!=len(grp):
                    errors.append(f"{fn.get('FunctionID')}: duplicate ParameterID in {'response' if resp else 'request'} params")
                if len({p.get("Order") for p in grp})!=len(grp):
                    errors.append(f"{fn.get('FunctionID')}: duplicate Order in {'response' if resp else 'request'} params")
                if enforce_io_prefixes:
                    prefix="o" if resp else "i"
                    for p in grp:
                        name=p.get("ArgumentName")
                        if not isinstance(name,str) or len(name)<2 or not name.startswith(prefix):
                            errors.append(f"{fn.get('FunctionID')}: {'response' if resp else 'request'} ArgumentName {name!r} must start with {prefix!r}")
            # ArgumentName must be ASCII letters and digits only, starting with a letter (Epicor constraint)
            for p in sig:
                name=p.get("ArgumentName")
                if not (isinstance(name,str) and name and name.isascii() and name.isalnum() and name[0].isalpha()):
                    errors.append(f"{fn.get('FunctionID')}: ArgumentName {name!r} must be letters and digits only (a-z, A-Z, 0-9), starting with a letter")
        try: validate_body(fn)
        except Exception as exc: errors.append(str(exc))
    return errors
def snapshot(doc):
    out={"LibraryId":doc.get("LibraryId"),"functionCount":len(funcs(doc)),"functions":{}}
    for fn in funcs(doc):
        structural={k:v for k,v in fn.items() if k!="Body"}
        if fn.get("Kind")==2 and fn.get("Body") is not None:
            body=parse_code_body(fn)
            structural["BodyWithoutCode"]={k:v for k,v in body.items() if k!="Code"}
            body_hash=str(body.get("Code",""))
        else:
            body_hash=str(fn.get("Body"))
        out["functions"][fn["FunctionID"]]={
            "structureSha256":hashlib.sha256(canon(structural).encode()).hexdigest(),
            "bodySha256":hashlib.sha256(body_hash.encode()).hexdigest()}
    return out
def paths(a,b,p="$"):
    if type(a) is not type(b): return [p]
    if isinstance(a,dict):
        out=[]
        for k in sorted(set(a)|set(b)):
            q=f"{p}.{k}"; out += [q] if k not in a or k not in b else paths(a[k],b[k],q)
        return out
    if isinstance(a,list):
        out=[]
        for i in range(max(len(a),len(b))):
            q=f"{p}[{i}]"; out += [q] if i>=len(a) or i>=len(b) else paths(a[i],b[i],q)
        return out
    return [] if a==b else [p]

CRLF="\r\n"
def make_body(code, usings=""):
    return json.dumps({"Code":code,"Usings":usings}, ensure_ascii=False, separators=(",",":"))

def _visual_body(action_xml, display):
    """Wrap a single action widget in a valid one-node DirectiveDefinition2 XAML graph."""
    name="__ReferenceID0"; nid=str(uuid.uuid4())
    return ('<?xml version="1.0" encoding="utf-16"?>'
      '<DirectiveDefinition2 StartNode="{x:Reference '+name+'}" AdditionalUsings="{x:Null}" Version="3" '
      'xmlns="clr-namespace:Ice.Lib.Bpm.Model;assembly=Ice.Lib.Bpm.Shared" '
      'xmlns:ecm="clr-namespace:Epicor.Customization.Metadata;assembly=Epicor.Customization.Core" '
      'xmlns:icbb="clr-namespace:Ice.Contracts.BO.BpMethod;assembly=Ice.Contracts.BO.BpMethod" '
      'xmlns:ilbma="clr-namespace:Ice.Lib.Bpm.Model.Actions;assembly=Ice.Lib.Bpm.Shared" '
      'xmlns:ilbmq="clr-namespace:Ice.Lib.Bpm.Model.Query;assembly=Ice.Lib.Bpm.Shared" '
      'xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib" '
      'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
      '<DirectiveDefinition2.AdditionalReferences><scg:List x:TypeArguments="icbb:ReferencesGroup" Capacity="0" /></DirectiveDefinition2.AdditionalReferences>'
      '<DirectiveDefinition2.Nodes>'
      '<DirectiveStep Next="{x:Null}" x:Name="'+name+'" DisplayName="'+display+'" Id="'+nid+'">'
      '<DirectiveStep.Action>'+action_xml+'</DirectiveStep.Action>'
      '<DirectiveStep.VisualProperties><VisualPropertiesStorage><x:Double x:Key="ElementX">40</x:Double><x:Double x:Key="ElementY">40</x:Double></VisualPropertiesStorage></DirectiveStep.VisualProperties>'
      '</DirectiveStep>'
      '</DirectiveDefinition2.Nodes>'
      '<DirectiveDefinition2.Variables><scg:List x:TypeArguments="DirectiveVariable2" Capacity="0" /></DirectiveDefinition2.Variables>'
      '<DirectiveDefinition2.VisualProperties><VisualPropertiesStorage><x:Double x:Key="ElementX">10</x:Double><x:Double x:Key="ElementY">10</x:Double></VisualPropertiesStorage></DirectiveDefinition2.VisualProperties>'
      '</DirectiveDefinition2>')

_SETARG = ('<ilbma:SetArgumentAction ArgumentName="oSuccess" DataType="System.Boolean" Id="0" TerminateOnError="True" ValidationState="Valid">'
  '<ilbma:SetArgumentAction.Expression><ExpressionDefinition Text="true">'
  '<ExpressionDefinition.TableParameters><scg:List x:TypeArguments="TableParameter" Capacity="0" /></ExpressionDefinition.TableParameters>'
  '</ExpressionDefinition></ilbma:SetArgumentAction.Expression></ilbma:SetArgumentAction>')

_CUSTOMCODE = ('<ilbma:CustomCodeAction PrimaryTable="{x:Null}" Code="this.oSuccess = true;" ExecutionRule="OnceForAllAffected" '
  'Id="0" IsAsync="False" RecordMode="Nothing" TerminateOnError="False" ValidationState="Valid" />')

def scaffold_function(fid, kind=2):
    """Minimal valid function. kind 0 = standard-widget visual (no custom-code flag);
       kind 1 = custom-code-widget visual (needs AllowCustomCodeWidgets); kind 2 = custom code."""
    sig=[
        {"Response":False,"ParameterID":1,"ArgumentName":"iKey","Order":1,"DataType":"System.Int32","Optional":False,"Description":""},
        {"Response":True,"ParameterID":1,"ArgumentName":"oSuccess","Order":1,"DataType":"System.Boolean","Optional":False,"Description":""},
        {"Response":True,"ParameterID":2,"ArgumentName":"oMessage","Order":2,"DataType":"System.String","Optional":False,"Description":""},
    ]
    fn={"FunctionID":fid,"Description":"","Kind":kind,"RequireTransaction":False,"SingleRowMode":False,
        "Private":False,"Disabled":False,"Invalid":False,"Thumbnail":None,"FunctionSignature":sig}
    if kind==2:
        fn["Body"]=make_body("this.oSuccess=false;" + CRLF + "if(iKey<=0){oMessage=\"invalid key\";return;}" + CRLF + "// TODO: implement" + CRLF + "oSuccess=true;")
    elif kind==1:
        fn["Body"]=_visual_body(_CUSTOMCODE, "Custom Code")
    else:
        fn["Body"]=_visual_body(_SETARG, "Set Success")
    return fn

def scaffold_package(lib_id, company="EPIC06", owner="", fid="MyFunc", kind=2):
    # Narrowest flags for the scaffolded body; raise them per SKILL.md §7.3 as you add code.
    return {"Mode":"Backup","Version":"5.1.100","SystemCode":"ERP","LibraryId":lib_id,
        "Library":{"OriginalID":lib_id,"Description":"","GlobalID":str(uuid.uuid4()),"EpicorVersion":"4.2.300",
            "Revision":1,"Published":False,"Private":False,"Disabled":False,"Mode":0,
            "AllowCustomCodeWidgets":(kind==1),"AllowCustomCodeFunctions":(kind==2),"DirectDBAccess":0,
            "OwnedByCompany":company,"Owner":owner,"SharedWithGroup":"",
            "Functions":[scaffold_function(fid,kind)],
            "LibraryReferences":[],
            "LibraryMappings":[{"Company":company,"Allowed":True}]}}

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("validate"); v.add_argument("file"); v.add_argument("--library"); v.add_argument("--count",type=int); v.add_argument("--target"); v.add_argument("--enforce-io-prefixes",action="store_true")
    s=sub.add_parser("snapshot"); s.add_argument("file")
    d=sub.add_parser("diff"); d.add_argument("before"); d.add_argument("after")
    c=sub.add_parser("add-code-comment"); c.add_argument("source"); c.add_argument("output"); c.add_argument("--function",required=True); c.add_argument("--comment",required=True)
    sc=sub.add_parser("scaffold"); sc.add_argument("output"); sc.add_argument("--library",required=True); sc.add_argument("--function",default="MyFunc"); sc.add_argument("--kind",type=int,default=2,choices=(0,1,2)); sc.add_argument("--company",default="EPIC06"); sc.add_argument("--owner",default="")
    a=ap.parse_args()
    if a.cmd=="validate":
        doc=load(a.file); errors=validate(doc,a.library,a.count,a.target,path=a.file,enforce_io_prefixes=a.enforce_io_prefixes)
        print(json.dumps({"valid":not errors,"errors":errors,"snapshot":snapshot(doc) if not errors else None},indent=2)); return 0 if not errors else 2
    if a.cmd=="snapshot": print(json.dumps(snapshot(load(a.file)),indent=2)); return 0
    if a.cmd=="diff":
        before,after=load(a.before),load(a.after)
        print(json.dumps({"changedPaths":paths(before,after),"before":snapshot(before),"after":snapshot(after)},indent=2)); return 0
    if a.cmd=="scaffold":
        doc=scaffold_package(a.library, a.company, a.owner, a.function, a.kind)
        errors=validate(doc, a.library, enforce_io_prefixes=True)
        if errors: raise ValueError("scaffold produced invalid package: "+"; ".join(errors))
        dump(doc, a.output)
        print(json.dumps({"output":a.output,"library":a.library,"function":a.function,"kind":a.kind,"valid":True},indent=2)); return 0
    # add-code-comment
    doc=load(a.source); matches=[x for x in funcs(doc) if x.get("FunctionID")==a.function]
    if len(matches)!=1: raise ValueError(f"expected one function {a.function!r}, found {len(matches)}")
    if matches[0].get("Kind")!=2: raise ValueError("add-code-comment requires a Kind 2 custom-code function")
    body=parse_code_body(matches[0]); code=body.get("Code")
    if not isinstance(code,str): raise ValueError("Body.Code must be a string")
    body["Code"]=a.comment.rstrip("\r\n")+"\r\n"+code
    matches[0]["Body"]=json.dumps(body,ensure_ascii=False,separators=(",",":"))
    errors=validate(doc,doc.get("LibraryId"),len(funcs(doc)),a.function)
    if errors: raise ValueError("; ".join(errors))
    dump(doc, a.output)
    print(json.dumps({"output":a.output,"changedPaths":paths(load(a.source),doc)},indent=2)); return 0
if __name__=="__main__":
    try: sys.exit(main())
    except Exception as exc: print(json.dumps({"error":str(exc)}),file=sys.stderr); sys.exit(1)
