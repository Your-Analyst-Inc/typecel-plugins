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

## Updates

The skill content is published here automatically from the Typecel source repository whenever it
changes; every synced commit is a new plugin version. Auto-update for third-party marketplaces is
off by default in Claude Code - turn it on for this marketplace in `/plugin` → Marketplaces, or pull
manually:

```
/plugin marketplace update typecel
/plugin update typecel-modeling@typecel
```

If you are not using Claude Code, the same skill is also served as a zip by any Typecel host at
`GET /skills/typecel-modeling.zip`, ready for upload to claude.ai or ChatGPT.

## Contributing

`plugins/typecel-modeling/skills/typecel-modeling/SKILL.md` is generated - it is synced from the
Typecel source repository by CI, and the trailing HTML comment is a distribution stamp added during
sync. Do not edit it here; changes land upstream.
