"""Simple panel-saw nesting: first-fit decreasing shelf packing.

Every layout is cut in strips (rip the board into shelves across its width, then
crosscut parts from each strip), so every board is guillotine-cuttable on a panel saw.
Parts keep the grain direction they were listed with (length runs along the board).
It favours simplicity over yield; expect roughly 70-85% on typical casework.

Leftover material is handed back as usable offcuts (real rectangles with size and
position), not just a waste percentage, so an agent can plan the next job around them.
Every offcut can be freed with guillotine cuts: the band left above a part that is
narrower than its strip, the end of each strip, and the unused width below the last strip.

Offcuts on hand can be passed back in (stock_offcuts). They are filled first, largest
first, and a fresh sheet is only opened for parts that do not fit on them.
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
class Board:
    """A full sheet or an offcut being cut. Offcuts have already-cut edges, so trim is 0."""
    length: float
    width: float
    trim: float
    offcut_id: str | None = None
    strips: list[Strip] = field(default_factory=list)

    @property
    def usable_length(self) -> float:
        return self.length - 2 * self.trim

    @property
    def usable_width(self) -> float:
        return self.width - 2 * self.trim

    def used_width(self, kerf: float) -> float:
        return sum(s.height + kerf for s in self.strips)

    def place(self, pc: dict, kerf: float) -> bool:
        L = self.usable_length
        if pc["length"] > L or pc["width"] > self.usable_width:
            return False
        for st in self.strips:
            if pc["width"] <= st.height and st.used + pc["length"] <= L:
                st.pieces.append({**pc, "x": round(self.trim + st.used, 5)})
                st.used += pc["length"] + kerf
                return True
        if self.used_width(kerf) + pc["width"] <= self.usable_width:
            self.strips.append(Strip(pc["width"], pc["length"] + kerf, [{**pc, "x": self.trim}]))
            return True
        return False


def _offcuts(b: Board, kerf: float, min_size: float) -> list[dict]:
    """Rectangles at least min_size on both sides, freeable with guillotine cuts."""
    found: list[dict] = []

    def add(length: float, width: float, x: float, y: float, where: str) -> None:
        if length >= min_size and width >= min_size:
            found.append({"length": round(length, 3), "width": round(width, 3),
                          "x": round(x, 3), "y": round(y, 3), "from": where,
                          "square_feet": round(length * width / 144, 2)})

    x_max, y_max = b.length - b.trim, b.width - b.trim
    y = b.trim
    for st in b.strips:
        for p in st.pieces:  # band above a part narrower than its strip
            add(p["length"], st.height - p["width"] - kerf, p["x"], y + p["width"] + kerf, "above part")
        add(x_max - (b.trim + st.used), st.height, b.trim + st.used, y, "end of strip")
        y += st.height + kerf
    add(x_max - b.trim, y_max - y, b.trim, y, "below last strip")
    return sorted(found, key=lambda o: o["length"] * o["width"], reverse=True)


def _layout(b: Board, kerf: float, min_offcut: float) -> dict:
    y, strips = b.trim, []
    for st in b.strips:
        strips.append({"rip_width": round(st.height, 5), "y": round(y, 5), "parts": st.pieces})
        y += st.height + kerf
    area = sum(p["length"] * p["width"] for st in b.strips for p in st.pieces)
    return {"yield_pct": round(100 * area / (b.length * b.width), 1), "strips": strips,
            "offcuts": _offcuts(b, kerf, min_offcut)}


def _pack(pieces: list[dict], boards: list[Board], sheet_length: float, sheet_width: float,
          kerf: float, trim: float) -> list[Board]:
    """Place each piece on the first board it fits (offcuts come first), else open a new sheet."""
    for pc in pieces:
        if not any(b.place(pc, kerf) for b in boards):
            nb = Board(sheet_length, sheet_width, trim)
            nb.place(pc, kerf)
            boards.append(nb)
    return boards


def nest(parts: list[Part], material: str, sheet_length: float = 96.0, sheet_width: float = 48.0,
         kerf: float = 0.125, trim: float = 0.25, min_offcut: float = 12.0,
         stock_offcuts: list[dict] | None = None) -> dict:
    L, W = sheet_length - 2 * trim, sheet_width - 2 * trim
    pieces = []
    for p in parts:
        if p.material != material:
            continue
        for _ in range(p.qty):
            pieces.append({"cabinet": p.cabinet, "name": p.name, "length": p.length, "width": p.width})
    oversize = [x for x in pieces if x["length"] > L or x["width"] > W]
    pieces = [x for x in pieces if x not in oversize]
    pieces.sort(key=lambda x: (x["width"], x["length"]), reverse=True)

    stock = [o for o in (stock_offcuts or []) if o.get("material", material) == material]
    stock.sort(key=lambda o: o["length"] * o["width"], reverse=True)
    offcut_boards = [Board(o["length"], o["width"], 0.0, str(o.get("id") or f"offcut-{i + 1}"))
                     for i, o in enumerate(stock)]

    boards = _pack(pieces, list(offcut_boards), sheet_length, sheet_width, kerf, trim)
    sheets = [b for b in boards if b.offcut_id is None]
    used_offcuts = [b for b in boards if b.offcut_id is not None and b.strips]
    unused_offcuts = [b.offcut_id for b in boards if b.offcut_id is not None and not b.strips]

    sheet_area = sheet_length * sheet_width
    part_area_on_sheets = sum(p["length"] * p["width"] for b in sheets for st in b.strips for p in st.pieces)
    out_sheets = [{"sheet": n, **_layout(b, kerf, min_offcut)} for n, b in enumerate(sheets, 1)]
    for sh in out_sheets:  # label leftovers so they can be passed straight back in as stock_offcuts
        for k, o in enumerate(sh["offcuts"], 1):
            o.update({"material": material, "id": f"sheet{sh['sheet']}-{k}"})
    result = {
        "material": material,
        "sheet_size": f"{sheet_width} x {sheet_length}",
        "sheets_needed": len(sheets),
        "parts_nested": len(pieces),
        "overall_yield_pct": round(100 * part_area_on_sheets / (sheet_area * len(sheets)), 1) if sheets else 0.0,
        "oversize_parts": oversize,
        "min_offcut": min_offcut,
        "usable_offcuts": sum(len(s["offcuts"]) for s in out_sheets),
        "offcut_square_feet": round(sum(o["square_feet"] for s in out_sheets for o in s["offcuts"]), 2),
        "sheets": out_sheets,
    }
    if stock:
        baseline = len(_pack(pieces, [], sheet_length, sheet_width, kerf, trim))
        result.update({
            "stock_offcuts_given": len(stock),
            "stock_offcuts_used": [{"id": b.offcut_id, "length": b.length, "width": b.width,
                                    "parts_placed": sum(len(st.pieces) for st in b.strips),
                                    **_layout(b, kerf, min_offcut)} for b in used_offcuts],
            "stock_offcuts_unused": unused_offcuts,
            "parts_on_offcuts": sum(len(st.pieces) for b in used_offcuts for st in b.strips),
            "sheets_without_offcuts": baseline,
            "sheets_saved": baseline - len(sheets),
        })
    return result
