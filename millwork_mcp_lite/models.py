"""Data types for millwork-mcp-lite. All dimensions are inches."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

CABINET_TYPES = ("base", "drawer_base", "sink_base", "wall", "tall")


@dataclass
class Cabinet:
    tag: str
    type: str
    width: float
    height: float
    depth: float
    doors: int = 0
    drawers: int = 0
    adj_shelves: int = 0
    qty: int = 1

    @classmethod
    def from_dict(cls, d: dict) -> "Cabinet":
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**known)


@dataclass
class Job:
    job_number: str
    cabinets: list[Cabinet]
    case_material: str = "MEL-34"
    back_material: str = "MEL-14"
    front_material: str = "MEL-34"
    case_thickness: float = 0.75
    back_thickness: float = 0.25

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        cabs = [Cabinet.from_dict(c) for c in d.get("cabinets", [])]
        extra = {k: d[k] for k in ("case_material", "back_material", "front_material",
                                   "case_thickness", "back_thickness") if k in d}
        return cls(job_number=str(d.get("job_number", "JOB")), cabinets=cabs, **extra)


@dataclass
class Part:
    cabinet: str
    name: str
    material: str
    length: float  # along the grain / long direction
    width: float
    qty: int = 1
    edgeband: str = ""
    notes: str = field(default="")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["length"] = round(self.length, 5)
        d["width"] = round(self.width, 5)
        return d
