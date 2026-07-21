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
edit it the way a coding agent edits a repo, and the pipeline
re-validates/compiles/evaluates the whole model on every write.

This skill is the **mechanics + the mental model**. Everything volatile lives on
the host and is served live: the exact per-kind JSON wire shapes by the
**`grammar` MCP tool**, the modeling doctrine by the **`methodology` MCP tool**,
and each tool's own contract (arguments, budgets, ack shapes) by its description.

**Orient first — before your first write, call `methodology()` and `grammar()`**:
the index first, then the topics matching the task. `grammar` answers how to
write the JSON, `methodology` answers what to build. Both serve the RUNNING
host, so what you read always matches the schema the host accepts — never guess
a shape, and call `grammar("common-mistakes")` when a write is rejected.
**Scale the orientation to the task**: building from scratch warrants the full
sweep, but when you are editing an existing model (or extending a provided
skeleton), read only the topics for the block kinds you will touch — the
model in front of you already shows the shapes, and every unread topic is
context you keep.

## 1. The surface — a virtual filesystem

The model is a `settings` doc plus a `root` tree of **folders** and **sheets**,
where each **sheet holds an ordered list of blocks**. Every model-scoped call
takes `model`, a locator of the form `{handle}/{name}` obtained from
`create_model` or `list_models`.

The tools name **what they target**. **Node** ops (`create_folder` /
`create_sheet` / `ls` and the rename/move/delete/reorder family) take a path that
*is* the target. **Content** ops (block = inside a sheet) take the sheet path
plus the block **name** and carry a `_block(s)` suffix. Reads are `read_sheet` /
`read_values` / `read_settings` / `read_checks` / `read_diagnostics`; the source
and citation tools are the trust loop (§6). Each tool's own description carries
its contract — read it rather than guessing.

```
settings                      → SettingsSpec   (top, outside root — the model's <head>)
root                          → the tree's top; ls it to list folders + sheets
root/<sheet>                  → a sheet sitting directly under root
root/<folder>/…/<sheet>       → a sheet nested under one or more folders
```

- The only separator is `/`; a `.` is just a name character. `settings` lives
  outside `root`, so `root` contains only the user's folders and sheets.
- **Structure ≠ content.** `create_folder` / `create_sheet` make the node;
  `write_sheet` / `add_block` fill it. Writing to a path that doesn't exist is
  an error (no ghost sheets). A flat model needs no folders at all.
- Structured arguments — sheet content, block bodies, `cite` cells — are
  **native JSON**: pass the document itself, never a string containing it. A
  line's `cells` is a period-keyed map; `read_sheet` returns the same shape you
  write — `grammar("inputs")` / `grammar("formulas")` for the entries.

**Diagnostics-first.** Every write-class call returns a small ack carrying an
`etag` and a `diagnostics` **summary**
(`{errors, warnings, total, delta:{appeared,resolved}, head, truncated}`) plus a
checks summary (`checks: {allGreen, failCount, indeterminateCount}`) — never the
whole evaluated model. The counts are the gate and `delta` tells you what THIS
write broke or fixed; pull `read_diagnostics` (filter by sheet path / severity /
code) when the head isn't enough, and inspect computed numbers per sheet with
`read_values` — sparingly: it is the largest read on the surface (every cell of
a sheet, evaluated), so let acks and `read_checks` answer "is it right?" and
reach for `read_values` only when you need the numbers themselves.

> **Legacy flat hosts.** If `ls(model, "")` returns the bare field names
> `["settings","bindings","assertions","model"]` instead of typed `{name, kind}`
> entries, you are on an older flat surface: one `write(model, path, json)` tool
> replaces the ops above — `settings` creates/updates the model, `model/<sheet>`
> upserts a single block (one block per sheet, no folders) — and evaluated reads
> are `get_evaluated`. The block JSON and the solver's rules are identical; only
> the call shape differs.

## 2. Authoring order

Before choosing the model's structure, read the `methodology()` topics matching
the task. Then build in this order — later slices reference earlier ones:

```
1. create_model            → get a locator (or list_models to find an existing one)
2. write_settings          → time axis + currency + constants — grammar("settings")
3. write_sheet root/<s>    → each sheet's whole blocks[] in display order, sheets in
                             dependency order — stocks before the statements that read
                             them (which sheets, and what goes on them:
                             methodology("model-architecture"))
4. (cross-block wiring)    → authored ON the lines as `relation` fields inside step 3's
                             blocks — there is NO separate bindings step — grammar("relations")
5. write the checks block  → balance, ranges, covenants — grammar("checks")
6. read_checks/read_values → verify; the write acks already carried diagnostics
```

Author blocks in dependency order (a line's `relation` references items that must
already resolve), and check each ack's counts and `delta` as you go.

## 3. The editing model — write whole, edit local

- **`write_sheet` = Write** — author a new sheet or restructure one wholesale;
  the `blocks` array order **is** the display order.
- **`add_block` / `edit_block` = Edit** — once a sheet exists, emit ONLY the
  block you're changing; the tool preserves the rest. Never re-emit unchanged
  blocks — that wholesale-rewrite habit is what causes drift.
- **`reorder_blocks`** — a names-only permutation, no bodies.

**Read before you edit.** `read_sheet` returns each block's `etag` plus the
sheet `etag`; pass the one you read as `if_match` (block etag for
`edit_block`/`remove_block`, sheet etag for `write_sheet`/`reorder_blocks`). The
etag is a stateless content hash — a mismatch means the content changed under
you (`stale`): re-read and retry.

There is **no block rename** — a block's name is the root of every reference to
it; to rename, restructure the sheet with `write_sheet` and fix the references.
Sheet and folder names appear in item paths (§4), so a rename or move shifts the
path of every item underneath — the ack surfaces the dangling references (TC2001)
for you to fix. Settle the layout and names **up front**, before authoring
relations and formulas. Re-ordering is path-safe.

## 4. Item paths — `[sheet, block, …ancestors, item]`

Every relation target, formula reference, and check predicate addresses an item
by its **canonical path**: `[…folders, sheet, block, …item-ancestors, item]`.
With sheets directly under `root` (the recommended layout for a small model) the
first segment is the **sheet** and the second the **block**; a folder, if
present, prepends its segment(s) ahead of the sheet — moving a sheet into a
folder shifts every path under it.

- The path includes the **full ancestor chain** inside the block (BS parent →
  leaf, P&L subtotal → child, KPI root → … → leaf). Get it wrong and you get
  `TC2001 — formula references an item that does not resolve`.
- A single-segment path (`["TaxRate"]`) reaches a Settings constant.
- The `grammar` topics use short flat tokens for density, so you'll see doubled
  paths like `["pl","pl",…]` there — that is the one-block-per-sheet convention
  where sheet and block names coincide. With several blocks per sheet the path
  reads naturally: `["Financial Statements","Profit And Loss","Revenue"]`.
- **Formulas write the shortest form that resolves** — a bare name for a sibling
  in the same block, `block.item` for a sibling block on the same sheet
  (`grammar("expressions")` has the ladder). **A formula never crosses a sheet**:
  compute beside your inputs and let results travel by relations. **Relations
  and check predicates take full canonical paths.**
- **Name legality**: names may contain spaces, capitals, `&`, and parentheses,
  but not `/`, `\`, `[`, `]`, control characters, or leading/trailing
  whitespace, and not a bare `.` or `..`. Spell names out in Title Case —
  `Balance Sheet`, never `bs` — the names ARE the path segments every reference
  is written in (`methodology("naming")`).

## 5. The mental model — blocks on one equation graph

Each block kind contributes equations to a single graph:

- **balanceSheet** — debit/credit trees of **stock** leaves; self-contained —
  `grammar("balance-sheet")`
- **profitLoss / cashFlow** — flow chains: sections of rows plus optional
  measure lines; **measures are cumulative running totals**, so the last CF
  measure is the total net change in cash — `grammar("profit-loss")` /
  `grammar("cash-flow")`
- **rollForward** — one stock + its flows: `Stock[t] = Stock[t-1] + Σ flows` —
  `grammar("roll-forward")`
- **kpiTree** — a decomposition `target = operator(children)`; one root per
  tree — `grammar("kpi-tree")`, `methodology("kpi-decomposition")`
- **series** — structure-free trajectory lines (input and/or formula cells);
  the home of drivers, assumptions, and actuals — `grammar("series")`
- **checks** — declared predicates over evaluated values; the model's unit
  tests — `grammar("checks")`

The equations are **undirected**. You supply enough values that each equation
can close (**N-1 rule**: an equation with N variables needs N-1 supplied) and
the solver derives the rest — which direction a formula-free identity computes
follows from what you supply.

**Cross-block wiring rides ON the lines** as inline `relation` fields —
`connection` (a same-value mirror whose accounting role is derived, never
declared), `stockDelta`, and `linkage` (the ratio identity `a = this × b`) —
`grammar("relations")` for the shapes and the classic-role mapping.
**Double-entry is structural**: wire every journal and the balance sheet closes
in every period by construction — balance is an outcome, never a target
(`methodology("three-statement-wiring")`).

Lay the model out in the three-layer sheet convention — statements, then
calculations, then assumptions, then historical data, one concern per block —
`methodology("model-architecture")`.

## 6. Actuals vs forecast — two eras, one structure

History and projection are **two eras over one period-independent structure**:
a historical series supplies the actual periods (records, wired to the
statements by connections), forecast drivers supply the forecast periods, and no
`(line, period)` is supplied twice. The identity is authored once, as structure,
and runs in both directions — on actuals the records derive the drivers (a
ratio's actual cells stay EMPTY; the identity reads it off the books), on the
forecast the carried-forward drivers compute the outcomes. The canon is
`methodology("actuals-and-forecast")` with `methodology("formulas-and-relations")`
(where computation lives, rate time-dimensions) and the routing shapes in
`grammar("relations")` / `grammar("series")` — read them before wiring.

**Scenarios are one active case at a time.** You cannot stack competing scenario
Series over the same forecast cells — two Series may target one item only over
**disjoint periods** (that is the actuals/forecast split, not rival cases), so
overlapping overrides over-determine the cell. Vary the easy-to-change levers
(headcount, conversion, the price you set) between case copies; the
hard-to-change drivers (FX, commodity, market size) stay put and go on a
sensitivity sweep instead.

## 7. Source transcription — the trust loop

When archived sources exist, transcription goes through the trust loop. **Never
retype a number you can read from an archived source without citing it** — the
value and its provenance land together (`cite` is a transcription; only `cite`
mints provenance, ordinary edits can carry it forward or drop it but never
create it).

```
list_sources -> get_source_overview -> search_source -> read_source -> cite -> verify_citations
```

The tools' own descriptions carry the mechanics (name vs id addressing, capture
budgets, batch `cells`, receipts). The doctrine:

- **Prefer official sources.** Capture the primary document — the company's IR
  page, the regulatory filing — over news articles or aggregators. A secondary
  source is a disclosed fallback: say what you used and why the primary wasn't
  available.
- **One filing rarely covers the whole actual era.** An annual filing prints
  comparatives for TWO fiscal years (a Japanese annual securities report shows
  the year and its prior), so count backward from what the model needs: three
  actual years plus an opening balance reach back one year further than the
  latest two filings cover — capture as many prior-year filings as it takes to
  reach the opening (or another source that carries it), and plan the captures
  before transcribing, not when the earliest year comes up empty.
- **A new edition of a document is a new source.** Capture the Q2 databook under
  its own name next to Q1, never replace it — sources are immutable archives and
  existing citations keep pointing at the edition they verified against.
  Renaming is always safe (citations anchor to the id); deleting a cited source
  is deliberate — the tool refuses with the citation count until you echo it
  back, and the surviving citations turning `unreadable` afterward is the system
  being honest, not an error to route around.
- **Address discipline.** Cite positions come from `read_source` /
  `locate_source` output, copied verbatim — never guessed from memory or a
  plausible layout. Search is hybrid — use the business term naturally, in
  Japanese or English, when the workbook mixes languages — and tells you the
  row; read the neighborhood to see the column.
- **PDF citations.** Copy the `[x,y,w,h]` annotation printed on the number in
  `read_source` output and cite `p<N>@x,y,w,h` — a page-level position (`p2`)
  proves a page exists but holds no single number, so a page-level `cite` fails
  honestly. A box verifies when it contains
  exactly one printed number **as printed** — sign, percent, or parentheses
  included; never carve marks off to make a box verify. Japanese filings print
  negatives as a leading triangle (`△6,508`): the box encloses the triangle,
  and the transcription stores the value as printed. Verification accepts
  either sign — a source's sign is display convention; the model's own sign
  system (row polarity, debit/credit) owns the business sign — so the badge
  cannot catch a double-applied sign. After citing a triangle figure, check
  the CONTRIBUTION: a negative value on a row whose polarity also negates is
  the classic double flip, and it wears a green badge while adding what
  should subtract. Hand-drawn boxes (via
  `view_source_page`) are the fallback: confirm twice — the framed page image
  and a `locate_source` echo — before citing. Re-read OCR pages and take their
  confidence disclosures seriously. If no box can verify, write the value
  uncited and say why — a bare-digit cite of a signed value is a wrong number
  with a badge.
- **Auditing an existing value is a composition, not a mode**: read the RAW cell
  with `read_sheet` (not `read_values` — the evaluated view can make a formula's
  result look like an input), read the source, compare them yourself — on a
  match, cite (the value gains provenance); on a discrepancy, report it instead
  of citing. **Input cells only**: citing an address held by a formula cell
  replaces the formula with a transcribed input. A receipt with a non-null
  `replaced` displaced a different existing number — surface it, never silence
  it.
- **Notes are orientation, never evidence** (`write_source_note`): always
  re-read and confirm before citing.
- **Finish with `verify_citations`** and expect every cited cell `verified`. A
  `mismatch` means the model value was edited after its mint; an
  unreadable/could-not-verify failure is the system being honest about the
  source read — fix the position, never work around it by writing an uncited
  value.

## 8. Green-bar discipline — done means zero diagnostics and green checks

A model is not done when its structure is written — it is done when it ships
with **zero diagnostics of any severity** (info included) and its declared
checks pass. `methodology("verification")` is the canon: mid-build diagnostics
are the normal cost of dependency-ordered authoring, the hygiene warnings
(TC2024 — balance doesn't close; TC2027 — a stock's movement accounted nowhere)
are wiring TODOs, and a red check firing on real data is INFORMATION to report
honestly, never a finding to silence. Common error codes to recognize: TC2001
(path doesn't resolve), TC2013 (relation endpoint specs mismatch), TC2029
(flow/stock dimension mismatch), TC4003 (a cell couldn't evaluate — usually a
cascade from one of the above).

- Declare the three checks worth having — the exact balance check
  (`ΣAssets == ΣL&E`, an exact `eq` between the two roots), a range check, a
  covenant — `grammar("checks")` for the shapes, then `read_checks` and get
  `allGreen: true`. That is the model's green bar. An `indeterminate` is NOT
  green: the predicate could not evaluate — find the undetermined cell and
  supply or derive it.
- Inspecting balance manually: compare the two BS **root totals** per period via
  `read_values`. Do NOT sum the leaves — supplied leaf input cells are not
  derived values, so a leaf-sum silently misses them.
- **Nothing essential is blank.** A blank derived cell means an equation is
  short of N-1 supply — find the missing input or relation.
- Excel delivery is a UI action (the editor's export button) — not part of the
  agent loop.

When public exemplar models are available on your host, prefer reading a real
one (`read_sheet` / `read_values` over this same MCP surface) to inventing
structure — a hosted exemplar always matches the current schema.

## 9. Rules of thumb (the ones that bite)

The `grammar` and `methodology` topics carry the full rulebook; these are the
traps no topic states:

- **A `sum` node cannot take a `negate` transform** — a subtracted KPI child
  carries `polarity: "negative"` (TC2046). The `complement` transform is the
  `1 − x` form.
- **`Complement`/`Increment` require a dimensionless operand** — a rate reused
  in `1 − Churn` is a factor and stays `stockFlow: null`, even where a pure
  stock-multiplier rate would declare `"flow"`.
- **Flows have no boundary value** — only stocks carry opening cells at the
  boundary period.
- **Forecast depreciation is a flat carry of the prior flow** (a bare self-ref
  at lag 1), never a fraction of a stock — `Building × DepRate` is stock ×
  dimensionless = stock, rejected on a flow line (TC2029).
- **A metric that doesn't wire arithmetically** (NPS, a satisfaction score) is a
  watched Series line, not a KPI tree node — every tree layer connects by
  arithmetic.

<!-- distributed by Typecel plugin marketplace - 2026-07-21Z - channel marketplace - skill sha256:abc8a4eae71b | pass this whole comment as skill_stamp on your first methodology() call so the host can flag a stale copy -->
