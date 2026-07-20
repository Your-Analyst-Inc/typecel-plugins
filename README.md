# Typecel plugins

Claude Code plugin marketplace for [Typecel Studio](https://app.typecel.io), a financial-modelling
environment your coding agent edits through an MCP server. The one plugin here, **typecel-modeling**,
carries both halves of the integration: the agent skill that teaches Claude how to author Typecel
models (the declarative language's mental model, the virtual-filesystem editing surface, the
source-citation trust loop), and the **Typecel Studio MCP server connection** (`typecel-studio`,
bundled via `.mcp.json`) - installing the plugin wires the connector too.

## Install

```
/plugin marketplace add Your-Analyst-Inc/typecel-plugins
/plugin install typecel-modeling@typecel
```

Then authenticate the bundled `typecel-studio` server once via `/mcp` (OAuth - sign in with your
Typecel account; the token is stored and refreshed automatically). The skill triggers automatically
whenever you ask Claude to build or change a financial model.

Codex CLI users install from the same repository; the skill declares the MCP server as a
dependency, so Codex offers to install and authenticate it when the skill first runs
(`codex mcp login typecel-studio` does it explicitly):

```
codex plugin marketplace add Your-Analyst-Inc/typecel-plugins
codex plugin add typecel-modeling@typecel
```

## Example prompts

- "Using the typecel-modeling skill, build a three-statement model (P&L, balance sheet, cash flow)
  for a subscription software company with two revenue segments, quarterly from FY2024 through
  FY2027. Orient before your first write: call methodology() and grammar() first."
- "Using the typecel-modeling skill, open my existing model and capture the latest results
  presentation from the company's IR page, transcribe the full-year actuals into the historical
  sheets with citations, then verify the citations."
- "Using the typecel-modeling skill, add working-capital roll-forwards (receivables, payables,
  inventory) to my model, declare a balance check and a minimum-cash covenant over the forecast,
  then read the checks and report the verdicts."

## Updates

The skill content is synced here daily by CI from the production host's public skill endpoint
(`GET /skills`), so it always matches what deployed hosts accept; every synced commit is a new
plugin version. Auto-update for third-party marketplaces is
off by default in Claude Code - turn it on for this marketplace in `/plugin` → Marketplaces, or pull
manually:

```
/plugin marketplace update typecel
/plugin update typecel-modeling@typecel
```

On claude.ai (paid plans), you can sync this marketplace from Customize > Plugins > Add
marketplace - the skill then works in web chat. The bundled MCP server does not carry to the web
surface: connect Typecel there once as a connector (`https://app.typecel.io/api/mcp`).

If you are using neither Claude Code nor a synced marketplace, the same skill is also served as a
zip by any Typecel host at `GET /skills/typecel-modeling.zip`, ready for upload to claude.ai or
ChatGPT.

## Support and privacy

Support: [support@typecel.io](mailto:support@typecel.io). The skill drives the Typecel Studio
service; its privacy policy is at
[app.typecel.io/legal/privacy.html](https://app.typecel.io/legal/privacy.html).

## Contributing

`plugins/typecel-modeling/skills/typecel-modeling/SKILL.md` is generated - CI (`sync-skill.yml`)
pulls it from the production host and appends the trailing distribution-stamp comment. Do not edit
it here; changes land in the Typecel source repository and arrive with the next deploy. The
`.mcp.json` server bundle and the skill's `agents/openai.yaml` dependency sidecar are maintained
in this repository directly.
