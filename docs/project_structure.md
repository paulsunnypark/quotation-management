# 프로젝트 구조

## 현재 구조

```text
quotation-management/
├── catalog/                         # CSV fallback 및 가격마스터 재생성용 시드
├── docs/                            # 운영/개발 문서
├── reports/                         # 사용자 보고 HTML
├── specs/                           # 설계 메모
├── tests/                           # CPQ 엔진 검증 테스트
├── arialuni.TTF                     # PDF 한글 폰트
├── build_price_master.py            # package_price.xlsx 재생성 도구
├── catalog_db.py                    # Track B 카탈로그 SQLite 재생성/조회
├── cpq_engine.py                    # Track B 패키지 CPQ 계산 엔진
├── data_manager.py                  # Track A 가격 로드 및 견적 저장 중계
├── database.py                      # SQLite 견적 이력 저장소
├── estimate_handler.py              # Track A 단가합산 처리
├── estimate_template.py             # Track A HTML 견적서 템플릿
├── main.py                          # Streamlit 메인 앱
├── package_price.xlsx               # 단일 가격 마스터
├── quote_export.py                  # Track B Excel/PDF 출력
├── requirements.txt
└── README.md
```

## 제외 대상

다음 항목은 로컬 실행 산출물이므로 Git에 포함하지 않습니다.

- `quotation.db`, `catalog.db`
- `견적서_이력/`
- `__pycache__/`, `.pytest_cache/`
- `*.log`
- `deliverables/`
- `검증_요약.xlsx`, `견적서.pdf`

## 가격 데이터 기준

`package_price.xlsx`가 우선 기준입니다. 앱은 다음 흐름으로 가격 데이터를 읽습니다.

1. Track A: `package_price.xlsx#base_item(A)`
2. Track B: `package_price.xlsx#base_product(B)`
3. 파일이 없을 때만 `catalog/*.csv` 또는 legacy CSV fallback 사용

Track B는 `base_product(B).항목코드`를 견적 저장과 프리셋 매칭의 영구키로 사용합니다. `순번`은 화면 정렬용입니다.
