# Changelog

## 0.2.0 - 2026-11-19
- New tools: `edgeband_takeoff` (linear feet per material with waste) and `list_cabinet_types` (reference sizes and an example job).
- Typed job input: every field now has a description, units and allowed values in the tool schema.
- Every tool is annotated read-only, idempotent and non-destructive.
- Fuller tool descriptions: when to use each tool, parameters, return fields and an example.
- Added an MCP prompt (`plan_cabinet_job`) and two resources (sample kitchen, construction defaults).
- CI on Python 3.10, 3.12 and 3.13.

## 0.1.0 - 2026-11-18
- First release: schedule review, frameless cut list, panel-saw strip nesting, sheet counts.
