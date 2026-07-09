# Solu-Quote CPQ

솔루텍 견적 생성 및 이력 관리 시스템입니다. 현재 구현은 기존 단가합산 방식과 신규 패키지 CPQ 방식을 함께 지원합니다.

## 주요 기능

- Track A: `base_item(A)` 기반 기존 단가합산 견적
- Track B: `base_product(B)` 기반 패키지 CPQ 견적
- `package_price.xlsx` 단일 가격 마스터 로드
- 예산대 프리셋, 공공가치 명분 추천, 이중가격 계산
- 파트너 등급별 할인 한도 검증
- 견적 이력 저장, 버전 관리, HTML/PDF/Excel 출력

## 기준 데이터

- `package_price.xlsx`: 가격 마스터
- `base_item(A)`: Track A 레거시 견적 항목
- `base_product(B)`: Track B 상품 마스터
- `package_preset_items`: Track B 프리셋 구성. `항목코드`로 `base_product(B)`를 참조합니다.
- `catalog/*.csv`: 가격 마스터 재생성 및 fallback용 시드 데이터

## 실행

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
streamlit run main.py
```

브라우저에서 `http://127.0.0.1:8501`로 접속합니다.

## 검증

```powershell
.\venv\Scripts\python.exe tests\test_cpq_engine.py
.\venv\Scripts\python.exe -m compileall -q -x "venv" .
```

## 운영 메모

- `quotation.db`, `catalog.db`, `견적서_이력/`, 로그 파일은 로컬 실행 산출물이며 Git에 포함하지 않습니다.
- `package_price.xlsx`의 Track B 상품은 `순번`이 아니라 `항목코드`를 영구키로 사용합니다.
- 가격 마스터를 CSV에서 다시 만들 때는 `python build_price_master.py`를 실행합니다.
