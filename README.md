# README.md 파일 생성
echo "# AI 견적서 관리 시스템

## 프로젝트 개요
AI 기반의 견적서 자동 생성 및 관리 시스템입니다.

## 주요 기능
- 견적서 자동 생성 및 버전 관리
- PDF/HTML 형식 지원
- 견적 이력 관리
- 자동 버전 관리 시스템

## 기술 스택
- Python
- Streamlit
- SQLite
- FPDF
- Pandas

## 설치 방법
1. 저장소 클론
\`\`\`bash
git clone https://github.com/YOUR_USERNAME/quotation-management.git
cd quotation-management
\`\`\`

2. 가상환경 생성 및 활성화
\`\`\`bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
\`\`\`

3. 의존성 설치
\`\`\`bash
pip install -r requirements.txt
\`\`\`

## 실행 방법
\`\`\`bash
streamlit run main.py
\`\`\`" > README.md

# requirements.txt 파일 생성
pip freeze > requirements.txt

# README.md와 requirements.txt 추가 및 커밋
git add README.md requirements.txt
git commit -m "문서: README 및 requirements.txt 추가"
git push
