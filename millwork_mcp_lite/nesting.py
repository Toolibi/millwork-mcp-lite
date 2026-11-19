"""Simple panel-saw nesting: first-fit decreasing shelf packing.

Every layout is cut in strips (rip the sheet into shelves across its width, then
crosscut parts from each strip), so every sheet is guillotine-cuttable on a panel saw.
Parts keep the grain direction they were listed with (length runs along the sheet).
It favours simplicity over yield; expect roughly 70-85% on typical casework.
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


def nest(parts: list[Part], material: str, sheet_length: float = 96.0, sheet_width: float = 48.0,
         kerf: float = 0.125, trim: float = 0.25) -> dict:
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
        out_sheets.append({"sheet": n, "yield_pct": round(100 * area / sheet_area, 1), "strips": strips})
    return {
        "material": material,
        "sheet_size": f"{sheet_width} x {sheet_length}",
        "sheets_needed": len(sheets),
        "parts_nested": len(pieces),
        "overall_yield_pct": round(100 * part_area / (sheet_area * len(sheets)), 1) if sheets else 0.0,
        "oversize_parts": oversize,
        "sheets": out_sheets,
    }
