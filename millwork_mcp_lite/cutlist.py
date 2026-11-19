"""A simple, generic frameless (European-style) box cut list.

These are textbook defaults, not any particular shop's standard:
  * sides run full height and full depth
  * bottom (and top on wall/tall cabinets) fit between the sides
  * base-type cabinets get two 4" top rails instead of a full top
  * a 1/4" back is applied to the rear, full width x full height
  * adjustable shelves are 1/16" narrower than the opening and 1" shallower
  * full-overlay fronts with a 1/16" reveal on every edge (1/8" between fronts)
"""
from __future__ import annotations

from .models import Cabinet, Job, Part

RAIL_WIDTH = 4.0
REVEAL = 1 / 16
SHELF_CLEARANCE = 1 / 16
SHELF_SETBACK = 1.0
DRAWER_FRONT_HEIGHT = 6.0  # top drawer on a base with doors below

BASE_TYPES = ("base", "drawer_base", "sink_base")


def _case_parts(c: Cabinet, job: Job) -> list[Part]:
    t = job.case_thickness
    inside_w = c.width - 2 * t
    m, tag = job.case_material, c.tag
    parts = [
        Part(tag, "Side", m, c.height, c.depth, 2 * c.qty, edgeband="front"),
        Part(tag, "Bottom", m, inside_w, c.depth, c.qty, edgeband="front"),
    ]
    if c.type in BASE_TYPES:
        parts.append(Part(tag, "Top rail", m, inside_w, RAIL_WIDTH, 2 * c.qty, edgeband="front",
                          notes="one front, one back"))
    else:
        parts.append(Part(tag, "Top", m, inside_w, c.depth, c.qty, edgeband="front"))
    if c.adj_shelves:
        parts.append(Part(tag, "Adjustable shelf", m, inside_w - SHELF_CLEARANCE,
                          c.depth - SHELF_SETBACK - job.back_thickness,
                          c.adj_shelves * c.qty, edgeband="front"))
    parts.append(Part(tag, "Back", job.back_material, c.height, c.width, c.qty))
    return parts


def _front_parts(c: Cabinet, job: Job) -> list[Part]:
    m, tag, parts = job.front_material, c.tag, []
    full_w = c.width - 2 * REVEAL
    if c.type == "drawer_base" and c.drawers:
        h = (c.height - REVEAL * (c.drawers + 1)) / c.drawers
        parts.append(Part(tag, "Drawer front", m, full_w, h, c.drawers * c.qty, edgeband="all"))
        return parts
    door_zone = c.height - 2 * REVEAL
    if c.drawers:
        parts.append(Part(tag, "Drawer front", m, full_w, DRAWER_FRONT_HEIGHT,
                          c.drawers * c.qty, edgeband="all"))
        door_zone -= c.drawers * (DRAWER_FRONT_HEIGHT + 2 * REVEAL)
    if c.doors:
        door_w = (c.width - REVEAL * (c.doors + 1)) / c.doors
        parts.append(Part(tag, "Door", m, door_zone, door_w, c.doors * c.qty, edgeband="all"))
    return parts


def build_cutlist(job: Job) -> list[Part]:
    parts: list[Part] = []
    for c in job.cabinets:
        parts += _case_parts(c, job) + _front_parts(c, job)
    return [p for p in parts if p.qty > 0 and p.length > 0 and p.width > 0]


def edgeband_takeoff(parts: list[Part], waste_pct: float = 10.0) -> dict:
    """Linear feet of edgebanding per material. 'front' = one long edge, 'all' = all four edges."""
    by_mat: dict[str, float] = {}
    for p in parts:
        if p.edgeband == "front":
            inches = p.length
        elif p.edgeband == "all":
            inches = 2 * (p.length + p.width)
        else:
            continue
        by_mat[p.material] = by_mat.get(p.material, 0.0) + inches * p.qty
    out = {}
    for m, inches in sorted(by_mat.items()):
        lf = inches / 12
        out[m] = {"linear_feet": round(lf, 1), "with_waste_linear_feet": round(lf * (1 + waste_pct / 100), 1)}
    return {"waste_pct": waste_pct, "by_material": out,
            "total_with_waste_linear_feet": round(sum(v["with_waste_linear_feet"] for v in out.values()), 1)}


def summarize(parts: list[Part]) -> dict:
    by_mat: dict[str, dict] = {}
    for p in parts:
        s = by_mat.setdefault(p.material, {"pieces": 0, "square_feet": 0.0})
        s["pieces"] += p.qty
        s["square_feet"] += p.length * p.width * p.qty / 144
    for s in by_mat.values():
        s["square_feet"] = round(s["square_feet"], 2)
    return {"total_pieces": sum(p.qty for p in parts), "by_material": by_mat}
