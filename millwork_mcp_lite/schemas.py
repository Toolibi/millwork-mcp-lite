"""Typed tool inputs, so every MCP client sees field-level descriptions and allowed values."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CabinetType = Literal["base", "drawer_base", "sink_base", "wall", "tall"]


class CabinetIn(BaseModel):
    """One line of a cabinet schedule."""

    model_config = ConfigDict(extra="ignore")

    tag: str = Field(description='Unique label from the drawings, e.g. "B1", "SB1", "W3". One line per tag; use qty for repeats.')
    type: CabinetType = Field(description=(
        "Cabinet type. base = doors and/or a top drawer; drawer_base = drawer stack only; "
        "sink_base = doors, no shelf; wall = hung upper with full top; tall = pantry/utility with full top."))
    width: float = Field(gt=0, description='Overall width in inches, e.g. 30. Typical 9-48".')
    height: float = Field(gt=0, description='Overall box height in inches (no toe kick), e.g. 34.5 base, 30 wall, 84 tall.')
    depth: float = Field(gt=0, description='Overall depth in inches, e.g. 24 base/tall, 12 wall.')
    doors: int = Field(0, ge=0, le=4, description="Number of doors, 0-4. Doors split the width equally.")
    drawers: int = Field(0, ge=0, le=6, description="Number of drawer fronts. On base: 6\" top drawers above the doors. On drawer_base: equal-height stack.")
    adj_shelves: int = Field(0, ge=0, le=8, description="Number of adjustable shelves.")
    qty: int = Field(1, ge=1, le=200, description="How many identical cabinets of this tag.")


class JobIn(BaseModel):
    """A cabinet job: materials plus the cabinet schedule."""

    model_config = ConfigDict(extra="ignore")

    job_number: str = Field("JOB", description='Job or quote reference, e.g. "K-101". Echoed back in every result.')
    case_material: str = Field("MEL-34", description='Material code for case parts (sides, bottoms, tops, rails, shelves), e.g. "MEL-WHT-34" for 3/4" white melamine.')
    back_material: str = Field("MEL-14", description='Material code for 1/4" backs, e.g. "MEL-WHT-14".')
    front_material: str = Field("MEL-34", description='Material code for doors and drawer fronts.')
    case_thickness: float = Field(0.75, gt=0, le=1.5, description="Case material thickness in inches. Default 0.75.")
    back_thickness: float = Field(0.25, gt=0, le=0.75, description="Back material thickness in inches. Default 0.25.")
    cabinets: list[CabinetIn] = Field(min_length=1, description="The cabinet schedule, one entry per tag.")


class StockOffcutIn(BaseModel):
    """A leftover piece already on the rack, e.g. an offcut returned by an earlier nest_sheets call."""

    model_config = ConfigDict(extra="ignore")

    material: str = Field(description='Material code, matching the job\'s codes, e.g. "MEL-WHT-34". Pieces in other materials are ignored.')
    length: float = Field(gt=0, le=200, description="Length in inches, along the grain (the long direction of the original sheet).")
    width: float = Field(gt=0, le=80, description="Width in inches.")
    id: str = Field("", description='Optional label or rack location, e.g. "R3-left". Echoed back so the shop can find the piece.')
