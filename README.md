<p align="center"><img src="assets/logo.png" width="120" alt="Cutova"></p>

# Cutova for Claude

The MCP server for Epicor® Kinetic®. This plugin connects Claude to Cutova (`https://server.cutova.ai/mcp`) so you can explore revenue, receivables, cash and backlog, and build BAQs, Epicor Functions and Kinetic apps.

## Structure

```
cutova-plugin/
├── .claude-plugin/
│   └── plugin.json   # manifest, icon and listing links
├── .mcp.json         # Cutova MCP server
├── assets/
│   └── logo.png      # plugin icon
└── README.md
```

## Install

Claude Code, from a local checkout:

```
/plugin install ./cutova-plugin
```

On first use, Claude prompts you to sign in to Cutova. An Epicor administrator must connect your Epicor instance first; see [Get started](https://cutova.ai/get-started).

## Links

- [Docs: connect Claude](https://cutova.ai/docs/connect/claude/)
- [Pricing](https://cutova.ai/pricing) · [Security](https://cutova.ai/security) · [Privacy](https://cutova.ai/privacy) · [Terms](https://cutova.ai/terms)
- Contact: hello@cutova.ai

---

Epicor® and Kinetic® are trademarks of Epicor Software Corporation. Cutova is an independent product and is not affiliated with, endorsed by, or sponsored by Epicor Software Corporation.
