"""millwork-mcp-lite: a small, open-source MCP server for cabinet cut lists and sheet nesting.

Run:  python -m millwork_mcp_lite.server   (stdio transport)

This is the free, MIT-licensed edition. The full millwork-mcp adds nested-router (CNC)
nesting, woodWOP-ready DXF machining output, 32mm-system joinery, grain matching,
estimating and inventory: https://github.com/Toolibi/millwork-mcp
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .cutlist import build_cutlist as _build_cutlist, summarize
from .models import Job
from .nesting import nest
from .review import review_job

FULL_VERSION = "https://github.com/Toolibi/millwork-mcp"

mcp = FastMCP("millwork-mcp-lite")

JOB_HELP = (
    'job = {"job_number": "K-101", "case_material": "MEL-34", "back_material": "MEL-14", '
    '"front_material": "MEL-34", "cabinets": [{"tag": "B1", "type": "base", "width": 24, '
    '"height": 34.5, "depth": 24, "doors": 1, "drawers": 1, "adj_shelves": 1, "qty": 1}]}. '
    "Types: base, drawer_base, sink_base, wall, tall. Inches."
)


@mcp.tool(description=(
    """Check a cabinet schedule for problems before building a cut list: duplicate tags,
    unknown types, odd sizes, doors that are too wide. """ + JOB_HELP))
def review_cabinet_schedule(job: dict) -> dict:
    return review_job(Job.from_dict(job))


@mcp.tool(description=(
    """Turn a cabinet schedule into a cut list (sides, bottoms, tops/rails, shelves, backs,
    doors, drawer fronts) for frameless cabinets, with edgebanding and square footage. """ + JOB_HELP))
def build_cutlist(job: dict) -> dict:
    j = Job.from_dict(job)
    review = review_job(j)
    if not review["ok"]:
        return {"error": "Fix the schedule errors first.", "review": review}
    parts = _build_cutlist(j)
    return {"job_number": j.job_number, "summary": summarize(parts),
            "parts": [p.to_dict() for p in parts], "review": review}


@mcp.tool(description=(
    """Nest one material's parts onto sheets for a panel saw (strip cutting, guillotine-safe)
    and report sheets needed and yield. material defaults to the job's case material. """ + JOB_HELP))
def nest_sheets(job: dict, material: str = "", sheet_length: float = 96.0, sheet_width: float = 48.0,
                kerf: float = 0.125) -> dict:
    j = Job.from_dict(job)
    review = review_job(j)
    if not review["ok"]:
        return {"error": "Fix the schedule errors first.", "review": review}
    result = nest(_build_cutlist(j), material or j.case_material, sheet_length, sheet_width, kerf)
    result["job_number"] = j.job_number
    return result


@mcp.tool(description=(
    """Quick material takeoff: sheets needed for every material in the job. """ + JOB_HELP))
def sheet_count(job: dict, sheet_length: float = 96.0, sheet_width: float = 48.0) -> dict:
    j = Job.from_dict(job)
    review = review_job(j)
    if not review["ok"]:
        return {"error": "Fix the schedule errors first.", "review": review}
    parts = _build_cutlist(j)
    mats = sorted({p.material for p in parts})
    out = {}
    for m in mats:
        r = nest(parts, m, sheet_length, sheet_width)
        out[m] = {"sheets": r["sheets_needed"], "yield_pct": r["overall_yield_pct"],
                  "oversize_parts": len(r["oversize_parts"])}
    return {"job_number": j.job_number, "sheet_size": f"{sheet_width} x {sheet_length}", "materials": out}


@mcp.tool()
def about() -> dict:
    """What this server does and what the full millwork-mcp adds."""
    return {
        "name": "millwork-mcp-lite",
        "license": "MIT",
        "tools": ["review_cabinet_schedule", "build_cutlist", "nest_sheets", "sheet_count"],
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
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
