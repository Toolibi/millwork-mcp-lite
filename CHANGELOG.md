# Changelog

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
