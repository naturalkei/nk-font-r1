from PIL import Image

from nkfont.checks import check_overflow
from nkfont.diff import diff_fonts
from nkfont.golden import compare
from nkfont.qa import Report, Stage, write_report


def test_overflow_flags_added_glyph_but_only_warns_for_inherited(latin):
    glyf = latin["glyf"]
    glyf["A"].coordinates.translate((300, 0))  # ink now 400..800 in a 600 cell
    glyf["A"].recalcBounds(glyf)
    errors, warnings = check_overflow(latin, inherited=None)
    assert any("U+0041" in e for e in errors)
    errors, warnings = check_overflow(latin, inherited={0x41})
    assert not errors and any("U+0041" in w for w in warnings)


def test_diff_reports_advance_and_name_changes(latin):
    from conftest import make_latin

    new = make_latin()
    new["hmtx"]["A"] = (1200, 100)
    new["name"].setName("Other", 1, 3, 1, 0x409)
    result = diff_fonts(latin, new)
    assert any("U+0041 advance 600 -> 1200" in line for line in result["advances"])
    assert any("nameID 1" in line for line in result["names"])
    assert result["features"] == []


def test_golden_compare_detects_change(tmp_path, monkeypatch):
    import nkfont.golden as golden

    monkeypatch.setattr(golden, "GOLDEN_DIR", tmp_path)
    monkeypatch.setattr(golden.config, "ROOT", tmp_path)
    img = Image.new("L", (100, 40), 255)
    assert compare("x", img).status == "new"
    assert compare("x", img).status == "pass"
    changed = img.copy()
    changed.paste(0, (0, 0, 50, 40))
    res = compare("x", changed, out_dir=tmp_path / "diff")
    assert res.status == "fail" and (tmp_path / "diff" / "x.diff.png").exists()


def test_report_fails_when_any_stage_fails(tmp_path):
    report = Report("quick", "sans", [Stage("a", "pass"), Stage("b", "warn")])
    assert report.ok
    report.stages.append(Stage("c", "fail", details=["boom"]))
    assert not report.ok
    md = write_report(report, tmp_path).read_text()
    assert "FAIL" in md and "boom" in md
