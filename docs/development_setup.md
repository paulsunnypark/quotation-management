# 개발 환경 설정

## 1. 사전 요구사항

- Python 3.10 이상
- pip (Python 패키지 관리자)
- Git

## 2. 설치 및 설정

1.  **저장소 복제:**
    ```bash
    git clone https://github.com/your-username/Quotation.git
    cd Quotation
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
    `database.py`의 `init_db()` 함수를 직접 실행하여 데이터베이스를 초기화할 수 있습니다.
    ```bash
    python -c "from database import Database; Database().init_db()"
    ```
