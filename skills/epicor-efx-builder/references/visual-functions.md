<!-- Visual (Kind 1) functions — part of the epicor-efx-builder skill. Section numbers match SKILL.md. -->

## 6. Visual (Kind 1) functions

**Kind 0 vs Kind 1 (and the library flag).** A visual function's `Body` is the same XAML graph whether it is Kind 0 or Kind 1 — the `Kind` is a classification: **Kind 0** = standard-widget visual function (InvokeBOMethodAction2, SetArgumentAction, InfoMessageAction, UpdateTableByQueryAction, …); **Kind 1** = a visual function that contains (or is created to allow) a `CustomCodeAction` widget. Author a graph that uses only standard widgets as **`Kind: 0`** — it imports with `AllowCustomCodeWidgets:false`. Author it as **`Kind: 1`** only when it includes a `CustomCodeAction`, and then the library must have `AllowCustomCodeWidgets:true` or the import fails with *"Library configuration does not allow custom code widget functions"*. (Getting this wrong is a common trap: a plain BO-call/SetArgument graph marked Kind 1 will be rejected unless the flag is on, even though it uses no custom code — mark it Kind 0 instead.)

The body is a **XAML object-graph string** (the MetaFX/BPM designer format), rooted at `DirectiveDefinition2`, stored as one JSON string inside `Body` (so `"` becomes `\"` at the JSON layer; attribute values additionally use XML escaping). It is **not** DataContract or plain XML — it is namespace- and prefix-sensitive XAML, and an incorrectly namespaced graph will import yet fail to deserialize/compile.

**Honesty about this half.** A Kind 2 function can be authored from scratch from this skill alone. A Kind 1 graph is far less forgiving: element prefixes, `{x:...}` markup extensions, and each widget's exact attribute set must be right. The two **reliable** ways to produce a new visual function are: (a) generate the skeleton with `scripts/efx_package.py scaffold --kind 1` and extend it, or (b) export one live function that already contains the widget you need and **clone that node's exact XML**, changing only the semantics. Hand-authoring a large graph from the templates below is possible but must be proven by a **Testing import** (XML/JSON validation cannot detect a XAML deserialization error — see §9). For branching or any widget beyond the four in §6.3, prefer a `CustomCodeAction` widget or a Kind 2 function.

### 6.1 Namespaces (required, exact)

Every graph declares these on the root; elements are prefixed accordingly. Use these exact `clr-namespace`/assembly strings:

| Prefix | Namespace | Used for |
|---|---|---|
| *(default)* | `clr-namespace:Ice.Lib.Bpm.Model;assembly=Ice.Lib.Bpm.Shared` | `DirectiveDefinition2`, `DirectiveStep`, `DirectiveVariable2`, `ParameterBinding2`, `VariableBindingTarget`, `ExpressionBindingTarget`, `ExpressionDefinition`, `TableParameter`, `VisualPropertiesStorage`, `TextNote`, `ColumnBinding` |
| `ilbma:` | `...Ice.Lib.Bpm.Model.Actions;assembly=Ice.Lib.Bpm.Shared` | action widgets: `ilbma:InvokeBOMethodAction2`, `ilbma:CustomCodeAction`, `ilbma:SetArgumentAction`, `ilbma:UpdateTableByQueryAction`, and their property-elements (`ilbma:X.Parameters`, `ilbma:X.Result`, `ilbma:SetArgumentAction.Expression`) |
| `ilbmq:` | `...Ice.Lib.Bpm.Model.Query;assembly=Ice.Lib.Bpm.Shared` | `ilbmq:QueryDefinition`, query rows/tables/relations/criteria |
| `ecm:` | `clr-namespace:Epicor.Customization.Metadata;assembly=Epicor.Customization.Core` | `ecm:TypeRefData` |
| `icbb:` | `clr-namespace:Ice.Contracts.BO.BpMethod;assembly=Ice.Contracts.BO.BpMethod` | `ReferencesGroup` (type arg of the AdditionalReferences list) |
| `scg:` | `clr-namespace:System.Collections.Generic;assembly=mscorlib` (or `System.Private.CoreLib`) | `scg:List` |
| `x:` | `http://schemas.microsoft.com/winfx/2006/xaml` | `x:Array`, `x:Null`, `x:Reference`, `x:Name`, `x:Key`, `x:Double`, `x:Int32`, `x:TypeArguments` |

XAML markup extensions you will use: `{x:Null}` (a null attribute value), `{x:Reference __ReferenceID0}` (a node reference, used by `StartNode` and `Next`).

### 6.2 Graph shape

The body optionally begins with `<?xml version="1.0" encoding="utf-16"?>` (both with and without are valid). Root skeleton:

```xml
<DirectiveDefinition2 StartNode="{x:Reference __ReferenceID0}" AdditionalUsings="{x:Null}" Version="3"
    xmlns="clr-namespace:Ice.Lib.Bpm.Model;assembly=Ice.Lib.Bpm.Shared"
    xmlns:ecm="clr-namespace:Epicor.Customization.Metadata;assembly=Epicor.Customization.Core"
    xmlns:icbb="clr-namespace:Ice.Contracts.BO.BpMethod;assembly=Ice.Contracts.BO.BpMethod"
    xmlns:ilbma="clr-namespace:Ice.Lib.Bpm.Model.Actions;assembly=Ice.Lib.Bpm.Shared"
    xmlns:ilbmq="clr-namespace:Ice.Lib.Bpm.Model.Query;assembly=Ice.Lib.Bpm.Shared"
    xmlns:scg="clr-namespace:System.Collections.Generic;assembly=mscorlib"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <DirectiveDefinition2.AdditionalReferences>
    <scg:List x:TypeArguments="icbb:ReferencesGroup" Capacity="0" />   <!-- extra assemblies for CustomCodeAction widgets -->
  </DirectiveDefinition2.AdditionalReferences>
  <DirectiveDefinition2.Nodes>
    <DirectiveStep Next="{x:Reference __ReferenceID1}" x:Name="__ReferenceID0" DisplayName="<label>" Id="<guid>">
      <DirectiveStep.Action> <!-- exactly one ilbma: action widget --> </DirectiveStep.Action>
      <DirectiveStep.VisualProperties> <!-- designer coords/notes --> </DirectiveStep.VisualProperties>
    </DirectiveStep>
    <DirectiveStep Next="{x:Null}" x:Name="__ReferenceID1" DisplayName="<label>" Id="<guid>"> ... </DirectiveStep>  <!-- terminal: Next = {x:Null} -->
  </DirectiveDefinition2.Nodes>
  <DirectiveDefinition2.Variables>
    <scg:List x:TypeArguments="DirectiveVariable2" Capacity="0" />
  </DirectiveDefinition2.Variables>
  <DirectiveDefinition2.VisualProperties> <!-- canvas coords + per-widget instance counters --> </DirectiveDefinition2.VisualProperties>
</DirectiveDefinition2>
```

**Connecting nodes.** `StartNode` (root attribute) = `{x:Reference <firstNodeName>}`. Each `DirectiveStep` has a unique `x:Name` (`__ReferenceIDn`) and a unique `Id` (guid), and points to its successor with `Next="{x:Reference <nextName>}"`; the last node uses `Next="{x:Null}"`. (Some exports instead nest a `<DirectiveStep.Next>` element containing the next step — either is valid; the flat list with `Next` references is simpler to author.) When you clone or insert a node, mint a new `x:Name` and `Id` and fix both the predecessor's `Next` and this node's `Next` — never reuse or orphan a reference.

### 6.3 The four proven action widgets

Each sits inside `<DirectiveStep.Action>`.

**`ilbma:InvokeBOMethodAction2`** — call a BO method:

```xml
<ilbma:InvokeBOMethodAction2 BusinessObject="SalesOrder" MethodName="GetByID" ObjectNs="BO" ProductCode="Erp"
                             Id="0" TerminateOnError="False" ValidationState="Valid">
  <ilbma:InvokeBOMethodAction2.Parameters>
    <x:Array Type="ParameterBinding2">
      <ParameterBinding2 ParameterDirection="Input" ParameterName="orderNum">
        <ParameterBinding2.BindingTarget>
          <VariableBindingTarget DirectiveLevelVariable="False" VariableName="OrderNum" />   <!-- a signature arg -->
        </ParameterBinding2.BindingTarget>
        <ParameterBinding2.ParamTypeData>
          <ecm:TypeRefData Assembly="{x:Null}" ElementType="{x:Null}" GenericArguments="{x:Null}" Name="Int32" Namespace="System" Options="1" WellknownType="Basic" />
        </ParameterBinding2.ParamTypeData>
      </ParameterBinding2>
    </x:Array>
  </ilbma:InvokeBOMethodAction2.Parameters>
  <ilbma:InvokeBOMethodAction2.Result>
    <ParameterBinding2 ParameterDirection="RetVal" ParameterName="result">
      <ParameterBinding2.BindingTarget>
        <VariableBindingTarget DirectiveLevelVariable="True" VariableName="sots" />           <!-- a directive-level variable -->
      </ParameterBinding2.BindingTarget>
      <ParameterBinding2.ParamTypeData>
        <ecm:TypeRefData ElementType="{x:Null}" GenericArguments="{x:Null}" Assembly="Erp.Contracts.BO.SalesOrder" Name="SalesOrderTableset" Namespace="Erp.Tablesets" Options="2" WellknownType="Tableset" />
      </ParameterBinding2.ParamTypeData>
    </ParameterBinding2>
  </ilbma:InvokeBOMethodAction2.Result>
</ilbma:InvokeBOMethodAction2>
```

Notes: a tableset param passed in/out uses `ParameterDirection="InputOutput"` and a Tableset `TypeRefData`. Provide `InvokeBOMethodAction2.Result` **only** for methods that return a value; omit the element for a `void` method (e.g. `Update`) rather than binding it. Do not also set a `Result="..."` attribute when you use the `.Result` element.

**`ilbma:CustomCodeAction`** — a C# widget in the graph (needs `AllowCustomCodeWidgets:true`). C# goes in the `Code` attribute (XML-escaped); its `using`s go in the root's `AdditionalUsings` attribute (a `\r\n`-joined string, or `{x:Null}`); extra assemblies go in `AdditionalReferences`. Binding is the same `this.<Arg>` as Kind 2.

```xml
<ilbma:CustomCodeAction PrimaryTable="{x:Null}" Code="&lt;C#, XML-escaped&gt;" ExecutionRule="OnceForAllAffected"
                        Id="0" IsAsync="False" RecordMode="Nothing" TerminateOnError="False" ValidationState="Valid" />
```

**`ilbma:SetArgumentAction`** — assign an expression to an output/variable:

```xml
<ilbma:SetArgumentAction ArgumentName="oSuccess" DataType="System.Boolean" Id="0" TerminateOnError="True" ValidationState="Valid">
  <ilbma:SetArgumentAction.Expression>
    <ExpressionDefinition Text="true">
      <ExpressionDefinition.TableParameters><scg:List x:TypeArguments="TableParameter" Capacity="0" /></ExpressionDefinition.TableParameters>
    </ExpressionDefinition>
  </ilbma:SetArgumentAction.Expression>
</ilbma:SetArgumentAction>
```

**`ilbma:UpdateTableByQueryAction`** — set columns on rows a query selects. Columns bind via `ColumnBinding`; the query is an `ilbmq:QueryDefinition` with `ilbmq:` tables/rows/relations and `ConstantCriterion`/`Field` filters. This widget is intricate — clone a live example when you need it rather than hand-authoring the full `QueryDefinition`. Shape:

```xml
<ilbma:UpdateTableByQueryAction Filter="Added" Id="0" IsExtensionTable="False"
     TableName="<tt.Table>" TableRowTypeName="Erp.Tablesets.<X>Row" TerminateOnError="False" ValidationState="Valid">
  <ilbma:UpdateTableByQueryAction.Columns>
    <x:Array Type="ColumnBinding">
      <ColumnBinding ColumnName="<Col>" ColumnType="System.String" IsUd="False">
        <ColumnBinding.BindingTarget><VariableBindingTarget DirectiveLevelVariable="False" VariableName="<Arg>" /></ColumnBinding.BindingTarget>
      </ColumnBinding>
    </x:Array>
  </ilbma:UpdateTableByQueryAction.Columns>
  <ilbma:UpdateTableByQueryAction.Query>
    <ilbmq:QueryDefinition Name="MyQuery"> ... </ilbmq:QueryDefinition>
  </ilbma:UpdateTableByQueryAction.Query>
</ilbma:UpdateTableByQueryAction>
```

### 6.4 Variables, bindings, and types

- **Signature argument** → `<VariableBindingTarget DirectiveLevelVariable="False" VariableName="<ArgumentName>" />`.
- **Scratch/directive variable** (e.g. a fetched tableset passed between widgets) → declare in `DirectiveDefinition2.Variables` as `<DirectiveVariable2 Initializer="{x:Null}" Name="<var>"><DirectiveVariable2.TypeData><ecm:TypeRefData .../></DirectiveVariable2.TypeData></DirectiveVariable2>`, and reference it with `DirectiveLevelVariable="True"`.
- **Literal / expression** → `<ExpressionBindingTarget><ExpressionBindingTarget.ExpressionInfo><ExpressionDefinition Text="<expr>"><ExpressionDefinition.TableParameters><scg:List x:TypeArguments="TableParameter" Capacity="0" /></ExpressionDefinition.TableParameters></ExpressionDefinition></ExpressionBindingTarget.ExpressionInfo></ExpressionBindingTarget>` (e.g. `Text="0"`, `Text="true"`).
- **Unbound** → `<DummyBindingTarget />`.
- **`ecm:TypeRefData`** describes a parameter's .NET type (mirrors `DataTypeInfo` from §4): scalar `Name="Int32" Namespace="System" Assembly="{x:Null}" Options="1" WellknownType="Basic"`; tableset `Name="<X>Tableset" Namespace="Erp.Tablesets" Assembly="Erp.Contracts.BO.<X>" Options="2" WellknownType="Tableset"`. `ElementType`/`GenericArguments` default to `{x:Null}` unless the type is generic (then a nested `<ecm:TypeRefData.GenericArguments><x:Array Type="ecm:TypeRefData">...</x:Array>` lists the type args).

### 6.5 Designer visual state

`DirectiveStep.VisualProperties` and `DirectiveDefinition2.VisualProperties` hold a `VisualPropertiesStorage` with `<x:Double x:Key="ElementX">40</x:Double>` / `ElementY` (canvas coordinates in element text), an optional `<TextNote Text="..." x:Key="Note" Background="Yellow" IsExpanded="False" X="0" Y="0" />`, optional `<LinkProperties x:Key="ExitLink" SourceConnectorId="10" DestinationConnectorId="1"><LinkProperties.Points>...</LinkProperties.Points></LinkProperties>`, and (on the graph-level storage) per-widget counters `<x:Int32 x:Key="Ice.UI.Bpm.Widgets.<Widget>PluginInstanceCounter">n</x:Int32>`. This is designer state, not execution logic — give each node distinct `ElementX`/`ElementY` so the graph is not stacked, and preserve existing values on edit; it need not be elaborate on a hand-built function.

### 6.6 Available widget palette

The serializer knows the full palette even when a graph uses only some: `CustomCodeAction`, `InvokeBOMethodAction2`, `InvokeEpicorFunctionAction2`, `SetArgumentAction`, `SetFieldAction`, `SetByQueryAction`, `SetBpmDataFieldAction`, `FillTableByQueryAction`, `UpdateTableByQueryAction`, `ShowMessageAction`, `RaiseExceptionAction`, `SendMailAction`, `LogMessageAction`, `NotifyCollaborateAction`, `AttachDataTagAction`, `RemoveDataTagAction`, and a Decision (condition/branch) widget; query criteria use `ConstantCriterion`/`Field` with `CompareOption`/`Operator`. Only the four in §6.3 have proven templates here. For any other widget — a Decision branch, `InvokeEpicorFunctionAction2`, `FillTableByQueryAction`, `RaiseExceptionAction`, etc. — either do it in a `CustomCodeAction`/Kind 2 function, or clone the node's exact XML from a live function that uses it. Do not synthesize an unproven widget's XML from its palette name; it will import and then fail to compile.

### 6.7 Building or editing a visual function

- **Edit**: change the action payload while preserving the node `x:Name`/`Id`, `Next` links, bindings, `ecm:TypeRefData`, variables, and visual properties.
- **Insert**: clone a nearby node of the same action type, mint a new `x:Name`+`Id`, splice the predecessor's `Next` and this node's `Next`, and confirm every `{x:Reference}` resolves exactly once.
- **Create**: start from `scripts/efx_package.py scaffold --kind 1` (a valid StartNode → `SetArgumentAction` graph) and add nodes, or assemble per §6.2 using §6.3 widgets. Declare each used signature argument via a `VariableBindingTarget` (`DirectiveLevelVariable="False"`); declare scratch values in `Variables`; give nodes coordinates. Validate the XML root (§9), then **import into Testing** to prove it deserializes and compiles before Production.

### 6.8 Serializer conventions and tolerances

- **`scg:List Capacity`** is a hint that normally equals the child count (e.g. `Capacity="0"` when empty). Set it to the number of items you add; the deserializer is not strict about the exact value, so a slightly-off capacity is not what breaks a graph — a wrong prefix/namespace or a bad `{x:Reference}` is.
- **`PluginInstanceCounter` entries** in `DirectiveDefinition2.VisualProperties` are designer bookkeeping (how many of each widget the designer has created). They are not required for execution; leave existing ones intact on edit and do not worry about incrementing them on a hand-inserted node.
- **An unbound signature argument** (declared but never referenced by any widget) is harmless — it simply isn't used. Remove it only if the intent is to change the signature.
- **`ValidationState`** on a widget is a designer status; author `Valid`. **`Id="0"`** on an action is the per-widget internal id and can stay `0`; node identity is carried by the `DirectiveStep`'s `x:Name`/`Id`, which must be unique.
