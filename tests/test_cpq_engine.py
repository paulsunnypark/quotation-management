"""CPQ 엔진 검증 테스트 (Track B). 실행: python -m pytest tests/ -q  또는  python tests/test_cpq_engine.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catalog_db import CatalogDB
import cpq_engine as eng


def _catalog():
    cat = CatalogDB()
    cat.rebuild()  # CSV로부터 재생성 보장
    return cat


def test_preset_C_proposed_total_matches_catalog():
    cat = _catalog()
    lines = eng.load_preset_lines("C", cat)
    totals = eng.compute_totals(lines)
    # 카탈로그 package_presets 산출합계와 일치해야 함
    assert totals["제안합계"] == 147150000


def test_all_presets_match_declared_sum():
    cat = _catalog()
    conn = cat.get_connection()
    declared = {r["프리셋코드"]: r["산출합계"] for r in conn.execute("SELECT * FROM package_presets")}
    conn.close()
    for code, expected in declared.items():
        lines = eng.load_preset_lines(code, cat)
        assert eng.compute_totals(lines)["제안합계"] == expected, code


def test_dual_pricing_supply_below_proposed():
    cat = _catalog()
    lines = eng.load_preset_lines("A", cat)
    t = eng.compute_totals(lines)
    assert t["공급합계"] < t["제안합계"]  # 공급가 < 제안가
    assert all(l["공급단가"] <= l["제안단가"] for l in lines)


def test_discount_within_limit_ok():
    cat = _catalog()
    ok, limit, _ = eng.validate_discount(0.10, "인증 파트너", cat)
    assert ok and limit == 0.10


def test_discount_over_limit_rejected():
    cat = _catalog()
    ok, limit, msg = eng.validate_discount(0.20, "일반 리셀러", cat)
    assert not ok and limit == 0.05 and "초과" in msg


def test_unknown_partner_grade():
    cat = _catalog()
    ok, limit, _ = eng.validate_discount(0.05, "없는등급", cat)
    assert not ok and limit is None


def test_vr_overlap_note_triggers_for_C():
    cat = _catalog()
    lines = eng.load_preset_lines("C", cat)  # IPX-SERIES + VR/STT 포함
    assert eng.vr_overlap_note(lines) is not None


def test_vr_overlap_note_absent_for_D():
    cat = _catalog()
    lines = eng.load_preset_lines("D", cat)  # ACS/VMS 중심, STT 없음
    assert eng.vr_overlap_note(lines) is None


def test_reg_status_breakdown_C():
    cat = _catalog()
    lines = eng.load_preset_lines("C", cat)
    bd = eng.reg_status_breakdown(lines)
    assert any("IP채널" in n for n in bd["등록"])
    assert len(bd["신규후보"]) >= 1
    assert len(bd["커스터마이징"]) >= 1


def test_preset_A_is_integrated_55M():
    cat = _catalog()
    lines = eng.load_preset_lines("A", cat)
    assert eng.compute_totals(lines)["제안합계"] == 55000000
    # 통합 Core(녹취내장)가 포함되어야 함
    assert any("통합 Core" in l["품목명"] for l in lines)


def test_preset_U_upgrade_40M():
    cat = _catalog()
    lines = eng.load_preset_lines("U", cat)
    assert eng.compute_totals(lines)["제안합계"] == 40000000


def test_recording_base_ok_for_A_integrated():
    cat = _catalog()
    lines = eng.load_preset_lines("A", cat)  # 통합 Core 포함 → 녹취 기반 OK
    assert eng.recording_base_status(lines) == "ok"


def test_recording_base_ok_for_C_has_ipxseries():
    cat = _catalog()
    lines = eng.load_preset_lines("C", cat)  # IPX-SERIES 포함
    assert eng.recording_base_status(lines) == "ok"


def test_recording_base_missing_for_U_addon():
    cat = _catalog()
    lines = eng.load_preset_lines("U", cat)  # 분석 add-on, 녹취 기반 없음
    assert eng.recording_base_status(lines) == "missing"


def test_checklist_existing_customer_waives_recording():
    cat = _catalog()
    lines = eng.load_preset_lines("U", cat)
    # 기존 고객이면 녹취 기반 항목 통과
    chk = dict(eng.submission_checklist(lines, "업그레이드", 0, "", existing_customer=True))
    assert chk["녹취 기반(IPX-Series/통합 Core)이 충족되는가"] is True
    # 신규로 처리하면 미통과
    chk2 = dict(eng.submission_checklist(lines, "업그레이드", 0, "", existing_customer=False))
    assert chk2["녹취 기반(IPX-Series/통합 Core)이 충족되는가"] is False


def test_integrated_core_supply_ratio_correct():
    # 통합 Core(녹취내장) 권장제안가 20M가 ACS Core(0.55)와 충돌해도 제품명 매칭으로 0.60 적용
    cat = _catalog()
    lines = eng.load_preset_lines("A", cat)
    core = next(l for l in lines if "통합 Core" in l["품목명"])
    assert core["공급가율"] == 0.60
    assert core["공급단가"] == 12000000  # 20,000,000 × 0.60 (오매핑 시 11,000,000)


def test_lines_have_tier_and_identifier():
    cat = _catalog()
    lines = eng.load_preset_lines("C", cat)
    assert all("계층" in l and l["계층"] in eng.TIERS for l in lines)
    ipx = next(l for l in lines if "IP채널" in l["품목명"])
    assert ipx["식별번호"] == "24234183"  # 제품마스터에서 연동


def test_product_master_has_unique_item_codes():
    cat = _catalog()
    products = cat.get_products()
    codes = [p.get("항목코드") for p in products]
    assert codes and all(codes)
    assert len(codes) == len(set(codes))
    assert products[0]["항목코드"] == "B-CH-001"


def test_preset_lines_use_item_code_matching():
    cat = _catalog()
    lines = eng.load_preset_lines("D", cat)
    response = next(l for l in lines if l["품목명"] == "Response/Report Module")
    assert response["항목코드"] == "B-MOD-004"
    assert response["계층"] == "Module"
    assert response["매칭방식"] == "항목코드"


def test_tier_of_mapping():
    assert eng.tier_of("STT Core") == "Core"
    assert eng.tier_of("Anchor/Channel") == "Channel"
    assert eng.tier_of("User Candidate") == "User"
    assert eng.tier_of("Integration Candidate") == "Interface"
    assert eng.tier_of("Analysis Module") == "Module"
    assert eng.tier_of("Service") == "Service"
    assert eng.tier_of("LCR Package") == "Core"


def test_tier_breakdown_sums_to_total():
    cat = _catalog()
    lines = eng.load_preset_lines("C", cat)
    tb = eng.tier_breakdown(lines)
    assert sum(tb.values()) == eng.compute_totals(lines)["제안합계"]


def test_recompute_line_qty_change():
    cat = _catalog()
    lines = eng.load_preset_lines("A", cat)
    line = lines[0]
    line["수량"] = 5
    eng.recompute_line(line)
    assert line["제안금액"] == line["제안단가"] * 5
    assert line["공급금액"] == line["공급단가"] * 5


if __name__ == "__main__":
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in funcs:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {fn.__name__}: {e}")
        except Exception as e:
            print(f"[ERROR] {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(funcs)} passed")
