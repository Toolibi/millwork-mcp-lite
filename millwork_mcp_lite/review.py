"""Basic sanity checks on a cabinet schedule before anything is cut."""
from __future__ import annotations

from collections import Counter

from .models import CABINET_TYPES, Job

MAX_DOOR_WIDTH = 24.0   # wider single doors sag and swing into the room
MIN_WIDTH, MAX_WIDTH = 9.0, 48.0


def review_job(job: Job) -> dict:
    """Return a list of issues. 'error' blocks the cut list; 'warning' needs a human look."""
    issues: list[dict] = []

    def add(level: str, tag: str, msg: str) -> None:
        issues.append({"level": level, "cabinet": tag, "message": msg})

    if not job.cabinets:
        add("error", "-", "The schedule has no cabinets.")

    for tag, n in Counter(c.tag for c in job.cabinets).items():
        if n > 1:
            add("error", tag, f"Tag {tag} is used {n} times; each line needs a unique tag (use qty for repeats).")

    for c in job.cabinets:
        if c.type not in CABINET_TYPES:
            add("error", c.tag, f"Unknown type '{c.type}'. Use one of: {', '.join(CABINET_TYPES)}.")
        if min(c.width, c.height, c.depth) <= 0:
            add("error", c.tag, "Width, height and depth must all be positive.")
            continue
        if not MIN_WIDTH <= c.width <= MAX_WIDTH:
            add("warning", c.tag, f'Width {c.width}" is outside the usual {MIN_WIDTH}-{MAX_WIDTH}" range.')
        if c.qty < 1:
            add("error", c.tag, "Quantity must be at least 1.")
        if c.doors:
            door_w = c.width / c.doors
            if door_w > MAX_DOOR_WIDTH:
                add("warning", c.tag, f'Each door would be about {door_w:.1f}" wide; consider {c.doors + 1} doors.')
        if c.type == "drawer_base" and c.drawers < 1:
            add("warning", c.tag, "Drawer base with no drawers listed.")
        if c.type == "sink_base" and c.adj_shelves:
            add("warning", c.tag, "Sink bases usually have no shelf (plumbing).")
        if c.type in ("base", "drawer_base", "sink_base") and not 30 <= c.height <= 36:
            add("warning", c.tag, f'Base height {c.height}" is unusual (typical 34.5").')
        if c.type == "wall" and c.depth > 16:
            add("warning", c.tag, f'Wall cabinet depth {c.depth}" is unusual (typical 12").')

    errors = sum(i["level"] == "error" for i in issues)
    return {"job_number": job.job_number, "ok": errors == 0, "errors": errors,
            "warnings": len(issues) - errors, "issues": issues}
