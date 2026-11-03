"""fontbakery audit: report parsing and the qa stage, without fontbakery installed."""

from nkfont import audit
from nkfont.qa import Runner, Stage


def _check(cid, result, code="x", msg="boom", font="NKMono-Regular.ttf"):
    return {
        "key": ["<Section: S>", f"<FontBakeryCheck:{cid}>", [["font", 0]]],
        "result": result,
        "filename": f"/tmp/{font}",
        "logs": [{"status": result, "message": {"code": code, "message": msg}}],
    }


REPORT = {
    "sections": [
        {
            "checks": [
                _check("opentype/font_version", "FAIL", "mismatch", "head 0.00101 vs 0.1.0"),
                _check("case_mapping", "FAIL", "missing-case-counterparts"),
                _check("opentype/caret_slope", "PASS", "ok"),
                _check("whitespace_ink", "WARN"),
            ]
        }
    ]
}


def test_parse_report_keeps_only_failures_and_marks_known():
    cfg = {"warn_only": {"case_mapping": "inherited from the Latin base"}}
    found = audit.parse_report(REPORT, cfg)
    assert [(f.check, f.known) for f in found] == [
        ("opentype/font_version", False),
        ("case_mapping", True),
    ]
    assert found[0].font == "NKMono-Regular.ttf" and found[0].code == "mismatch"
    assert "(known)" in audit.format_findings(found)[1]


def test_families_split_masters_and_patched_files(tmp_path):
    names = ["NKMono-Regular", "NKMono-Bold", "NKMonoNerdFont-Regular", "NKSans-Regular"]
    groups = audit.families([tmp_path / f"{n}.ttf" for n in names])
    assert {k: len(v) for k, v in groups.items()} == {"NKMono": 2, "NKMonoNerdFont": 1, "NKSans": 1}


def test_repo_audit_config_loads():
    cfg = audit.load_audit_config()
    assert cfg["profile"] == "universal"
    assert all(reason for reason in cfg.get("warn_only", {}).values())


def _runner(tmp_path):
    r = Runner("release", "mono", tmp_path, update_golden=False)
    r.masters = [tmp_path / "NKMono-Regular.ttf"]
    return r


def test_audit_stage_skips_without_fontbakery(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "available", lambda: False)
    st = Stage("fontbakery audit")
    _runner(tmp_path).audit(st)
    assert st.status == "skip" and "[audit]" in st.details[0]


def test_audit_stage_fails_on_new_finding_and_warns_on_known(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "available", lambda: True)
    cfg = {"warn_only": {"case_mapping": "inherited"}}
    findings = audit.parse_report(REPORT, cfg)
    monkeypatch.setattr(audit, "run_fontbakery", lambda files: findings)
    st = Stage("fontbakery audit")
    _runner(tmp_path).audit(st)
    assert st.status == "fail"

    monkeypatch.setattr(audit, "run_fontbakery", lambda files: [f for f in findings if f.known])
    st = Stage("fontbakery audit")
    _runner(tmp_path).audit(st)
    assert st.status == "warn"
