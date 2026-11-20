"""Simple panel-saw nesting: first-fit decreasing shelf packing.

Every layout is cut in strips (rip the sheet into shelves across its width, then
crosscut parts from each strip), so every sheet is guillotine-cuttable on a panel saw.
Parts keep the grain direction they were listed with (length runs along the sheet).
It favours simplicity over yield; expect roughly 70-85% on typical casework.

Leftover material is handed back as usable offcuts (real rectangles with size and
position), not just a waste percentage, so an agent can plan the next job around them.
Every offcut can be freed with guillotine cuts: the band left above a part that is
narrower than its strip, the end of each strip, and the unused width below the last strip.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import Part


@dataclass
class Strip:
    height: float
    used: float = 0.0
    pieces: list[dict] = field(default_factory=list)


@dataclass
class Sheet:
    length: float
    width: float
    strips: list[Strip] = field(default_factory=list)

    def used_width(self, kerf: float) -> float:
        return sum(s.height + kerf for s in self.strips)


def _offcuts(sh: "Sheet", sheet_length: float, sheet_width: float, kerf: float, trim: float,
             min_size: float) -> list[dict]:
    """Rectangles at least min_size on both sides, freeable with guillotine cuts."""
    found: list[dict] = []

    def add(length: float, width: float, x: float, y: float, where: str) -> None:
        if length >= min_size and width >= min_size:
            found.append({"length": round(length, 3), "width": round(width, 3),
                          "x": round(x, 3), "y": round(y, 3), "from": where,
                          "square_feet": round(length * width / 144, 2)})

    x_max, y_max = sheet_length - trim, sheet_width - trim
    y = trim
    for st in sh.strips:
        for p in st.pieces:  # band above a part narrower than its strip
            add(p["length"], st.height - p["width"] - kerf, p["x"], y + p["width"] + kerf, "above part")
        add(x_max - (trim + st.used), st.height, trim + st.used, y, "end of strip")
        y += st.height + kerf
    add(x_max - trim, y_max - y, trim, y, "below last strip")
    return sorted(found, key=lambda o: o["length"] * o["width"], reverse=True)


def nest(parts: list[Part], material: str, sheet_length: float = 96.0, sheet_width: float = 48.0,
         kerf: float = 0.125, trim: float = 0.25, min_offcut: float = 12.0) -> dict:
    L, W = sheet_length - 2 * trim, sheet_width - 2 * trim
    pieces = []
    for p in parts:
        if p.material != material:
            continue
        for i in range(p.qty):
            pieces.append({"cabinet": p.cabinet, "name": p.name, "length": p.length, "width": p.width})
    oversize = [x for x in pieces if x["length"] > L or x["width"] > W]
    pieces = [x for x in pieces if x not in oversize]
    pieces.sort(key=lambda x: (x["width"], x["length"]), reverse=True)

    sheets: list[Sheet] = []
    for pc in pieces:
        placed = False
        for sh in sheets:
            for st in sh.strips:
                if pc["width"] <= st.height and st.used + pc["length"] <= L:
                    st.pieces.append({**pc, "x": round(trim + st.used, 5)})
                    st.used += pc["length"] + kerf
                    placed = True
                    break
            if placed:
                break
            if sh.used_width(kerf) + pc["width"] <= W:
                st = Strip(pc["width"])
                st.pieces.append({**pc, "x": trim})
                st.used = pc["length"] + kerf
                sh.strips.append(st)
                placed = True
                break
        if not placed:
            sh = Sheet(sheet_length, sheet_width)
            st = Strip(pc["width"], pc["length"] + kerf, [{**pc, "x": trim}])
            sh.strips.append(st)
            sheets.append(sh)

    sheet_area = sheet_length * sheet_width
    part_area = sum(x["length"] * x["width"] for x in pieces)
    out_sheets = []
    for n, sh in enumerate(sheets, 1):
        y = trim
        strips = []
        for st in sh.strips:
            strips.append({"rip_width": round(st.height, 5), "y": round(y, 5), "parts": st.pieces})
            y += st.height + kerf
        area = sum(p["length"] * p["width"] for st in sh.strips for p in st.pieces)
        offcuts = _offcuts(sh, sheet_length, sheet_width, kerf, trim, min_offcut)
        out_sheets.append({"sheet": n, "yield_pct": round(100 * area / sheet_area, 1), "strips": strips,
                           "offcuts": offcuts})
    return {
        "material": material,
        "sheet_size": f"{sheet_width} x {sheet_length}",
        "sheets_needed": len(sheets),
        "parts_nested": len(pieces),
        "overall_yield_pct": round(100 * part_area / (sheet_area * len(sheets)), 1) if sheets else 0.0,
        "oversize_parts": oversize,
        "min_offcut": min_offcut,
        "usable_offcuts": sum(len(s["offcuts"]) for s in out_sheets),
        "offcut_square_feet": round(sum(o["square_feet"] for s in out_sheets for o in s["offcuts"]), 2),
        "sheets": out_sheets,
    }
