---
name: typecel-modeling
description: >
  Build and edit financial models through the Typecel Studio MCP server (the
  `mcp__studio__*` tools) — a virtual filesystem of folders, sheets, and blocks
  where you author structure as canonical JSON and the host validates, compiles,
  and evaluates on every write. Use this skill whenever the user asks to create
  or change a financial model: a three-statement model (P&L, balance sheet, cash
  flow), roll-forwards, KPI decompositions, driver-based forecasts, actuals plus
  projections, working capital, checks, source-backed citations, or an Excel
  export. Load this skill BEFORE touching any Studio tool, then fetch the exact
  JSON wire shapes from the host's `grammar` tool and the modeling doctrine from
  its `methodology` tool — the shapes and the solver's rules are exact, and
  writing without them produces models that do not compile.
---

# Building Financial Models through the Typecel Studio MCP

Typecel is a **declarative** financial-modeling language: you say what items exist
and how they relate, and the solver infers calculation direction. The Studio MCP
exposes the model as a **virtual filesystem** of folders, sheets, and blocks — you
edit it the way a coding agent edits a repo (`write_sheet` to author a whole file,
`edit_block` to change one block in place), and the pipeline
re-validates/compiles/evaluates the whole model on every write. Your job is to
translate a business scenario into a `ModelLanguage` document — settings + a tree
of sheets, each holding one or more blocks — then read it back and confirm it
evaluates clean and balances.

This skill is the **mechanics + the mental model**. The exact per-kind JSON wire
shapes are served by the host itself through the **`grammar` MCP tool** — call
`grammar()` for the index (organized by the language's three axes: **structure** =
the blocks + relations, **time** = settings, **content** = inputs + formulas +
expressions), read the relevant topics **before your first write**, and call
`grammar("common-mistakes")` when a write is rejected. The tool serves the RUNNING
host's grammar, so what you read always matches the schema the host accepts.

## 0. The Studio MCP surface — a virtual filesystem

The model is a **virtual filesystem**: a `settings` doc plus a `root` tree of
**folders** and **sheets**, where each **sheet holds an ordered list of blocks**.
You edit it the way a coding agent edits a repo — `write_sheet` to author a whole
file, `add_block`/`edit_block` to change one block in place, `reorder_blocks` to
re-order. Every model-scoped call takes `model`, a locator of the form
`{handle}/{name}` obtained from `create_model` or `list_models`.

> **Surface status — VFS vs. the flat host.** This skill targets the **multi-block VFS
> surface** below (folders, several blocks per sheet, `write_sheet` / `add_block`, etag).
> A host may still expose only the **flat core tools** — `write` / `read` / `ls` /
> `get_model` / `get_evaluated`, where a `write` to `model/<sheet>` upserts
> **one block** (no folders, no `{blocks:[…]}` sheet body). `ls(model, "")` tells you
> which you're on: typed `{name, kind}` sheet/folder entries ⇒ VFS; the bare field names
> `["settings","bindings","assertions","model"]` ⇒ flat. **The §0 tool table, the §1
> authoring order, and the §1c multi-block layout all assume the VFS surface.** On a flat
> host everything goes through the one `write(model, <path>, <json>)` tool instead:
> `write(…, "settings", <SettingsSpec>)` creates/updates the model (there is no
> `create_model` / `write_settings`); `write(…, "model/<sheet>", <one block>)` upserts a
> single block (no `{blocks:[…]}` sheet body, no folders, so one block per sheet);
> `write(…, "bindings" | "assertions", <array>)` sets those; read back with
> `read_evaluated(model, "model/<sheet>")` or `get_evaluated` (no `read_values`);
> Excel delivery is a UI action on every surface. The block JSON, item-path rules (§3), naming (§1c), and the
> solver's rules are identical on both surfaces — only the call shape differs.

The tools name **what they target**. **Node** ops (folder / sheet) take a path that
*is* the target. **Content** ops (block = inside a sheet) take the sheet path plus
the block **name**, and carry a `_block(s)` suffix. Structured arguments —
`write_sheet`/`write_settings` content, block bodies, `cite` cells — are **native
JSON**: pass the document itself, never a string containing it (escaping a whole
sheet doubles its cost and invites quote bugs; the string form is tolerated for
compatibility only). A line's `cells` is a **period-keyed map** — values as decimal
strings, formulas as `=` DSL text, an intemporal line's single cell as the bare
entry (`"cells": "0.21"`); read_sheet returns the same shape you write. Exact
shapes: `grammar("inputs")` / `grammar("formulas")`.

| Group | Tool | Use |
|---|---|---|
| **model** | `create_model(name, organization_id?, draft?)` | Create a fresh model — under your handle by default, or in an ORG workspace (`organization_id`: an `org_…` you belong to with an editor/admin role; the model lands org-owned, born Private). `draft: true` (requires `organization_id`) makes it a DRAFT — invisible to the workspace until opened up; only you, people you grant, and org admins reach it. Returns `{locator, name}`; use `locator` as `model` in later calls. A non-member refusal names your actual orgs, so call it once to discover ids. |
| | `list_models(organization_id?)` | Discover models — `[{locator, name, orgAccess, …}]`. Personal scope by default; `organization_id` lists THAT org's models instead (drafts — `orgAccess: "MembersOff"` — appear only when you hold a grant on them). (No `model` needed; this is how you find one.) |
| **folder** | `create_folder(model, path)` | Make a directory node (parent must exist — no `mkdir -p`). |
| | `ls(model, path)` | List children as typed entries `[{name, kind}]` (`kind: folder \| sheet`); sheet entries carry an `etag`. `path:"root"` lists the top of the tree. |
| | `rename_folder` / `move_folder` / `reorder_folder` | Re-name / re-parent / re-order a folder's children. `reorder` is path-safe; **rename/move shift the item paths underneath** (§3). |
| | `delete_folder(model, path)` | Remove the folder. |
| **sheet** | `create_sheet(model, path)` | Make an **empty** sheet (parent must exist). Returns `{etag, blocks:[]}`. |
| | `read_sheet(model, path)` | Read the sheet: its `blocks` **in display order**, each with its own `etag` (the key to local edits) plus a sheet `etag`. |
| | `read_values(model, path)` | Read the **evaluated cell values** for that sheet (the new-world `read_evaluated`, scoped to one sheet). |
| | `read_checks(model)` | Read the declared checks with their **evaluated verdicts** - per check x period: `pass \| fail \| indeterminate` (+ failure detail), plus `allGreen`. Model-global and read-only; it runs nothing (the verdicts come from the evaluation the last write already ran). |
| | `read_diagnostics(model, path?, severity?, code?, limit?)` | Read the **full diagnostics list** behind the ack's summary — `{summary:{errors,warnings,total}, diagnostics, truncated}`, narrowable by sheet path / severity / code. Model-global and read-only. |
| | `write_sheet(model, path, {blocks:[…]}, if_match?)` | Author / replace the **whole** sheet (array order = display order). Like `Write`. Returns `{etag, diagnostics}` (diagnostics = the summary — see below). |
| | `rename_sheet` / `move_sheet` / `delete_sheet` | Re-name / re-parent / remove the sheet. **rename/move shift the item paths of every block on it** (§3) — settle the layout first. |
| **block** | `add_block(model, sheetPath, <block json>)` | Append a block to the sheet's content. Returns `{etag, sheet_etag, diagnostics}`. |
| | `edit_block(model, sheetPath, <block json>, if_match?)` | Replace **one** block's body in place (matched by its `name`; position unchanged). Like `Edit` — emit only the changed block. |
| | `reorder_blocks(model, sheetPath, [names…], if_match?)` | Set the display order with a **names-only** permutation (no bodies). |
| | `remove_block(model, sheetPath, name, if_match?)` | Delete the named block. |
| **settings** | `read_settings(model)` | Read the `SettingsSpec` JSON (time axis / currency / constants). |
| | `write_settings(model, <SettingsSpec>, if_match?)` | Replace the settings doc. |
| **sources** | `list_sources(model)` | List archived sources for the model's project. Read tools address the `name`; `rename_source`/`delete_source` take the `id` — the stable entity handle a concurrent rename can never repoint. |
| | `capture_url(model, url, name?)` | Fetch a document from a public URL into the project's archive (SSRF-guarded, 25 MB cap, kind detected from bytes). Budget: 20 captures per project per hour. |
| | `rename_source(model, source_id, new_name)` | Rename an archived source, addressed by its stable id. Citations anchor to the same id, so a rename never breaks or downgrades a badge. |
| | `delete_source(model, source_id, acknowledge_citations?)` | Delete a source and its search projections, addressed by its stable id. If model cells cite it, the call is refused with the citation count until you re-run **echoing that count** in `acknowledge_citations` (a stale count is re-refused with the current one); the surviving citations turn `unreadable` on the next `verify_citations`. |
| | `get_source_overview(model, source)` | Start here for a source map: xlsx sheets with used ranges and preview rows, or PDF page count. |
| | `search_source(model, query, source?)` | Search archived chunks: xlsx row records and PDF text-layer lines (a PDF hit's `sheet` is the page, e.g. `p6`). Hybrid search handles Japanese/English labels and synonyms; read the hit before citing it. |
| | `read_source(model, source, range)` | Read a compact addressed grid window. Xlsx rows show worksheet row numbers and column letters; use this to derive cell addresses. |
| | `locate_source(model, name, position)` | Check that a document-native position exists (`Sheet!A1`, `p<N>`, or a PDF page box `p<N>@x,y,w,h`). Useful before cite; a box label echoes the box text. |
| | `write_source_note(model, source, position?, text)` | Leave or revise a reader note for the next reader. Notes are starting points, never evidence; empty text deletes the note. |
| | `cite(model, path, name, cells?, line?, source?, position?, time?, if_match?)` | Transcribe source values + provenance onto a block's input cells (every cite is a fill; there is no provenance-only mode). **Batch by block**: pass `cells` — a JSON array of `{line, time?, source, position}` — to fill a block's recorded cells in ONE call, all-or-nothing; the ack returns one receipt per cell under `verifications` (in call order). The single-cell fields are the one-element shorthand. A receipt whose `replaced` is non-null displaced a different existing number — surface that. |
| | `verify_citations(model)` | Re-check every cited input against archived bytes. Finish transcription with this and expect all cited cells to be `verified`. |
| | `trace(model, path, name, line, time?)` | Inspect one cell's sourceName/position/current citation status. |

**Diagnostics-first.** Every write-class call (`write_sheet` / `add_block` /
`edit_block` / `reorder_blocks` / `remove_block` / `write_settings`) returns a small
ack carrying a `diagnostics` **summary** (and an `etag`) — **not** the whole evaluated
model, and never the full diagnostics list. The summary is
`{errors, warnings, total, delta:{appeared,resolved}, head:[first few in full], truncated}`:
the counts are the gate, `delta` tells you what THIS write broke or fixed, and `head`
carries the first few diagnostics verbatim. When you need more than the head, pull
`read_diagnostics(model, path?, severity?, code?)` — the checks-style pull side. The
pipeline still re-validates/compiles/evaluates the whole model on every write. To
inspect computed numbers, call `read_values(root/<sheet>)` — evaluation is pulled per
sheet, never dumped wholesale.

### Paths — `root/<folder>/…/<sheet>` plus `settings`

```
settings                      → SettingsSpec   (top, outside root — the model's <head>)
root                          → the tree's top; ls it to list folders + sheets
root/<sheet>                  → a sheet sitting directly under root
root/<folder>/…/<sheet>       → a sheet nested under one or more folders
```

- The only separator is `/` (the one reserved character — it can't appear in a
  name). A `.` is **just a name character**, so `root/q1.2024` is a perfectly
  normal sheet path.
- `settings` lives at the **top, outside `root`** (its `<head>` position) — so
  `root` contains only the user's folders and sheets, never the config.
- A **sheet holds an ordered list of blocks** (1 sheet = 1+ blocks). Folders
  (`create_folder`) let you organize sheets into a tree (e.g. `root/Financials/BS`,
  `root/Financials/PL`, `root/Drivers/asm`). The display order of blocks within a
  sheet is set by `reorder_blocks`; the order of children within a folder by
  `reorder_folder`.
- **Structure ≠ content.** `create_folder` / `create_sheet` make the node;
  `write_sheet` / `add_block` fill it. Writing to a path that doesn't exist is an
  error (no ghost sheets). A flat model needs no folders at all — just sheets under
  `root`.

## 1. Authoring order

Before choosing the model's **structure** — the sheets, the decomposition, the
wiring — call `methodology()` for the index and read the topics matching the task:
`grammar` answers how to write the JSON, `methodology` answers what to build.

Build in this order — later slices reference earlier ones:

```
1. create_model(name)       → get a locator (or list_models to find an existing one);
                             add organization_id to land it in an org workspace, draft:true
                             to keep it invisible to the workspace while you build
2. write_settings          → time axis (boundary + periods + period types), currency, constants
3. write_sheet root/<s>    → author the sheets, each with its blocks[] in display order
                             (which sheets, and what goes on them: methodology("model-architecture")).
                             Build the blocks in dependency order across the sheets — stocks before
                             the statements that read them — so mid-build diagnostics stay small
                             (a sheet's write_sheet carries all its blocks at once)
4. (cross-block wiring)    → authored ON the lines as `relation` fields inside step 3's
                             blocks — there is NO separate bindings step (a non-empty
                             top-level bindings array is rejected)
5. write the checks block   → declared checks (ranges, ties, covenants) — grammar("checks")
6. read_values(root/<s>)    → VERIFY numbers; the write acks already carry diagnostics
```

Author blocks in dependency order (a line's `relation` references items that must
already resolve). Every write-class call returns an ack with a `diagnostics` summary,
so you catch errors as you go — check the summary's counts and `delta` after each write
(diagnostics-first; `read_diagnostics` when the head isn't enough), and pull the
resulting numbers with `read_values(root/<sheet>)`.

## 1b. The editing model — write whole, edit local (coding-agent style)

Author the surface like a coding agent edits a repo:

- **`write_sheet(root/<sheet>, {blocks:[…]})` = Write** — create a new sheet or
  replace one wholesale. The `blocks` array order **is** the display order. Use it
  when authoring a sheet for the first time, or when restructuring it.
- **`add_block` / `edit_block` = Edit (local)** — once a sheet exists, **emit only
  the block you're changing**: `edit_block` replaces one block's body in place
  (matched by its `name`, position unchanged); `add_block` appends a new one. The
  tool **preserves the blocks you don't touch** — never re-emit unchanged blocks
  (that wholesale-rewrite habit is what causes drift/hallucination).
- **`reorder_blocks(root/<sheet>, [names…])` = order only** — a **names-only**
  permutation of the sheet's current blocks, no bodies. Keep the heavy thing (block
  bodies) out of the light operation (ordering).
- **`remove_block(root/<sheet>, name)`** deletes one block.

**Read before you edit.** `read_sheet` returns each block with its own `etag`;
`edit_block`/`remove_block` take that block `etag` as `if_match`, and
`write_sheet`/`reorder_blocks` take the **sheet** `etag`. The etag is a stateless
content hash — pass back the one you read, and a mismatch means the content changed
under you (`stale`): re-read and retry. There is **no block rename** (a block name is
the root of every reference to it, so renaming would cascade across formulas and
bindings) — to rename, restructure the sheet with `write_sheet` and fix the
references. **Sheet and folder names also appear in item paths** (§3), so renaming or
moving a sheet/folder shifts the path of every item under it — settle the layout and
names **up front**, before authoring bindings/formulas, and treat any later sheet/folder
rename or move as a path-changing edit (rewrite the affected references). Re-ordering
(`reorder_blocks` / `reorder_folder`) is path-safe — order is not part of a path.

## 1c. Sheet & block layout — group blocks, spell names out

A sheet holds an **ordered list of blocks**, so **put several related blocks on one
sheet** rather than one-block-per-sheet. Aim for **3–5 sheets total**. A typical
three-statement layout:

```
root/Financial Statements   → Balance Sheet · Profit And Loss · Cash Flow Statement
root/Calculations            → Accounts Receivable Rollforward · Accounts Payable Rollforward ·
                               Inventory Rollforward · PP&E Rollforward · Debt Rollforward ·
                               Retained Earnings Rollforward · Cash Rollforward
root/KPI Drivers             → one KpiTree block per headline metric (segment / driver trees)
root/Assumptions             → forecast drivers only, scoped by concern (Cost Drivers · Working
                               Capital Drivers · …)
root/Historical Data         → the recorded actuals — the P&L's and the balance sheet's — wired
                               to the statements by connections (never typed on a statement)
```

- **Spell names out, in Title Case, no abbreviations** — for sheets, blocks, **and**
  items. `Balance Sheet` not `bs`; `Accounts Payable Rollforward` not `ap_rf`; `Accounts
  Receivable` not `AR`; `Profit And Loss` not `pl`. Names may contain spaces, capitals, and
  `&`, but **not** `/` or `` `\` `` (path separators), no control characters, no leading or
  trailing whitespace, and not a bare `.` or `..` — the `Identifier` well-formedness rule,
  enforced at intake. These names *are* the path segments every binding and formula is
  written in (§3), so legible names keep the whole model self-documenting.
- **Order blocks by reading flow** within a sheet (the `blocks[]` array order, or
  `reorder_blocks`): on `Financial Statements`, Balance Sheet → Profit And Loss → Cash
  Flow Statement.
- **No folders for a small model** — keep sheets directly under `root`, so an item path
  stays exactly `[sheet, block, …]` (a folder prepends a segment — §3).

This is the layout the rest of the skill assumes; the item-path examples in §3 use it.

## 2. The mental model — five fields, one equation graph

A `ModelLanguage` has exactly five fields:

- **Blocks** — the structure. Six kinds, each contributing equations to one graph:
  - **BalanceSheet** — debit/credit trees of **stock** leaves (`Assets`, `L&E`).
  - **ProfitLoss / CashFlow** — a **flow chain**: sections of `FlowRow`s followed
    by an optional `MeasureLine`. **Measure lines are cumulative running totals**
    down the chain (so the
    last CF measure = total net change in cash). **Decompose revenue (and costs that
    differ by segment) into per-segment rows** where the segments earn differently —
    nest `flow` rows under a subtotal.
  - **RollForward** — one stock + its flows: `Stock[t] = Stock[t-1] + Σ flows`.
    Working-capital cycles are roll-forwards (e.g. `Accounts Payable Rollforward`).
  - **KpiTree** — a decomposition: `target = operator(children)` (e.g.
    `Bookings = Product(Subscribers, ARPU, Months)`). **One root per tree** — use
    several KpiTree blocks for several top metrics. Go **as deep as the business is
    actually run** for the metrics that matter (§8).
  - **Series** — structure-free lines whose value is a **trajectory**: input cells
    and/or **formula cells** (repeat one `=` entry per period to fill a span). The home of
    drivers, assumptions, and analytics.
- **Bindings** — cross-block links (five kinds, §4).
- **Namespace** — the folder/sheet tree under `root` (managed by `create_folder` /
  `create_sheet` / `write_sheet` and the rename/move ops).
- **Settings** — time axis, currency, constants.
- **Assertions** — declared checks over evaluated values (§6).

The equations are **undirected**. `Revenue = Subscribers × ARPU` (a KPI) and
`Receivables[t] = Receivables[t-1] + Revenue` (an RF) are equally first-class. You
supply enough values that each equation can close (**N-1 rule**: an equation with
N variables needs N-1 supplied), and the solver derives the rest.

## 3. Item paths — `[sheet, block, …ancestors, item]`

Every binding, every formula `itemRef`, and every assertion addresses an item by its
**canonical path**: the namespace address of its block plus the item's ancestor chain
inside the block. The path is built by walking the namespace tree —
**`[…folders, sheet, block, …item-ancestors, item]`**. With **sheets directly under `root`**
(the recommended no-folder layout), the first segment is the **sheet** and the second the
**block**; a folder, if present, prepends its segment(s) ahead of the sheet (see below):

| Convention | Where the item lives | Item | Path |
|---|---|---|---|
| **Multi-block (use this)** | sheet `Financial Statements`, block `Balance Sheet` | leaf `Cash` under `Assets` | `["Financial Statements","Balance Sheet","Assets","Cash"]` |
| | sheet `Financial Statements`, block `Profit And Loss` | flow `Revenue` | `["Financial Statements","Profit And Loss","Revenue"]` |
| | sheet `KPI Drivers`, block `Bookings Tree` | leaf `Subscribers` under root `Bookings` | `["KPI Drivers","Bookings Tree","Bookings","Subscribers"]` |
| **Flat (1 block/sheet)** | sheet `pl` == block `pl` | flow `Revenue` | `["pl","pl","Revenue"]` (name doubled) |
| **Settings constant** | — | `TaxRate` | `["TaxRate"]` (single segment) |

- The sheet and block names **only coincide in the flat one-block-per-sheet convention** —
  hence the doubled `["pl","pl",…]` you'll see in the `grammar` topics, which use short flat
  tokens for density. With several blocks on a sheet they differ, and the path reads
  naturally (`["Financial Statements","Profit And Loss","Revenue"]`).
- **Folders prepend to the path.** A block on sheet `BS` inside folder `Financials`
  resolves at `["Financials","BS",<block>,…]` — moving a sheet into a folder shifts every
  path under it. So for a small model **keep sheets directly under `root` (no folders)** and
  the path is exactly `[sheet, block, …]`.
- The path includes the **full ancestor chain** inside the block (BS parent → leaf,
  PL/CF subtotal → child, KPI root → … → leaf). Get it wrong and you get `TC2001 — formula
  references an item that does not resolve`.
- **Relative references (formulas only).** Inside a block, a formula may write a **bare
  name** (1 segment) to reach a sibling in the *same block*, or **`block.item`** (2
  segments) to reach a sibling block *on the same sheet* — the resolver burns it to the full
  path (an ambiguous bare name is `TC2050`). Three-plus segments are taken as a full
  canonical path — but **a formula should never need one: formulas do not cross sheets**.
  A formula computes beside its inputs; when a computation needs another sheet's value,
  delegate — compute in a block that owns its inputs and let the result travel by a
  relation (relations are what cross sheets). **Bindings and assertions take full
  canonical paths.**

## 4. Bindings — five kinds

A binding links two items across blocks. **Both items' specs must match**
(DataType / Unit / Temporality / StockFlow) or you get `TC2013`.

| Kind | Shape | Meaning |
|---|---|---|
| `target` | `{implementing, implemented}` | `implementing` carries the value for `implemented`. RF stock → BS leaf; a conduit; a Series driver → a model line. |
| `coupling` | `{peerA, peerB}` | Symmetric double-entry journal (opposite signs). PL flow ↔ RF flow. |
| `reference` | `{reader, source}` | `reader` mirrors `source`'s value (read-only). |
| `stockDelta` | `{flow, stock}` | `flow[t] = ±(stock[t] − stock[t-1])` — CF working-capital lines. |
| `addBack` | `{addingBack, addedBack}` | CF add-back of a non-cash PL charge (Depreciation). Same sign. |

**Double-entry is structural.** When each journal is two-sided — every PL flow
coupled to an RF flow, every RF stock targeting a BS leaf, the income conduit
(`pl Net Income → rfRE niFlow`) and the cash conduit (`cf Cash from Financing →
cashRf netChangeFlow`) wired — the balance sheet closes in every period
automatically. You don't supply the balance; you wire the journals.

## 5. Actuals vs forecast — two Series, disjoint ranges (the backbone)

The cleanest way to split history from projection (the two Series are named
`Historical Actuals` and `Forecast Assumptions` in a real model — §1c; the short
`data`/`asm` tokens here match the `grammar` topics):

- A **`data` Series** carries input cells for the **actuals** (the historical periods).
- An **`asm` Series** carries **forecast formula cells** (the projected periods).
- Each model line that's exogenous is **targeted by both** — `target(data.X →
  home)` and `target(asm.X → home)` — over **disjoint period ranges**. `data.X`
  has input cells only in the actual periods; `asm.X` has formula cells only in the
  forecast periods. No `(line, period)` is supplied twice, so the cell-level
  over-determination check passes (this is the supported "multiple Series target
  one item" pattern).

The `home` is the model line itself (e.g. `["pl","pl","Revenue"]`), which then has
values across the **whole** horizon — and the wire is a **two-way mirror**, so the home's
actual values flow BACK into the `asm` line. A forecast formula therefore never reaches
across sheets (§3): it references **its own line** at a lag (a bare name — the prior
period's value arrives through the line's own connection) and its rate item beside it:

```
asm.Revenue[t]  (forecast) = Revenue[t-1] × RevenueGrowth   ← bare self-ref lag 1 + a rate item in the same block
```

(Ratio-driven lines like `COGS = Cost Ratio × Revenue` need **no formula at all**: the
identity lives as a **linkage** — see §4 and the attached ratio rider in
`grammar("profit-loss")` — and the era decides which corner is supplied. On the actual
period, supply the RECORDS (COGS and revenue) and leave the ratio empty: the identity
derives the ratio off the books, and its `[t-1]` carry-forward walks it into the
forecast; the forecast outcomes then derive exactly. Never type an
estimate-style ratio in the actual era. One solver rule shapes this: a record on a line
the structure already fully determines is flagged redundant (`TC3004`) — such a record
belongs in the checks layer, not a Series supply.)

A Series item's `stockFlow` **must match its home** (a Series feeding `pl.Revenue`,
a flow, declares `stockFlow:"flow"`). A standalone driver declares its own **time
dimension**, and for a rate the rule is **what it multiplies** — the per-period
dimension lives in exactly one factor of a product: a rate that multiplies a
**stock** into a flow (ARPU in `Subscribers × ARPU = Revenue`, an interest rate on
a balance, an average salary per head) carries the per-period itself and declares
`"flow"`; a rate that multiplies a **flow** (a per-unit price against a sales
volume, a cost ratio against revenue) stays `null` — there the per-period lives in
the volume/revenue. A point-in-time count (subscribers, headcount) is `"stock"`;
growth factors (`1 + g` forms), turnover/days ratios and other dimensionless
ratios (a margin, DSCR — a KPI ratio leaf) stay `stockFlow:null`.

**Forecast each driver from its own driver, not the top line by a single growth %.**
Project a stock as a roll (opening + additions − churn, a roll-forward — never one cell); a
ratio/run-rate as `revenue × ratio` or a days-ratio; a cost as `driver × constant` wired to
its KPI leaf. Represent **base/upside/downside one active case at a time** — edit the
`Forecast Assumptions` for the few easy-to-change levers (or keep separate model copies for
cases you want side by side). You **cannot stack competing scenario Series over the same
forecast cells**: two Series may target one item only over **disjoint periods** (that is the
actuals/forecast split above — not rival cases), so overlapping overrides over-determine the
cell. The **easy-to-change levers** (headcount, conversion, the price you set) are what you
**vary** between case copies; the hard-to-change drivers (FX, commodity, market size) stay
put and go on a **sensitivity sweep** instead.

## 5b. Source transcription — the trust loop

When archived sources exist, **transcription goes through the trust loop**. Never
retype a number you can read from an archived source without citing it; the value and
its provenance should land together.

The loop:

```
list_sources -> get_source_overview -> search_source -> read_source -> cite -> verify_citations
```

- `list_sources(model)` shows the available sources. Read tools (`read_source` /
  `locate_source` / `cite` …) address the `name`; the state-changing
  `rename_source`/`delete_source` take the `id` from the same card — never invent
  an id, always copy it from `list_sources`.
- `capture_url(model, url, name?)` brings a document in yourself — when the user
  points you at an IR page or a filing URL, capture it and continue the loop with
  no manual upload. The fetch is SSRF-guarded and size-capped, and the budget is
  20 captures per project per hour; if a fetch is rejected or times out, report
  the tool's reason instead of retrying blindly.
- **Prefer official sources.** When you choose what to capture, take the primary,
  official document — the company's IR page, the regulatory filing (SEC EDGAR,
  EDINET) — over news articles, aggregators, or data portals. Secondary sources
  are a fallback for when the official document is unreachable, and then you say
  so: report what you used and why the primary wasn't available. Numbers modeled
  from a secondary source are only as trustworthy as that source's transcription.
- **A new edition of a document is a new source.** When the Q2 databook arrives,
  capture it under its own name next to Q1 — never replace the old one. Sources are
  immutable archives, and existing citations keep pointing at the edition they
  verified against. `rename_source` is always safe (badges anchor to the id);
  `delete_source` is deliberate — if the source is cited it refuses with the
  citation count until you re-run echoing that count in
  `acknowledge_citations: <count>` (never guess it: copy it from the refusal or
  `verify_citations` — a stale count is re-refused because the citations
  changed since you looked). The surviving citations turn `unreadable` on the
  next check, which is the system being honest, not an error to route around.
- `get_source_overview(model, source)` is the map: workbook sheets, used ranges,
  preview rows — or a PDF page count plus a `pageMap` (each page's headline), which
  is how you pick the page to read without walking all of them.
- `search_source(model, query, source?)` finds likely rows by label. It is hybrid,
  so use the business term naturally, including Japanese/English synonyms when the
  workbook mixes languages.
- `read_source(model, source, range)` is the verification step. Read the
  neighborhood before citing. Xlsx output shows worksheet row numbers and column
  letters so the exact cell address is visible. PDF ranges are `p<N>` (whole page,
  line-capped) or `p<N>@x,y,w,h` (zoom); every parseable number in the output is
  annotated with its citation box — `売上高 497[255,99,18,8] 億円` means you cite
  `p6@255,99,18,8`, copied verbatim.
- After reading a source deeply, leave or update a note with `write_source_note`.
  Notes are for the next reader's orientation, never evidence: always re-read and
  box-confirm before citing. There is one note per place, so revise the existing
  note rather than appending a thread.
- `cite(...)` transcribes: it reads each source value and writes **value +
  provenance** in one write. **Batch a block's records into one call** (`cells`,
  all-or-nothing, one `verifications[]` receipt per cell) — a statement's actual
  year is one batch, not a call per cell; check every receipt, not just the ack. **Auditing a value someone already typed** is a
  composition, not a mode: read the RAW cell with `read_sheet` (not `read_values` —
  that is the evaluated view, where a formula's result can look like an input),
  read the source, compare them yourself — on a match, cite (the value stays the
  same and gains provenance); on a discrepancy, report it to the user instead of
  citing. **Only input cells are audit targets**: citing an address held by a
  formula cell replaces the formula with a transcribed input — never do that as an
  "audit". Never cite a non-empty cell you have not compared: a differing existing
  number is overwritten, and its receipt discloses it as a non-null `replaced` —
  treat that as a signal to surface, not to silence.
- Finish with `verify_citations(model)`. A clean transcription pass has the cited
  cells `verified`; investigate anything else before trusting the model. Use
  `trace(...)` on a single cell when you need to show its `sourceName`, `position`,
  and current status.

**Address discipline.** Cite positions come from `read_source` or `locate_source`
output. If the tool shows `'Financial Highlights'!G5`, keep the quoted sheet name
and cite that exact label. Search tells you the row; read the neighborhood to see the
column. Never guess a cell address from memory or from a plausible workbook layout.

**Mismatch handling.** Mismatch detection is yours before the write and the
system's after it: compare cell vs source before citing (above), and run
`verify_citations` after transcription — a `mismatch` there means the model value
was edited after its mint. A cite that fails with an unreadable/could-not-verify
error is the system being honest about the source read: fix the position (or the
box), never silence it by writing an uncited value. A successful ack with a
non-null `replaced` means you displaced an existing number — report it.

**PDF citations.** The loop is the same as xlsx with the page as the sheet:
pick the page from `get_source_overview`'s `pageMap` → `search_source` (a hit's `sheet`
carries the page, `p6`-form) → `read_source(range: "p6")` → **copy the `[x,y,w,h]` annotation** printed
on the number you want → `cite` with `p6@x,y,w,h`. A page-level position (`p2`)
proves a page exists but has no single numeric value, so a page-level `cite` fails
honestly. The box (PDF points, top-left origin, y down) verifies when it contains
exactly one printed number (`1,234`, `(56)`, `△8`, `78%` = 0.78 — values read as
written). **Never cite unconfirmed coordinates** — default to boxes shown by
`read_source` (or confirmed via a `locate_source` label, which echoes the box
text). Scanned pages read like any other PDF page after OCR, but they carry a
`machine-read (OCR, mean confidence ...)` disclosure. Before citing from an OCR
page, re-read the value and copy its box from `read_source` output, never from the
search snippet. Lines marked `[low-confidence]` deserve extra care before you cite.

**Hand-drawn boxes (fallback).** Use this only when the number has no annotation
or a copied box is refused. Open `view_source_page(model, source, page)` and read
the pt rulers. Estimate a tight `x,y,w,h` around the one printed number, including
its sign or percent. Confirm twice before citing: `view_source_page(..., box:"x,y,w,h")`
must show the red frame around exactly that number, and `locate_source(...,
position:"p<N>@x,y,w,h")` must echo exactly the same printed number. Then `cite`
the confirmed box; it gets the same exactly-one-number verification as any copied
box. Never carve a sign, percent, or parenthesis off a number to make a box verify —
if the value as printed (`△8`, `78 %`, `(56)`) will not verify with its marks
included, the marks were probably torn by the scan; write the value uncited and say
why. A bare-digit cite of a signed or percent value is a wrong number with a badge.
If no box can verify because the original is blurred or torn, write the value
uncited and say why.

**Provenance rules.** Ordinary edits may carry existing provenance forward or drop it,
but they cannot mint it. Only `cite` creates a new provenance ref. Copying a cited row
keeps the badge's meaning because it still points at the immutable archive; new facts
need their own cite.

## 6. Formulas, constants, and assertions — the literal rule

- A **formula cell cannot contain a `literal`** (`Formula`'s wall). A
  calculation's constants are **Settings constants** or **input cells**. Reference a
  constant with `intemporalRef` to its single-segment path:
  `{"kind":"intemporalRef","target":["TaxRate"]}`. The numbers 0 and 1 are the
  structural constants `{"kind":"zero"}` / `{"kind":"one"}`.
- An **assertion predicate MAY contain literals** — thresholds are evident data,
  like expected values in a test — and a number literal **declares its unit**
  (the same shape as an item's `unit`):
  `{"kind":"literal","value":{"kind":"number","value":"100000"},"unit":{"components":[{"baseUnit":"JPY","exponent":1}],"scaleExponent":0}}`.
  Comparisons are unit-checked (`TC2028`): a threshold on a JPY item is written
  `100000 JPY`, never a bare `100000`; a dimensionless ratio threshold (`1.2`)
  keeps an empty `unit`. A **unit-bearing zero is a literal** (`0 JPY`) — the
  bare `{"kind":"zero"}` is dimensionless and no longer type-checks against a
  unit-bearing item. (Stock vs flow is not judged against a literal, so a flow
  threshold needs no extra marking.)
- Predicate item references are **full canonical paths** (`[sheet, block, …, item]`;
  a single bare segment means a Settings constant). Inline `from`/`to` narrow the
  checked window (inclusive; a `null` end is open - `from` only checks from that
  period to the end, `to` only from the start of the timeline; both `null` = every
  period). A check is **one declared line = a parameterized test**: the predicate
  is the single assertion body and each period in the window is a case, reported
  `pass | fail | indeterminate`.

Three assertions worth declaring: a **balance check** (an exact `Compare(eq, …)`
between the two roots — `ΣAssets == ΣL&E` holds exactly in every period; see
`grammar("checks")` for the shape), a
**range check** (gross margin `0 < x < 1` — dimensionless, so bare `zero`/`one`
type-check), a **covenant** (forecast cash `>= 0 JPY` — the zero carries the
item's unit; windowed to the forecast with `from`).

**Green-bar discipline.** A model is not done when its structure is written - it is
done when its checks pass. The definition of finished: write the structure, declare
the checks (the balance check, the range checks, the covenants), then call
`read_checks(model)` and get `allGreen: true`. That is the model's unit-test green
bar. `fail` means a declared invariant is breached (the detail carries the
evaluated left/right values - read them before touching the model). An
`indeterminate` is **not** green: the predicate could not be evaluated (an
undetermined or errored cell underneath) - find the undetermined cell and supply or
derive it rather than shipping a model whose covenants never actually ran.

## 7. Type system — flow vs stock dimensions

The validator is **dimensionally typed** (a flow is `dStock/dt`). A formula on a
`flow`-declared line must compute a flow. `Building × DepRate` is **stock ×
dimensionless = stock** → `TC2029` if assigned to a flow line. Model a forecast
depreciation as a flat carry of the prior flow — a bare-name self-reference at
`lag 1` on the depreciation line's own series (§5) — or another flow-dimensioned
expression; never as a fraction of a stock.

## 8. KPI specifics

- **One root per KpiTree.** Several metrics → several KpiTree blocks.
- A leaf gets its value from an **input cell**, a **formula cell**, or a **binding** (a
  `target`/`reference` from a Series driver). Mixing temporal leaves with one
  **intemporal** leaf (e.g. `Months` = 12) in a `product` broadcasts fine.
- **`transform` sits on the child edge**, not the parent. `Retention = 1 − Churn`
  is a root `Retention` (operator `sum`) whose **child `Churn` carries
  `transform: "complement"`** — the child contributes `1 − Churn` upward. Putting
  `complement` on the root leaves the root's own value untransformed.
- **A node's operator is one primitive**: **multiplicative** (`price × count`,
  `operator: product`), **additive** (`existing + new − churn`, `operator: sum`; a subtracted
  child carries **`polarity: "negative"`** — a `sum` with a `negate` *transform* is rejected
  (`TC2046`) — while a `complement` transform gives `1 − rate`), or **transition-rate**
  (`population × rate%`, a `product` whose rate leaf is a per-period intensity and
  declares `stockFlow:"flow"` — **unless the same rate also rides a `complement`**:
  `Complement`/`Increment` require a dimensionless period-0 operand, so a `Churn` reused
  in `1 − Churn` is a factor and stays `stockFlow:null`; declare `"flow"` only for a
  pure stock-multiplier rate). One primitive per
  layer; every layer connects by arithmetic (a metric like NPS that doesn't wire
  arithmetically is a watched Series, not a tree node).

## 9. Verification — `diagnostics` is the gate

Every write-class call returns an ack carrying a `diagnostics` summary
(`{errors, warnings, total, delta, head, truncated}`), so the gate is
**diagnostics-first, per-write** — no separate whole-model call. Check:

1. **The summary's `total` is ZERO.** Not just errors and warnings — the pipeline
   can emit info-severity findings too, and a delivered model carries none of any
   severity. Mid-build diagnostics are
   expected while dependencies are pending (statements written before their
   roll-forwards land) — watch the summary's `delta` to see what each write broke
   or fixed, and pull `read_diagnostics` (filter by sheet path / severity / code)
   when the `head` isn't enough to act on. The finished model ships with zero
   diagnostics of any severity. Common error codes: `TC2001` (path doesn't resolve), `TC2013`
   (binding spec mismatch), `TC2029` (flow/stock dimension mismatch), `TC4003` (a
   cell couldn't evaluate — usually a cascade from one of the above). Hygiene
   warnings are defects too, not noise: `TC2024` (the balance doesn't close) and
   `TC2027` (a stock whose change is accounted nowhere) — a deliberately constant
   stock still needs its (zero) change referenced on the cash flow or a
   roll-forward. Check verdicts are NOT diagnostics: every write ack also carries
   a checks summary (`checks: { allGreen, failCount, indeterminateCount }`), and
   the per-check report is `read_checks`. A red check firing on real data is
   INFORMATION to report honestly to the user, never a finding to silence.
2. **Balance closes every period.** A declared balance assertion turns a break
   into a fail verdict — the ack's `checks.allGreen` goes false on the very write
   that broke it, so the per-write gate catches it. To inspect manually,
   `read_values(root/<bs-sheet>)` and compare the BS **totals**: read the asset-root
   and L&E-root derived totals at each period and confirm they're equal. Do **not**
   sum the leaves: supplied leaf input cells (cash, receivables, debt, …) are supplied cells, not
   derived `values`, so a leaf-sum would silently miss them.
3. **Nothing essential is blank.** A blank derived cell (in a sheet's `read_values`)
   means an equation is short of N-1 supply — find the missing input/binding.

Excel delivery is a UI action (the editor's export button) — not part of the agent loop.

## 10. Worked examples

The complete wire shape of every block kind — including a balance sheet with opening
cells and the roll-forward / `StockDelta` relations that wire a three-statement model —
is served by the `grammar` MCP tool. Read the relevant topics before authoring anything
non-trivial (`grammar()` lists them).
§1's authoring order applied to §1c's sheet layout is exactly how those pieces compose
into a full, balancing model with spelled-out names
(`["Financial Statements", "Profit And Loss", …]`, §3).

When public exemplar models are available on your host, prefer reading a real one
(`read_sheet` / `read_values` over this same MCP surface) to inventing structure —
a hosted exemplar always matches the current schema.

## 11. Rules of thumb (the ones that bite)

- **Group blocks onto 3–5 sheets; spell names out.** Put several related blocks on a
  sheet (`Financial Statements` = Balance Sheet + Profit And Loss + Cash Flow Statement),
  not one block per sheet. Use full Title-Case names everywhere — `Accounts Payable
  Rollforward`, not `ap_rf` (§1c). Order blocks with `reorder_blocks`; keep sheets directly
  under `root` (no folders) for a small model.
- **If sources exist, use the trust loop.** `list_sources` -> `get_source_overview`
  -> `search_source` -> `read_source` -> `cite` -> `verify_citations`. Every cite
  transcribes value + provenance together; to audit an existing value, read the raw
  cell (`read_sheet`) and the source, compare, then cite on match or report the
  discrepancy — input cells only, never over a formula (§5b). Cell positions come
  from `read_source`/`locate_source`, never from a guess.
- **Paths are `[sheet, block, …ancestors, item]`** (§3) — first segment the sheet, second
  the block (they differ once a sheet holds multiple blocks); the doubled `["pl","pl",…]`
  is only the flat convention. **Folders, if used, prepend to the path.** KPI leaves are deep
  (`["KPI Drivers","Bookings Tree","Bookings","Subscribers"]`).
- **Segment the P&L; go deep on the KPIs that run the business.** Decompose revenue into
  per-segment ProfitLoss rows where segments earn differently, and decompose each headline
  into a multi-level KpiTree (classify price, decompose quantity) — but only where the parts
  have different trajectories (§8).
- **Bound items' specs must match** (DataType/Unit/Temporality/StockFlow) — a
  Series driver's `stockFlow` mirrors its home (§5), or `TC2013`.
- **Formulas reject literals** — use Settings constants via `intemporalRef`, or
  `zero`/`one`. Predicates allow literals (§6).
- **Flow lines must compute flows** — no `stock × scalar` into a flow (§7).
- **`sum` needs a shared period dimension; a Settings constant has none** — you
  cannot `sum` a flow with an intemporal constant (`TC2028`). For an additive
  increment like `capex = D&A + $20M`, carry the $20M as a **flow-typed Series
  input line** and `sum` that line, not a constant. (`product` broadcasts a scalar
  fine; `sum` does not — §6.)
- **A balance assertion is an exact `eq`** — `ΣAssets == ΣL&E` holds exactly in
  every period, so compare the two roots directly (§6).
- **Valuation `fmItemRef` targets need a compiled cell** — a formula (`Formulas`)
  or a supplied input cell; the validator's target set is exactly
  `Formulas.Keys ∪ Inputs.Keys`, with no "presented" filter. A Series line that
  carries a cell qualifies (a flat WACC is simplest as a one-line Series input cell).
  What fails `TC2512` is a target with no cell at all: an untargeted/empty line, or
  a wrong path. A 1-node KpiTree also works but isn't required (§8).
- **KPI `transform` is on the child edge** (§8).
- **Measure points are cumulative** running totals down the flow chain.
- **Double-entry is structural** — wire every journal (coupling + target +
  conduits) and the BS closes itself (§4).
- **Flows have no boundary value** — only stocks carry opening cells at the boundary period.
- **Diagnostics-first** — each write-class call returns an ack with `diagnostics`;
  check it after every write, and pull numbers per sheet with `read_values` (§10).
- **Local edits, not full rewrites** — `write_sheet` for a new/whole sheet,
  `edit_block` (matched by `name`) to change one block, `reorder_blocks` for order;
  don't re-emit unchanged blocks (§1b). Pass the `etag` from `read_sheet` as
  `if_match` — a mismatch is `stale`, so re-read and retry. **No block rename.**
- **Number values serialize as strings** in JSON (`{"kind":"number","value":"100"}`).

<!-- distributed by Typecel plugin marketplace - 2026-07-19Z - channel marketplace - skill sha256:e7ffdc0bb01d | pass this whole comment as skill_stamp on your first methodology() call so the host can flag a stale copy -->
