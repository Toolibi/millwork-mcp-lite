# Changelog

## 0.5.0 - 2026-11-19
- New `stock_offcuts` input on `nest_sheets` and `count_sheets`: pass leftover pieces on hand (material, length, width, optional id/rack location) and they are filled first, largest first, before any fresh sheet is opened. Results report which pieces were used, the parts placed on each, `parts_on_offcuts`, `sheets_without_offcuts` and `sheets_saved`.
- Offcuts returned by `nest_sheets` now carry `material` and an `id`, so an agent can pass one job's leftovers straight into the next job. Lite stays stateless: the agent carries the rack between calls.
- Closes the loop suggested on r/mcp: leftovers with an x/y position, then reused before cutting into a fresh sheet.

## 0.4.0 - 2026-11-19
- `nest_sheets` now hands back leftover material as usable offcuts: real rectangles (length, width, x, y) at least `min_offcut` on both sides, each freeable with guillotine cuts, listed largest first. An agent can plan the next job around them instead of seeing only a waste percentage. Thanks to the r/mcp commenter who suggested it.
- New `min_offcut` parameter (default 12").
- `count_sheets` adds `usable_offcuts` and `offcut_square_feet` per material.

## 0.3.1 - 2026-11-19
- Fixed two tool-description typos introduced by the 0.3.0 rename.

## 0.3.0 - 2026-11-19
- Consistent verb-first tool names: `sheet_count` is now `count_sheets`, `edgeband_takeoff` is now `calculate_edgeband`, `about` is now `get_server_info`.
- `calculate_edgeband` description now spells out which edges are counted, the error behaviour and an example result.

## 0.2.0 - 2026-11-19
- New tools: `edgeband_takeoff` (linear feet per material with waste) and `list_cabinet_types` (reference sizes and an example job).
- Typed job input: every field now has a description, units and allowed values in the tool schema.
- Every tool is annotated read-only, idempotent and non-destructive.
- Fuller tool descriptions: when to use each tool, parameters, return fields and an example.
- Added an MCP prompt (`plan_cabinet_job`) and two resources (sample kitchen, construction defaults).
- CI on Python 3.10, 3.12 and 3.13.

## 0.1.0 - 2026-11-18
- First release: schedule review, frameless cut list, panel-saw strip nesting, sheet counts.
