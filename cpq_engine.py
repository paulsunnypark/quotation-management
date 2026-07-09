"""
CPQ 견적 엔진 (Track B - 신규 패키지)

Streamlit 비의존 순수 로직. catalog_db.CatalogDB를 데이터원으로 사용하며
프리셋 적재 / 이중가격 계산 / 할인 하한 검증 / VR중복 문구 / 식별번호 조합 집계를 제공한다.
단위 테스트가 가능하도록 UI와 분리되어 있다.
"""
import re
from catalog_db import CatalogDB

DEFAULT_SUPPLY_RATIO = 0.6  # 공급가율 미매칭 시 기본값

# 6대 표준 계층 (사업전략 v4 S2: 단일 SKU → 6계층 구조)
TIERS = ["Core", "Channel", "User", "Interface", "Module", "Service"]


def _num(x):
    if x in (None, ""):
        return None
    try:
        return int(float(str(x).replace(",", "")))
    except ValueError:
        return None


def _tokens(s):
    return set(re.findall(r"[0-9A-Za-z]+|[가-힣]+", str(s).upper()))


def tier_of(상품계층):
    """제품의 상품계층 문자열을 6대 표준 계층으로 정규화."""
    s = str(상품계층)
    if "Core" in s:
        return "Core"
    if "User" in s:
        return "User"
    if "Channel" in s:
        return "Channel"
    if "Integration" in s or "Interface" in s:
        return "Interface"
    if "Service" in s:
        return "Service"
    if "Package" in s:  # LCR Package 등 묶음
        return "Core"
    return "Module"


def _match_product(name, price, products):
    """견적 구성항목(이름+단가)을 제품마스터의 한 행에 매칭.

    단가 일치(+3)와 제품명 토큰 중첩(+토큰수)으로 점수화. 단가 충돌 시 이름으로 분별.
    """
    iname = _tokens(name)
    best, best_score = None, 0
    for p in products:
        score = 0
        if price is not None and _num(p.get("권장제안가")) == price:
            score += 3
        pname = _tokens(p.get("내부제품명")) | _tokens(p.get("외부조달표현"))
        score += len(pname & iname)
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 1 else None


def _match_product_by_code(item_code, products):
    """프리셋 항목코드로 제품마스터를 정확히 매칭한다."""
    code = str(item_code or "").strip()
    if not code:
        return None
    for product in products:
        if str(product.get("항목코드") or "").strip() == code:
            return product
    return None

VR_OVERLAP_NOTE = (
    "IPX-Series는 통신채널·ARS·CRS·기본녹취 수집 플랫폼으로 적용되며, "
    "IPX-VR/STT는 해당 녹취데이터를 STT 변환·검색·분석하는 확장 모듈입니다. "
    "본 구성에서는 기본 녹취 기능을 중복 과금하지 않습니다."
)


def load_preset_lines(preset_code, catalog=None):
    """예산대 프리셋 구성항목을 견적 라인으로 적재.

    각 라인을 제품마스터에 매칭하여 정확한 공급가율·계층(tier)·식별번호·등록상태를 부여한다.
    package_preset_items에 항목코드가 있으면 코드 매칭을 우선하고, 없으면 기존 이름+단가 매칭으로 fallback한다.
    각 라인: 항목코드, 품목명, 계층, 조달상태, 식별번호, 단위, 수량, 제안단가, 제안금액,
             공급가율, 공급단가, 공급금액, 비고, 매칭
    """
    catalog = catalog or CatalogDB()
    products = catalog.get_products()
    lines = []
    for item in catalog.get_preset_items(preset_code):
        proposed_unit = item["단가_VAT포함"]
        qty = item["수량"]
        item_code = item.get("항목코드")
        prod = _match_product_by_code(item_code, products)
        matched_by_code = prod is not None
        if prod is None:
            prod = _match_product(item["구성항목"], proposed_unit, products)
        if prod:
            ratio = prod.get("공급가율") or DEFAULT_SUPPLY_RATIO
            tier = tier_of(prod.get("상품계층"))
            reg = prod.get("등록상태") or item["조달등록후보"]
            # 식별번호는 '등록' 제품만 실제 번호. 신규후보 칸엔 등록방향 텍스트가 있어 제외
            ident = str(prod.get("식별번호") or "") if str(reg).startswith("등록") else ""
            item_code = prod.get("항목코드") or item_code
        else:
            ratio, tier, ident, reg = DEFAULT_SUPPLY_RATIO, "Service", "", item["조달등록후보"]
        supply_unit = round(proposed_unit * ratio)
        lines.append({
            "항목코드": str(item_code or ""),
            "품목명": item["구성항목"],
            "계층": tier,
            "조달상태": item["조달등록후보"],
            "식별번호": str(ident),
            "단위": item["단위"],
            "수량": qty,
            "제안단가": proposed_unit,
            "제안금액": proposed_unit * qty,
            "공급가율": ratio,
            "공급단가": supply_unit,
            "공급금액": supply_unit * qty,
            "비고": item.get("비고", ""),
            "매칭": prod is not None,
            "매칭방식": "항목코드" if matched_by_code else ("휴리스틱" if prod else "미매칭"),
        })
    return lines


def tier_breakdown(lines):
    """6계층별 제안금액 합계 (사업전략 v4 S2 구조 시각화). 0원 계층은 제외."""
    agg = {t: 0 for t in TIERS}
    for l in lines:
        agg[l.get("계층", "Module")] = agg.get(l.get("계층", "Module"), 0) + l["제안금액"]
    return {t: v for t, v in agg.items() if v > 0}


def recompute_line(line):
    """수량/단가 수정 후 금액 재계산 (in-place 반환)."""
    line["제안금액"] = line["제안단가"] * line["수량"]
    line["공급단가"] = round(line["제안단가"] * line["공급가율"])
    line["공급금액"] = line["공급단가"] * line["수량"]
    return line


def compute_totals(lines, discount_rate=0.0):
    """이중가격 합계 + 할인 적용 + 마진 산출."""
    proposed_sum = sum(l["제안금액"] for l in lines)
    supply_sum = sum(l["공급금액"] for l in lines)
    proposed_after_dc = round(proposed_sum * (1 - discount_rate))
    return {
        "제안합계": proposed_sum,
        "공급합계": supply_sum,
        "할인율": discount_rate,
        "제안가_할인후": proposed_after_dc,
        "마진": proposed_after_dc - supply_sum,
    }


def validate_discount(discount_rate, partner_grade, catalog=None):
    """파트너 등급별 할인 하한(한도) 검증.

    반환: (ok: bool, limit: float|None, message: str)
    """
    catalog = catalog or CatalogDB()
    limit = catalog.get_discount_limit(partner_grade)
    if limit is None:
        return False, None, f"알 수 없는 파트너 등급: {partner_grade}"
    if discount_rate > limit:
        return False, limit, (
            f"할인율 {discount_rate:.0%}이(가) '{partner_grade}' 한도 "
            f"{limit:.0%}을(를) 초과합니다. 승인권자 결재 필요."
        )
    return True, limit, f"할인율 {discount_rate:.0%} 승인 가능 (한도 {limit:.0%})"


def vr_overlap_note(lines):
    """IPX-Series 계열과 VR/STT가 함께 있으면 중복과금 방지 표준문구 반환, 없으면 None."""
    names = " ".join(l["품목명"] for l in lines)
    has_series = "IPX-SERIES" in names.upper() or "IP채널" in names
    has_stt = "VR/STT" in names.upper() or "STT" in names.upper()
    return VR_OVERLAP_NOTE if (has_series and has_stt) else None


def suggest_preset(service_name):
    """공공가치 서비스명 -> 적합 예산대 프리셋 코드 추천 (키워드 휴리스틱)."""
    s = service_name or ""
    if "악성민원" in s or "공무원 보호" in s:
        return "C"
    if "분석" in s or "응대품질" in s or "지식DB" in s:
        return "B"
    if "재난" in s or "복지" in s or "취약계층" in s:
        return "D"
    if "통합" in s and "플랫폼" in s:
        return "E"
    return "A"  # 기본 진입상품


def recording_base_status(lines):
    """녹취 기반 충족 여부 검증 (이름 기반).

    STT 채널/분석 모듈(녹취데이터 의존)이 있는데 녹취 기반
    (IPX-Series 또는 VR/STT 통합 Core)이 견적에 없으면 'missing'.
    반환: 'ok' | 'missing'
    """
    names = " ".join(l["품목명"] for l in lines)
    up = names.upper()
    needs_recording = (any(k in up for k in ("STT", "ANALYSIS", "ABUSE", "EVIDENCE"))
                       or "분석" in names)
    has_base = ("IPX-SERIES" in up or "통합 CORE" in up
                or "통합CORE" in up or "IP채널" in names)
    if needs_recording and not has_base:
        return "missing"
    return "ok"


RECORDING_MISSING_MSG = (
    "녹취 기반(IPX-Series 또는 VR/STT 통합 Core)이 견적에 없습니다. "
    "신규 고객이라면 'VR/STT 통합 Core(녹취내장)'를 추가하세요. "
    "기존 IPX-Series 보유 고객(업그레이드)이면 무시해도 됩니다."
)


def submission_checklist(lines, service_name, discount_rate, approver,
                         existing_customer=False):
    """제출 전 자동 체크리스트 (09_운영원칙). 반환: [(항목, 통과여부)]."""
    bd = reg_status_breakdown(lines)
    # 녹취 기반: 기존 고객(업그레이드)이면 면제, 아니면 기반 필요
    rec_ok = existing_customer or recording_base_status(lines) == "ok"
    return [
        ("패키지명/공공 명분이 명확한가", bool(service_name)),
        ("녹취 기반(IPX-Series/통합 Core)이 충족되는가", rec_ok),
        ("VR 중복방지 문구가 적용되는가", vr_overlap_note(lines) is not None or
         not ("STT" in " ".join(l["품목명"].upper() for l in lines))),
        ("등록/신규후보/커스터마이징이 구분되었는가",
         sum(1 for v in bd.values() if v) >= 2),
        ("할인 시 승인권자가 기록되었는가", discount_rate == 0 or bool(approver)),
        ("무상(0원) 항목이 없는가", all(l["제안금액"] > 0 for l in lines)),
    ]


def reg_status_breakdown(lines):
    """등록/신규후보/커스터마이징 구분 집계 (식별번호 조합표용)."""
    breakdown = {"등록": [], "신규후보": [], "커스터마이징": []}
    for l in lines:
        status = str(l.get("조달상태", ""))
        if status.startswith("등록"):
            breakdown["등록"].append(l["품목명"])
        elif "후보" in status:
            breakdown["신규후보"].append(l["품목명"])
        else:
            breakdown["커스터마이징"].append(l["품목명"])
    return breakdown
