"""millwork-mcp-lite: a small, open-source MCP server for cabinet cut lists and sheet nesting.

Run:  millwork-mcp-lite        (or: python -m millwork_mcp_lite.server)   stdio transport

This is the free, MIT-licensed edition. The full millwork-mcp adds nested-router (CNC)
nesting, woodWOP-ready DXF machining output, 32mm-system joinery, grain matching,
estimating and inventory: https://github.com/Toolibi/millwork-mcp
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from . import cutlist as cl
from .models import CABINET_TYPES, Job
from .nesting import nest
from .review import review_job
from .schemas import JobIn

FULL_VERSION = "https://github.com/Toolibi/millwork-mcp"
EXAMPLE_PATH = Path(__file__).parent / "small_kitchen.json"

mcp = FastMCP(
    "millwork-mcp-lite",
    instructions=(
        "Cabinet-shop calculator for frameless (European-style) casework. Typical flow: "
        "review_cabinet_schedule -> build_cutlist -> count_sheets or nest_sheets -> calculate_edgeband. "
        "All dimensions are inches. Every tool is read-only and deterministic: it computes from the "
        "job you pass in and never writes files or contacts a machine. Use list_cabinet_types first "
        "if you are unsure how to describe a cabinet."
    ),
)

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)


def _job(job: JobIn) -> Job:
    return Job.from_dict(job.model_dump())


def _blocked(review: dict) -> dict:
    return {"error": "The schedule has errors. Fix the cabinets listed in review.issues and call again.",
            "review": review}


JobArg = Annotated[JobIn, Field(description="The cabinet job: job_number, material codes and the cabinets list (inches).")]


@mcp.tool(
    title="Review cabinet schedule",
    annotations=READ_ONLY,
    description=(
        "Check a cabinet schedule for mistakes before anything is calculated or cut.\n\n"
        "Use this first on any schedule read from drawings or typed by a person. It does not build parts; "
        "use build_cutlist for that (build_cutlist also runs this review and refuses to continue on errors).\n\n"
        "Checks: duplicate tags, unknown cabinet types, non-positive sizes, widths outside 9-48\", single doors "
        "wider than 24\", drawer bases with no drawers, shelves in sink bases, unusual base heights (not 30-36\") "
        "and deep wall cabinets (over 16\").\n\n"
        "Returns: {job_number, ok (true when there are no errors), errors (count), warnings (count), "
        "issues: [{level: \"error\"|\"warning\", cabinet: tag, message}]}. Errors block the cut list; warnings "
        "need a person to confirm.\n\n"
        'Example: {"job": {"job_number": "K-101", "cabinets": [{"tag": "B1", "type": "base", "width": 36, '
        '"height": 34.5, "depth": 24, "doors": 1}]}} -> ok=true with one warning that the single door would be get_server_info 36" wide.'
    ),
)
def review_cabinet_schedule(job: JobArg) -> dict:
    return review_job(_job(job))


@mcp.tool(
    title="Build cut list",
    annotations=READ_ONLY,
    description=(
        "Turn a cabinet schedule into a part-by-part cut list for frameless cabinets.\n\n"
        "Use when someone needs the parts to cut, a parts count, or square footage per material. For sheet "
        "counts use count_sheets; for sheet layouts use nest_sheets; for edgebanding length use calculate_edgeband.\n\n"
        "Construction (generic defaults): full-height sides; bottom between the sides; two 4\" top rails on "
        "base, drawer_base and sink_base, a full top on wall and tall; adjustable shelves 1/16\" narrower than "
        "the opening and 1\" plus the back thickness shallower than the box; an applied back, full width x full "
        "height; full-overlay doors and drawer fronts with a 1/16\" reveal. Runs review_cabinet_schedule first "
        "and returns {error, review} instead of parts if the schedule has errors.\n\n"
        "Returns: {job_number, summary: {total_pieces, by_material: {code: {pieces, square_feet}}}, "
        "parts: [{cabinet, name, material, length, width, qty, edgeband (\"front\"|\"all\"|\"\"), notes}], review}. "
        "length is the long/grain direction; all sizes are finished inches.\n\n"
        'Example: a 24" base with 1 door and 1 shelf gives 2 sides 34.5x24, a bottom 22.5x24, 2 top rails '
        '22.5x4, a shelf 22.4375x22.75, a back 34.5x24 and a door 34.375x23.875.'
    ),
)
def build_cutlist(job: JobArg) -> dict:
    j = _job(job)
    review = review_job(j)
    if not review["ok"]:
        return _blocked(review)
    parts = cl.build_cutlist(j)
    return {"job_number": j.job_number, "summary": cl.summarize(parts),
            "parts": [p.to_dict() for p in parts], "review": review}


@mcp.tool(
    title="Nest sheets for a panel saw",
    annotations=READ_ONLY,
    description=(
        "Lay out one material's parts on full sheets for a panel saw and report the cutting plan.\n\n"
        "Use when someone needs the actual sheet layouts (which part goes where). For just the number of sheets "
        "across every material, count_sheets is faster. The layout is strip-cut and guillotine-safe: each sheet is "
        "ripped into strips across its width, then parts are crosscut from each strip. Parts keep their listed "
        "grain direction (length runs along the sheet). 1/4\" is trimmed off each sheet edge. Not for CNC routers.\n\n"
        "Parameters: material is a material code from the job (defaults to case_material); sheet_length and "
        "sheet_width in inches (default 96 x 48); kerf is the saw blade width in inches (default 0.125).\n\n"
        "Returns: {job_number, material, sheet_size, sheets_needed, parts_nested, overall_yield_pct, "
        "oversize_parts: [parts too big for the sheet], sheets: [{sheet, yield_pct, strips: [{rip_width, y, "
        "parts: [{cabinet, name, length, width, x}]}]}]}. x and y are inches from the sheet's corner.\n\n"
        'Example: {"job": {...}, "material": "MEL-WHT-34", "sheet_length": 97, "sheet_width": 49}.'
    ),
)
def nest_sheets(
    job: JobArg,
    material: Annotated[str, Field(description='Material code to nest, e.g. "MEL-WHT-34". Empty = the job\'s case_material.')] = "",
    sheet_length: Annotated[float, Field(gt=12, le=200, description="Sheet length in inches, e.g. 96, 97, 120.")] = 96.0,
    sheet_width: Annotated[float, Field(gt=12, le=80, description="Sheet width in inches, e.g. 48, 49, 60.")] = 48.0,
    kerf: Annotated[float, Field(ge=0, le=0.5, description="Saw blade kerf in inches. Default 0.125 (1/8\").")] = 0.125,
) -> dict:
    j = _job(job)
    review = review_job(j)
    if not review["ok"]:
        return _blocked(review)
    result = nest(cl.build_cutlist(j), material or j.case_material, sheet_length, sheet_width, kerf)
    result["job_number"] = j.job_number
    return result


@mcp.tool(
    title="Count sheets",
    annotations=READ_ONLY,
    description=(
        "Count how many full sheets each material in the job needs (quick material takeoff).\n\n"
        "Use for bids and ordering (\"how many sheets of melamine do I need?\"). It runs the same panel-saw "
        "nesting as nest_sheets for every material but returns only the totals; call nest_sheets when someone "
        "needs the layouts.\n\n"
        "Returns: {job_number, sheet_size, materials: {code: {sheets, yield_pct, oversize_parts}}}. "
        "oversize_parts counts parts that do not fit the sheet and need a bigger sheet or a joint.\n\n"
        'Example: the bundled sample kitchen (8 cabinets) returns 9 sheets of 3/4" case material and 3 sheets '
        'of 1/4" back on 48 x 96 sheets.'
    ),
)
def count_sheets(
    job: JobArg,
    sheet_length: Annotated[float, Field(gt=12, le=200, description="Sheet length in inches. Default 96.")] = 96.0,
    sheet_width: Annotated[float, Field(gt=12, le=80, description="Sheet width in inches. Default 48.")] = 48.0,
) -> dict:
    j = _job(job)
    review = review_job(j)
    if not review["ok"]:
        return _blocked(review)
    parts = cl.build_cutlist(j)
    out = {}
    for m in sorted({p.material for p in parts}):
        r = nest(parts, m, sheet_length, sheet_width)
        out[m] = {"sheets": r["sheets_needed"], "yield_pct": r["overall_yield_pct"],
                  "oversize_parts": len(r["oversize_parts"])}
    return {"job_number": j.job_number, "sheet_size": f"{sheet_width} x {sheet_length}", "materials": out}


@mcp.tool(
    title="Calculate edgebanding",
    annotations=READ_ONLY,
    description=(
        "Calculate the linear feet of edgebanding a job needs, per material, with a waste allowance.\n\n"
        "Use when ordering edgeband rolls or pricing edgebanding. For sheet goods use count_sheets; for the "
        "individual parts and which edges they get, use build_cutlist (its edgeband field drives this total).\n\n"
        "Counted edges: the front edge of sides, bottoms, tops, top rails and adjustable shelves ('front'), and "
        "all four edges of doors and drawer fronts ('all'). Backs get no edgebanding. Edgeband is grouped by the "
        "part's material code, so doors in front_material are totalled separately from case parts.\n\n"
        "Parameters: waste_pct is the extra percentage added for trimming and machine setup, 0-50 (default 10).\n\n"
        "Behaviour: read-only and deterministic. Runs review_cabinet_schedule first and returns {error, review} "
        "instead of totals if the schedule has errors.\n\n"
        "Returns: {job_number, waste_pct, by_material: {code: {linear_feet, with_waste_linear_feet}}, "
        "total_with_waste_linear_feet}. Feet are rounded to 0.1.\n\n"
        'Example: one 30" x 30" x 12" wall cabinet with one door and waste_pct=0 gives 19.7 linear feet of the '
        'case material (sides, bottom and top front edges plus the door perimeter).'
    ),
)
def calculate_edgeband(
    job: JobArg,
    waste_pct: Annotated[float, Field(ge=0, le=50, description="Waste allowance in percent. Default 10.")] = 10.0,
) -> dict:
    j = _job(job)
    review = review_job(j)
    if not review["ok"]:
        return _blocked(review)
    return {"job_number": j.job_number, **cl.edgeband_takeoff(cl.build_cutlist(j), waste_pct)}


@mcp.tool(
    title="List cabinet types",
    annotations=READ_ONLY,
    description=(
        "Reference for building a job: the cabinet types this server understands, with typical sizes and "
        "which fields each uses.\n\n"
        "Use before calling the other tools when you are turning drawings or a description into a schedule and "
        "are unsure which type or size to use. Takes no input.\n\n"
        "Returns: {units, types: {type: {description, typical: {width, height, depth}, uses}}, defaults: "
        "{construction rules and thicknesses}, example_job}."
    ),
)
def list_cabinet_types() -> dict:
    return {
        "units": "inches",
        "types": {
            "base": {"description": "Floor cabinet with doors and optional top drawers; two top rails.",
                     "typical": {"width": "12-36", "height": 34.5, "depth": 24}, "uses": ["doors", "drawers", "adj_shelves"]},
            "drawer_base": {"description": "Floor cabinet with a stack of equal-height drawer fronts.",
                            "typical": {"width": "15-36", "height": 34.5, "depth": 24}, "uses": ["drawers"]},
            "sink_base": {"description": "Floor cabinet with doors and no shelf, for plumbing.",
                          "typical": {"width": "30-36", "height": 34.5, "depth": 24}, "uses": ["doors"]},
            "wall": {"description": "Hung upper cabinet with a full top.",
                     "typical": {"width": "12-36", "height": "12-42", "depth": 12}, "uses": ["doors", "adj_shelves"]},
            "tall": {"description": "Pantry or utility cabinet with a full top.",
                     "typical": {"width": "18-36", "height": "84-96", "depth": "12-24"}, "uses": ["doors", "adj_shelves"]},
        },
        "defaults": {"case_thickness": 0.75, "back_thickness": 0.25, "top_rail_width": cl.RAIL_WIDTH,
                     "reveal": cl.REVEAL, "top_drawer_front_height": cl.DRAWER_FRONT_HEIGHT},
        "example_job": json.loads(EXAMPLE_PATH.read_text()),
    }


@mcp.tool(
    title="Get server info",
    annotations=READ_ONLY,
    description=(
        "What millwork-mcp-lite does, its license, and what the full millwork-mcp adds (CNC router nesting, "
        "woodWOP DXF output, 32mm joinery, grain matching, estimating, inventory).\n\n"
        "Use when someone asks what this server can do, or needs something outside the lite tools. Takes no input.\n\n"
        "Returns: {name, license, tools, typical_flow, full_version, full_version_adds, contact}."
    ),
)
def get_server_info() -> dict:
    return {
        "name": "millwork-mcp-lite",
        "license": "MIT",
        "tools": ["review_cabinet_schedule", "build_cutlist", "nest_sheets", "count_sheets",
                  "calculate_edgeband", "list_cabinet_types", "get_server_info"],
        "typical_flow": "review_cabinet_schedule -> build_cutlist -> count_sheets / nest_sheets -> calculate_edgeband",
        "full_version": FULL_VERSION,
        "full_version_adds": [
            "nested-router CNC nesting (MaxRects, grain-locked, multi-start)",
            "woodWOP-ready DXF per sheet with machining layers",
            "32mm-system joinery: dowel, confirmat, cam, Lamello Clamex",
            "grain matching for doors and drawer fronts",
            "estimating from the real nest: material, hardware, labor, markup",
            "inventory: stock, offcuts, reserve -> cut -> consume",
            "hosted mode for Azure / Microsoft Foundry",
        ],
        "contact": "Contact@princeboafo.com",
    }


@mcp.resource("millwork://examples/small-kitchen", name="Sample kitchen job", mime_type="application/json",
              description="An 8-cabinet frameless kitchen schedule to try every tool with.")
def example_job() -> str:
    return EXAMPLE_PATH.read_text()


@mcp.resource("millwork://reference/construction", name="Construction defaults", mime_type="application/json",
              description="The generic frameless construction rules the cut list uses.")
def construction_reference() -> str:
    return json.dumps({
        "sides": "full height x full depth, 2 per cabinet",
        "bottom": "between the sides: (width - 2 x case_thickness) x depth",
        "top": "base types: two 4\" rails; wall and tall: full top between the sides",
        "shelves": "opening width - 1/16\", depth - 1\" - back_thickness",
        "back": "applied, full width x full height, back_material",
        "fronts": "full overlay, 1/16\" reveal; 6\" top drawers on base cabinets",
        "edgeband": "front edge of case parts; all edges of fronts",
        "cabinet_types": list(CABINET_TYPES),
    }, indent=2)


@mcp.prompt(title="Plan a cabinet job",
            description="Walk an AI through turning a cabinet description into a reviewed cut list and material order.")
def plan_cabinet_job(
    description: Annotated[str, Field(description="Plain-language description of the cabinets, e.g. 'L-shaped kitchen, 10 ft run...'")],
    sheet_size: Annotated[Literal["48x96", "49x97", "60x120"], Field(description="Sheet size the shop buys.")] = "48x96",
) -> str:
    w, l = sheet_size.split("x")
    return (
        f"Turn this into a millwork-mcp-lite job and plan the material order.\n\nDescription: {description}\n\n"
        "1. Call list_cabinet_types if unsure get_server_info types or typical sizes.\n"
        "2. Build the job JSON (unique tags, inches) and call review_cabinet_schedule. Show any warnings and ask "
        "before guessing at missing sizes.\n"
        "3. Call build_cutlist and summarise pieces and square feet per material.\n"
        f"4. Call count_sheets with sheet_width={w} and sheet_length={l}, then calculate_edgeband.\n"
        "5. Give a short order list: sheets per material and edgeband linear feet with waste."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
