import json
from pathlib import Path

from millwork_mcp_lite.cutlist import build_cutlist, summarize
from millwork_mcp_lite.models import Job
from millwork_mcp_lite.nesting import nest
from millwork_mcp_lite.review import review_job

EXAMPLE = json.loads((Path(__file__).parent.parent / "examples" / "small_kitchen.json").read_text())


def job(**over):
    d = json.loads(json.dumps(EXAMPLE))
    d.update(over)
    return Job.from_dict(d)


def test_example_reviews_clean():
    r = review_job(job())
    assert r["ok"] and r["errors"] == 0


def test_duplicate_tag_is_an_error():
    d = json.loads(json.dumps(EXAMPLE))
    d["cabinets"].append(dict(d["cabinets"][0]))
    r = review_job(Job.from_dict(d))
    assert not r["ok"]
    assert any("used 2 times" in i["message"] for i in r["issues"])


def test_wide_single_door_warns():
    d = {"job_number": "X", "cabinets": [{"tag": "B9", "type": "base", "width": 36,
                                          "height": 34.5, "depth": 24, "doors": 1}]}
    r = review_job(Job.from_dict(d))
    assert r["ok"] and r["warnings"] == 1


def test_base_cabinet_parts():
    d = {"job_number": "X", "cabinets": [{"tag": "B1", "type": "base", "width": 24,
                                          "height": 34.5, "depth": 24, "doors": 1, "adj_shelves": 1}]}
    parts = {p.name: p for p in build_cutlist(Job.from_dict(d))}
    assert parts["Side"].qty == 2 and parts["Side"].length == 34.5
    assert parts["Bottom"].length == 22.5            # 24 - 2 x 3/4
    assert parts["Top rail"].qty == 2 and parts["Top rail"].width == 4
    assert parts["Adjustable shelf"].length == 22.5 - 1 / 16
    assert parts["Door"].width == 24 - 2 / 16


def test_qty_multiplies_parts():
    one = build_cutlist(job())
    d = json.loads(json.dumps(EXAMPLE))
    for c in d["cabinets"]:
        c["qty"] = c.get("qty", 1) * 2
    two = build_cutlist(Job.from_dict(d))
    assert summarize(two)["total_pieces"] == 2 * summarize(one)["total_pieces"]


def test_nesting_places_every_part_inside_the_sheet():
    j = job()
    parts = build_cutlist(j)
    r = nest(parts, j.case_material)
    expected = sum(p.qty for p in parts if p.material == j.case_material)
    placed = sum(len(s["parts"]) for sh in r["sheets"] for s in sh["strips"])
    assert placed == r["parts_nested"] == expected
    assert not r["oversize_parts"]
    for sh in r["sheets"]:
        for s in sh["strips"]:
            assert s["y"] + s["rip_width"] <= 48
            for p in s["parts"]:
                assert p["x"] + p["length"] <= 96 and p["width"] <= s["rip_width"]
    assert 0 < r["overall_yield_pct"] <= 100


def test_oversize_parts_are_reported():
    d = {"job_number": "X", "cabinets": [{"tag": "T9", "type": "tall", "width": 24,
                                          "height": 100, "depth": 24}]}
    j = Job.from_dict(d)
    r = nest(build_cutlist(j), j.case_material)
    assert len(r["oversize_parts"]) == 2   # two 100" sides don't fit a 96" sheet


def test_edgeband_takeoff_counts_front_and_all_edges():
    from millwork_mcp_lite.cutlist import edgeband_takeoff
    d = {"job_number": "X", "cabinets": [{"tag": "W1", "type": "wall", "width": 30,
                                          "height": 30, "depth": 12, "doors": 1}]}
    r = edgeband_takeoff(build_cutlist(Job.from_dict(d)), waste_pct=0)
    # 2 sides 30 + bottom 28.5 + top 28.5 (front edges) = 117; door 2*(29.875+29.875) = 119.5
    assert r["by_material"]["MEL-34"]["linear_feet"] == round((117 + 119.5) / 12, 1)


def _call(name, args):
    import asyncio
    from millwork_mcp_lite.server import mcp
    return asyncio.run(mcp.call_tool(name, args))


def test_server_exposes_tools_prompts_resources():
    import asyncio
    from millwork_mcp_lite.server import mcp
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert set(tools) == {"review_cabinet_schedule", "build_cutlist", "nest_sheets", "sheet_count",
                          "edgeband_takeoff", "list_cabinet_types", "about"}
    for t in tools.values():
        assert t.annotations.readOnlyHint and not t.annotations.destructiveHint
        assert "Returns:" in t.description and len(t.description) > 200
    job_schema = tools["build_cutlist"].inputSchema
    assert "cabinets" in str(job_schema) and "drawer_base" in str(job_schema)
    assert asyncio.run(mcp.list_prompts())[0].name == "plan_cabinet_job"
    assert len(asyncio.run(mcp.list_resources())) == 2


def test_tools_run_end_to_end_through_mcp():
    out = _call("sheet_count", {"job": EXAMPLE})
    text = str(out)
    assert "MEL-WHT-34" in text and "LITE-101" in text


def test_invalid_type_is_rejected_by_schema():
    import pytest
    bad = {"job_number": "X", "cabinets": [{"tag": "Z1", "type": "island", "width": 30, "height": 34.5, "depth": 24}]}
    with pytest.raises(Exception):
        _call("build_cutlist", {"job": bad})
