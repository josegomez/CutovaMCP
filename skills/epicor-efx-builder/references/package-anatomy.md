<!-- Package anatomy — part of the epicor-efx-builder skill. Section numbers match SKILL.md. -->

## 3. Package anatomy

An `.efxj` export is **UTF-8 JSON with a BOM**. Preserve the BOM — Epicor's restore parser rejects an otherwise-valid package if the framing is removed. Read/write with `utf-8-sig`.

### 3.1 Top level

```jsonc
{ "Mode": "Backup", "Version": "5.1.100", "SystemCode": "ERP",
  "LibraryId": "<LibId>",
  "Library": { ... } }
```

`SystemCode` is `ERP` (or `ICE` for a purely framework library). `Version` is the export schema version and `Library.EpicorVersion` (§3.2) the Kinetic app version. On edit, keep the values the environment produced. When **creating** a library with no export in hand, do not invent them — copy both from any current export of the **target** environment (export any small library first), so your package matches that environment's parser; the scaffold's placeholders (`Version` `5.1.100`, `EpicorVersion` `4.2.300`) are only a fallback for recent Kinetic and should be replaced with the target's real values before import.

### 3.2 Library object

```jsonc
"Library": {
  "OriginalID": "<LibId>",          // provenance; may differ from LibraryId after a historical rename — do NOT rewrite to match
  "Description": "<text>",
  "GlobalID": "<guid>",             // stable identity; generate a NEW guid for a brand-new library, preserve on edit
  "EpicorVersion": "4.2.300",       // Kinetic app version the lib targets
  "Revision": 1,
  "Published": true,                // false while drafting; true to make Public functions callable by other libs
  "Private": false,
  "Disabled": false,
  "Mode": 0,
  "AllowCustomCodeWidgets": true,   // required only if the library has a Kind 1 (custom-code-widget) function; a Kind 0 visual function does NOT need it
  "AllowCustomCodeFunctions": true, // required for any Kind 2 function
  "DirectDBAccess": 2,              // 0 = none, 1 = read-only (only Db queries), 2 = read/write (any Db.SaveChanges)
  "OwnedByCompany": "<Company>",
  "Owner": "<UserID>",
  "SharedWithGroup": "<SecGroup>",  // may be absent
  "Functions": [ ... ],
  "LibraryReferences": [ ... ],
  "LibraryMappings": [ ... ]
}
```

Preserve unknown properties and their values on edit. On create, set governance flags deliberately and to the **narrowest** value the functions need: `AllowCustomCodeFunctions:true` only if the library has a Kind 2 function; `AllowCustomCodeWidgets:true` only if the library has a **Kind 1** function (a visual function classified as a custom-code-widget function — see §3.3). A **Kind 0** visual function (standard widgets only, e.g. InvokeBOMethodAction2 / SetArgumentAction / InfoMessageAction) does **not** need this flag — verified against live imports of Kind 0 visual functions with `AllowCustomCodeWidgets:false`. If a library does contain a Kind 1 function and the flag is false, the import fails with *"Library configuration does not allow custom code widget functions"* — so match the flag to the highest kind present. `DirectDBAccess` `0` if no `Db` use, `1` for read-only `Db` queries, `2` only if the code calls `Db.SaveChanges()` (calling a BO that writes does **not** require `2`); `Published:false` while drafting (set `true` only to expose Public functions to other libraries). Fill governance identity from the target environment, not with placeholders: `OwnedByCompany` and the `LibraryMappings` companies come from the environment's company list (the connector's company/plant context, or a company field on any export), and `Owner` is the importing user's ID (the scaffold takes `--company`/`--owner` so no `<...>` literal ships). Never copy a Production company mapping into Testing or another tenant.

### 3.3 Function object

Every entry of `Library.Functions[]`:

```jsonc
{ "FunctionID": "<Fn>",            // unique within the library; select by this, never by array position
  "Description": "<text>",         // may be absent
  "Notes": "<text>",               // may be absent
  "Kind": 2,                        // 0 = standard-widget visual, 1 = custom-code-widget visual, 2 = custom code (JSON-string body)
  "RequireTransaction": false,
  "SingleRowMode": false,
  "Private": false,                 // Private true => callable only within this library (ThisLib), not via EfxLib
  "Disabled": false,
  "Invalid": false,                 // set by Epicor when the last compile failed; never author true
  "Thumbnail": null,
  "FunctionSignature": [ ... ],     // array of parameter objects (see §4); may be null on a legacy function
  "Body": "<see below>" }
```

- **Kind 2** `Body` is a **JSON-encoded string** whose parsed object is `{ "Code": "<C#>", "Usings": "<string>" }` — i.e. double-encoded JSON. Requires `AllowCustomCodeFunctions:true`. See §5.
- **Kind 1** and **Kind 0** `Body` are both a **XAML object-graph string** (namespace/prefix-sensitive) rooted at `DirectiveDefinition2` — the visual widget graph (§6). The difference is classification, not body format: **Kind 1** is a *custom-code-widget* visual function (it contains, or was created to allow, a `CustomCodeAction` widget) and **requires `AllowCustomCodeWidgets:true`**; **Kind 0** is a *standard-widget* visual function (InvokeBOMethodAction2, SetArgumentAction, InfoMessageAction, UpdateTableByQueryAction, …) and needs **no** custom-code flag. When you author a visual function using only standard widgets, set `Kind: 0`; use `Kind: 1` only when the graph includes a `CustomCodeAction`.
- A live export may carry a **null body**; preserve it unless the task explicitly repairs that function.

Do not change `RequireTransaction`, `SingleRowMode`, `Private`, `Disabled`, `Invalid`, or the signature as a side effect of a body edit.

### 3.4 Minimal valid package (copy-and-adapt)

A complete new library with one custom-code function. Serialize with a UTF-8 BOM and no unnecessary whitespace.

```jsonc
{"Mode":"Backup","Version":"5.1.100","SystemCode":"ERP","LibraryId":"MyLib",
 "Library":{
   "OriginalID":"MyLib","Description":"<desc>","GlobalID":"<new-guid>","EpicorVersion":"4.2.300",
   "Revision":1,"Published":false,"Private":false,"Disabled":false,"Mode":0,
   "AllowCustomCodeWidgets":false,"AllowCustomCodeFunctions":true,"DirectDBAccess":0,
   "OwnedByCompany":"<Company>","Owner":"<UserID>","SharedWithGroup":"",
   "Functions":[
     {"FunctionID":"MyFunc","Description":"<desc>","Kind":2,
      "RequireTransaction":false,"SingleRowMode":false,"Private":false,"Disabled":false,"Invalid":false,"Thumbnail":null,
      "FunctionSignature":[
        {"Response":false,"ParameterID":1,"ArgumentName":"iKey","Order":1,"DataType":"System.Int32","Optional":false,"Description":""},
        {"Response":true,"ParameterID":1,"ArgumentName":"oSuccess","Order":1,"DataType":"System.Boolean","Optional":false,"Description":""},
        {"Response":true,"ParameterID":2,"ArgumentName":"oMessage","Order":2,"DataType":"System.String","Optional":false,"Description":""}
      ],
      "Body":"{\"Code\":\"this.oSuccess=false;\\r\\nif(iKey<=0){oMessage=\\\"invalid key\\\";return;}\\r\\noSuccess=true;\",\"Usings\":\"\"}"
     }
   ],
   "LibraryReferences":[],
   "LibraryMappings":[{"Company":"<Company>","Allowed":true}]
 }}
```

Note the three levels of escaping in `Body`: C# source → JSON string (`{"Code":...}`) → JSON string again (the outer `"Body":"..."`). Build the inner object first, `json.dumps` it to a string, assign to `Body`, then `json.dumps` the whole package. The helper script does this for you.

---
