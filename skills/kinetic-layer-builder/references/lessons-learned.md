# Kinetic Layer Uplift — Lessons Learned (field-proven gotcha log)

Practical findings from real layer builds: uplifting a classic Sales Order Entry
customization into a Kinetic App Studio layer on `Erp.UI.SalesOrderEntry` (§1–§15), and building
a BAQ-search app on `Ice.UI.UD103Entry` (§16–§18). These are things
discovered through trial, error, and user feedback that the framework references don't cover.
Capture-worthy because they cost real iterations to find.

---

## 1. Import / round-trip mechanics

**Outbound import: never paste base64.** Hand-transcribing or pasting large base64 into a
tool call corrupts the payload mid-stream. The reliable path is:
`request_file_upload` → `curl -T <zip> "<uploadUrl>"` (direct HTTP PUT) → `MCPToolsKinetic-ImportLayer`
with the returned `fileRef` GUID. This avoids transcription corruption entirely.

**Inbound read — SOLVED later (see §3i/§11); this paragraph is the original, outdated worry.**
At first, reading the *current server state* back appeared to corrupt via base64 over the wire.
This was resolved once `MCPToolsKinetic-GetIndividualLayer` returned an off-band `downloadUrl` (GET the
zip directly — no base64 transcription; §3i, §11). NOTE that re-importing still replaces the
**whole** layer, so any manual/published edit not mirrored in your local build is overwritten —
so **always re-download the current published layer before editing** (§3r) and diff against it,
rather than replaying edits from memory.

**Always `MCPToolsKinetic-Commit` before importing** — it versions the record (returned an
incrementing rev number like "35") so there's a rollback point.

**Local build artifacts** live in a local working zip of the layer. Patching the manifest in-place with a small inline Python script
(unzip → edit `SysCharacter03` JSON → rezip) proved more robust than regenerating from the
full `build_layer.py`, which kept getting truncated at the tail.

---

## 2. What broke Save — and "always call existing events"

**Save broke because of a `data-commit` widget added to the RTP toggle event.** Dropping a
`data-commit` action into a custom event to force a save was the culprit. **Removing the
`data-commit`** fixed it — and the right behavior is to let the user click the toolbar **Save**
to commit the data manually.

**If you want to commit automatically, don't reinvent the commit — call the existing Save
event.** Use an **`event-next`** action that invokes the app's built-in Save event rather than
a raw `data-commit`. The toolbar Save event already handles the commit correctly; piggy-backing
on it avoids the breakage a bare `data-commit` causes.

**General principle: always call existing events when one already does the job.** Prefer
`event-next` into a stock event over hand-rolling the same effect with low-level actions.

---

## 3. property-set: what actually updates live vs what doesn't

- On **buttons**, use the `disabled` property to lock them, **not** `enabled`. Setting
  `enabled` via `property-set` does nothing visible. (This is why the Project Search button
  wouldn't go read-only until switched to `disabled`.)
- On **shapes (metafx-shape)**, `property-set` on `enabledCaption` / `enabled` does **not**
  re-render live. You can't change a shape's text/color on the fly that way.
- **Working pattern for a shape that must reflect a boolean live:** create *two* shapes
  (one per state, pre-colored and pre-captioned) and toggle their `hidden` property. Critical
  detail: place the two shapes **immediately adjacent** in the same column. If they're
  separated, the visible one "jumps" to fill the hidden one's slot when toggled.

---

## 3a. Sibling order = Diffs ARRAY order, not the `Index` value

This one cost a round-trip. When several components share a parent (e.g. the buttons and
shapes in `custInfoColD`), the engine inserts them in **the order their `Add` diffs appear in
the page's `Diffs` array** — it does **not** sort siblings by their `Index` field. A diff with
`Index:1018` placed *last* in the array still lands at the bottom of the column.

Fix: physically reorder the diff objects in the `Diffs` array to the desired visual order
(and renumber `Index` to match for clarity). Don't rely on `Index` alone to slot a component
between existing siblings — move its diff to the right array position.

## 3b. onInit timing — trigger the toggle off the LAST control to render

For the two-shape hidden-toggle pattern (3 above), the initial-state event must run **after
the shapes themselves exist**. Symptom we hit: on first load the *button* label updated
correctly ("Make Changes") but the *green* shape stayed visible — the wrong one. Cause: the
init event was triggered on `btnCustRTP`'s `onInit`, which fires before the shapes render, so
`property-set hidden` on the not-yet-created shapes was a silent no-op (while the button, which
already existed, did update).

Attempted fix (insufficient): trigger the display event on the onInit of the last-rendering
control. This still failed — the shape's `onInit` fires while `OrderHed` is still empty
(`count 0, row -1`), and re-running the toggle after the row loads still didn't re-render the
shape. See 3c for the real fix.

## 3c. FAILED approach — rules on `CallContextBpmData.CharacterNN` collide with base shapes

Tempting idea that **backfired badly**: drive the two shapes' visibility with
`SettingStyle.Invisible` rules keyed on `OrderHed.ReadyToCalc`, targeting the shapes by their
`epBinding` (`CallContextBpmData.Character19` / `Character20`).

Why it broke: **`CallContextBpmData.CharacterNN` is NOT a private scratch space — the base
Sales Order form already uses that range for its own status shapes** (Inactive Customer, LOC
Hold, Credit Hold, Linked, Attributes Required, etc.). A rule that targets an `epBinding` in
that range resolves against the base components that share it, and the result was **every base
status shape forced visible on load**. Reverted immediately.

Takeaways:
- Do **not** assume `CallContextBpmData.CharacterNN` is free. The base app squats on much of
  that range. If you bind custom shapes there, you're sharing a namespace with base controls —
  fine for a plain bound shape, but **dangerous for rules**, which match by binding and will
  sweep in every component on that binding.
- A rule that toggles `SettingStyle.Invisible` by `epBinding` will hit *all* components bound
  to that path, not just yours. Rules match on binding, not component id.
- When a change has blast radius beyond the intended control, **revert first, diagnose second**
  — don't stack another speculative fix on a regression the user is staring at.

## 3d. The real fix — bind custom shapes to unique `TransView` columns, then rule them

The rules approach (3c) was right; the *binding* was wrong. Fix: bind each custom shape to a
**unique `TransView` column** that nothing else uses, then key the visibility rules to those
specific `dataview.column` bindings.

- `shpCustRTP` → `model.epBinding = "TransView.RTCShapeGreen"`
- `shpCustRTPYellow` → `model.epBinding = "TransView.RTCShapeYellow"`
- Rule `r_custRTPGreenInvis`: `OrderHed.ReadyToCalc = true` → `SettingStyle.Invisible` on
  `TransView.RTCShapeGreen`.
- Rule `r_custRTPYellowInvis`: `OrderHed.ReadyToCalc = false` → `SettingStyle.Invisible` on
  `TransView.RTCShapeYellow`.

Why `TransView` is the right home:
- **`TransView` is a transient, UI-only transaction view** — there is no server schema, and
  the base app freely sets ad-hoc `TransView.*` flags via `row-update` (e.g. `SearchRanBefore`,
  `SysReadOnly`). So you can introduce a brand-new column like `RTCShapeGreen` just by binding
  to it; no `additionalColumns` / dataview Replace needed, and it does NOT go to the BO (no
  Save pollution, cf. section 2).
- Because the column name is **yours and unique**, a rule that matches on that binding affects
  **only your shape** — eliminating the base-shape collision from 3c.
- Default both shapes `model.hidden = false`; let the rules do the hiding. (Leaving a shape
  `hidden:true` in the model can fight the rule that wants it visible.)
- Each shape's *color* comes from its static `model.status` (0 = green, 1 = yellow); the
  binding is just the rule's handle, it doesn't need a data value to render.

General principle: **for a custom control whose state is data-driven, give it its own unique
`TransView` binding and control it with a rule.** Never hang custom rules off a binding the
base app also uses (`CallContextBpmData.CharacterNN` is base-owned — see 3c).

Confirmed working pattern (user's own implementation, the one we kept): shapes bound to
`TransView.RTPShapeGreen` / `TransView.RTPShapeYellow`, with two rules whose **`dataView` is
`TransView`** but whose **`condition` references `OrderHed.ReadyToCalc`** —
`cr_RTPShapeGreen` (`OrderHed.ReadyToCalc = True` → Invisible `TransView.RTPShapeGreen`) and
`cr_RTPShapeYellow` (`OrderHed.ReadyToCalc = False` → Invisible `TransView.RTPShapeYellow`).
So a rule's `condition` CAN reference a different view than its `dataView`; the `dataView` just
scopes which component the action resolves against. The event (`ce_custRTPDisp`) is left to do
only the button `labelText` — no shape handling at all.

## 3e. `customizable: false` = LOCKED. Always set `customizable: true` on items you generate

App Studio shows layer items (rules, events, etc.) as **locked** when `customizable: false` —
the user can't edit them in the designer. Several rules I generated defaulted to
`customizable: false`, which the user (rightly) objected to. **Always emit `customizable: true`
on every rule/event/component you create**, so the user can edit them in App Studio. Unlocking
later is just flipping that flag to `true`.

## 3f. `DisableRow` DOES disable native status shapes — exclude them by column

`DisableRow` on `OrderHed` (the Ready-to-Process lock) greys out the **native status shapes**
(Closed, Open, Credit Hold, LOC Hold, Linked, EDI Changes Made, Inactive Customer, etc.),
because those shapes are bound to `OrderHed.*Shape` columns. To keep them looking normal while
locked, add their column names to the rule's `exceptTheseColumns`.

The native OrderHed status-shape columns (from `GetNativeKineticApp`, strip the `OrderHed.`
prefix) are: `LinkedShape, LinkedIssueShape, CustomerPrintAckShape, CreditOverrideShape,
ShowApplyOrderDiscountsControlShape, LOCHoldShape, OrderHeldEsh, AttributesRequiredShape,
CounterSaleProcessedShape, MakeDirectReleasesNoJobLinkShape, CustOnCreditHoldShape,
EDISendAckShape, ExtAOEShape, ERSOverrideShape, OTSTaxValidationStatusNotValidated,
OTSTaxValidationStatusInvalid, OTSTaxValidationStatusValid, OTSSavedShape, ClosedOrderShape,
OpenOrderShape, InactiveShipViaShape, TaxIncldPriceEsh, InactiveCustomerShape,
InactiveShipToShape`. (Note: this **contradicts the earlier worry in §4** that a long
`exceptTheseColumns` breaks `DisableRow` — excluding real, valid column names is fine and is in
fact required here. The earlier lock failure had other causes.)

## 3g. Reading the live layer back — OBSOLETE base64 method (Lens has since changed; use §3i/§11)

> **OUTDATED — `MCPToolsKinetic-GetIndividualLayer` no longer returns inline base64.** Lens was changed so
> the tool returns an **off-band download** instead: a `downloadUrl` under `Base64EncodedLayerZip`.
> GET that URL directly (`curl -o`/`requests.get`) to retrieve the zip — there is no base64 to
> transcribe or repair anymore. Do NOT use the base64/`base64 -d`/one-char-repair dance below; it
> describes a version of the tool that no longer exists. See §3i and §11 for the current mechanic.

Historical record (the old method, kept only to explain earlier notes): the tool used to return
`Base64EncodedLayerZip` inline; hand-transcribing that base64 corrupted it, so the workaround was to
write it to a file and `base64 -d`, brute-force-repairing an off-by-one (`len % 4 == 1`) by deleting
each index until a variant decoded to a valid zip (`raw[:2] == b'PK'`). None of that is needed now —
the current tool hands back a file/download reference (a `downloadUrl`), not inline base64.

## 3h. CRITICAL: `GetIndividualLayer` returns the PUBLISHED layer, NOT the user's draft

`MCPToolsKinetic-GetIndividualLayer` exports only the **published** version of a layer. If the user is
editing in App Studio and hasn't published, their work lives in **unpublished draft content**
that this export does not include. Symptom that burned us: the export showed only 3 rules, but
the user's App Studio session had `r_custApprove` and many more — because those were in the
draft, not the published layer.

How to detect: call `MCPToolsKinetic-GetLayers` with `IncludeUnpublished: true` and check
**`HasDraftContent`** on the target layer. `true` = there is unpublished draft work you cannot
see via `GetIndividualLayer`. (Also note `WIP` and `ChangedOn`.)

Consequences and rule of thumb:
- Do **not** reconstruct/diff against `GetIndividualLayer` output when `HasDraftContent: true` —
  you'll be working from a stale, incomplete baseline and will silently drop the user's draft
  rules/components on re-import.
- `MCPToolsKinetic-ImportLayer` + `MCPToolsKinetic-Commit` write to the **published** track. They do not merge
  into an open draft; the user's draft persists separately (`HasDraftContent` stays true), so
  published and draft diverge.
- Correct workflow when the user is actively editing: have the user **publish their draft
  first**, then read the now-complete published layer, apply changes, and re-import. There is no
  tool here to read or write the unpublished draft directly.

> **UPDATE (see §18):** in a later session the export's record carried the
> App Studio draft in `SysCharacter03` alongside the published `Content` — diff the two blocks to
> see (and adopt) the user's draft edits before assuming draft work is unreachable.

## 3i. Reliable read via download URL; published manifest lives in `Content`

`MCPToolsKinetic-GetIndividualLayer` was updated to return an **off-band download** (a `downloadUrl`
under `Base64EncodedLayerZip`), not inline base64. `curl -o`/`requests.get` the URL to get the
zip directly — this finally kills the hand-transcription corruption problem (sections 3g) for
good. Use this path; don't transcribe base64 anymore.

Key format gotcha: in the **published** layer export, the manifest JSON is stored in the
record's **`Content`** field, and `SysCharacter03` is empty — the opposite of the builds we
generated (which put it in `SysCharacter03` with `Content` empty). Both import fine, but when
editing a downloaded published layer, read/modify/write **`Content`**. Detect which field holds
it by checking which is non-empty.

Also confirmed: the layer legitimately had only **3 custom rules**
(`r_custRTPLockHed`, `cr_RTPShapeGreen`, `cr_RTPShapeYellow`). The dozens of other rules visible
in App Studio's Data Rules panel are **base** rules from the native app, not layer diffs — so a
low layer-rule count is not necessarily a sign of lost work.

## 3j. Upload endpoint can fail transiently — just retry

The `request_file_upload` → `curl -T` → `MCPToolsKinetic-ImportLayer` flow returned HTTP 400
`"Connection closed before upload completed"` on ~6 consecutive attempts (fresh refs, curl and
Python, with/without `Expect:`), then succeeded on a later retry with no change to the command.
Treat this error as transient infrastructure, not a problem with your zip or method — retry
after a short wait rather than rebuilding. Each `uploadUrl`/`fileRef` is effectively single-use;
request a fresh one per attempt. (Local working files in `/tmp` don't survive between separate
bash calls — copy from the mounted folder within the same call.)

## 3l. CORRECTION — the right way to lock the SO form: drive `TransView.SysReadOnly`

The diagnoses in 3k and 3f were WRONG; the base app settled it. Findings from
`GetNativeKineticApp`:

- The base rule **`openOrderRule`** (dataView `OrderHed`, action `DisableRow`) already makes the
  main Order Header read-only, keyed on
  `OpenOrder = false or [TransView].[SysReadOnly] = true or (...)`. Its `exceptTheseColumns`
  lists **exactly the native status-shape bindings** (`CustomerPrintAckShape`, `OpenOrderShape`,
  `InactiveCustomerShape`, `LinkedShape`, …) plus `OrderNum`/`ShowKitDetails`. So:
  - Shape names in `exceptTheseColumns` are **valid and reversible** (3f's worry was wrong).
  - `DisableRow` **does** reverse on a live condition flip (3k's "not symmetric" was wrong).
- Whole-form read-only in Sales Order Entry is governed by the framework flag
  **`TransView.SysReadOnly`**. Many base rules key on it: `openOrderRule` (main hed),
  `releaseClosedRule` (OrderRel), `disableOrderHedUPSRow`, `hideToolsReadOnlyMode` (hides
  toolbar tools — this is why the Save icon disappears in read-only), etc.

So the real bug behind "lock won't release" was a **custom `DisableRow` rule
(`r_custRTPLockHed`) on the same `OrderHed` dataview duplicating/conflicting with the base
`openOrderRule`** — two rules managing the same row's disable state don't compose, so the
re-enable didn't take.

Correct implementation (what we shipped): **delete the custom lock rule** and instead set
`TransView.SysReadOnly = {ReadyToCalc}` (true→lock, false→editable) from the existing
`ce_custRTPDisp` event (fires on `onInit`, OrderHed `rowChanged`, and `ReadyToCalc`
`columnChanged`). The base `openOrderRule` then does the locking + reversal for free, native
shapes stay intact, and `hideToolsReadOnlyMode` handles the toolbar. Don't hand-roll a
row-disable rule on a dataview the base already governs — drive the base's own read-only flag.

Caveat: `SysReadOnly` is the framework's *global* read-only flag; tying it to `ReadyToCalc`
means a genuinely read-only/tracker context could be overridden. Guard if that ever matters.

Also: chaining the toggle button to the base `Update` (Save) event was a mistake — it engaged
the update-lock/read-only state and **hid the Save toolbar icon**. Removed. (Rules re-evaluate
on a field change without needing a row-change/refresh, per the user — so no commit was needed.)

## 3m. "No record loaded" state for the custom box

> **The button `property-set {disabled}` approach below is SUPERSEDED by §3n/§3o:** give the
> buttons a `TransView` binding and disable them with a RULE instead (declarative, reversible, no
> competing event triggers). The shape/rule guidance here still stands.

When no order is loaded (`[OrderHed].[$rowCount] = 0`, OrderNum 0), the RTP box should: green
shape disabled showing "No Record Loaded", yellow shape hidden, both buttons disabled.

- **Buttons have no `epBinding`** (`btnCustRTP`, `btnCustApprove`), so rules can't target them —
  disable via `property-set` `{prop:"disabled"}` in an event. Folded into `ce_custRTPDisp` as a
  prepended condition `"{OrderHed.OrderNum} > 0"` → onSuccess enable both, onFailure disable
  both. (Keeping it in `ce_custRTPDisp` reuses its init/rowChanged/columnChanged triggers
  instead of adding competing handlers on the same trigger.)
- **Shapes have `epBinding`**, so use rules. Green: set `model.disabledCaption = "No Record
  Loaded"` and add a rule `SettingStyle.Disabled` on `TransView.RTPShapeGreen` when
  `[OrderHed].[$rowCount] = 0` (dataView `TransView`, condition cross-refs OrderHed rowCount).
  Yellow: extend its Invisible condition to
  `OrderHed.ReadyToCalc = False or [OrderHed].[$rowCount] = 0` so it's also hidden with no row.
- Open question to verify on the device: whether `SettingStyle.Disabled` on an `erp-shape`
  swaps the caption to `disabledCaption`. If it only greys without swapping text, drive the
  shape's bound boolean value instead (false → disabledCaption).

## 3n. Give ANY control a binding so rules can target it (incl. buttons)

A control with no `epBinding` (e.g. a plain button) can be made rule-targetable by simply
**assigning it an `epBinding` to a `TransView` column — the column does not need to exist in
any dataview; it's created on the fly** (same trick as the RTP shapes). Then a rule's
`SettingStyle.Disabled` (or Invisible/ReadOnly) action can target that binding.

Applied here: `btnCustRTP` → `TransView.RTPBtnRTP`, `btnCustApprove` → `TransView.RTPBtnApprove`,
and the single rule `r_custRTPGreenNoRec` (`[OrderHed].[$rowCount] = 0`) now disables the green
shape AND both buttons in one place (a rule can hold multiple actions).

The binding view is **not restricted to `TransView`** — the column just has to be a unique
handle and need not exist in the dataview. Per the user, `OrderHed.MyNewButton` (a column that
doesn't exist on OrderHed) is perfectly acceptable as a control binding for rule targeting.
`TransView` is simply a convenient, clearly-client-only home; pick whatever reads best. This replaced the
event `property-set {disabled}` approach (§3m) — prefer the rule: it's declarative, reversible,
and doesn't compete for event triggers. Rule of thumb: if the only reason you were reaching for
an event `property-set` is that a control "has no binding," just give it a `TransView` binding
and use a rule instead.

## 3o. `OrderHed.$rowCount = 0` (dotted) is the correct no-record condition — CONFIRMED

Row-count in a rule condition, confirmed against the user's own published rules:

- `OrderHed.$rowCount = 0` — **dotted cross-view form**; correct when the rule's `dataView` is
  something else (e.g. `TransView`). This is what the user shipped and it works. Same dotted
  convention as a cross-view field ref (`OrderHed.ReadyToCalc`).
- `[OrderHed].[$rowCount] = 0` — bracket form the base uses in its own `OrderHed`-dataView
  rules.

IMPORTANT correction: my earlier belief that the dotted `$rowCount` form "corrupted" the rules
was WRONG. The dotted form is fine. The corruption that emptied App Studio's Data Rules panel
and lit up every shape was entirely the **malformed diff wrapper** (§3p) — a red herring that
made the syntax look guilty. `$rowCount = 0` also catches the literal zero-row state, which a
field ref like `OrderNum = 0` can miss (a field reads null when there's no row).

Shipped no-record pattern (Action Data View = `TransView`, per-binding `SettingStyle`, NOT
`DisableRow`):
- `r_custRTPGreenNoRec` (cond `OrderHed.$rowCount = 0`) → `SettingStyle.Disabled` on
  `TransView.RTPShapeGreen`, `TransView.RTPBtnRTP`, `TransView.RTPBtnApprove`, and
  `TransView.BypassOutlierSession` (the Bypass Outlier checkbox `custBypassWarn` was bound to
  that column so it disables too — "everything in the box").
- `cr_RTPShapeYellow` cond `OrderHed.ReadyToCalc = False or OrderHed.$rowCount = 0`.

Hide the native Ready To Process tag: it's the base component **`chkReadyToCalc`** (an
`erp-tag` bound to `OrderHed.ReadyToCalc`, captions "Ready To Process" / "Ready To Process is
not set"). **Prefer setting the control's own `hidden:true` over a hide rule** (user's
preference, and cleaner). To change a base control's property, use a **`Replace` diff** with the
control's **full component** + the changed prop:
`{"Id":"chkReadyToCalc","Path":"components","Value":{...full base component..., model.hidden:true},"Operation":"Replace","Index":<n>}`
placed in the page section the control lives on (`Details` here). Per the layer reference
(§"Modify an existing component"): `Path:"components"`, `Operation:"Replace"`, `Id`=component
id, `Value`=full component. Since it's hidden, `Index`/position is irrelevant.

Rule of thumb: an always-on visibility/enable change to a SINGLE base control = set the
control's property via a `Replace` diff; reserve rules for *conditional* styling.

## 3r. ALWAYS re-download the current layer before each edit (don't reuse a stale local copy)

Bit me: I rebuilt a new revision from a `layer_cur.zip` that predated an earlier commit, so a
prior change (`chkReadyToCalc` hidden) silently got dropped because import REPLACES the whole
layer. Each `MCPToolsKinetic-ImportLayer` overwrites everything; if you build from a stale baseline you
lose any commits made since. **Before every edit, `GetIndividualLayer` → download fresh →
modify → import.** Never trust the on-disk `layer_cur.zip` from a previous turn, especially
after the user has published or you've committed in between.

## 3s. Dissolve a custom panel card into a base panel (header pattern, reused on lines)

To merge a custom "X Info" panel card's fields into a base panel (so they appear inside the
base section rather than as a separate card):
- Reparent the custom row container to the base panel's body slot: set the row's `parentId` to
  `<basePanelId>#bodyComponents`.
- Remove the custom `metafx-panel-card` diff entirely.
Header used base `pcOrderDetail` ("Order Header"); lines use base **`pcOrderDtlDetail`**
("Line Detail"). Base panel ids come from `GetNativeKineticApp` (grep `metafx-panel-card`
ids/titles). Component types seen: text area = **`erp-text-area`** (vs `erp-text-box`); a
standalone "own card" = a top-level `metafx-panel-card` with `parentId:null` and a `title`,
fields parented to its `#bodyComponents`.

## 3t. Placing custom fields into base columns to mirror classic (Line Detail)

To make an uplifted page resemble the classic layout, don't drop custom fields in a single
appended row — reparent them into the **base column containers** at sensible positions. Base
container ids come from the base app layout file: `GetNativeKineticApp` →
`AppContent.Files["pages\\OrderLineDetailPage.layout.jsonc"]` → `layout.components` (a FLAT
list; each has `parentId`). Panels expose body slots as `<id>#bodyComponents`; **rows/cols use
the plain id as `parentId`** (e.g. a field in a column has `parentId:"div-col-839ad"`, not
`#bodyComponents`). Base Line Detail map: panel `pcOrderDtlDetail` → body row `div-row-c051b` →
4 columns; key inner cols: Quantity/Price = `div-col-839ad`, Discount = `div-col-d321f`,
Reference = `div-col-e89f2`. Append a custom field by reparenting it to the target col id with a
high `Index` (e.g. 1100+) so it lands at the bottom of that column.

Classic→Kinetic line mapping used: Est Unit/Ext Cost + Order UOM + Get-Est button →
`div-col-839ad`; Bypass Outlier + Reason → `div-col-d321f`; Project + Project Search →
`div-col-e89f2`. Each "Close Reason" became its own top-level `metafx-panel-card`
(parentId null) holding an `erp-text-area`.

## 3u. GetIndividualLayer can lag a revision — always build the COMPLETE desired state

Observed: after committing a new revision, `GetIndividualLayer` still returned the previous
revision's content (publish/cache lag). Building on that stale download silently omitted the
newly committed changes. Mitigation:
(a) re-download right before editing (§3r), AND (b) when in doubt, **build the complete desired
end-state** rather than an incremental diff — since `MCPToolsKinetic-ImportLayer` replaces the whole
layer, a complete build is self-correcting even if the baseline lagged. After import, verify by
re-downloading; if it still shows the old state, it's a publish lag, not a failed import — the
user's App Studio reload reflects the import.

## 3v. Inline field search (built-in icon) instead of a separate search button

To give a text field a built-in search icon (like base `OrderNum`/`ShipToNum`/`CustomerCustID`)
rather than a separate button: set **`model.enableSearch: true`** on the `erp-text-box`. For a
*custom* search (no framework default), wire the field's **`onSearch`** hook to your search
event: trigger `{"type":"Control","target":"<fieldId>","hook":"onSearch"}` → the same
`search-show` + `search-value-set` actions the button used. Then delete the button.

Applied: `custHedProjectId` (OrderHed.ProjectID_c) and `lineProjectId` (OrderDtl.ProjectID) got
`enableSearch:true`; buttons `btnCustHedProject`/`btnLineProject` removed. Before deleting a
button, confirm nothing else references it (e.g. grep `ce_custRTPDisp` for property-set targets).

**Wiring the click — the correct trigger (confirmed against App Studio):** `enableSearch:true`
only shows the icon. The icon's behavior is **"On Search Click"** in the App Studio property
panel, which is the **`onSearch`** hook — and the trigger MUST be
`{"type":"EpBinding","hook":"onSearch","target":"<binding>"}` (target = the field's *binding*,
e.g. `OrderHed.ProjectID_c`), NOT `type:"Control"`. When wired correctly, App Studio shows an
**ellipsis** on "On Search Click"; a **`+`** means no event is attached (the giveaway that the
trigger is wrong/mis-typed).

Pitfalls I burned time on:
- `{"type":"Control","hook":"onSearch"}` — wrong trigger TYPE; doesn't bind to On Search Click.
- `{"type":"Control","hook":"onClick"}` — that's the field's "On Click", a different slot;
  leaves "On Search Click" empty (`+`).
- The header `TypeError: 'null' where a stream was expected` happened while On Search Click was
  unattached: the framework tried its default search for the field and, because the binding is
  the **custom `OrderHed.ProjectID_c`** (no framework-registered search), returned null. (The
  line "worked" only because its base binding `OrderDtl.ProjectID` HAS a framework search.) Once
  our event is properly attached via `EpBinding/onSearch`, our `search-show` runs and both
  base- and custom-bound fields work.

## 3y. DEFINITIVE: inline field search wiring = `EpBinding` → `onClick` → `DataView.Column`

CONFIRMED CORRECT (user fixed it after I burned many iterations): for a field with
`model.enableSearch: true`, wire the search to an event whose trigger is
**`{"type":"EpBinding","hook":"onClick","target":"<DataView.Column>"}`** — EpBinding type,
**`onClick`** hook, target = the field's data binding (e.g. `OrderHed.ProjectID_c`,
`OrderDtl.ProjectID`). The event then runs `search-show` + (column-suppressed) `search-value-set`.

What was wrong in my attempts (all of §3v/§3w/§3x guesses):
- `Control/onSearch` and `Control/onClick` → did NOT attach to the search icon (null / no fire).
- `EpBinding/onSearch` → attached but fired on every column change (typing) and looped.
- The right hook is **`onClick`** (not `onSearch`) with **`EpBinding`** type.

When to add a custom search event at all:
- Field bound to a **base searchable field** (e.g. `OrderDtl.ProjectID`): just set
  `enableSearch: true` — the framework's **native `onClick` search fires automatically**. Do NOT
  add a custom search event; it double-fires `search-show`. (Removed `ce_custLineProjSearch` for
  this reason.)
- Field bound to a **custom `_c` field** with no native search (e.g. `OrderHed.ProjectID_c`):
  `enableSearch: true` + a custom event `{"type":"EpBinding","hook":"onClick","target":"<binding>"}`
  that runs `search-show` + column-suppressed `search-value-set`.

PROCESS LESSON: when replicating a base behavior (here, the built-in search icon), **inspect a
working base control first** — `numKeyField`/`OrderNum`, `txtShipToNum`, `txtCustomerCustID2`
all have `enableSearch:true`; reading how their search event is wired would have given the
`EpBinding/onClick/binding` answer immediately instead of guessing trigger permutations.
(Sections 3v/3w/3x below are kept only as a record of the wrong turns; 3y is the truth.)

## 3x. CORRECTION: `EpBinding` trigger on a column = a column-change listener (not a search-icon trigger)

Despite the reference table listing `{"type":"EpBinding","hook":"onSearch","target":"<binding>"}`
as "the search icon on a field," in practice an **`EpBinding` trigger whose target is a data
column registers as a column-change listener** — it fires on every change to that column
(confirmed: just *typing* in the project field fired `ce_custHedProjSearch`). The `onSearch` hook
did not restrict it. This (not "bindings inherently fire columnChanging" — they don't) was the
real cause of the project search re-running.

Fix: trigger the search event from the **control**, not the binding:
`{"type":"Control","hook":"onSearch","target":"<controlId>"}` (e.g. target `custHedProjectId`).
That fires on the search-icon click only, not on column changes. Rule of thumb: for a
field/control UI action (search icon, button), use a **`Control`** trigger keyed to the control
**id**; reserve `EpBinding` triggers for when you genuinely want to react to a column's data
changing (those are `columnChanging`/`columnChanged`-style listeners).

## 3w. Search feedback loop: wrap value-set in event-column-disable/enable

Symptom: the inline project search fired TWICE — once correctly (`onSearch`), then a second
WIDE-OPEN `GetList` (`pageSize=0`, no filter) that locked the client. The debug log showed
`onSearch: ce_custHedProjSearch` → `search-value-set` writes `OrderHed.ProjectID_c=180` →
**`columnChanging: ce_custHedProjSearch`** (the SAME event re-firing).

Cause: the search event's trigger is `EpBinding/onSearch` on `OrderHed.ProjectID_c`; an
`EpBinding` trigger also reacts to that binding's `columnChanging`. When the event's own
`search-value-set` writes the value back to that binding, it fires `columnChanging`, which
re-invokes the event → infinite-ish/second search. (The line *looked* fine only because its
base binding resolves to a bounded framework search.)

Fix: wrap the programmatic write in column-event suppression. **Exact shape matters** — the
working form (used by our own prepay events `ce_custPrepayPct`/`ce_custPrepayAmt`) is
`{"type":"event-column-disable","param":{"dataTable":"OrderHed"}}` …
`{"type":"event-column-enable","param":{"dataTable":"OrderHed"}}`. A first attempt with
`{"type":"event-column-disable","dataview":"OrderHed"}` (top-level `dataview`, no `param`) was a
**no-op** and the loop persisted. So:
```
"onSuccess":[
  {"type":"event-column-disable","param":{"dataTable":"OrderHed"}},
  {"type":"search-value-set","epBinding":"OrderHed.ProjectID_c","value":"searchResult.ProjectID"},
  {"type":"event-column-enable","param":{"dataTable":"OrderHed"}}
]
```
(`dataTable` = the view of the field being set: `OrderHed` for header, `OrderDtl` for line.)
General rule: any time an event writes to a binding that its own (or another) trigger watches,
bracket the write with `event-column-disable`/`event-column-enable` (note `param.dataTable`
shape) to avoid re-entrancy. (Base also uses a top-level `dataview` variant in some events, but
`param.dataTable` is the one confirmed working in this layer.) If `columnChanging` STILL fires
after correct suppression, the `EpBinding/onSearch` trigger itself is catching column changes
and the trigger type must change — not yet confirmed here.

## 3z. Guard row-change-triggered BAQ/erp calls against transient null context

> **Did NOT resolve the Refresh split-null spam — see §3aa for the actual root cause: a null page
> `/navigation/epBinding`.** This BAQ guard is still worthwhile *defensive hardening*, but it was
> not the fix; the spam continued after it. Keep the guard, but don't rely on it to explain the crash.

Symptom: clicking toolbar **Refresh** on the header spammed
`ERROR TypeError: Cannot read properties of null (reading 'split')` (many repeats).

Cause: Refresh reloads the whole dataset; `OrderRel` reloading fires `rowChanged` for every
release, and `ce_custAvailOnRelRow` → `ce_custRefreshAvail` ran the `OrderAvailableInventory` BAQ
each time. Its `executeOptions.where` = `PartDtl_PartNum = '{OrderDtl.PartNum}'`; mid-reload
`{OrderDtl.PartNum}` is transiently null, so the query/response processing threw — once per
release row = the spam.

Fix: wrap the `erp-baq` in a `condition` that only runs when the token is populated:
`"expression":"'{OrderDtl.PartNum}' != '' && '{OrderDtl.PartNum}' != 'null'"`, BAQ in
`onSuccess`. General rule: any event triggered by `rowChanged`/`columnChanged` that runs a BAQ
or `rest-erp` using a `{View.Column}` token should first guard that the token is non-empty,
because full-dataset reloads (Refresh, GetByID) fire those triggers with transiently-null rows.

## 3aa. The Refresh/load "reading 'split' of null" — CAUSE: a null page `epBinding` (see RESOLVED)

> The "cumulative / density-threshold" framing in the isolation notes below turned out to be a
> **phantom** — the real cause was a null page `/navigation/epBinding` (jump to **RESOLVED**). The
> isolation bullets are kept only as a record of the wrong path and WHY it misled (the test subsets
> excluded the page-nav diff, so they never reproduced the real crash).

Symptom: on header **Refresh**, console spams `TypeError: Cannot read properties of null (reading 'split')`
in the binding-broadcast path (`processErpPostResponse` -> `createBindingEventFromTableChange` /
`resetViewUponParentChange` -> broadcast -> subscriber `.next` -> `.split`). On record **load** a single
matching crash fires in the crumb bar (`ngOnInit` -> `reLoadCrumb` -> `loadDropDownItems` ->
`setCrumbBarItemSelected` -> `.split`).

Mistaken isolation path (23 import/commit/test cycles, incognito, empty-layer baseline clean) — kept
as a cautionary record; the conclusion was WRONG (see RESOLVED):
- The empty layer is clean; the crash is caused by OUR layer.
- It is caused purely by **Details/header COMPONENTS** - events, rules, and dataviews are NOT involved
  (a build with those three sections emptied but components present still crashed; emptying the
  page-section components cleared it).
- **No single component triggers it.** Every individual control, every column subtree, and the full
  Col D group tested clean. It only appears when ~the whole header (~19 controls) is present:
  17 controls = clean, 19 = crash; removing ANY column group OR either RTP sub-group = clean.
- I concluded (WRONGLY) that it was a **cumulative / high-order interaction**. It was not — this
  apparent pattern was an artifact of the bisection excluding the page-nav diff (so no subset ever
  contained the null page binding). The real, single cause is in RESOLVED below.

### RESOLVED — root cause: a missing (null) page `epBinding`

Root cause: the split-null was caused by the Sales Order page's **missing `epBinding`** — nothing
else. The `Details` page section carried `Replace` diffs blanking `/navigation/epBinding` = null
(and `/navigation/dataSetId` = null, `/navigation/pageCaption` = null). The crumb bar
(`ngOnInit -> reLoadCrumb -> loadDropDownItems -> setCrumbBarItemSelected`, and the reload path on
Refresh) reads the page's `epBinding` and `.split`s it into view/column — a null there is the crash.
Fix (made in App Studio, then baked into the layer): set the Sales Order page's
**Ep Binding = `OrderHed.OrderNum`** and **Data Set = `SalesOrder`** (page-details -> Data section);
in the .jsonc these are the `/navigation/epBinding` and `/navigation/dataSetId` diffs under the
`Details` page section. Removing the null-`epBinding` override so the base value stands is enough.

CRITICAL METHODOLOGY BLIND SPOT (why a 27-cycle component bisection never found it): my subset builds
filtered each page section's Diffs by `Value.id`, but page-level nav diffs have `Value:null` and no
id, so they were silently EXCLUDED from every subset. The subsets therefore never contained the null
page binding and never reproduced the real crumb crash — so the entire "cumulative / density-threshold
/ which control is the straw" investigation was chasing a phantom. LESSON: page/navigation-level diffs
(`/navigation/*`, `/model/*`, any Path-based diff with no component id) are NOT components — bisect
them separately, and on ANY split-of-null in the crumb/binding path, audit `/navigation/epBinding` +
`/navigation/dataSetId` **first**, before bisecting components.

NOTE — the `custReservePri` `dataMode` change was **NOT** a cause (I originally mis-recorded it as a
second bug). During the phantom bisection I added `dataMode:"rows"` to the `custReservePri` combo and a
subset appeared to "go clean," which I wrongly read as a second root cause — but the subsets couldn't
reproduce the real (page-binding) crash at all, so that signal was meaningless. Setting `dataMode:"rows"`
on a service-fetch combo is still reasonable convention (the skill notes UserCodes combos use it) and is
harmless, but do **not** record it as a split-null cause.

--- (superseded) earlier hypothesis below, kept for history ---
DISPROVEN hypothesis: "unresolvable/invented column bindings cause it." Tested by stripping
epBinding from the 6 controls bound to invented/custom targets (RTP shapes/buttons -> TransView.RTP*,
shpCustApprove -> HDCaseInfo, custRemainBal -> OrderHed.RemainingBalance) on the otherwise-full layer:
the Refresh crash STILL occurred. Per the user, binding controls to custom/"invented" columns on
TransView (and elsewhere) is standard Kinetic practice that Epicor uses in native apps, so this is
NOT the cause. Also ruled out: duplicate/missing component GUIDs, duplicate component IDs (none found).

Still-open mechanism: a cumulative interaction among the header controls (no single control, event,
rule, or dataview is at fault; every proper subset is clean, only ~the full header set crashes).
Precise repro boundary captured: Col D(6) + Col A + Col B (17 controls) = CLEAN; adding Col C
(custHedProjectId + custReservePri, ->19) = CRASH. Removing any one column-group or either RTP
sub-group returns to clean. Root cause not yet identified; candidate next steps: compare against the
native base-app layout for an equivalently dense header, or escalate to Epicor with this minimal repro
plus the two stack traces (createBindingEventFromTableChange / setCrumbBarItemSelected).

## 3q. Auditing the classic customization for completeness

Pull the classic customization with `MCPToolsKinetic-GetCustomizationByID` (id `<YourCustomizationID>`).
It returns JSON; the UI definition is XML in `CustomizationData.XXXDef[0].Content`
(`<CustomizationDS>`). Parse it: `<Controls>` rows give `ControlName`/`ControlType`/
`ParentControlKey`; `<Properties>` rows give `PropertyName`/`PropertyValue` per control
(notably **`EpiBinding`** = the data field, `Text` = label/caption, `Multiline`). Extract every
data-bound control (EpiTextBox, EpiCheckBox, EpiCombo, EpiNumericEditor, EpiCurrencyEditor,
EpiDateTimeEditor) and diff its `EpiBinding` against the set of `epBinding`s in the Kinetic
layer to find gaps.

Result of the audit: all 22 custom fields were already uplifted **except the three Close Reason
fields** — `OrderHed/OrderDtl/OrderRel.custCloseReason_c` (classic had them on dedicated "Close
Reason" tabs under Header/Line/Release, each a multiline textbox + label "Reason for closing
order/line/release"). Added as `erp-text-box` with `model.multiline:true, rows:3` on the
Details / OrderLineDetailPage / OrderRelDetailPage pages.

Note on `CallContextBpmData.Checkbox10`: the classic Bypass checkbox (`chkMarginByPass`) binds
`CallContextBpmData.Checkbox10` — keep that exact binding in Kinetic (a BPM reads it). It had
been temporarily rebound to `TransView.BypassOutlierSession`; restored to `Checkbox10` and the
no-record disable rule retargeted to it. Lesson: preserve the classic binding for fields a BPM
depends on, even if a different binding would have been "cleaner."

## 3p. A NEW rule (or any diff) must be wrapped with `Id` / `Path` / `Index`, not just `{Operation, Value}`

THE big one. A well-formed entry in `rules.Diffs` (and other `*.Diffs`) looks like the
user-authored rules:

```
{"Id":"cr_RTPShapeGreen","Path":"","Value":{...rule...},"Operation":"Add","Index":361}
```

When I created `r_custRTPGreenNoRec` from scratch I wrote only
`{"Operation":"Add","Value":{...}}` — **missing `Id`, `Path`, and `Index`**. That single
malformed diff entry **broke the entire rules collection**: App Studio's Data Rules panel
showed **zero rules**, and at runtime the base shape-hide rules stopped running so **every
status shape lit up**. It also wasted several cycles because the symptom looked like a bad
condition (`$rowCount`) — it wasn't.

Rule of thumb when adding a brand-new item to any `*.Diffs` array by hand: copy the **exact
wrapper shape** of an existing well-formed sibling diff —
`{"Id":"<itemId>","Path":"","Value":{...},"Operation":"Add","Index":<max existing + 1>}` — not
the bare `{Operation, Value}` form. Match `Id` to the item's `Value.id`, `Path` to `""`, and
give a unique `Index`. If App Studio's list for a section goes empty or all controls in a family
misbehave after an import, suspect a malformed diff wrapper in that section, not the inner
content.

## 3k. [SUPERSEDED by 3l] `DisableRow` symmetry — earlier mis-diagnosis

Symptom: form is correctly read-only on load when `OrderHed.ReadyToCalc = true`; user clicks
"Make Changes", `ReadyToCalc` flips to false, the shapes update — but the form **stays
read-only**.

Diagnosis (the asymmetry is the tell): the `cr_RTPShape*` rules read the *same*
`OrderHed.ReadyToCalc` and reverse both directions fine, so the rule engine **is**
re-evaluating on the toggle. So it isn't a trigger problem. The `DisableRow` rule action simply
**applies the disable when its condition becomes true but does not remove it when the condition
goes false within the same row instance**. On a fresh load it's always correct (re-evaluated
from scratch); it only "sticks" on a live true→false toggle. Contrast: `SettingStyle.Invisible`
*is* symmetric and toggles both ways.

Fix (user's chosen approach, and the right one): make the toggle **refresh the row** so
`DisableRow` is re-applied from scratch against the new value. The button event toggles
`ReadyToCalc` (+ `RowMod = "U"`) and then **chains to the base `Update` (Save) event via
`event-next`** — `Update` is the top-level Save entry point (guards on `TransView.UpdateLock`,
runs override checks, calls `MasterUpdate` → `rest-erp MasterUpdate` with
`ErpPostWithDataViewProcessing`, which reloads the dataset). After the refresh the lock rule
evaluates correctly. This also embodies "call the existing event" (§2): don't re-add
`data-commit` (which risks the save-pollution issues), chain into `Update`.

To find the right Save event: in `GetNativeKineticApp`, the top-level event is **`Update`**
(not `MasterUpdate`, which is the inner BO call, nor the toolbar handler `OnClick_toolSave`
which isn't in the app JSON). `event-next` value examples in the base app: `Update`,
`PerformUpdate`, `MasterUpdate`, `Refresh`, `GetNew`.

---

## 4. DisableRow / read-only locking gotchas

> **CORRECTED by §3f, §3l, §3o (verified against the base app — trust those over this section).**
> Two claims below are now known WRONG: (1) that the native status shapes live on
> `CallContextBpmData` and therefore `DisableRow` doesn't touch them — they are actually bound to
> `OrderHed.*Shape` columns, `DisableRow` DOES grey them, and they must be excepted by their real
> column names; and (2) that a long `exceptTheseColumns` is what broke locking — the real cause was
> a custom `DisableRow` rule conflicting with the base `openOrderRule` (§3l). The shipped read-only
> approach is NOT a custom `DisableRow` rule at all: drive `TransView.SysReadOnly` and let the base
> `openOrderRule` do the lock/reverse (§3l). `exceptTheseColumns` with REAL column names is fine and
> is in fact required for the shapes; only invalid/pseudo column names are a problem.

- The read-only lock for "Ready to Process = true" uses **rules** with `DisableRow` and an
  `exceptTheseColumns` array (plus `DisableColumns` with a `columns` array for narrower
  cases). Only `SettingStyle.Disabled / Invisible / ReadOnly` are valid setting styles.
- **Big finding:** stuffing `exceptTheseColumns` with many pseudo-columns (shape/button ids
  that aren't real BO columns) **silently breaks DisableRow** — the whole rule stops applying
  and nothing locks. Keep `exceptTheseColumns` to **real BO columns only** (e.g. `OrderNum`).
- Because shapes/buttons are on `CallContextBpmData` (not the BO view), an `OrderHed`
  `DisableRow` doesn't touch them anyway — so they never needed excepting. The fix that
  restored locking: `OrderHed` → `["OrderNum"]`, `OrderDtl`/`OrderRel` → `[]`.
- Rule condition syntax is `View.Column = value` (e.g. `OrderHed.ReadyToCalc = true`) and
  `[View].[$rowCount]` for row-count checks. Rules need `disabled:false` to be active.
- To hide a *native* control (the stock ReadyToCalc checkbox), use an `Invisible` rule
  targeting its binding rather than trying to delete the base component.

---

## 5. Token evaluation quirks (the double-eval trap)

The rule/event engine **double-evaluates** the result of a `#_ ... _#` raw-JS expression.
- A bare `#_ new Date().toISOString() _#` throws `SyntaxError: Invalid or unexpected token`
  because the engine evaluates the returned date string *again* as code. Fix: wrap the whole
  thing in quotes so the second pass sees a string literal:
  `'#_ new Date().toISOString() _#'`.
- Toggling a boolean works as `#_ !{OrderHed.ReadyToCalc} _#` (curly `{View.Column}` token
  inside the JS). After mutating a BO field via `row-update`, also set
  `OrderHed.RowMod = "U"` so the row is marked dirty for the next Save.
- Token kinds to keep straight: `{View.Column}` (curly, value substitution),
  `%patch%` constants, and `#_ raw JS _#` (double-evaluated).

---

## 6. erp-baq / BAQ-bound grids

- To filter a BAQ grid from the current row, put the filter in the **`executeOptions.where`**
  of the `erp-baq` widget (not an empty ExecutionParameter). Syntax uses the BAQ's flattened
  column names with single-quoted token values:
  `PartDtl_PartNum = '{OrderDtl.PartNum}'`.
- A BAQ-backed `metafx-panel-card-grid` should set `allowAddNew:false` and `allowDelete:false`
  (Add/Delete aren't meaningful on a BAQ result), `hideViewSelector`, and turn off the
  Full-Screen button via `fullScreenButtonVisible:false`. Hide the new/delete **tools** on its
  dataview too.
- Put a **Refresh** as a panel-card **action item** (`enableActionButton` with `actionData`
  Refresh + the row binding), not as a floating button — cleaner and what you asked for.
- **Direct-navigation load bug:** a grid that refreshed only when stepping between records but
  stayed empty on direct navigation needs a **`Control` / `onInit`** trigger to fire its load
  on first render (row-changed events don't fire on the initial direct load).

---

## 7. Search widgets (GetSearches mapping)

- The `GetSearches` tool gives the metadata for wiring a `search-show` + `search-value-set`.
  Mapping that wasn't obvious: BAQ `Calculated_Like` → the **Like\*** property in App Studio;
  `Calculated_SearchForm` → the **Search Form** property.
- A project search needs both `like` (e.g. `"Project.ProjectID"`) and
  `searchForm:"default"`, or it crashes on `.replace` (missing required `like`).
- The value setter must read from the search result object, not a guessed binding:
  `search-value-set` with `value:"searchResult.ProjectID"`. Setting a `_c`-style binding
  came back `undefined`.

---

## 8. Layout placement rules learned the hard way

- **Keep all base sections.** Pruning "empty" base layout sections produced a totally blank
  form. Retaining every section (all 37) fixed it — don't trim the base layout.
- **The primary/base panel must stay first.** Order is governed by the **physical array position
  of the diff objects** in the section's `Diffs` list — NOT by the `Index` value (see §3a and the
  VERIFIED §10; editing `Index` alone is a no-op). To keep custom content after the base panels,
  place the custom diffs **later in the `Diffs` array**, not merely at a high `Index`. (The old
  "use `Index` 1000+" advice is superseded: bumping `Index` only appeared to work because those
  diffs were also appended later in the array; the array position was doing the work.)
- To merge a classic custom group into a base panel, dissolve it and re-parent its fields
  into the base panel's `#bodyComponents` slot (e.g. into `pcOrderDetail#bodyComponents`)
  rather than leaving it as a separate floating card.
- Numeric vs currency boxes matter: a value bound to a plain number (Get Est Unit Cost)
  wouldn't display in a currency box — switch the component to a numeric box.
- Move only what's asked. Re-parenting a field group, double-check you didn't drag adjacent
  base controls (the Entity Use Code button) along with it.

---

## 9. Manifest section versions (for reference)

When emitting the manifest, these section versions were in play:
layout/pages 3.0, events 5.0, rules 3.0, tools 2.0, dataviews 4.0, config 2.0.
Diff grammar: `{Id, Path, Value, Operation: Add|Replace|Move, Index}`. **`Index` does NOT drive
render order — the physical array position of the diff in the section's `Diffs` list does** (§3a,
§10; VERIFIED). Keep `Index` ascending/unique for readability and to mirror App Studio's output,
but to (re)position a component, move its diff object to the correct array position. `Operation`
values include `Move` (`Value:null`) for repositioning existing components. Events/rules carry
`mode:"A"`, `customizable:true`, `disable:false` (events) / `disabled:false` (rules).

---

## 10. Reordering & hiding panel cards (top-level Details cards) — VERIFIED

Confirmed empirically by having the user drag ONE card (Close Reason) in App Studio, publishing,
then downloading and diffing the layer.

- **Render order = the PHYSICAL ARRAY ORDER of the component diffs in the section's `Diffs` list — NOT
  the `Index` property.** Editing `Index` alone does nothing (an Index-only revision was a no-op for
  exactly this reason). To reorder, you must physically move the diff objects within the `Diffs` array.
- **A top-level card's position is governed by its CARD-NODE diff's array position.** Children attach
  by `parentId` and render under their card wherever the node sits, so you do NOT need to move a card's
  children to move the card. In the base flat `components` list children actually PRECEDE their card node.
- **`Operation:"Move"` is real** (the reference only documents Add/Replace). Shape:
  `{"Id":"<compId>","Path":"components","Value":null,"Operation":"Move","Index":<n>}`. App Studio emits
  a big Move cascade (one per component from the first changed position onward) when you drag — but for a
  pure top-level reorder you only need to re-sequence the ~N card-node diffs.
- Cards with NO diff (e.g. base `pcOrderDetail`/Order Header, `pcOrderLines`/Lines) stay at their base
  positions (first), so leaving them untouched keeps them at the top.
- **Hide a card** with a property diff (NOT `model.hidden` inside a component Value):
  `{"Id":"<cardId>","Path":"/model/hidden","Value":true,"Operation":"Add","Index":<n>}`.
- Custom cards the layer ADDS are positioned by where their `Add` diff sits in the array (same rule).

Working recipe used: find each visible card's single card-node diff (Move for native, Add for
custom) and its array position; collect the slot positions (sorted); place the diff objects back into
those slots in the desired (classic) order. Keep Index values consistent/ascending with the new order
for cleanliness, but array order is what actually drives rendering.

Page-root card ids on Erp.UI.SalesOrderEntry Details: pcOrderDetail(Order Header), pcOrderLines(Lines),
pcOrderHedCreditCard, pcgOrderHedMiscChrg, pcOrderHedSalespersons, pcOrderHedTotals, pcgCommissions,
pcOrderHedComments, pcOHManifestDetail, pcOrderHedTax, pcgPaymentSched, pcOrderHedWeb, pcOrderHedOTS,
pcFSMIntegration, 37a3d55e-...(EDI Demand Import). Order Totals summary containers: card pcOrderHedTotals
-> Summary row div-row-36256 -> Lines column div-col-c24b5 (holds txtLineCount) and Releases column
div-col-bc751 (holds txtReleases).

## 11. ALWAYS look up each tool's schema — parameter names are INCONSISTENT across the Lens tools

Cost hours of false "server 500s": the analysis/read tools use `AppName`/`LayerName`, but the
import/commit tools use `InID`/`InLayerName`. Passing `InID` to `GetNativeKineticApp`/`GetIndividualLayer`
returned a generic HTTP 500 (a malformed call, NOT a server outage). Verify the schema before every call.

- `MCPToolsKinetic-GetNativeKineticApp` → `AppName` (e.g. "Erp.UI.SalesOrderEntry"). Returns the full base app
  (~2MB); may exceed inline token limits and be saved to a file — slice it with python/jq.
- `MCPToolsKinetic-GetIndividualLayer` → `AppName`, `LayerName`. Returns an **off-band `downloadUrl`** (GET it
  with curl), a zip whose entry is `Layers/<App>/<Layer>.jsonc`; the published manifest is the JSON
  string in the record's **`Content`** field (SysCharacter03 may be empty on the published copy).
- `MCPToolsKinetic-GetLayers` → `AppName`, `IncludeUnpublished` (bool).
- `MCPToolsKinetic-ImportLayer` → `InContent` (a fileRef from `request_file_upload`, uploaded via direct PUT).
- `MCPToolsKinetic-Commit` → `InID`, `InLayerName`, `InComment`.
- `request_file_upload` → `tool`, `param`, `filename`, `contentType` (all optional).

## 12. Lines detail cards: hide-only sufficed; "Expand at Runtime" = `model.expanded`

- Base OrderLineDetailPage card order (from GetNativeKineticApp): pcOrderDtlDetail(Line Detail),
  pcgReleaseList(Releases), pcgLineMiscChrg(Misc Charges), pcgOrderLineBookDtl(Book Details),
  pcOrderDtlCommissions, pcOrderDtlComments, pcgSalesKitComponent(Kit Lines),
  pcgOrderDtlKBExt(CPQ Lines), 654a3877-599a-46cf-88c6-9799a0859e79(EDI Demand Import).
  Hidden (final): CPQ Lines + EDI Demand Import only. **Releases stays visible by
  design** (it was unhidden) even though Classic's Lines tab had no Releases sheet — it sits at
  its base position between Line Detail and Misc Charges. Rest of the order mirrors Classic
  (Detail, Misc Charges, Book Details, Commissions, Comments, Kits Detail, Close Reason) with
  NO Move cascade needed. Check whether hide-only achieves the target order before building Moves.
- App Studio's panel-card **"Expand at Runtime" checkbox = `model.expanded`** (bool). Set
  `expanded:false` inside the card's own Add-diff `Value.model` to make a layer-created card
  collapsed at runtime. Applied to 4 custom cards: pcCustCloseReason, pcCustRental (Details),
  pcCustLineCloseReason (Lines), pcCustRelCloseReason (Releases page). **pcCustPartAvail stays
  `expanded:true` by design** — the Part Availability / Mini Time Phase card should
  always open expanded.
- EDI Demand Import cards are GUID-id'd per page: Details=37a3d55e-…, Lines=654a3877-…,
  Releases=2e89d539-…. pcCustPartAvail is a `metafx-panel-card-grid` (a type filter on
  `=='metafx-panel-card'` misses it).

## 13. Classic code uplift wave — what was added and why

The full classic script was extracted, with an exhaustive inventory of it (agent-extracted from the GetCustomizationByID dump).

Biggest find: **HDCaseInfo and RentalInfo BAQ dataviews existed in the layer but were never
executed** — no erp-baq action referenced SalesOrderCaseDV/SORental, so the approval indicator and
rental panel ran on empty views. Classic used BAQDataView pub/sub (auto-refresh on OrderNum);
Kinetic needs an explicit event: `ce_custCaseRentalLoad` (OrderHed rowChanged, OrderNum-guarded per
§3z) runs both BAQs with `where` filters. Numeric where tokens go unquoted
(`HDCase_OrderNum = {OrderHed.OrderNum}`); strings quoted.

Added events: `ce_custRelBTO` (BuyToOrder mirrors to DropShip, wrapped in event-column-
disable/enable), `ce_custRelMake` (Make unchecked + BTO → DropShip=true), `ce_custEstExtInit`
(OrderDtl rowChanged recalc of invented EstExtCost — row-update does NOT set RowMod, so no dirty
risk per §5), approve now re-runs the case BAQ onSuccess.

Added rules: `r_custPrepayAmtLock` (DeterminedBy=2 → disable PrepayAmt), `r_custAnalReasonRO`
(AnalBypass_c=false → RO reason), `r_custApproveBtn` (NOT SORDY or empty case/order → disable
approve btn — consolidated INTO ONE RULE incl. the $rowCount=0 term, and RTPBtnApprove REMOVED
from `r_custRTPGreenNoRec`, because two rules targeting one binding fight each other per §3l),
`r_custApproveShape` (SORDY → disable indicator shape), `r_custRentBtnNew`/`r_custRentBtnSave`
(RentalInfo.$rowCount drives New/Save Event buttons, mirroring classic EpiViewNotification).

Static props (per §3o rule-of-thumb): readOnly:true on the 3 close-reason text areas +
custRemainBal (classic disabled them via always-true rules / control flags).

Condition grammar confirmed in rules-and-dataviews.md §A3: `<>`, `in`, `contains` supported;
strings in single quotes; `[View].[$rowCount]` bracket form; unparseable condition degrades to
ALWAYS-TRUE (watch console for "Errors in criteria parser").

Known deviation: `ce_custRentalSave` sends `{RentalInfo.SysRowID}` as InRow but
classic serialized the whole row JSON — function-side change needed (no client-side row
serialization in Kinetic events). Rental new-row persistence (classic oTrans.Update()) also needs
a server-side answer (UBAQ update or SaveRental doing the insert).

## 14. Read-only model key is `readonly` — ALL LOWERCASE

`/model/readOnly` (camelCase) is a DEAD KEY — the control model's state property is **`readonly`**
(all lowercase; state ids: `disabled, hidden, labeltext, readonly, required, status`). The base
app serializes `readonly` exclusively (verified by grep of GetNativeKineticApp). Symptom of the
camelCase mistake: the property silently does nothing (cboEntityUseCode stayed editable).
The fix corrected the cboEntityUseCode `/model/readonly` prop diff AND the 4 custom fields
(custHedCloseReasonTA, custRemainBal, custLineCloseReason, custRelCloseReason) that had model.readOnly.
Pattern reminder: user edits blocked, but event `row-update` still writes the bound value, so
`ce_custToggleEUC`'s toggle button remains the only way to change Entity Use Code.

**Rental feature parked:** the dependent `Rental.SaveRental` Epicor Function was
unavailable. Rather than delete the uplifted rental work, it
was all kept but neutralized reversibly: `pcCustRental` card `model.hidden:true`, events
`ce_custRentalNew`/`ce_custRentalSave` set `disable:true`, rules `r_custRentBtnNew`/`r_custRentBtnSave`
set `disabled:true`, and the SORental erp-baq removed from `ce_custCaseRentalLoad` (in case the BAQ
is also gone — a missing BAQ would error on every order load). To revive: restore the function,
re-add the SORental erp-baq to `ce_custCaseRentalLoad`, and flip the four flags back.

## 15. Panel-card-stack pattern (approved)

The base app's only `metafx-panel-card-stack` is `pcDelPlans` (DeliveryPlan page) — used as the
verified template. Key facts:
- Node: `{parentId:null, id:<guid>, sourceTypeId:"metafx-panel-card-stack", model:{guid, labelText,
  id:<friendly>, panels:[{id:<CARD NODE ID>, name:<label>}], expanded:true, widgetHeight:415},
  layoutData:{flexLayout:true, hostId:"<PageName>"}}`.
- `panels[].id` references each card's **model.guid** (CONFIRMED across two revisions: node ids like
  `pcOrderDetail` left App Studio's Panels checkboxes unchecked; the base example was ambiguous
  because its node id = guid). Cards STAY top-level (`parentId:null`); the stack consumes/hosts
  them by reference — do not reparent, do not remove their Move diffs. Card guids: pcOrderDetail
  07b17325…, pcOrderLines 14e13ea5…, pcCustCloseReason 72d3297a…, pcOrderHedWeb fb13a70f…,
  pcOrderHedCreditCard 2c79d3f0…, pcgPaymentSched c878430e…, pcgOrderHedMiscChrg 31293839…,
  pcOrderHedTax 734cb3ee…, pcOrderHedSalespersons f0f7eda4…, pcOHManifestDetail 279c54dd…,
  pcOrderHedTotals 58bc8fcf…, pcOrderHedComments 6b0a0e6c…, pcOrderHedOTS 5d800c8d….
- **Each member card must ALSO carry `model.stacked: true`** (CONFIRMED; found on the base
  DeliveryPlan stacked cards). The panels array alone renders the card in the stack AND in normal
  flow (double-render bug). App Studio's Panels checkbox sets both sides at once: panels
  entry on the stack + `stacked:true` on the card. For base cards use a `/model/stacked` property
  diff; for own cards set it in the Add diff's model.
- `pcCustHeaderStack` (guid 94fca229-…) added at front of Details Diffs. Final:
  12 members (Order Header, Close Reason, Web, Credit Card, Payment Schedule, Misc Charges, Tax,
  Salespersons, Manifest Info, Order Totals, Comments, One Time Ship To); **Lines excluded by
  design — pcOrderLines got a Move diff at array pos 1 (right after the stack) so it renders
  below the stack.** Hidden cards excluded. widgetHeight 415 may need tuning.
- Header approved → the next revision added the other two stacks:
  - `pcCustLineStack` (OrderLineDetailPage, guid e2195ea4-…): Line Detail, Misc Charges, Book
    Details, Commissions, Comments, Kit Lines, Close Reason. **pcgReleaseList kept out + Moved
    below the stack** (array pos 1). CPQ/EDI Demand Import stay hidden; **pcgOrderDtlEDIAck (EDI
    Acknowledgement) left out — base rule already drives its visibility via
    `SettingStyle.Invisible` on `TransView.EDIPanel`; stacking it could fight that rule.**
  - `pcCustRelStack` (OrderRelDetailPage, guid 9307cf4b-…): Release Detail, Tax, Shipping
    Information, Mark For, Project, Jobs, Part Availability, Close Reason. Note
    **pcgOrderRelTaxList is NESTED inside pcOrderRelTax** (`parentId: pcOrderRelTax#bodyComponents`)
    — only the outer Tax card goes in a stack.
  - Release-page card guids: pcOrderRelDtl 7fa3bb82…, pcOrderRelTax 7c5cc828…, pcOrderRelOTSDetail
    33a8ddd3…, pcOrderRelMarkForDetail b3886b93…, pcProjectDetail 66cb71be…, pcgJobs c9e56cf9…,
    pcCustPartAvail 6fbe6655…, pcCustRelCloseReason 15379b53…; line-page extras: pcgOrderLineBookDtl
    4ad24b00…, pcgOrderDtlEDIAck 61e44826…, pcCustLineCloseReason 07b1f07d….

## 16. Gated BAQ search grid — BAQ provider + pub/sub filter, blocked until a filter is entered (Ice.UI.UD103Entry)

A panel-card grid bound to a BAQ via `providerModel`, filtered by a client "filter" dataview
through `baqOptions.whereList`, with a "gate" so the query does NOT run until the user enters at
least one filter. Condensed here; the mechanics also live in search-baq-rest.md §2.3–2.4b.

### 16.1 The grid

```jsonc
{
  "id": "grdSearchResults",
  "epBinding": "SearchResult",          // schema:"baq" dataview
  "autoLoadColumns": true,
  "autoLoadGrid": false,                    // optional; gate handles "don't run on open" anyway
  "providerModel": {
    "baqId": "MyOrderSearchBAQ",
    "baqOptions": { "whereList": [ /* see 16.2 */ ] }
  }
}
```

The result dataview needs the FULL required set (see §19): `{ "id":"SearchResult",
"schema":"baq", "data":"<same BAQ id>", "table":"SearchResult", "tools":{ "new":{"hidden":true},
"delete":{"hidden":true} }, "mode":"U" }` — without `tools` it disappears on import; without
`table` it won't register in App Studio's Data View picker.

Works with either a simple or a complex BAQ as long as `autoLoadColumns:true` and there is
**no `columns` array** — a columns array makes the grid emit a dynamic `Select` that can throw
"Invalid column name" on complex multi-subquery BAQs. The BAQ itself was never the crash cause.
(Exception — server paging: `serverPaging:true` requires the opposite config, `autoLoadColumns:false`
+ a COMPLETE `columns` list with hidden key/sort columns; see §20.)

### 16.2 whereList ITEM SHAPE — critical

Each item must be EXACTLY `{ "column", "condition", "value" }`. **Do NOT add `honorNull` or
`emptyValue`.** A boolean `honorNull:false` makes the client where-clause builder call
`.replace` on a boolean →

```
TypeError: t.replace is not a function
  at L.processValue → getCriteria → processCriteriaItem → getProcessedWhereClause
```

This error is NOT the BAQ, not paging, not the gate — it is the extra boolean property on the
whereList item. Strip items to the three keys.

### 16.3 Token + quoting rules (the actual gate mechanism)

`baqOptions.whereList[].value` uses provider binding tokens:

| token | meaning |
|---|---|
| `?{View.Col}`  | **REQUIRED**. If the bound value is empty, `validateFilter` fails and the provider **does not run the query at all**. |
| `??{View.Col}` | **OPTIONAL**. Empty → that item is dropped; the query still runs. |

**Quote string BAQ columns.** `?{}`/`??{}` do NOT auto-quote for string columns — wrap the
token in single quotes yourself:

- string `=`   → `"'??{SearchFilter.Key2}'"`
- string `like`→ `"'??{SearchFilter.CustName}%'"` or `"'%??{SearchFilter.PartNum}%'"`
- required gate on a string col → `"'?{SearchFilter.Company}'"`

(Non-string columns — numeric/date — are left unquoted. Dates need special handling; we left
the date prompt out of the whereList.)

### 16.4 The GATE (block the query until at least one filter is entered)

Goal: on open the grid is empty; the moment ANY prompt is typed, the grid queries with whatever
filters are filled.

Mechanism = one **required** `?{}` token on a dedicated gate column, compared so it never
actually restricts once set:

1. Add a gate column to the filter dataview (we reused a column named `Company`).
2. whereList gate item (required token):
   `{ "column":"UD103_Company", "condition":"<>", "value":"'?{SearchFilter.Company}'" }`
   - Gate empty → required `?{}` fails validateFilter → **query blocked** (blank grid).
   - Gate set to `'XXX'` → `UD103_Company <> 'XXX'` is always true (Company is never `XXX`)
     → does not restrict, just **unblocks** the query.
3. All the real filters use optional `??{}` so empty ones drop out.
4. A gate-setter event flips the gate the moment any prompt changes:

```jsonc
{
  "id": "searchGate", "mode": "U",
  "trigger": { "type":"DataTable", "target":"SearchFilterTbl",   // TABLE id, not the view id!
               "hook":"columnChanged",
               "columns":["Key2","Key3","Key4","Status","Date01","CustID","CustName",
                          "InvoiceNum","UserID","CustPO","SalesRep","Editor",
                          "WrittenBy","PartNum","ShipNotes"] },
  "actions": [ { "type":"row-update",
                 "param":[ { "columns":[ { "epBinding":"SearchFilter.Company", "value":"XXX" } ] } ] } ]
}
```

5. The "open" event seeds the gate column blank (grid blank on open); the Clear button also
   resets it blank.

Gotcha: the `columnChanged` trigger `target` is the **table id** (`SearchFilterTbl`), NOT the
dataview id (`SearchFilter`). Targeting the view id → the event never fires.

### 16.5 Filter dataview column datatype

Client filter dataview `additionalColumns[].datatype` must be **`"string"`**, not `"nvarchar"`.
`nvarchar` causes the dataview to silently disappear on import.

```jsonc
{ "id":"SearchFilter", "table":"SearchFilterTbl", "datasetId":"SearchFilterDS",
  "mode":"U",
  "additionalColumns":[ { "columnName":"Key2", "caption":"Key2", "datatype":"string" }, ... ],
  "tools":{ "new":{"hidden":true}, "delete":{"hidden":true} } }
```

(Full per-kind dataview required-property sets — including why `tools` and `table` are effectively
mandatory on every hand-built view — in §19 / rules-and-dataviews.md §B12.)

## 17. UDCodes dropdown via a REUSABLE combo (`UserCodes.UserCodesCombo`)

To populate a dropdown from Ice.UDCodes filtered by a CodeType (e.g. `OrderStatus`), use the
**Reusable Combo** `UserCodes.UserCodesCombo`.

**Do it in App Studio, not by hand.** Picking the reusable combo makes App Studio *resolve* the
definition and bake in the concrete fetch properties. `type`/`subType` ALONE do not fetch
anything (the dropdown comes up empty). The full working model App Studio produces:

```jsonc
{
  "id": "txtStatus",
  "sourceTypeId": "erp-combo-box",
  "model": {
    "labelText": "Status =",
    "epBinding": "SearchFilter.Status",
    "dropDownStyle": "DropDownList",
    // reusable identity:
    "type": "UserCodes.UserCodesCombo",
    "subType": "default",
    "comboId": "UserCodes.UserCodesCombo",
    // resolved fetch definition (baked in by App Studio):
    "svc": "Ice.BO.UserCodesSvc", "svcPath": "GetRows",
    "tableName": "UDCodes",
    "valueField": "CodeID", "textField": "CodeDesc", "sort": "CodeID",
    "retrieveColumns": ["CodeDesc"],
    "filters": ["CodeTypeID = '?{CodeTypeParam}'"],   // inherited from the reusable def
    // your inputs:
    "filtersParams": ["CodeTypeParam=OrderStatus"],    // supplies the CodeType
    "hiddenColumnsAppend": ["IsActive"],
    "rowFilter": "IsActive=true"                       // active codes only
  }
}
```

- The combo stores the **CodeID** into its binding; filter the code column with it
  (e.g. `UD103_ShortChar01 = '??{SearchFilter.Status}'`).
- `filters` (`CodeTypeID = '?{CodeTypeParam}'`) is part of the reusable definition; you feed it
  with `filtersParams: ["CodeTypeParam=<CodeType>"]` — a literal value, not just a column remap.

If you must generate the combo programmatically, emit the **full resolved model above**, not
just `type`/`subType`. (See components.md §6.2 for the reusable-combo property surface.)

## 18. The two content blocks — `Content` (published) vs `SysCharacter03` (App Studio draft)

Why edits sometimes "don't take". A layer row has TWO content blocks:

- `Content` — the published layer (what `ImportLayer` writes).
- `SysCharacter03` — the **App Studio draft**. The running preview renders the DRAFT.

If App Studio is open on the layer, it re-freezes `SysCharacter03` over your imports, so
imported changes appear to "not take" and stale config (e.g. an old `queryId`) keeps running.

(Reconciling with §3i: on the published SO exports `SysCharacter03` was empty and the manifest
lived in `Content`; on the UD103 build both blocks were in play and the draft block was what the
preview rendered. Always check both, and treat a populated, differing `SysCharacter03` as the
user's draft.)

### Golden rule: keep `Content` and `SysCharacter03` in sync

When Claude edits the layer, **always write BOTH blocks identically** and commit — never touch
one without the other:

1. Build the change into `Content`.
2. Set `SysCharacter03 = Content` (byte-for-byte identical).
3. `ImportLayer` (writes `Content`) then `MCPToolsKinetic-Commit`.
4. Verify BOTH blocks via `GetIndividualLayer` and confirm they match.
5. Tell the user to CLOSE App Studio (or hard-refresh) before testing.

### Exception: the user edited on their side (App Studio) — adopt their draft

If the user made changes by hand, their edits live in the **draft (`SysCharacter03`)**, which
will differ from `Content`. Do NOT blindly overwrite it. Instead:

1. **Pull the layer down** (`GetIndividualLayer`).
2. **Diff the blocks** — compare `SysCharacter03` (their draft) against `Content` to see exactly
   what they changed (e.g. a hand-picked reusable combo that App Studio fully resolved).
3. **Adopt their changes** as the source of truth — take the draft's version of whatever they
   touched.
4. **Rebuild BOTH blocks** so they're identical again and include those adopted changes
   (`Content = SysCharacter03`), then `ImportLayer` + `MCPToolsKinetic-Commit`.
5. Re-verify both blocks match.

In short: Claude keeps the two blocks in lock-step; the only time they legitimately diverge is a
live user hand-edit, and the response is to pull, read the draft, adopt, and re-sync both — not
to clobber the user's work with a stale `Content`.

## 19. Dataview setup reference — get the property set right per kind, or the view disappears

Symptom: a dataview you added silently vanishes on import or doesn't function, while native views
persist. Cause is almost always a wrong/incomplete property set. Before importing ANY hand-built
dataview, diff it against a native one of the SAME kind and match the shape. (Full reference with
examples: rules-and-dataviews.md §B12.)

**Universal invariant — EVERY dataview must have `id`, `table`, `tools`, `mode`.** Per kind:

- **BO / server view** (`schema:"Erp"|"Ice"`): + `serverTable`, `datasetId`, `serverDataset`.
- **BAQ view** (`schema:"baq"`): + `data` (the BAQ id) and — verified the hard way — **BOTH
  `table` AND `tools`**. No `tools` → disappears on import. No `table` → imports but does NOT
  register in App Studio's Data View picker (convention: `table` = same string as `id`). Adding
  `table` is exactly what made `OrderSearch`/`SearchResult`/`DepositBalance`/
  `RelatedViews` show up.
- **Client / in-memory view** (no `schema`): + `datasetId`, `additionalColumns`.

**Column `datatype` = a Kinetic type token, never a SQL type:** `string`, `int`, `decimal`,
`date`, `boolean`, `guid`. `nvarchar` (or any SQL type) makes the whole dataview disappear on
import — that was the original bug. Match the token to the column: text→`string`,
numbers→`decimal`/`int`, dates→`date`, SysRowID/keys→`guid`.

Audit habit: enumerate `dataviews.Diffs`, classify each by kind, confirm the required set. Quick
checks that catch almost everything: (1) every non-BO view has a `tools` block; (2) every BAQ view
has BOTH `table` and `tools`; (3) every client column uses a Kinetic type token.

## 20. Server-paged BAQ grid drops the sort/key columns from its Select

Symptom: with `providerModel.serverPaging:true`, the grid's `ExecuteBaq` `Select` omits some
columns (e.g. `UD103_Key2/Key3/Key4`). Sorting breaks and any event that reads those columns from
the result view (e.g. an OK button mapping `KeyFields.Key2/3/4` from `SearchResult`) gets nothing.

Cause:
- The BAQ has a `QuerySortBy` (ORDER BY) on those columns.
- Under server paging, `ExecuteBaq` projects ONLY the grid's columns. With `autoLoadColumns:true`,
  the auto Select = the BAQ's *display* fields, which may EXCLUDE the key/sort columns (they're in
  the query for joins/keys/sort but not flagged display).
- So the paged query is ordered by columns it isn't projecting → the sort has nothing to sort on,
  and the rows don't carry those values.
- (Client paging hides this because it sorts the full in-memory set.)

Fix: make the sort/key columns real grid columns so they land in the Select. Add them to the grid
`columns` with `hidden:true` (retrieved, not shown).

**Important — column-config rules that bite here:**
- `autoLoadColumns:true` + a PARTIAL `columns` array is NOT a valid combo. App Studio always writes
  `autoLoadColumns:false` and the COMPLETE column list when any column is customized. A partial
  array under `autoLoadColumns:true` may be ignored (fix doesn't take) or blank the grid.
- So: set `autoLoadColumns:false` and provide the FULL column list, marking the extra key/sort
  columns `hidden:true`:

```jsonc
{ "id":"grdSearchResults", "epBinding":"SearchResult",
  "autoLoadColumns": false,
  "providerModel": { "baqId":"MyOrderSearchBAQ", "serverPaging": true, "baqOptions": { "whereList":[...] } },
  "columns": [
    { "field":"UD103_Key2", "hidden":true },   // sort + nav, retrieved not shown
    { "field":"UD103_Key3", "hidden":true },
    { "field":"UD103_Key4", "hidden":true },
    { "field":"Customer_CustID" }, { "field":"Customer_Name" }, ...  // the visible display columns
  ] }
```

Rule of thumb: any column referenced by the BAQ's `QuerySortBy`, OR by an event reading the result
dataview, MUST be a grid column (visible or hidden) so it's in the server-paged Select. (This does
NOT contradict §16.1's "no columns array" — that guidance is for unpaged grids; the two valid
configs are all-or-nothing: `autoLoadColumns:true` + no columns, or `autoLoadColumns:false` + the
complete list.)

**UPDATE — Select mechanism (observed behavior; see search-baq-rest.md §2.3c for the full chain):**
the Select = `union(providerModel.baqOptions.select, <bracketed fieldList from the LIVE grid
model's columns>)`. Grid columns only count if they reached the
live model AND carry `erpInternal` (stamped by the grid's own column prep); `providerModel.columns`
is never read by the Select path at all. If the emitted Select equals exactly the BAQ's display
columns, the live model had NO columns at provider init (auto-generation branch) — check the draft
block (§18), a diff that didn't apply, `providerModel.columns` misplacement, or saved
personalization. **Simplest reliable lever: `providerModel.baqOptions.select` — e.g.
`"select": ["[UD103_Key2]","[UD103_Key3]","[UD103_Key4]"]` (bracketed) — unioned in verbatim, and
works with `autoLoadColumns:true` + no `columns` array.**

## 21. RESOLVED: server-paged BAQ grid silently drops UPDATABLE fields from its Select

Observed: on a `providerModel.baqId` grid (`serverPaging:true`) over an UPDATABLE BAQ, certain
columns never arrived — omitted from the `ExecuteBaq` Select no matter what was in
`gridModel.columns`/`providerModel.columns`/`autoLoadColumns`. Toggling the field's **Updatable**
flag added/removed it from the captured Select.

**Mechanism FULLY VERIFIED — and it is CLIENT-side, in newer builds only** (the earlier suspicion
of the server's `GetQueryResultSetMetadataByID` was wrong). Observed on deployed builds: newer
Kinetic client builds gate the grid's field enumeration (`updateFieldMetadata`): a column is
pushed into the Select list ONLY when its BAQ metadata column is found AND
`updatable === false`. Older client builds pushed all non-image columns — which is why this only
appeared after a client upgrade. Two accidental
maskers: `addOuterSortingFields` re-appends `QuerySortBy` fields at the END of the Select (so
sort-coincident updatable fields "work"), and that band-aid is disabled entirely by any saved
personal sort/grouping (which persists per grid GUID across layer imports — breakage looks
immune to layer edits).

**Fix: always declare `baqOptions.select` (full bracketed column list) on any server-paged grid
over a UBAQ** — it is unioned into the Select FIRST, unconditionally, immune to the
updatable-drop, the sort-append skip, and saved-layout state. It is layer-JSON only (not exposed
in App Studio). Full detail and debug tell-tales: search-baq-rest.md §2.3d.

## 22. metafx-matrix IS real; `#slot` parentId IS the layer form (skill corrections)

Two earlier components.md claims were wrong for real layers and produced broken UIs (both reflect
older-build vs deployed-build divergence, cf. §21):

- **`metafx-matrix` exists** and is App Studio's standard grid-of-fields layout widget (live:
  `mxConfirmTop`, `mxConfirmTotals`, `mxBillTotals`, `mxSalesAgents`, header matrices). Pattern:
  matrix node in a panel-card slot → `metafx-col` cells with component-level `x`/`y` and
  `model.width:"auto"` → exactly ONE control per cell (blank `ep-label` spacers for empty cells;
  fill every cell of the bounding grid). **#1 gotcha: `model.columns`/`model.rows` are SWAPPED —
  `columns` = ROW count (`max(y)+1`), `rows` = COLUMN count (`max(x)+1`) — and cells beyond them
  are silently CLIPPED** (a 2-col × 4-row panel needs `columns:4, rows:2`; `columns:2, rows:4`
  dropped two inputs). Violations render partially with NO error. Full pattern + evidence table:
  components.md §3.8a.
- **`parentId: "<containerId>#<slot>"` is the correct flat layer-authoring form**
  (`#bodyComponents`, `#headerComponents`, `#expandedHeaderComponents`, `#extensionComponents`);
  no nested `components` arrays needed. The "slots are model arrays / no `#`" description applies
  only to the raw runtime model. Rows/cols/matrix cells use the plain container id as `parentId`.
- `metafx-col` cells in these layers use `model.width` (e.g. `"auto"`), not `flexBasis`.

Working reference (committed): `pcGetOrder` body = `lblGOInfo` (full width) → `mxGetOrder` (2×4
matrix; left column Company/Office/OrderNum/BackOrder combos+boxes, right column a spinner-anchor
label + 3 blank spacers) → `txtGO_Log` (full-width `erp-text-area`, sibling of the matrix).

## 23. Dashboard `imports` blocks: preview passes, menu launch 500s — strings.jsonc key must be `default` (VERIFIED)

Symptom: a dashboard base app worked in every App Studio preview but failed EVERY real menu launch
with a generic "unexpected internal problem" + Correlation ID. Server log:
`InvalidCastException: Unable to cast JArray to JObject` at
`Epicor.MetaFX.Core.Helper.Translation.MergeWithGeneratedString` inside `GetApp` —
a code path that ONLY runs on a real menu-driven launch, never in preview.

Cause: a speculative `imports` block added to the base-app jsonc files with a guessed item key —
`{"strings": {"$ref": "...strings.jsonc#/strings"}}` in `strings.jsonc`. Verified against the
published v3.0 strings schema AND a real App-Studio-generated dashboard (PartBinSummaryDB):

- Real dashboards DO ship `imports` in `dataviews/events/rules/strings/tools.jsonc`, pulling shared
  `../shared/imports/UIDashboards/base/*` content.
- The item key matches the file name for `dataviews`/`events`/`rules`/`tools` — **but `strings.jsonc`
  uses `default`** (the schema allows only `default`; additionalProperties:false).
- `"imports": []` (or no block) is also valid and ships in real apps (ProjectListingDb) — the right
  choice when there's no shared content to merge. Removing all five blocks fixed the live failure.

Rules: never invent `imports` shapes — copy them from a real generated dashboard or leave them
empty. And **preview passing ≠ done**: always test a real menu launch, and diagnose generic launch
failures by pulling the server log by Correlation ID.

---

<!-- Field notes from a dashboard uplift. Its §1–§14 numbering is LOCAL to this chapter — cross-references elsewhere in the skill of the form "lessons §N" refer to the numbered sections ABOVE this line. -->

# Kinetic layer build notes: dashboard uplift

Field notes from a classic-to-Kinetic dashboard uplift (`Ice.UIDbd.<DashboardID>`, Kinetic 2024.x). Written for the model running the build skill.

These are **standards, not rules**. Each records what was observed in one environment and what it
usually implies. Where a note says "prefer", "usually" or "in this environment", that hedging is
deliberate: the underlying behaviour has been seen once or twice, not proven universal. Judge each
against what the system in front of you is actually doing, and let observed behaviour override
anything written here.

---

## 1. Treating a write as landed

**Observed.** `MCPToolsKinetic-ImportLayer` returned `{"Success": true}` for a write that did not reach the
published content. Separately, a layer verified correct on the server was later found replaced by
different content, with no error anywhere.

**Standard.** Treat a success response as "the call was accepted", not "the content is live". After
a write that matters, re-read from the server and compare against what you sent.

**How much verification is proportionate.** Scale it to what is at stake and how subtle the change
is. A content hash comparison catches wholesale replacement cheaply and is a reasonable default. When
the change is a single property, compare that property explicitly, because a hash tells you something
differs without telling you what. When several imports happen in a row, verifying the last one is
usually enough unless an earlier one is load-bearing for a user test in between.

**Related.** Verification is most valuable immediately before handing artefacts to someone else or
declaring a phase done. That is the point where an unnoticed regression becomes expensive.

---

## 2. The App Studio draft as a competing writer

**Observed.** A layer imported and verified correct was later found holding content that matched none
of the local builds, timestamped after the imports, attributed to the user's account, with the draft
block empty. Reconstruction: App Studio held a stale draft from earlier in the build, and a publish
flushed that draft over the imported content. Two fixes and a panel layout were silently reverted.

**Standard.** The layer record carries published content and an App Studio draft. Both can be
written. An open App Studio is a second writer you do not control, and its draft may be much older
than it appears.

**Practical shape.**

* Prefer having App Studio closed during an import cycle, and say so when asking a user to test.
* After a session where App Studio has been open, re-verify before treating the layer as current.
* Writing both blocks identically on import reduces the window where they can diverge.
* `HasDraftContent` on the layer list tells you a draft exists, not whether it is stale. It is a
  prompt to look, not a diagnosis.

**Recognising it.** Content that matches none of your local builds, a modification timestamp later
than your last import, or components with IDs you never authored. Comparing the server content
against every local build you have made is a fast way to distinguish "someone else's work" from "an
older version of mine", and the distinction matters: one you merge, the other you replace.

**Before overwriting.** Save the current server content locally first, and establish whether it is
newer work or a stale revert before deciding. Component GUIDs help: matching GUIDs mean it descends
from your layer, while unfamiliar component IDs mean something was authored elsewhere.

---

## 3. What App Studio Export actually contains

**Observed.** Exporting from App Studio produced an archive containing `Apps/<AppId>/*.jsonc` and no
`Layers/` entry at all. The base app content was correct and current. The customization layer was
absent, with nothing in the archive indicating an omission.

**Standard.** Do not assume an export carries everything the screen needs. Inspect the archive's
folder structure before treating it as a deployment artefact.

**Why it matters.** For a dashboard uplift where the customization lives in a layer, shipping only
the app produces a screen that loads and works but is missing every layer-supplied behaviour. That
failure is silent at deploy time and only surfaces when someone looks for a missing button.

**Practical shape.** An uplift of this shape generally needs the base app, the layer, the BAQ and the
menu record, and they travel by different routes. When a user asks whether an export is sufficient,
checking the archive contents answers it definitively and quickly.

---

## 4. Layer archive path

**Observed.** A layer zip built as `Layers/<LayerName>.jsonc` was rejected with
`startIndex cannot be larger than length of string`. The same content at
`Layers/<ViewID>/<LayerName>.jsonc` imported cleanly.

**Standard.** The importer appears to derive the view ID from the folder path. Mirror the path shape
that a server-produced export uses rather than flattening it.

**Recognising it.** A string-index or substring error from the import call usually points at package
shape rather than content. Comparing your archive's entry names against a downloaded one resolves it
faster than inspecting the JSON.

---

## 5. Update in place versus delete and recreate

**Observed earlier in this build.** Importing over an existing layer was rejected with a message
about the customization already existing in another company, across several package shapes and
company values. Later in the same build, delete-then-import under the same name worked reliably and
repeatedly.

**Standard.** Prefer delete-then-recreate as the layer iteration idiom on this system. Keeping the
same layer name matters, because menu records and user selections reference it.

**Softening a note that was previously too absolute.** An earlier version of these notes said import
"cannot update, only create" and advised building the complete end state in one shot. That
overstated it. What holds up is narrower: update-in-place has not been made to work here, so plan on
recreate; but iteration is perfectly practical, and there is no need to treat each import as a single
irreversible shot.

**Caution.** Delete-then-recreate leaves a window where the layer does not exist. If a user may be
looking at the screen, sequence it deliberately, and keep the current server content locally before
deleting so the previous state can be restored if the import fails.

---

## 6. Company and user scoping on layers

**Observed.** Sampling layers across six apps in one environment: every established, shared,
non-WIP customization layer was scoped to all companies with no user attached. The company-scoped
records were personalization layers, scratch layers, and in-progress work with unpublished drafts.
Separately, a company-scoped layer could not be deleted through the tooling, which resolves against
the all-companies scope and reported the record as not found.

**Standard.** For a shared customization layer, all-companies with no user is the usual target. The
Epicor import dialog defaults to the current user and company, which is generally not what a shared
layer wants.

**Interpretation.** This is an estate convention rather than a product requirement, and conventions
differ. Sampling comparable layers in the target environment is a better guide than any fixed rule,
and it also surfaces which naming patterns correspond to shared versus personal work. Note that a
"last updated by" value identifies whoever last touched a record, not necessarily its author, so it
is weak evidence about intent.

---

## 7. Combo sort field

**Observed.** A BO-backed combo generated with `sort` set to its value field listed by code. Setting
`sort` to the text field produced the ordering users expected. A delivered example
(`Erp.BO.MiscChrgsvc` with `valueField: MiscCode`, `textField: Description`, `sort: Description`)
confirms the shape: a bare column name, no direction suffix.

**Standard.** When a combo displays a description but stores a code, sorting on the text field is
usually what people want. The stored value is unaffected.

**Interpretation.** Not universal. Where users genuinely think in codes, code order is correct. Worth
asking rather than assuming, and worth recording the decision either way, because generators tend to
emit value-field sort and it will return if a component is regenerated.

---

## 8. Dates that render raw

**Observed.** A grid column and a panel field bound to `Ice.Memo.MemoDate` displayed a raw ISO
timestamp. That field is a SQL `datetime` carrying a UTC business type. Other date fields on the same
screen were plain SQL `date` and formatted correctly with no intervention. Changing the panel field
from `erp-text-box` to `erp-date-picker` resolved it, and the displayed date matched classic.

**Standard.** Before treating a formatting problem as a Kinetic limitation, check the underlying SQL
type and business type. Plain dates generally format from BAQ metadata; datetimes with a timezone
business type behave differently.

**On the component choice.** `erp-date-picker` is the delivered component for date-bound fields and
carries the framework's own conversion, which is why it agrees with classic. A server-side cast is
available but carries a timezone risk: casting a UTC datetime to a date yields the UTC calendar day,
which can differ from the local day for late-in-day records. Prefer the client component where one
exists.

**Interpretation.** Grid columns and panel fields are different surfaces, and a fix for one does not
imply the other is broken. Verify each against the running screen before claiming a defect. In this
build two formatting problems were reported to the user that turned out not to exist, both inferred
from metadata rather than observed.

---

## 9. Claiming a defect you have not seen

**Observed.** Twice in this build, formatting defects were reported to the user based on metadata
inference, and both were contradicted when the user looked at the screen. Both had already been
written into a list of known issues destined for QA.

**Standard.** Distinguish what you have observed from what you have inferred, and say which. A
metadata-derived expectation is a hypothesis worth checking, not a finding worth reporting.

**Why it matters more than it looks.** A fabricated defect costs more than a missed one at this
stage: it gets written into documentation, handed to QA, and sometimes triggers remediation work on
something that was never broken. When you cannot see the running screen, asking for a screenshot or a
network payload is cheap relative to that.

---

## 10. State property casing

**Observed.** `readOnly` in camelCase had no effect. `readonly` in lowercase worked.

**Standard.** Kinetic state properties are lowercase. When a property appears to be ignored, casing
is worth checking early, since the failure is silent.

---

## 11. Guarding a toolbar action

**Observed.** A grid toolbar button that opened a slide-out errored when clicked with no row
selected. Delivered apps guard equivalent cases with a condition action, an `erp-message-handler`,
then `exit`.

**Standard.** Reuse the delivered guard shape rather than inventing one. Delivered message handlers
in the sampled apps skew toward `warning` level with `Slideout` presentation for user-sequence
mistakes, and `error` for genuine failures.

**Related.** Toolbar buttons that act on a selected row are worth checking against the no-selection
case as a matter of course, since it is easy to miss when testing with data already loaded.

---

## 12. Layout: what the vocabulary does and does not offer

**Observed.** No delivered panel-card in the sampled apps sets a height, minimum height or maximum
height. `autoFillContainer` on a panel-card filled the page rather than matching a sibling, pushing
the grid off screen. Nesting cards with `columnsWide` stacked them; `metafx-col` columns placed them
side by side. Wide fields are achieved with `erp-text-area` and a `rows` value rather than any width
property; no delivered component in the sample sets `width` or `capWidth`.

**Standard.** When a layout property is not present on any delivered instance, that is meaningful
evidence it is not the mechanism, and inventing a plausible property name is not a good use of an
iteration. Searching the delivered apps for the property before using it is fast and usually decisive.

**On equal-height sibling cards.** No mechanism for this was found in the delivered vocabulary during
this build. That is a statement about what was searched, not a proof of impossibility, so treat it as
"not found" rather than "cannot be done", and revisit if a delivered example turns up.

**Softening a note that was previously too absolute.** The generator guidance pairs
`autoFillContainer: true` with no `gridModel.height` plus `scrollable`, described as three settings
that must go together. In this build the opposite pairing (`autoFillContainer: false` with an
explicit height) was needed once a sibling panel shared the row, and it worked. The durable version
of the guidance: these settings interact and should be changed together, the generator default suits
a full-width grid, and a fixed height is a legitimate alternative when the layout differs, at the
cost of responsive behaviour below a certain viewport width. Note the width at which it degrades.

---

## 13. Preview is not a menu launch

**Restated, since it held up.** App Studio Preview bypasses the launcher. A screen that works in
Preview has not been shown to work from a menu, and Preview does not fire `onLoad`, which is why
initialization is usually chained from a component `onInit` as well.

**Standard.** Treat Preview results as provisional until the same paths have been exercised through a
real menu record. When testing has all been in Preview, say so plainly rather than letting it read as
verified, and carry it as an outstanding item.

**Interpretation.** This does not mean Preview testing is worthless; it is the fastest way to iterate
and catches most functional problems. It means the sign-off step is different from the iteration
step.

---

## 14. Pacing and knowing when to stop

**On repeated failed fixes.** When a symptom survives a couple of attempts, that is a signal the
model of the problem is wrong, and continuing to layer fixes tends to compound rather than converge.
The useful response is to say so, strip back to a configuration known to work, and gather evidence
before the next attempt. Treat this as a judgement about whether understanding is improving, not as a
fixed attempt count; three quick attempts that each narrow the cause are healthier than two that each
guess.

**On asking for evidence.** When something fails in a running screen you cannot see, a network
payload, a row count or a screenshot resolves in one exchange what theorising resolves in several.
Ask early rather than after exhausting hypotheses.

**On delegation.** Work handed to a subagent is opaque while it runs, and a long silence is
indistinguishable from progress. For lookups against tools that return large payloads, doing the
calls directly in small visible steps keeps the user oriented. Where delegation is worthwhile, scope
it tightly and say what it is doing and roughly how long it should take.

**On internal names.** Working filenames and build iteration numbers mean nothing to the user.
Refer to artefacts by what they are and what they contain, and name delivered files so the name
carries the meaning.
