# Typecel plugins

Claude Code plugin marketplace for [Typecel Studio](https://app.typecel.io), a financial-modelling
environment your coding agent edits through an MCP server. The one plugin here, **typecel-modeling**,
carries the agent skill that teaches Claude how to author Typecel models: the declarative language's
mental model, the virtual-filesystem editing surface, and the source-citation trust loop.

## Install

```
/plugin marketplace add Your-Analyst-Inc/typecel-plugins
/plugin install typecel-modeling@typecel
```

The skill triggers automatically whenever you ask Claude to build or change a financial model
against a connected Typecel Studio MCP server.

Codex CLI users can install from the same repository:

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

If you are not using Claude Code, the same skill is also served as a zip by any Typecel host at
`GET /skills/typecel-modeling.zip`, ready for upload to claude.ai or ChatGPT.

## Support and privacy

Support: [support@typecel.io](mailto:support@typecel.io). The skill drives the Typecel Studio
service; its privacy policy is at
[app.typecel.io/legal/privacy.html](https://app.typecel.io/legal/privacy.html).

## Contributing

`plugins/typecel-modeling/skills/typecel-modeling/SKILL.md` is generated - CI (`sync-skill.yml`)
pulls it from the production host and appends the trailing distribution-stamp comment. Do not edit
it here; changes land in the Typecel source repository and arrive with the next deploy.
