# 프로젝트 구조

## 1. 디렉토리 구조

```
Quotation/
├── .git/               # Git 버전 관리
├── .gitignore          # Git 무시 파일 목록
├── docs/               # 프로젝트 문서
│   ├── development_setup.md
│   └── project_structure.md
├── venv/               # Python 가상 환경
├── 견적서_이력/         # 생성된 견적서 파일 (PDF, CSV, HTML)
├── __pycache__/        # Python 캐시 파일
├── arialuni.TTF        # PDF 생성용 한글 폰트
├── data_manager.py     # 데이터베이스 및 파일 I/O 관리
├── database.py         # SQLite 데이터베이스 연결 및 초기화
├── Estimate_App.py     # (구) Streamlit 견적 앱 (단일 파일)
├── estimate_handler.py # 견적 계산 및 PDF/HTML 생성 로직
├── estimate_template.py# HTML 견적서 템플릿
├── main.py             # 메인 Streamlit 애플리케이션
├── Quote_Reload_App.py # (구) Streamlit 견적 불러오기 앱
├── README.md           # 프로젝트 개요
├── requirements.txt    # Python 의존성 목록
├── 기초_견적항목_테이블.csv # 초기 견적 항목 데이터
└── 견적서.pdf          # (예시) 생성된 견적서 PDF
```

## 2. 주요 파일 설명

-   **`main.py`**: Streamlit을 사용하여 GUI를 렌더링하고 사용자 입력을 처리하는 메인 진입점입니다.
-   **`data_manager.py`**: `database.py`를 사용하여 데이터베이스와 상호작용하며, 견적 이력 CRUD(생성, 읽기, 갱신, 삭제)를 담당합니다.
-   **`database.py`**: SQLite 데이터베이스 연결을 설정하고, 테이블을 생성하며, 기본적인 DB 작업을 수행합니다.
-   **`estimate_handler.py`**: 선택된 항목을 기반으로 견적 금액을 계산하고, `fpdf`와 `xhtml2pdf`를 사용하여 PDF 및 HTML 파일을 생성하는 로직을 포함합니다.
-   **`estimate_template.py`**: 견적서 HTML의 구조와 스타일을 정의하는 템플릿입니다.
-   **`견적서_이력/`**: 사용자가 생성한 모든 견적 관련 파일(PDF, CSV, HTML)이 저장되는 디렉토리입니다.
-   **`기초_견적항목_테이블.csv`**: 애플리케이션이 처음 시작될 때 데이터베이스에 로드되는 기본 견적 항목 목록입니다.
-   **`Estimate_App.py`, `Quote_Reload_App.py`**: 현재는 `main.py`로 통합된 이전 버전의 단일 파일 앱입니다. (보관용 또는 참고용)
