# millwork-mcp-lite

[![CI](https://github.com/Toolibi/millwork-mcp-lite/actions/workflows/ci.yml/badge.svg)](https://github.com/Toolibi/millwork-mcp-lite/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Toolibi/millwork-mcp-lite MCP server](https://glama.ai/mcp/servers/Toolibi/millwork-mcp-lite/badges/score.svg)](https://glama.ai/mcp/servers/Toolibi/millwork-mcp-lite)

**A free, open-source MCP server that gives an AI assistant basic cabinet-shop tools: schedule review, frameless cut lists and panel-saw sheet nesting.**

Ask Claude, ChatGPT, Copilot or any MCP client *"here's my kitchen, how many sheets of melamine do I need?"* and it calls real code to get the answer, instead of guessing.

Built by a 20-year cabinet/millwork CNC programmer. This is the free edition of [**millwork-mcp**](https://github.com/Toolibi/millwork-mcp), which takes cabinet drawings all the way to CNC-ready nests ([see the demos](https://github.com/Toolibi/millwork-mcp#demos)).

## Tools

All tools are read-only and deterministic: they compute from the job you pass in and never write files or touch a machine.

| Tool | What it does |
|---|---|
| `review_cabinet_schedule` | Flags duplicate tags, unknown cabinet types, odd sizes, doors that are too wide, shelves in sink bases |
| `build_cutlist` | Sides, bottoms, tops or rails, shelves, backs, doors and drawer fronts, with edgebanding and square footage per material |
| `sheet_count` | Quick takeoff: sheets needed for every material in the job |
| `nest_sheets` | Strip-cut (guillotine) nesting for a panel saw: sheets needed, yield, and where each part goes |
| `edgeband_takeoff` | Linear feet of edgebanding per material, with a waste allowance |
| `list_cabinet_types` | Cabinet types, typical sizes and an example job, for turning drawings into a schedule |
| `about` | What this server does and what the full version adds |

Also included: a `plan_cabinet_job` prompt that walks an AI from a plain-language description to a material order, and two resources (`millwork://examples/small-kitchen`, `millwork://reference/construction`).

**Typical flow:** `review_cabinet_schedule` → `build_cutlist` → `sheet_count` / `nest_sheets` → `edgeband_takeoff`

All dimensions are inches. Construction follows generic frameless (European-style) defaults: full-height sides, bottom between the sides, two 4" top rails on base cabinets, an applied 1/4" back, and full-overlay fronts with a 1/16" reveal.

## Quick start

```bash
pip install -r requirements.txt
python -m millwork_mcp_lite.server        # stdio MCP server
python -m pytest -q                       # 11 tests
```

### Claude Desktop, Cursor, VS Code

No clone needed if you have [uv](https://docs.astral.sh/uv/):

```json
{
  "mcpServers": {
    "millwork-lite": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/Toolibi/millwork-mcp-lite", "millwork-mcp-lite"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add millwork-lite -- uvx --from git+https://github.com/Toolibi/millwork-mcp-lite millwork-mcp-lite
```

### Docker

```bash
docker build -t millwork-mcp-lite .
docker run -i --rm millwork-mcp-lite
```

### Example job

```json
{
  "job_number": "K-101",
  "case_material": "MEL-WHT-34",
  "back_material": "MEL-WHT-14",
  "front_material": "MEL-WHT-34",
  "cabinets": [
    {"tag": "B1", "type": "base", "width": 24, "height": 34.5, "depth": 24, "doors": 1, "drawers": 1, "adj_shelves": 1},
    {"tag": "W1", "type": "wall", "width": 30, "height": 30, "depth": 12, "doors": 2, "adj_shelves": 2}
  ]
}
```

Cabinet types: `base`, `drawer_base`, `sink_base`, `wall`, `tall`. A fuller sample is in [`examples/small_kitchen.json`](examples/small_kitchen.json): 8 cabinets come out to 9 sheets of 3/4" melamine and 3 sheets of 1/4" back.

## Lite vs. full

| | **lite** (this repo, MIT) | [**millwork-mcp**](https://github.com/Toolibi/millwork-mcp) |
|---|---|---|
| Schedule review | Basic checks | Plus material codes vs. price list, oversized doors, shop rules |
| Cut list | Generic frameless box | Configurable shop construction standard, finished ends, pre-lam, nailers |
| Joinery | - | 32mm system: dowel, confirmat, cam & dowel, Lamello Clamex |
| Grain matching | - | Doors and drawer fronts nested as matched blanks |
| Nesting | Panel-saw strip packing | Nested-router MaxRects (grain-locked, multi-start) or two-stage panel saw, sheet-size comparison |
| CNC output | - | woodWOP-ready DXF per sheet with machining layers, CNC program lists |
| Estimating | Sheet counts and edgeband takeoff | Material from the real nest + hardware + labor + markup |
| Inventory | - | Stock, offcuts, reserve → cut → consume |
| Hosting | Local (stdio) | Local or hosted on Azure / Microsoft Foundry, with approval on every shop-floor step |

Shops interested in the full version or a pilot: **Contact@princeboafo.com**

## Safety

Nothing here talks to a machine. Outputs are lists for a person to check before anything is cut.

## License

[MIT](LICENSE) © 2026 Prince Boafo. The full millwork-mcp is a separate project under its own license.
