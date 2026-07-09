# 개발 환경 설정

## 1. 사전 요구사항

- Python 3.10 이상
- pip (Python 패키지 관리자)
- Git

## 2. 설치 및 설정

1.  **저장소 복제:**
    ```bash
    git clone https://github.com/paulsunnypark/quotation-management.git
    cd quotation-management
    ```

2.  **가상 환경 생성 및 활성화:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **의존성 설치:**
    ```bash
    pip install -r requirements.txt
    ```

## 3. 애플리케이션 실행

-   **Streamlit GUI 실행:**
    ```bash
    streamlit run main.py
    ```
    위 명령어를 실행하면 웹 브라우저에서 애플리케이션이 열립니다.

-   **데이터베이스 초기화 (필요 시):**
    `Database()` 생성 시 필요한 테이블과 마이그레이션이 자동 적용됩니다.
    ```bash
    python -c "from database import Database; Database()"
    ```

-   **가격 마스터 재생성 (필요 시):**
    ```bash
    python build_price_master.py
    python catalog_db.py
    ```
