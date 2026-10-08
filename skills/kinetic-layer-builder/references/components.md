# Kinetic App Studio Component Catalog — Reference

Derived from observed runtime behavior and App Studio output. Property surfaces below reflect the default models the controls start with and the keys the App Studio property panel writes into layer JSON.

---

## 1. Component registries (type string → component)

### 1.1 ERP registry

PascalCase `controlTypeId`s are registered with `EpComponentFactoryService`; a control map translates the kebab-case **sourceTypeId used in layer JSON** to the controlTypeId. The complete control map (this is the exhaustive list of `erp-*` sourceTypeIds usable in a layer):

| sourceTypeId | controlTypeId | component class |
|---|---|---|
| `erp-attachments` | ErpAttachments | ErpAttachmentsComponent |
| `erp-button` | ErpButton | ErpButtonComponent |
| `erp-check-box` | ErpCheckBox | ErpCheckBoxComponent |
| `erp-combo-box` | ErpComboBox | ErpComboBoxComponent |
| `erp-date-picker` | ErpDatePicker | ErpDatePickerComponent |
| `erp-edge-agent-error` | ErpEdgeAgentErrorComponent | ErpEdgeAgentErrorComponent |
| `erp-gl-account-editor` | ErpGlAccountEditor | ErpGlAccountEditorComponent |
| `erp-gl-multibook-account-editor` | ErpGlMultibookAccountEditor | ErpGlMultibookAccountEditorComponent |
| `erp-gl-control-panel` | ErpGlControlPanel | ErpGlControlPanelComponent |
| `erp-numeric-box` | ErpNumericBox | ErpNumericBoxComponent |
| `erp-print-output-format` | ErpPrintOutputFormat | ErpPrintOutputFormatComponent |
| `erp-print-report` | ErpPrintReport | ErpPrintReportComponent |
| `erp-email` | ErpEmail | ErpEmailComponent |
| `erp-radio-button` | ErpRadioButton | ErpRadioButtonComponent |
| `erp-process-set` | ErpProcessSet | ErpProcessSetComponent |
| `erp-server-folder-picker` | ErpServerFolderPicker | ErpServerFolderPickerComponent |
| `erp-printer-selector` | ErpPrinterSelector | ErpPrinterSelectorComponent |
| `erp-shape` | ErpShape | ErpShapeComponent |
| `erp-text-area` | ErpTextArea | ErpTextAreaComponent |
| `erp-text-box` | ErpTextBox | ErpTextBoxComponent |
| `erp-relationship-map` | ErpRelationshipMap | ErpRelationshipMapComponent |
| `erp-time-picker` | ErpTimePicker | ErpTimePickerComponent |
| `erp-token-date` | ErpTokenDate | ErpTokenDateComponent |
| `erp-server-file-picker` | ErpServerFilePicker | ErpServerFilePickerComponent |
| `erp-server-file-box` | ErpServerFileBox | ErpServerFileBoxComponent |
| `erp-file-box` | ErpFileBox | ErpFileBoxComponent |
| `erp-selection-list` | ErpSelectionList | ErpSelectionListComponent |
| `erp-server-folder-box` | ErpServerFolderBox | ErpServerFolderBoxComponent |
| `erp-currency-box` | ErpCurrencyBox | ErpCurrencyBoxComponent |
| `erp-currency-child-box` | ErpCurrencyChildBox | ErpCurrencyChildBoxComponent |
| `erp-grid` | ErpGrid | ErpGridComponent |
| `erp-list-box` | ErpListBox | ErpListBoxComponent |
| `erp-picture-box` | ErpPictureBox | ErpPictureBoxComponent |
| `erp-rich-text-editor` | ErpRichTextEditor | ErpRichTextEditorComponent |
| `erp-currency-selector` | ErpCurrencySelector | ErpCurrencySelectorComponent |
| `erp-confirm-form-options` | ErpConfirmFormOptions | ErpConfirmFormOptionsComponent |
| `erp-panel-card-grid` | ErpPanelCardGrid | ErpPanelCardGridComponent |
| `erp-call-log` | ErpCallLog | ErpCallLogComponent |
| `erp-field-help` | ErpFieldHelp | ErpFieldHelpComponent |
| `erp-memos` | ErpMemos | ErpMemosComponent |
| `erp-change-log` | ErpChangeLog | ErpChangeLogComponent |
| `erp-dynamic` | ErpDynamic | ErpDynamicComponent |
| `erp-dynamic-sliding-panel` | ErpDynamicSlidingPanel | ErpDynamicSlidingPanelComponent |
| `erp-search-selector` | ErpSearchSelector | ErpSearchSelectorComponent |
| `erp-baq-search` | ErpBaqSearch | ErpBaqSearchComponent |
| `erp-part-rev-desc` | ErpPartRevDesc | ErpPartRevDescComponent |
| `erp-qty-uom` | ErpQtyUom | ErpQtyUomComponent |
| `erp-fiscal-year-suffix` | ErpFiscalYearSuffix | ErpFiscalYearSuffixComponent |
| `erp-data-tree` | ErpDataTree | ErpDataTreeComponent |
| `erp-foreign-language-description` | ErpForeignLanguageDescription | ErpForeignLanguageDescriptionComponent |
| `erp-tag` | ErpTag | ErpTagComponent |
| `erp-panel-card` | ErpPanelCard | ErpPanelCardComponent |
| `erp-website` | ErpWebsite | ErpWebsiteComponent |
| `erp-grow-widget` | ErpGrowWidget | ErpGrowWidgetComponent |
| `erp-foreign-lang-desc-text-box` | ErpForeignLangDescTextBox | ErpForeignLangDescTextBoxComponent |
| `erp-auto-complete-ep-binding` | ErpAutoCompleteEpBinding | ErpAutoCompleteEpBindingComponent |
| `erp-panel-card-gantt` | ErpPanelCardGantt | ErpPanelCardGanttComponent |
| `erp-panel-user-preference` | ErpGanttUserPreferences | ErpGanttUserPreferencesComponent |
| `erp-pdf-viewer` | ErpPdfViewer | ErpPdfViewerComponent |
| `erp-link-combo-box` | ErpLinkComboBox | ErpLinkComboBoxComponent |
| `erp-pe-log-viewer` | ErpPELogViewer | ErpPELogViewerComponent |
| `erp-baq-info-zone-sliding-panel` | ErpBaqInfoZoneSlidingPanel | ErpBaqInfoZoneSlidingPanelComponent |
| `erp-data-tags-sliding-panel` | ErpDataTagsSlidingPanel | ErpDataTagsSlidingPanelComponent |
| `erp-data-tags-search` | ErpDataTagsSearch | ErpDataTagsSearchComponent |

Additionally registered directly under their kebab id (usable as sourceTypeId): `erp-panel-card`, `erp-panel-card-grid`, `erp-panel-card-gantt`, `erp-relationship-map`. Also registered (controlTypeId only, no kebab map entry): `ErpDataTagsSearch`, `ErpImagePicker` (kebab would be via targetTypeId), `ErpEdgeAgentError`, `ErpTokenDate`, etc.

### 1.2 MetaFx / core widget registry
Registered by `EpMetaFxFactoryControlService`. Registered ids (these are used verbatim as sourceTypeId in layers):

- `ep-search-chip-selection` → EpSearchChipSelectionComponent (core)
- `ep-hero-bar` → EpHeroBarComponent (core)
- `ep-nav-link` → EpNavLinkComponent (core)
- `ep-label` → EpLabelComponent (core)
- `ep-color-picker` → EpColorPickerComponent (core)
- `ep-embedded-app` → EpEmbeddedAppComponent (core)
- `ep-row-navigator` → EpRowNavigatorComponent (core)
- `ep-multi-view-calendar` → EpMultiViewCalendarComponent (core)
- `ep-scheduler` → EpSchedulerComponent (core)
- `ep-address-format` → EpAddressFormatComponent (core)
- `ep-multi-level-menu` → EpMultiLevelMenuComponent (core)
- `metafx-panel-card` → MetaFxPanelCardComponent
- `metafx-panel-card-grid` → MetaFxPanelCardGridComponent
- `metafx-panel-card-gantt` → MetaFxPanelCardGanttComponent
- `metafx-panel-card-stack` → MetaFxPanelCardStackComponent
- `metafx-relationship-map` → MetafxRelationshipMapComponent
- `metafx-udc` → MetafxUdcComponent
- `metafx-flex-box` → MetafxFlexBoxComponent
- `metafx-box` → MetaFxBoxComponent
- `metafx-tabstrip` → MetaFxTabComponent
- `metafx-epbinding` → MetaFxEpBindingComponent
- `metafx-div` → MetaFxDivComponent
- `metafx-col` → MetaFxColComponent

There are also non-factory containers handled directly by the layout renderer: `metafx-page`, `metafx-panel`, `metafx-group-box`, `metafx-grid-box`, `metafx-tree`, `metafx-toprow-template`, `metafx-panel-card-classic`, `metafx-factory-control` (host that instantiates all Ep*/Erp* controls above).

---

## 2. Runtime reactivity — how `property-set` works (definitive mechanism)

### 2.1 The pipeline
1. **Event action** `property-set` (id `'property-set'`): clones the action `param` (`ISetPropertyParam { component: string, props: [{ prop, value }] }`), runs `eventParamService.parseValue()` on the component id and every value (so `{DataView.Field}` tokens work in both), then calls `MetaFxComponentService.setProperty(param)`.
2. **Broker** `MetaFxComponentService`: `setProperty` pushes onto a `Subject<ISetPropertyParam>`; `propertyChanged(epBinding, uniqueName, guid, modelID)` filters that stream — a widget receives the patch when `param.component` equals **its epBinding, OR its component id, OR its model.guid, OR its model.id**.
3. **Widget base** `EpKineticComponent.setProperty()`: for each `{prop, value}`:
   - If prop is in `NON_MODEL_PROPERTIES = ['sourceTypeId','targetTypeId','parentId','components']` → `lodash.set(this._component, prop, value)` (patches the layout node itself, not the model).
   - Else → `lodash.set(this._component.model, prop, value)` (patches the layout schema model) and, if the live control was already instantiated, `lodash.set(this.factoryControl.controlModel, prop, cloneDeep(value))` (patches the live control's model). **Deep paths work** (`gridModel.columns[2].hidden` etc.); when the path contains `[` the parent array is re-assigned to itself to force change detection (`updateModel()`).
   - Special-cased props:
     - `hidden` (case-insensitive): additionally toggles the metafx wrapper's `layoutControlVisibility` and adds/removes the `contenthidden` CSS class on the wrapper. This is why `hidden` reliably works on EVERY component including containers.
     - `alignment`: rebuilds wrapper alignment CSS class (`Left`/`Right`/`Center`).
     - radio buttons (`sourceTypeId 'RadioButton'|'erp-radio-button'`): `value`/`labelText` are rerouted into `controlModel.data[0].value|label` and `labelText` is blanked.
     - `ep-search-chip-selection`: after any patch calls `updateChips()`.
4. **Control base** `EpComponentComponent`: the model object is held **by reference**; a `KeyValueDiffer` over `this.model` runs each change-detection cycle (ngDoCheck) and dispatches `doModelValueChange(key, cur, prev, EpKeyValueChangeType.added|modified|removed)` → the component's `onModelValueChange()` override plus built-in handlers for `guid`, `extendedComponent`, `extendedProps`, `width`, `height`, `classes`. **The differ is shallow (top-level keys only)** — a top-level scalar change is always detected; a mutation inside a nested object (e.g. `gridModel.height`) changes no top-level key, so only components that read the nested object in their template each CD cycle will visually update.

### 2.2 State-property system (why disabled/hidden/readonly behave specially)
`EpComponentComponent.getStateProperty(id, modelValue, modelDefault, fallback)` + `setStateProperty(id, priority, value)` implement a **priority-layered state** for the ids in `EpStateProperty`: `disabled`, `hidden`, `labeltext`, `readonly`, `required`, `status`. Priorities (`EpPropertyStatePriority`): `control=0`, `extended=1` (from `model.extendedProps` — column metadata/security), `keyField=2`, `rowRuleDisableRow=3`, `rowRule=4`.

Resolution order (see `getStateProperty`): **if the model property differs from its default it wins outright**; otherwise the priority chain (extendedProps → keyField → rowRules) is consulted. Consequences for layer authors:

- `property-set` of `disabled: true` on the model works (model value ≠ default → wins). Setting `disabled: false` may appear to "not work" if extendedProps/row-rules/keyField state is holding it disabled — false equals the default, so the state chain wins.
- **`enabled` is NOT a model property of any Ep/Erp control.** The model key is `disabled`. `property-set` of `enabled` just writes a dead key. (Confirms lessons-learned §3: use `disabled`, not `enabled`.) The App Studio *rules* engine exposes an "Enabled" style only because row-rules map it to the state system; raw `property-set` must target `disabled`.
- `hidden` works everywhere because of the wrapper special-case in 2.1 (independent of the control's own template).

### 2.3 Per-property reactivity guidance
- **Reactive (live) for all controls**: any *top-level scalar* model property that the control's template reads through a getter — e.g. `labelText`, `disabled`, `readonly`, `required`, `placeholder`, `value`, `hidden`, `tooltip`-style strings. Verified template-getter pattern in `ep-text-box`, `erp-shape`, `erp-tag`, `ep-button` etc.
- **Reroute cases**: radio-button `value`/`labelText` (see 2.1); `list` on combos is re-parsed only at create time (`createEpControl` parses `list` for `erp-combo-box` once — replacing `list` later via property-set injects the raw array without `parseComboList` token parsing).
- **Create-time-only (render-once)**: properties consumed in `ngOnInit`/`createEpControl` and never re-read: combo `retrieveColumns` single-column collapse, `masked→type` translation happens in ngOnInit *and* in `onModelValueChange` (so masked IS live for text-box), grid `providerModel`/BAQ wiring (needs `invalidated`/refresh event instead — see grid section), panel-card slot arrays (`bodyComponents` etc. are rendered by the layout engine at create).
- **ErpShape**: template binds `status`, `disabled`, `enabledCaption`, `disabledCaption` via getters — mechanically these should live-update; lessons-learned observed `enabledCaption`/`enabled` not re-rendering. Likely root causes: (a) `enabled` is not a model key (nothing to update); (b) caption getters pass through `getString()` translation of the *model* value — if the property-set targeted the layout model before control instantiation (`factoryControl` not yet created) only `_component.model` is patched and an already-rendered control keeps its own copy ONLY when the model object identity diverges (state restore path `componentStateService.getComponentProps` uses `set(activityData.model,...)` on a `cloneDeep`ed activityData — note `createEpControl` does `this.activityData = cloneDeep(ctrl)` — **the live control model is a deep clone of the layout node model**, so patches to `_component.model` alone do NOT reach the rendered control; only the `factoryControl.controlModel` patch does, and that object is `activityData.model`, not `_component.model`). Practical rule: property-set works only while the target is instantiated (on-screen); the safest live props are the wrapper-handled ones (`hidden`) and scalars patched after render.

### 2.4 Targeting
`param.component` matches epBinding OR component id OR guid OR model.id — so in a layer event you may target a control by its `id` (unique name in App Studio), its `guid`, or its `epBinding` string. Beware epBinding targeting hits *every* control bound to that column.

---

## 3. Layout & page system

### 3.1 The App Studio model dictionary
App Studio's designer property models (namespace `DesignerProperty`) define the exact **default model per sourceTypeId as App Studio serializes it**, plus the designer row-rules that constrain values. §3-4 below reflect those serialized models.

`ControlType` constants — includes legacy/classic ids that appear in converted apps: `Page`, `Div`, `Panel`, `GroupBox`, `Label`, `Grid`, `Tab`, `Column1`, `Column2`, `RadioButton`, `CheckBox`, `Textbox`, `Button`, `ComboBox`, `NumericBox`, `SplitButton`, `PanelCard`, `PageDiagram`, `epView`, `tool-bar`, plus all `metafx-*`/`ep-*`/`erp-*` ids from §1. Also:
- `HeaderTemplateControls = ['headerComponents','expandedHeaderComponents']`
- `AllowOnlyDivControls = ['bodyComponents','extensionComponents','metafx-panel-card-classic','tabBodyComponents']` — these slots only accept layout containers (divs) as direct children in the designer.

### 3.2 Page / view model (`MetaFxLayoutSchema`)
Designer models: `PageDiagramProperty`, `EpViewProeprty`.

```ts
{
  name: string; namespace?: string; caption: string; guid: string;
  viewType: string;                 // see list below
  pageType?: 'Responsive'|'Absolute'|'';
  height: number; width: number;    // SlidingPanel width defaults to 683
  flexLayout?: boolean;
  components: IEpCreateComponentActivityData[];  // sibling order = array order
  navigation?: { ... };             // see below
  slidingPanel?: ISlidingPanel;     // when viewType === 'SlidingPanel'
}
```

**viewType values** (all appear in `PageDiagramProperty.rules()` / `EpViewProeprty.rules()`): `Apps` (root app page), `Tab`, `Page`, `TabPage`, `VirtualPage`, `ContentPage`, `SlidingPanel`, `Dashboard`, `Report`, `Process`, `Configurator`, `Shared`. Notes:
- `enableFullWidth` and `disableUiLocking` are only editable on app-level viewTypes (`Apps`, `Dashboard`, `Report`, `Process`, `Configurator`, `Shared`).
- `epBindingPeerOrder` (sibling order in the nav tree) is only enabled for `TabPage` and `VirtualPage`.
- When `viewType === 'SlidingPanel'`: `navigation.epBinding/parentPage/dataSetId/pageCaption/tabId` are disabled and `width` is forced to **683**; allowed preset widths (`widthTypes`) are **370, 683, 967, 1270, `100% - 20px`**.
- `navigation.dataSetId` defaults to the token `%datasetId%` when the page has no parentPage.

**Page-level model (`PageDiagramProperty`)** — a page node also carries `caption`, `width`, `enableFullWidth` (default false), `disableUiLocking`, `maxItemsInToolBar` (default 6), and:

```jsonc
"navigation": {
  "epBinding": "",            // root binding context, e.g. "OrderDtl"
  "parentPage": "",           // parent page name; "Main" or empty = top level
  "dataSetId": "",            // default "%datasetId%"
  "pageCaption": "",          // caption in nav tree / tab
  "tabId": "",                // tab identifier when hosted as a tab
  "epBindingPeerOrder": 0,    // sibling order among peer pages
  "enable": false,
  "extendedProps": { "disableMemos": false, "disableCallLog": false,
                     "disableChangeLog": false, "disableAttachments": false,
                     "disableBPMHoldBadge": false },
  "expandInNavigation": 0,
  "expandNavigationLevels": 0,
  "dataTreeShowCollpase": [{ "overrideTreeCaptions": false, "treeOptions": "" }],
  "entityType": ""
},
"slidingPanel": {
  "status": "",               // EpBaseSlidingPanelStatus — set via events to open/close
  "hideClose": false, "showTitle": true, "showButtons": false,
  "collapseOnOutsideClick": false,
  "buttons": [{ "id": "", "labelText": "", "epBinding": "", "dialogResult": "OK",
                "size": "ep-btn-size-regular", "style": 0, "width": "", "icon": "" }],
  "actionData": [{ "id": "", "description": "", "icon": "", "imageUrl": "", "epBinding": "",
                   "shortCut": "", "showInToolBar": false, "disabled": false,
                   "divider": false, "sequence": undefined }]
}
```

**epView (app root, `EpViewProeprty`)**: `caption`, `viewType`, `widthTypes`, `width` (default 900, min 600 for non-sliding), `flexLayout` (default true), `deviceType` (`DeskTop|Mobile|Tablet`), `showHeroBar`, `heroBar {disabled, readonly, items}`, `navigation {parentPage, dataSetId, enableHeader, topRowTemplate[]}`, and the app `tools[]` array: `{ id, sequence, icon, text, imageUrl, epBinding, shortCut, disabled, showInToolBar, showInSecondaryToolBar, showInDataTree, divider, style, sysType, parent }` (a tool cannot be in both toolbars; `parent` groups tools under an overflow item).

### 3.3 Tree, slots and sibling order
- The component tree is `components[]` arrays; a node is `IEpCreateComponentActivityData { id, sourceTypeId, targetTypeId?, parentId, model, components }`. `parentId`, `components`, `sourceTypeId`, `targetTypeId` live on the NODE (they are the `NON_MODEL_PROPERTIES`), everything else lives under `model`.
- **Sibling order = array index order** (children are rendered by iterating the arrays in order).
- **Slots — two representations, don't confuse them.** In the RAW runtime model, container slots are MODEL ARRAYS: children of a panel card live in `model.bodyComponents[]`, `model.headerComponents[]`, `model.expandedHeaderComponents[]`, `model.extensionComponents[]`; tabstrip children in `model.data[n].components[]`; the raw runtime model does not use `'#'` (designer-internal drop ids use `~`). **BUT the LAYER/diff representation — what you actually author — is a FLAT list using `parentId: "<containerId>#<slot>"`, and that form is CORRECT and FIELD-PROVEN** (`pcGetOrder#bodyComponents`, `pcDetail#expandedHeaderComponents`, `pcConfirm#bodyComponents` all render; base apps expose slots the same way per GetNativeKineticApp). Valid slots seen: `#bodyComponents`, `#headerComponents`, `#expandedHeaderComponents`, `#extensionComponents`. When authoring layer diffs, use flat `parentId` + `#slot` — you do NOT need to nest `components` arrays; the server-side merge resolves the flat form into the slot arrays. (Rows/cols use the plain container id as `parentId`, no `#`.)
- Rendering: each slot array is passed to a `metafx-widget-container` with `root="<slotName>"` and `[components]="model.<slotName>"`; that container instantiates each child through `metafx-factory-control` → `EpComponentFactoryService` using `sourceTypeId` (falling back to `targetTypeId` for the final control type — `EpKineticComponent.createEpControl`: `controlTypeId = targetTypeId || sourceTypeId`).

### 3.4 Rows/columns flex layout
- `metafx-div` (`DivProperty` model): `{ labelText, column: 1, orientation: ''('vertical'|'horizontal'), class: '', capWidth: true, hidden, customizable, personalizable }` + node-level `components[]`. When `class === 'row'` the div is a ROW whose `column` count is auto-set to `components.length` (clamped 1..10) and `capWidth` is hidden. Runtime default: `orientation:'vertical'`, `columns = components.length || 1`. Column resize broadcasts `flexBasis` in 5% steps.
- `metafx-col`: container with `capWidth: true` default (caps children to the standard 290px control width), `labelText`, `orientation`; in the plain flex layout the column's width is `model.flexBasis` (string CSS flex-basis, e.g. `"25%"`) read by `EpKineticComponent.flexBasis()`. **CORRECTED (FIELD-PROVEN): in real converted/classic layers `metafx-col` cells DO carry `model.width` (e.g. `"auto"`) — and inside a `metafx-matrix` (§3.8a) that is the form to use; `flexBasis` is not used there.** The earlier claim "no width property — use flexBasis" holds only for the plain flex layout, not for matrix layers.
- `metafx-box` (`MetafxBoxProperty`): `{ labelText, columnsWide, flexDirection }` (flexDirection Column→vertical, Row→horizontal).
- `metafx-flex-box` (`MetafxFlexProperty`): `{ labelText, columnsWide, flexDirection, flexAlignMain, flexAlignCross, flexWrap, flex, flexGap, flexOffset, flexOrder, flexAlignSelf, template }` — full CSS flexbox surface.
- Widget wrapper adds `capWidth` handling globally: any control model with `capWidth === undefined || true` gets the `cap-width` class unless its type has behavior `ignoreCapWidth` (buttons, text-area, selection-list, grids, panel-card-grid, gl editors, rich-text, data-tree, website, gantt, pdf-viewer, relationship map…; see §1 registry `behavior` entries).
- `columnsWide` (string) appears on panel-card / box / grid models — designer column-span within a row.

### 3.5 metafx-tabstrip (`TabProperty`)
Model: `{ class, width, hidden, customizable, personalizable, data: IMetaFxTabStripData[] }`. Each tab item:

| key | type/default | meaning |
|---|---|---|
| `id` | string, required | unique tab id |
| `title` | string | tab caption |
| `epBinding` | string | binding for tab badge/state |
| `selected` | bool false | initially selected tab (designer rule un-checks all others) |
| `page` | string | name of a PAGE whose components render inside this tab (page reference mode) |
| `pageName` | string | page-name hierarchy for 4.x layout generation |
| `panelCardId` | string | panel card id for 4.x generated content |
| `components` | [] | inline child components (used when `page` empty) |
| `showAddNewPage` | bool true | designer-only |

Runtime: `getComponents(tabItem)` — if `tabItem.page` set, loads `pages.find(p=>p.name===page).components`; else `tabItem.components`. Slot name `tabBodyComponents`.

### 3.6 metafx-panel-card (`MetafxPanelCardProperty` — the exact serialized model)
```jsonc
{
  "guid": "", "epBinding": "", "columnsWide": "", "flexLayout": false,
  "title": "", "enableActionButton": false, "enableAddButton": false,
  "autoFillContainer": false, "expanded": true,
  "customizable": true, "personalizable": true, "hidden": false,
  "fullScreenButtonVisible": false,
  "actionData": [{ "id": "", "description": "", "icon": "", "imageUrl": "", "epBinding": "",
                   "shortCut": "", "showInToolBar": true, "disabled": false, "divider": false,
                   "sequence": undefined, "sysType": "" }],
  "providerModel": { "description": "", "svc": "", "svcPath": "", "tableName": "",
                     "epBinding": "", "outParamName": "", "restParams": {} },
  "headerComponents": [], "expandedHeaderComponents": [],
  "bodyComponents": [], "extensionComponents": []
}
```
Runtime extras (default model): `keepItemContent: true`, `componentType: Container`; runtime model also honors `footer` (`IEpFooterPanelCardModel` with `navLinkModel`), `hideDropDown`, `subTitle`, `customIcon`, `lazyLoadContent`, `disableExpandCollapse`, `headerDisabled`, `selectable/selected`, `showMore`, `invalidated`, `epOnStateChange/epOnClickAction/epOnClickAdd/epOnClickCustomIcon/epOnClickFullScreen/epOnClickBack` (IErpPanelCardModel defaults). `actionData` items surface in the card's "…" action menu when `enableActionButton: true`; each fires the panel-card action event with its `id`. `providerModel` (added by `ErpPanelCardPropertiesExtension`) lets the CARD itself fetch data: `{description, svc, svcPath, tableName, epBinding, outParamName, restParams(json)}`.

### 3.7 metafx-panel-card-grid (`MetafxPanelCardGridProperty` — exact serialized model, VERBATIM)
Top level: `{ guid, columnsWide, epBinding, epBindingViewOption, flexLayout: false, title, autoFillContainer: false, invalidated: false, expanded: true, disablePanelCardStyle: false, customizable: true, personalizable: true, disabled: false, readonly: false, hidden: false, fullScreenButtonVisible: true, gridModel: {...}, actionData: [...], viewOptions: [...], headerComponents: [], expandedHeaderComponents: [] }`.

**gridModel**:
```jsonc
"gridModel": {
  "id": "", "collapseGroups": true, "autoLoadColumns": false, "epBinding": "",
  "scrollable": "scrollable", "height": 300, "width": "", "rowHeight": 0,
  "pageSize": "", "dragImageIcon": "", "entityType": "",
  "editOptions": { "editMode": "cell" /* EpGridEditMode.cell */, "updateOnChange": true },
  "providerModel": {
    "description": "", "svc": "", "svcPath": "", "tableName": "", "epBinding": "",
    "clientFilter": "", "outParamName": "", "restParams": {},
    "baqId": "",
    "baqOptions": { "pageNumber": "", "pageSize": "", "where": "",
      "whereList": [{ "column": "", "condition": "", "value": "", "honorNull": false, "emptyValue": "" }] },
    "pagePaddingSize": 0, "isDefault": false, "serverPaging": false
  },
  "selectionOptions": { "showCheckBox": false, "showSelectAll": false,
                        "selectByField": "", "epBindingSelectAll": "" },
  "resizable": false, "sortable": false, "pageable": false, "groupable": false,
  "filterable": false, "virtualColumns": false, "selectorColumn": true,
  "enableAdvanceFilter": false, "reorderable": false,
  "rowReorder": { "enabled": false, "orderColumn": "" },
  "editable": false, "disablePasteNew": false, "disablePasteUpdate": false,
  "selectable": true, "maxColumns": "",
  "columns": [{
    "field": "", "title": "", "epBinding": "", "erpEditor": null,
    "erpEditorModel": { "mask": "", "epBinding": "", "spinners": "", "updateOn": null },
    "masked": false, "isLink": false, "editable": false,
    "disableCurrencyToggle": false, "skipRowChangeOnLinkClick": false, "selector": false
  }],
  "columnsHidden": [{ "field": "" }],
  "showOnlyDataView": true
}
```
Column extras seen at runtime (IErpGridColumn usage): `hidden`, `format`, `width`, `comboFilter`, plus `erpEditor` editor-type string (combo, date, numeric etc. — `ErpEditorType` enum) with `erpEditorModel` sub-model. Grid-level runtime extras (IErpGridModel extends core IEpGridModel): `autoLoadColumns`, `activeCurrencyType` (ErpCurrencyToggleCode), `disabledColumns: string[]`, `providerModel`, `isProviderDisabled`, `collapseGroups`, `hidePreloadButton`, `disableAutoPageSize`, `onLinkClick/onLikeLinkClick` handlers. Personalization patches `gridModel.columns` live (see §2.1 `onGridColumnPersonalizationChange`).

**viewOptions[]** (the grid's "view selector" dropdown; each option is an alternate provider + column set):
```jsonc
"viewOptions": [{
  "id": "", "description": "", "isDefault": false,
  "svc": "", "svcPath": "", "tableName": "", "outParamName": "", "epBinding": "",
  "clientFilter": "", "serverPaging": false, "pagePaddingSize": 0, "restParams": {},
  "autoLoadGrid": false,
  "columns": [ /* same column shape as gridModel.columns */ ],
  "baqId": "",
  "baqOptions": { "pageNumber": "", "pageSize": "", "where": "", "whereList": [...] }
}]
```
`epBindingViewOption` holds the currently-selected view option id. NOTE: **`allowAddNew`, `allowDelete`, `hideViewSelector` are NOT part of the serialized grid model** — add/delete come via `enableAddButton`/toolbar tools and `editOptions`; the view selector shows only when `viewOptions.length > 0`. Designer rules: `fullScreenButtonVisible` hidden when `autoFillContainer=true`; `gridModel~width` min 0. ERP property extension adds `autoLoadColumns` ("Enable auto load of columns from data view"). Refresh a provider-driven grid at runtime with the grid-refresh event action or by setting `invalidated: true` via property-set.

Known `providerModel` keys: `baqId, baqOptions, epBinding, restParams, tableName, svc, svcPath, outParamName, serverPaging, serverPageSize, clientFilter, id, data, description, columns, skipAutoload, recentRecordsFilter, autoLoadGrid, sort, pagePaddingSize, baq, isRecentRecords, isDefault, customSort, crossCompany, populateRelatedViews`.

**BAQ-provider grid — columns vs `autoLoadColumns` (FIELD-PROVEN):** on a grid driven by `providerModel.baqId`, a `columns` array makes the grid emit a restrictive dynamic `Select` against the BAQ, which can throw **"Invalid column name"** on complex multi-subquery BAQs (the BAQ itself is fine — the generated Select is the problem). Prefer `autoLoadColumns: true` and **no `columns` array** so the full query runs and columns come from the result. Works for both simple and complex BAQs. To filter such a grid, use `baqOptions.whereList` — see search-baq-rest.md §2.3–2.4 (item shape and gating rules).

**The two valid column configs (all-or-nothing):** either `autoLoadColumns:true` + **no** `columns` array, or `autoLoadColumns:false` + the **COMPLETE** `columns` list. `autoLoadColumns:true` + a *partial* `columns` array is NOT a valid combo — App Studio always writes `autoLoadColumns:false` with the full list when any column is customized; a partial array under `true` may be silently ignored or blank the grid.

**Server paging (`providerModel.serverPaging:true`) drops non-column sort/key fields from the Select (FIELD-PROVEN):** under server paging, `ExecuteBaq` projects ONLY the grid's columns; with `autoLoadColumns:true` that's the BAQ's *display* fields, which can EXCLUDE the key/sort columns (present in the query for joins/keys/`QuerySortBy` but not flagged display). The paged query is then ordered by columns it isn't projecting — sorting breaks, and events reading those columns from the result view get nothing (client paging masks this by sorting the full in-memory set). Fix: force them via `providerModel.baqOptions.select: ["[UD103_Key2]", ...]` (bracketed) — unioned into the Select verbatim, first and unconditionally, with no grid-column machinery (`providerModel.columns` is never read by the Select path). The `autoLoadColumns:false` + full-`columns` alternative is NOT sufficient on newer builds: their Select enumeration drops Updatable-flagged UBAQ fields and metadata-less columns (search-baq-rest.md §2.3d). Rule of thumb: any column referenced by the BAQ's `QuerySortBy` OR read from the result dataview by an event MUST be in the Select — on a UBAQ + serverPaging grid, ALWAYS via `baqOptions.select`. See search-baq-rest.md §2.3b–2.3d.

### 3.8 metafx-panel-card-gantt / metafx-panel-card-stack / others
- `MetafxPanelCardGanttProperty` model: `{ guid, epBinding, title, autoFillContainer, expanded: true, disablePanelCardStyle: false, disableExpandCollapse: false, customizable, personalizable, disabled, readonly, hidden, ganttModel: { id, timeline: 'Days', verticalAutosize: false, templates: {}, config: {}, columns: [{name,label,width,align:'Left',resize:true,tree:false}] }, actionData: [...], headerComponents: [], expandedHeaderComponents: [] }`. ERP variant adds `schedulingBoardType`, `epBindingSchedulingBoard`, `epBindingSelectedJob`, `epBindingSBMaterial`, `epBindingSBJobs` (ErpPanelCardGantt).
- `metafx-panel-card-stack`: container that stacks panel cards; model: id/title/epBinding/data list of cards.
- `metafx-udc` (`MetaFxUDCProperty`): `{ guid, personalizable: true, hidden: false }` — hosts a User Defined Component.
- `ep-embedded-app` (`EpEmbeddedAppProperty`): `{ guid, labelText, embeddedAppWidget, widgetType(readonly), widgetWidth, widgetHeight, hidden, guidedSetupButton, pubSubSetupButton }`.
- `metafx-epbinding`: invisible binding host used to place an epBinding on a container region.
- `metafx-panel-card-classic` (`PanelCardProperty`, sourceTypeId `metafx-panel-card-classic`): `{ labelText, expanded: true, hidden, columnsWide }` + node `components[]` — the simple converted-classic card (no slots).
- Legacy classic containers (converted apps): `GroupBox {labelText, class, hidden}`, `Grid {labelText, class, hidden}` (layout grid), `Page {flexLayout, page, showAddNewPage}`, `tool-bar {disabled, icon, parentId, toolbartext, sequence}`.
- **`metafx-matrix` — CORRECTED: it EXISTS on current builds and is the standard grid-of-fields layout widget.** App Studio emits it for row/column field layouts. FIELD-PROVEN (`mxConfirmTop`, `mxConfirmTotals`, `mxBillTotals`, `mxSalesAgents`, several header matrices). Full pattern in §3.8a below — prefer it over hand-rolled `metafx-div`/`metafx-col` flex layouts, which produced partial renders here.

### 3.8a metafx-matrix — the working pattern (FIELD-PROVEN)

A matrix is a **grid of single-control cells**: three component types, flat `components` list, flat `parentId`.

1. **The matrix** — in a panel-card slot:
```json
{ "id": "mxGetOrder", "sourceTypeId": "metafx-matrix",
  "parentId": "pcGetOrder#bodyComponents",
  "model": { "guid": "...", "id": "metafx-matrix-go",
             "columns": 4, "rows": 2,   // SWAPPED: columns = ROW count (max y+1), rows = COLUMN count (max x+1)!
             "forceMinWidth": true, "spacing": "Default" } }
```
2. **Each cell** — `metafx-col`, `parentId` = the matrix id, with **integer `x` (column) and `y` (row) at the COMPONENT level** (not the model), and `model.width: "auto"`:
```json
{ "id": "gocL0", "sourceTypeId": "metafx-col", "parentId": "mxGetOrder",
  "model": { "guid": "...", "id": "div-col-gocL0", "width": "auto" }, "x": 0, "y": 0 }
```
3. **ONE control per cell** — `parentId` = the cell id:
```json
{ "id": "txtGO_Company", "sourceTypeId": "erp-combo-box", "parentId": "gocL0",
  "model": { "epBinding": "GetOrderFilter.Company", "labelText": "Company" } }
```

Hard rules (each one cost a broken render):
- **Exactly ONE control per cell.** Multiple controls in one cell → only the first renders, the rest silently drop (this is what made a whole column "disappear"). A visually empty cell gets a **blank `ep-label` spacer** (`labelText: " "`) — never leave a cell controlless.
- **Fill every cell of the bounding grid** (2×4 → all 8 `(x,y)` cells); gaps can blank the panel.
- **`x` = column, `y` = row**, on the cell component. Placement is driven by `x`/`y`.
- **`model.columns`/`model.rows` are SWAPPED vs intuition AND they CLIP — the #1 matrix gotcha.**
  The engine uses **`model.columns` = number of ROWS = `max(y) + 1`** and **`model.rows` = number of
  COLUMNS = `max(x) + 1`**. Cells whose `y >= columns` (or `x >= rows`) are **silently dropped** — no
  error. So for a layout with `X` columns and `Y` rows: set **`columns = Y`, `rows = X`**. Field
  failure: a 2-column × 4-row panel set to `columns:2, rows:4` clipped `y=2,3` and dropped two
  inputs; the fix was `columns:4, rows:2`. Proven across every matrix in the layer:

  | matrix | model cols,rows | actual x-range | actual y-range |
  |---|---|---|---|
  | mxBillTotals | 6, 1 | 0..0 (1 col) | 0..5 (6 rows) |
  | 6e5f0 / 8bc24 / d28e3 | 2, 5 | 0..4 (5 cols) | 0..1 (2 rows) |
  | 018ef | 2, 7 | 0..6 (7 cols) | 0..1 (2 rows) |
  | 50546 | 5, 2 | 0..1 (2 cols) | 0..4 (5 rows) |
  | mxSalesAgents | 4, 3 | 0..2 (3 cols) | 0..3 (4 rows) |
- Full-width controls (e.g. a tall log `erp-text-area`) go **directly in the panel-card slot**, sibling to the matrix — not inside a cell.

Failure signature: fields/columns/regions simply don't appear, **no console error** — suspect (in order) `model.columns`/`model.rows` swapped-clipping (cells with `y >= columns` or `x >= rows` are dropped), multi-control cells, empty cells, or a hand-rolled div/col layout where App Studio would have used a matrix.

### 3.9 Core nav/label widgets (exact serialized models)
- **ep-label** (`LabelProperty`): `{ guid, labelText, epBinding, alignment: 'Left', customizable: true, personalizable: true, hidden: false }`. Runtime extras: `text`, `for`, `textAlign`, `textStyle` (EpTextAlign/EpTextStyle enums). Displays `labelText` or bound value.
- **ep-nav-link** (`EpNavLinkProperty`): `{ guid, epBinding, alignment: 'Left', target: '_blank', href: '', text: 'NavLink', page: '', iconClass: 'mdi mdi-launch', customizable, personalizable, disabled, readonly, hidden, showAddNewPage: true }`. If `page` set → navigates to that layer page (NAVIGATE_PAGE event) instead of `href`.
- **ep-row-navigator** (`EpRowNavigatorProperty`): `{ guid, labelText, epBinding, comboBoxLabel, columns: [], alignment: 'Left', customizable, personalizable, disabled, readonly, epiGuid, hidden }` — record navigator over the bound dataview; `columns` lists combo display columns; runtime `showCountText`, `data`.
- **ep-search-chip-selection** (`SearchChipProperty`): `{ guid, alignment: 'Left', epBinding, Like, PeekSubType, pluralLabelText: 'Selected', singularLabelText: 'Selected', emptyLabelText: 'None Selected', errorMessage, customizable, personalizable, readonly, disabled, hidden, autoFocus }`.
- **ep-address-format** (`EpAddressComponent`): `{ guid, labelText, epBinding, alignment: 'Left', customizable, personalizable, disabled, readonly, epiGuid, hidden }`.

---

## 4. Common base model (every component)

The base default model shared by every control (`EpComponentComponent` / `EpComponent`):

| property | type | default | notes |
|---|---|---|---|
| `id` | string | '' | unique name; property-set / events target |
| `guid` | string | '' | designer guid; also a property-set target |
| `labelText` | string | '' | field label (state-property `labeltext`) |
| `epBinding` | string | '' | `View.Column` binding |
| `value` | any | null | current value (value components) |
| `disabled` / `readonly` / `required` / `hidden` | bool | false | state properties (see §2.2). **No `enabled` property exists.** |
| `alignment` | 'Left'\|'Right'\|'Center' | 'Left' | wrapper CSS class |
| `width`/`height`/`maxWidth`/`top`/`left`/`bottom`/`right` | number | 0 | width/height changes ARE handled live (`onModelValueChange` → setSize) |
| `autoFocus` | bool | false | plus `autoFocusAfterBinding` |
| `tabIndex` | number | 0 | |
| `extendedProps` | object | {} | column metadata/security overlay (priority 1 state) |
| `customizable`/`personalizable` | bool | true | designer flags |
| `userData` | any | null | free-form |
| `features` | string | '' | feature flags |
| `componentType` | EpComponentType | 'ep-component' \| 'ep-container' \| 'ep-composite' | |
| event hooks | EpEventHandler | null | `epOnFocus`, `epOnBlur`, `epOnValueChange`, `epOnHelpClick`, `epOnEvent` |

---

## 5. Field components (per-type property surfaces)

Base App Studio property chain (from core property classes): `EpCoreBaseProperties` → adds `id`, `personalizable`, `customizable`, `isKeyField`, `comments`; `EpBaseCommonProperties` → `labelText`, `hidden`, `epBinding`, `alignment`; `EpCommonProperties` → `width`, `disabled`, `readonly`, `autoFocus`. All field components below include these.

### 5.1 erp-text-box (core base: `ep-text-box`)
Defaults (`getDefaultModel`): `type:'text'`, `value:''`, `labelText:''`, `autocomplete/autocorrect/autocapitalize: 'off'` (EpToggle.Off; values `'on'|'off'`), `spellcheck:false`, `noFloatingLabel:'off'`, `readonly/disabled/required:false`, `pattern:''`, `masked:false`, `searchTitle:''`, `customActionTitle:''`, `enableContextMenu:true`.

| property | type | default | meaning / reactivity |
|---|---|---|---|
| `type` | string | 'text' | html input type; auto-set to 'password' when `masked` (live: onModelValueChange) |
| `maxLength` | number | (from column metadata via `vSetupColumn`) | max chars |
| `pattern` | string | '' | regex validation |
| `masked` | bool | false | password masking — LIVE (onModelValueChange flips `type`) |
| `enableSearch` | bool | false | shows the search (magnifier) button; Enter key triggers it; fires `epOnSearchBarClick` — wire a layer event to it |
| `searchTitle` / `searchIconClass` / `searchOnly` | string/string/bool | ''/-/false | search button tooltip / icon / icon-only (text entry disabled) |
| `enableCustomAction` / `customActionTitle` / `customActionIconClass` / `customActionOnly` | | | second action icon; fires `epOnCustomActionClick` |
| `autocomplete`,`autocorrect`,`autocapitalize` | 'on'\|'off' | 'off' | browser assist toggles |
| `noFloatingLabel` | 'on'\|'off' | 'off' | suppress floating label |
| `spellcheck` | bool | false | |
| `hasDifference`/`previousValue`/`diferenceClass` | | | difference-highlight support (note the misspelled key `diferenceClass`) |
| `contextMenuItems` | array | – | via `contextMenuItem` input |
| ERP extras | | | `labelTextSearchDesc` (string, Advanced), `epBindingSearchDesc` (epBinding, Data) — description text shown next to a search field |

Also on the ERP wrapper: `updateOn: 'change'|'blur'|'submit'`, `resizable`.

### 5.2 erp-text-area (core `ep-text-area`)
Adds to base: `rows` (number, default 0 in ERP model), `cols`, `maxLength`, `noFloatingLabel` ('on'/'off'), `spellcheck` (false), plus the customAction/difference/context-menu extras like text-box. Behavior `ignoreCapWidth: true`. `width` is hidden in the property panel.

### 5.3 erp-numeric-box (core `ep-numeric-box`)
Defaults: `value: 0`, `autoCorrect: false`, `format: undefined`, `step: 0`, `spinners: false`, `precisionWarning: false`, `disableChangeValueOnScroll: true`, `enableContextMenu: true`. ERP model adds `mask: ''`, `nullable: false`.

| property | notes |
|---|---|
| `min`/`max` | bounds; `autoCorrect: true` snaps into range |
| `step`, `spinners` | spinner buttons (auto-hidden when disabled) |
| `decimals` | precision (also parsed from `format` like 'N2') |
| `format` | string ('N2','c2',…) or object `{style: 'currency'|'percent'|'scientific'|'accounting', currency, currencyDisplay: 'symbol'|'code'|'name', minimumIntegerDigits, minimumFractionDigits, maximumFractionDigits, useGrouping}` |
| `numberInputType` | use tel input (mobile keypad) |
| `nullable` | ERP: allow null instead of 0 |
| `mask` | ERP numeric mask |
| `precisionWarning` | warn on float precision loss |

### 5.4 erp-currency-box
Extends numeric behavior; ERP defaults: `isToggleDisabled:false`, `mask:''`, `epBindingDocument:''`, `epBindingShowBase:''`, `showBase:false`, `activeCurrencyType: null` (`ErpCurrencyToggleCode`: `BASE|DOC|RPT1|RPT2|RPT3|GLOBAL|Unspecified`), `epBindingDocumentSymbol:''`, `showSymbol:false`. The currency toggle switches which bound column (base/doc/rpt) is displayed; `erp-currency-child-box` is the secondary display box. `erp-currency-selector`: `{ epBindingDocument: '', showBaseCurrencyForDocCurrency: false }` — currency-code picker.

### 5.5 erp-date-picker (core `ep-date-picker`)
Model keys (ERP defaults + core property panel): `min`/`max` (Date), `format` (`{displayFormat, inputFormat}` or string), `formatPlaceholder` (`wide|narrow|short|formatPattern`), `placeholder`, `rangeValidation:false`, `weekNumber:false`, `navigation:false` (calendar sidebar), `activeView/bottomView/topView` (`month|year|decade|century`), `focusedDate`, `updateOnSelect:false`, `mask:''`, `epOnClose/epOnOpen`.

### 5.6 erp-time-picker
`format` (e.g. 'HH:mm:ss'), `formatPlaceholder`, `placeholder`, `min`/`max`, `nowButton:false`, `cancelButton:false`, `popupSettings {animate, appendTo, popupClass}`, `steps {hour,minute,second}`, `rangeValidation:false`, `readOnlyInput:false`, `mask:''`, plus ERP-only: `use24HourClock:false`, `timeStoredAsDateTime:false`, `isDecimal:false`, `roundToMinutes:false`, `treatZeroAsNull:false`.

### 5.7 erp-check-box (core `ep-check-box`)
`value` (bool), `highlightSelected:false`, `threeState:false`, `indeterminate:false` (setting it forces threeState), states `'0'|'1'|'2'` (UnChecked/Indeterminate/Checked).

### 5.8 erp-button (core `ep-button`)
ERP defaults: `id:''`, `title:''`, `icon:''`, `style:null`, `selected:false`, `size:null`, `iconAlignRight:false`, `type:null`, `fixedWidth:false`, `toolBarType:null`, `toolBarAction:null`, `block:false`.

| property | enum values (exact) |
|---|---|
| `style` | `EpButtonStyle`: `Primary=0, Secondary=1, Outline=2, Toggle=3, Done=4` (numeric!) |
| `size` | `EpButtonSize`: `'ep-btn-size-small' | 'ep-btn-size-medium' | 'ep-btn-size-regular' | 'ep-btn-size-custom'` |
| `type` | `'reset' | 'submit' | 'button'` |
| `labelText` | button caption |
| `icon` / `iconAlignRight` | mdi icon class |
| `block` | full-width |
| `selected` | toggle-style pressed state (Toggle style flips it on click, emits binding events) |
| `disabled` | THE enable/disable switch. There is **no `enabled` property** — rules use "Enabled" action but property-set must write `disabled`. |
| behavior | `ignoreCapWidth: true, excludeFromSearch: true`; setting `width` auto-forces `fixedWidth` |

Click event: layer events trigger on the control's `epOnClick` via its `id`.

### 5.9 erp-radio-button (core `ep-radio-button`)
`data: []` (array of `{label, value}` or plain strings auto-converted), `valueField:'value'`, `labelField:'label'`, `verticalAlign:false`, `highlightSelected:false`, `value`, `label`, `disabled`, `readonly`. **property-set special case** (§2.1): setting `value`/`labelText` reroutes to `controlModel.data[0].value|label`.

### 5.10 erp-shape
Model: `{ enabledCaption: '', disabledCaption: '', status: null }` + base. Property panel: hidden, epBinding, alignment, disabled, readonly, enabledCaption, disabledCaption, status (enum editor).
`ErpShapeStatusType`: `OK = 0` → **green** (`ep-background-green`), `Warning = 1` → **yellow**, `Stop = 2` → **red**, `Global = 3` → **blue**, `None = 4` → no background. Rendering: when `disabled` → grey (`ep-state-disabled`) and shows `disabledCaption`; otherwise the status color and `enabledCaption`. Default status = OK. In layers `status` is serialized as the NUMBER. Toolbox behavior: label preview = `enabledCaption || disabledCaption`.

### 5.11 erp-tag
Defaults: `trueStatus: Global(3)`, `falseStatus: Global(3)`, `trueCaption` (default 'Checked'), `falseCaption` (default 'Unchecked'). Bound to a BOOLEAN column; shows trueCaption w/ trueStatus color when true, falseCaption/falseStatus when false. Colors map through `ErpTagBackground` using the same `ErpShapeStatusType` numbers as erp-shape. **Fully reactive**: `onModelValueChange` re-initializes on `trueCaption|falseCaption|trueStatus|falseStatus|epBinding|value` changes — property-set on these keys works live.

### 5.12 erp-qty-uom
Composite: `{ qtyModel: <numeric-box model>, comboModel: <combo-box model> }` — quantity + UOM dropdown pair. `labelText` preview uses `qtyModel.labelText`. Set nested props e.g. `qtyModel.epBinding`, `comboModel.svc` etc.

### 5.13 erp-part-rev-desc
`{ epBindingPartNum: '', epBindingRevision: '', epBindingDescription: '', partRevLabel: '', partDescLabel: '', partSearchClick: <handler> }` — Part / Rev / Description trio with part search.

### 5.14 erp-selection-list (behavior `ignoreCapWidth`)
Key model props: `items:[]`, `maxItemsHorizontal`, `valuePrimitive:false`, `delimited:false`, `delimiter` (EpDelimiter), `emptyLineText`, `mode` (IEpSelectionListMode), `listOrientation` (EpOrientation), `uiMode`, `positionMode`, `reorder`, `manualSort:false`, `header`, `targetLabelText`, `showEdit/enableEdit/enableHeaderEdit:false`, `limit:0`, item props (`id,text,idName,selected,checkMarkHidden,toggleDisabled,required,description,subText,leftIcon,command,bookmark`), and the dual-list data wiring: `sourceViewName, sourceTableName, sourceCodeCol, sourceDescCol, targetViewName, targetTableName, targetCodeCol, targetDescCol, tableName, parentRelatedCol, childRelatedCol, relatedCol`. Events: `epOnSelectionChange`, `epOnSortChange`, `epOnBookMark`, `epOnDeleteItem`, `epOnListItemClick`, `epOnEditClick`, `epOnEditListItem`, `epOnHeaderEditButtonClick`. (erp-list-box shares this surface + `selectionMode`.)

### 5.15 Other input-ish components (default models)
- **erp-token-date**: `{ showToken:false, epBindingToken:'', epBindingShowToken:'', tokenValue:'' }` — date with token ("today", etc.).
- **erp-picture-box**: `{ image:'', imageType, imageFillType, imageStyle, hideBorder:false }` (enums ErpPictureBoxImageType/FillType/Style).
- **erp-rich-text-editor**: `{ value:'', toolBar: IEpToolBarModel, showAllToolbarItems:false }`.
- **erp-file-box**: `{ files:[], multiselect:false, filter:'', hideSearch:false, maxHeight:0, filesCacheKey:'' }`.
- **erp-server-file-box**: `{ title, specialFolder (ErpSpecialFolder enum), filter, checkFileExists, bindingFileName }`; **erp-server-folder-box**: `{ title, specialFolder, disableValidation }`.
- **erp-fiscal-year-suffix**: `{ epBindingSuffix, labelFiscalYear, labelSuffix, epBindingFiscalCalendarID }`.
- **erp-foreign-lang-desc-text-box**: `{ epBindingKey1..3, tableName, dynAttrShortDescription, availableLanguages, disableTranslationPanel }`.
- **erp-auto-complete-ep-binding**: `{ dataViews:[], spellcheck, epBindingText, mode (ErpBindingAutoCompleteMode), patches:[] }`.
- **erp-website**: `{ title, url, token:false, userContext:false, capabilities:[], widgetWidth, widgetHeight, iconClass }`.
- **erp-pdf-viewer**: `{ showToolbar:true, showOpenFileButton:true, showZoomButtons:true, pageViewMode:'multiple', showPagingButtons:true, showSidebarButton:true, height:'' }` + appStudio props `src`, `base64Src`, `selectedPage`. Behavior: container/canvasContainer.
- **erp-attachments**: `{ readOnlyMode:false, systemCode:'', dataSetId:'', dataViewId:'', attachmentInfo, onOkHandler, onCancelHandler }` (+ sliding-panel extension props).
- **Sliding-panel style components** (erp-print-report, erp-email, erp-process-set, erp-printer-selector, erp-server-folder/file-picker, erp-confirm-form-options, erp-call-log, erp-field-help, erp-memos, erp-change-log, erp-foreign-language-description, erp-dynamic-sliding-panel): share `{ status (EpBaseSlidingPanelStatus), title, iconClass, buttons:[], hideClose, showButtons, showTitle, data, actionData:[], showActions, epOnIconClick, epOnClose }` + component-specific inputs (e.g. print-report: `inputReportId`, `inputStyleNum`, `inputCurrentOutputFormat`, `inputEnableRouting`, `emailOnly`, `clientPrinterMode`; email: `emailTo/From/Cc/Bcc/Subject/Body/attachmentType/...`; process-set: `inputProcessId/Company/SystemCode/TaskNum`). Set `status` via property-set/event to open/close.
- **erp-search-selector**: `{ searchId, likeId }`; **erp-baq-search**: `{ requestModel, searchIdModel, baqId, provider, returnField }`.
- **erp-data-tree**: very large model — nodes/bindings (`treeBindings`, `epTreeViewCheckable`, `checkedKeys`, `expandedKeys`, `selectedKeys`, `rowFilter`, `displayColumns`, `iconRules`, `disabledRule`, `hiddenRule`, per-node `text/key/sysRowID/iconClass/expanded/...`). Behavior `ignoreCapWidth`.
- **erp-gl-account-editor**: `{ hideDynamic, doNotRequireDynamic, coaCodeColumn, allowPattern, separatorCharacter, validateSegmentValues, validateAccountCode, validateDynamicSegments, hideSegmentLabels, bindingExternalCompanyId, bindingDescription, bindingAcctDisp, bindingSegments, accountSearchBinding, bookSelectBinding, showDescription, showBookSelect, useInternalSearch, showAccountSearch, showInternalSearch, descriptionOrientation }`.

---

## 6. erp-combo-box — complete data-source reference

### 6.1 Provider resolution (exact priority — `getDataProviderClass`)
1. `userCodeId` set → **ODataProvider** against `Ice.BO.UserCodesSvc` (obsolete; svc forced to UserCodes).
2. `viewName` set → **ViewProvider** — items from a DATAVIEW (with optional `viewColumnName` = column in that view holding a tilde-delimited list).
3. `queryId` set → **BaqDataProvider** — items from a BAQ (e.g. `zCustomer01`); `restArguments`/`restArgumentsParams` pass BAQ parameters; `searchFilter` applied server-side.
4. `svc` + `svcPath` set → **RestDataProvider** — calls custom REST method (e.g. svc `Erp.BO.CustomerTypeSvc`, svcPath `GetList`); `isDelimited: true` means the method returns a tilde-delimited string found in `parameterName`; `restArguments` are the call arguments.
5. `svc` only → **BoReaderProvider** — BOReader against the service; `dataMode: 'list' | 'rows'` selects GetList vs GetRows; `tableName` names the returned table; `searchFilter` = server whereClause; `filters` applied.
6. `tableName` + `fieldName` (no svc) → **ZDataProvider** — reads the tilde-delimited list stored in that zData table/column (`schema` picks ERP/ICE system code). For zData combos `valueField`/`textField` conventionally `Code`/`Desc` (rowFilter auto-rewrites Code/Desc to actual field names).
7. none of the above → empty data. A static `list` can exist alone or be prepended to provider data when `appendList: true`.
8. Fallback when nothing configured but the bound column's extendedProps carry `codeDescriptionList` → parses that tilde/backtick-delimited string (textField/valueField default to code/description).

### 6.2 Full App Studio property surface (ErpComboBoxProperties + EpComboBoxProperties base)
| property | editor | category | meaning (official tooltip précis) |
|---|---|---|---|
| `dropDownStyle` | auto: `'DropDown'|'DropDownList'` | Advanced | DropDown allows typing when Allow Custom unchecked |
| `list` | collection of `{display, value}` | Advanced | static items |
| `appendList` | bool | Advanced | append static list to retrieved data[] |
| `selectedValue` | string | Advanced | selected value |
| `type` / `subType` / `comboId` | auto/auto/string | **Reusable Combo** | pick a server-defined REUSABLE COMBO (folder/subfolder from `ErpComboBoxReusableService.getTypes()`); choosing type+subType downloads the combo definition and locks (read-only) all reusable properties. This is the mechanism behind "shared combos" — **there is no `$ref` combo mechanism**. Reusable property set = `comboId, svc, svcPath, tableName, fieldName, viewName, textField, valueField, noDataTextField, sort, columns, filters, hiddenColumns, parameterName, returnObj, isDelimited, retrieveColumns, columnCaptions` |
| `svc` | string | Reusable | REST service (e.g. `Erp.BO.CustomerTypeSvc`) |
| `svcPath` | string | Reusable | REST method (e.g. `GetList`) |
| `dataMode` | auto: `'list'|'rows'` | Advanced | when svc without svcPath: GetList vs GetRows |
| `tableName` / `fieldName` | string | Reusable | zData table/column with tilde-delimited items |
| `schema` | auto (system codes ERP/ICE/ext) | Reusable | zData schema |
| `queryId` | string | Advanced | BAQ id |
| `viewName` / `viewColumnName` | string | Reusable | dataview source / delimited column in view |
| `textField` / `valueField` | string | Reusable | display/value member of data objects |
| `noDataText` | string | Reusable | empty text |
| `sort` | string | Reusable | sort column (static list sorted client-side) |
| `retrieveColumns` / `columnCaptions` | stringArray | Reusable | multi-column dropdown columns + captions (single retrieveColumn collapses to no header — see §2.1 create-time behavior) |
| `hiddenColumns` / `hiddenColumnsAppend` | stringArray | Reusable | fetched but not displayed |
| `filters` | stringArray | Reusable | server filters, e.g. `"CustNum = ?[OrderHed.CustNum]"` — `?[View.Col]` tokens bind to the current row; when tokens' values change the combo is invalidated and re-fetched |
| `filtersAppend` | stringArray | Reusable | extra filters appended to reusable-combo filters |
| `filtersParams` | stringArray | Reusable | remap filter token columns to differently-named dataview columns |
| `restArguments` / `restArgumentsParams` | stringArray | Reusable | REST/BAQ call arguments (+ dataview remap) |
| `whereClause` | multiline | Advanced | (Obsolete) use rowFilter |
| `userCodeId` | string | Advanced | (Obsolete) UserCodes source |
| `rowFilter` | multiline | Advanced | CLIENT-side filter applied after retrieval, e.g. `State = 'TX' or State = 'MN'` |
| `searchFilter` | multiline | Advanced | SERVER-side filter applied during retrieval (same syntax) |
| `isDelimited` | bool | Reusable | REST result is a tilde-delimited list |
| `parameterName` | string | Reusable | name of out-param holding the delimited list |
| `defaultZeroString` | string | Reusable | placeholder text assigned value 0 (numeric bindings get an auto "None Selected" zero row unless `isInsertZeroDisabled: true`) |
| model-only extras | | | `epBindingTextColumn` (bind the DESCRIPTION to another column — enables placeholder rows before data loads), `showDistinct`, `isInsertZeroDisabled`, `invalidated` (set true to force refill), `linkedModels` (erp-link-combo-box shares one dataset between combos), `designMode` |

Runtime notes: data re-retrieval happens when filter tokens/rest params change, when a view provider is used, or when data is empty (`shouldGetData`). The `COMBO_REFILL` IceEvent (`setComboInvalidate` in EpKineticComponent) forces `invalidate()` on the live control — this is what the "refresh combo" style actions use. **`retrieveOnActivate` is not a supported property** — do not emit it; refresh behavior is governed by filter invalidation + COMBO_REFILL.

**Reusable combos in hand-authored layers (FIELD-PROVEN):** `type`/`subType` ALONE fetch nothing — the dropdown comes up empty. In App Studio, picking the reusable combo *resolves* the server definition and bakes the concrete fetch properties into the model; a layer you generate must do the same: **emit the full resolved model**, not just the reusable identity. Working example — UDCodes filtered by CodeType via `UserCodes.UserCodesCombo`:

```jsonc
{ "id": "txtStatus", "sourceTypeId": "erp-combo-box",
  "model": {
    "labelText": "Status =", "epBinding": "SearchFilter.Status",
    "dropDownStyle": "DropDownList",
    // reusable identity:
    "type": "UserCodes.UserCodesCombo", "subType": "default", "comboId": "UserCodes.UserCodesCombo",
    // resolved fetch definition (what App Studio bakes in):
    "svc": "Ice.BO.UserCodesSvc", "svcPath": "GetRows", "tableName": "UDCodes",
    "valueField": "CodeID", "textField": "CodeDesc", "sort": "CodeID",
    "retrieveColumns": ["CodeDesc"],
    "filters": ["CodeTypeID = '?{CodeTypeParam}'"],   // inherited from the reusable def
    // your inputs:
    "filtersParams": ["CodeTypeParam=OrderStatus"],    // supplies the CodeType value
    "hiddenColumnsAppend": ["IsActive"], "rowFilter": "IsActive=true" } }
```

Note `filtersParams` here supplies a **literal value** for the reusable filter token (`CodeTypeParam=<CodeType>`), not just a dataview-column remap. The combo stores the **CodeID** into its binding — filter downstream queries with that (e.g. `UD103_ShortChar01 = '??{SearchFilter.Status}'`). When possible, let the user pick the reusable combo in App Studio once, then pull the layer down and adopt the resolved model.

### 6.3 Example layer component
```jsonc
{
  "id": "cmbShipVia",
  "sourceTypeId": "erp-combo-box",
  "parentId": "colRight",
  "model": {
    "labelText": "Ship Via",
    "epBinding": "OrderHed.ShipViaCode",
    "svc": "Erp.BO.ShipViaSvc", "dataMode": "list", "tableName": "ShipViaList",
    "valueField": "ShipViaCode", "textField": "Description",
    "filters": ["Company = ?[CallContextClientData.CurrentCompany]"],
    "searchFilter": "", "rowFilter": "",
    "retrieveColumns": ["ShipViaCode", "Description"],
    "columnCaptions": ["Code", "Description"],
    "dropDownStyle": "DropDownList"
  }
}
```

---

## 7. Example layer snippets (verified shapes)

```jsonc
// text box with search button
{ "id": "txtPartNum", "sourceTypeId": "erp-text-box", "parentId": "col1",
  "model": { "labelText": "Part", "epBinding": "OrderDtl.PartNum",
             "enableSearch": true, "searchTitle": "Part search...",
             "autocomplete": "off", "masked": false } }

// button (disabled via rules/property-set — never 'enabled')
{ "id": "btnCalc", "sourceTypeId": "erp-button", "parentId": "col2",
  "model": { "labelText": "Calculate", "style": 0, "size": "ep-btn-size-regular",
             "icon": "mdi mdi-calculator", "disabled": false } }

// shape
{ "id": "shpOnHold", "sourceTypeId": "erp-shape", "parentId": "col2",
  "model": { "enabledCaption": "ON HOLD", "disabledCaption": "OK",
             "status": 2, "hidden": true } }

// tag bound to boolean
{ "id": "tagOpen", "sourceTypeId": "erp-tag", "parentId": "col1",
  "model": { "epBinding": "OrderHed.OpenOrder",
             "trueCaption": "Open", "trueStatus": 0,
             "falseCaption": "Closed", "falseStatus": 2 } }

// panel card with a row of two columns in the body
{ "id": "cardHeader", "sourceTypeId": "metafx-panel-card", "parentId": "page1",
  "model": { "title": "Header", "expanded": true,
    "bodyComponents": [
      { "id": "rowMain", "sourceTypeId": "metafx-div",
        "model": { "class": "row", "column": 2 },
        "components": [
          { "id": "col1", "sourceTypeId": "metafx-col",
            "model": { "flexBasis": "50%" }, "components": [ /* fields */ ] },
          { "id": "col2", "sourceTypeId": "metafx-col",
            "model": { "flexBasis": "50%" }, "components": [ /* fields */ ] } ] } ] } }
// NOTE: this nested form documents the RAW runtime model. Real exported layers are FLAT:
// each component is its own entry with parentId ("cardHeader#bodyComponents", "rowMain", …) —
// author layers in the flat form (§3.3), and prefer metafx-matrix (§3.8a) for field grids.

// property-set event action param
{ "type": "property-set",
  "param": { "component": "shpOnHold",
             "props": [ { "prop": "hidden", "value": false },
                        { "prop": "status", "value": 1 } ] } }
```

---

## 8. `appStudiosModel` activity surface

`appStudiosModel` is the per-control property lists surfaced to the reflection/activity API (`getAppStudiosComponentModel(id)`). Every erp control exposes at minimum `id, labelText, epBinding, readonly, disabled, hidden, alignment`; controls with extra entries: ErpComboBox (all data-source props), ErpGlAccountEditor (binding/validation props), ErpShape (`enabledCaption, disabledCaption, status`), ErpTag (`trueCaption, trueStatus, falseCaption, falseStatus`), ErpTokenDate (`epBindingToken`), ErpServerFileBox / ErpServerFolderBox / ErpFileBox (folder/filter props), ErpPrintOutputFormat (`epBindingEnableRouting`), ErpPdfViewer (`src, base64Src, selectedPage, showToolbar, ...`). Use this as the safe subset for dynamic property manipulation.

---

## 9. Contradictions / corrections vs existing reference & lessons

1. **`enabled` is not a property.** Confirmed: no Ep/Erp model has `enabled`; the key is `disabled` (state-property). Lessons §3 correct; any reference text suggesting `enabled` in property-set is wrong.
2. **Shape `enabledCaption` live behavior**: runtime mechanics (template getters + shallow KeyValueDiffer + property-set patching the live `controlModel`) say a top-level `enabledCaption` patch SHOULD re-render. The observed lessons failure is most plausibly (a) writing `enabled` (dead key) alongside, (b) targeting the layout node before/without instantiation (the live control model is a `cloneDeep` of the layout node — patches only reach it through the `factoryControl.controlModel` path while the control exists), or (c) rule-based (row-rule) attempts, which only handle the EpStateProperty ids (`disabled/hidden/readonly/required/labeltext/status`), NOT arbitrary props like enabledCaption. Recommendation stands: prefer `hidden`, `status`, `disabled` for live shape changes; treat captions as render-once unless proven otherwise on the target version.
3. **`hidden` special-cased** in the metafx wrapper (CSS class + layoutControlVisibility) — reliably live for every component including containers. Matches lessons.
4. **RETRACTED — `parentId: "<id>#<slot>"` IS the valid layer-authoring form** (see §3.3). The "no `#` syntax" claim was true only of the raw runtime model; App Studio layers/diffs use the flat `#slot` form and it renders (FIELD-PROVEN). Author layers with flat `parentId` + `#slot`.
5. **RETRACTED — `metafx-matrix` EXISTS on current builds** and is App Studio's standard grid-of-fields layout (see §3.8a for the working pattern).
6. **`retrieveOnActivate` does not exist.** Combo refresh = filter-token invalidation, `invalidated` flag, or COMBO_REFILL event.
7. **`$ref` shared combos do not exist**; the shared-combo mechanism is the Reusable Combo (`type`/`subType`/`comboId`) resolved via `ErpComboBoxReusableService` server metadata.
8. **`zdata` is not a property**: the zData source is selected implicitly by `tableName`+`fieldName` (without `svc`).
9. **Grid model**: `allowAddNew`/`allowDelete`/`hideViewSelector` are NOT in the serialized panel-card-grid gridModel; the serialized shape is the §3.7 verbatim block (editOptions/editable/disablePasteNew/disablePasteUpdate/selectorColumn/selectionOptions/viewOptions...). If the existing reference lists those three keys, they are from a different (newer) Kinetic version or invented — verify against a live GetNativeKineticApp dump before use.
10. **erp-tag IS fully reactive** (explicit onModelValueChange) — safe to property-set captions/statuses live, unlike erp-shape.
11. Button `style` is a **numeric** enum in JSON (0..4), `size` is a CSS-class string — mixing these up silently falls back to defaults.
