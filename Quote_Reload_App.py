# Streamlit 기반 견적서 생성 MVP + CSV 저장 개선 + 메타/항목 분리 저장 (Excel 등 확장 가능성 고려)

import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime
import os

# CSV 파일 이름 변경 반영
csv_file = "기초_견적항목_테이블.csv"
df = pd.read_csv(csv_file)

st.set_page_config(page_title="AI 견적서 생성기", layout="wide")
st.title("📄 AI 견적서 생성 MVP")

# 저장 디렉토리 설정
doc_folder = "견적서_이력"
os.makedirs(doc_folder, exist_ok=True)

# 이력 파일 리스트 출력 및 선택
st.sidebar.subheader("📁 저장된 견적서 목록")
saved_files = sorted([f for f in os.listdir(doc_folder) if f.endswith(".csv")])
if saved_files:
    selected_file = st.sidebar.selectbox("견적 이력 선택", saved_files)
    if st.sidebar.button("📂 견적 불러오기"):
        loaded_df = pd.read_csv(os.path.join(doc_folder, selected_file))
        st.session_state['loaded_items'] = loaded_df[loaded_df['항목코드'].notnull()].to_dict(orient='records')
        st.session_state['base_filename'] = selected_file.replace(".csv", "")

        # 메타 정보 로드 (첫 행 기준)
        meta_row = loaded_df.iloc[0]
        st.session_state['고객사명'] = meta_row.get('고객사명', '')
        st.session_state['프로젝트명'] = meta_row.get('프로젝트명', '')
        st.session_state['담당자명'] = meta_row.get('담당자명', '')
        st.session_state['직위_고객'] = meta_row.get('직위', '')
        st.session_state['전화_고객'] = meta_row.get('전화번호', '')
        st.session_state['이메일_고객'] = meta_row.get('이메일', '')
        st.session_state['납품기간'] = meta_row.get('납품기간', '')
        st.session_state['하자기간'] = meta_row.get('하자기간', '')
        st.session_state['건명'] = meta_row.get('건명', '')
        st.session_state['견적담당자명'] = meta_row.get('견적담당자명', '')
        st.session_state['직위_당사'] = meta_row.get('견적담당자직위', '')
        st.session_state['전화_당사'] = meta_row.get('견적담당자전화번호', '')
        st.session_state['이메일_당사'] = meta_row.get('견적담당자이메일', '')
        st.success(f"{selected_file} 불러오기 완료")
else:
    st.sidebar.info("저장된 견적 이력이 없습니다.")

# 견적 항목 입력 및 집계

st.subheader("1️⃣ 견적 항목 선택")
categories = df['분류'].unique()
selected_items = []

for cat in categories:
    with st.expander(f"📂 {cat} 항목 보기"):
        sub_df = df[df['분류'] == cat].reset_index(drop=True)
        for i, row in sub_df.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**[{row['항목코드']}] {row['품목명']}**")
                st.markdown(f"{row['설명']}")
            with col2:
                default_qty = 0
                if 'loaded_items' in st.session_state:
                    for item in st.session_state['loaded_items']:
                        if item['항목코드'] == row['항목코드']:
                            default_qty = item['수량']
                qty = st.number_input(f"수량 ({row['단위']}) - {row['항목코드']}", min_value=0, step=1, value=default_qty, key=f"qty_{cat}_{i}")
                if qty > 0:
                    selected_items.append({
                        "항목코드": row['항목코드'],
                        "품목명": row['품목명'],
                        "단위": row['단위'],
                        "수량": qty,
                        "단가": row['기본단가'],
                        "금액": qty * row['기본단가']
                    })

if selected_items:
    st.subheader("2️⃣ 견적 결과")
    result_df = pd.DataFrame(selected_items)
    result_df["금액"] = result_df["금액"].apply(lambda x: f"{x:,.0f}₩")
    st.table(result_df)

    total = sum([item['수량'] * item['단가'] for item in selected_items])
    st.success(f"💰 총 견적 금액 (VAT 별도): {total:,.0f}₩")

# 저장 후 PDF 생성
    if st.button("📄 견적서 PDF (뷰어용) 다운로드"):
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("ArialUnicode", '', "arialuni.ttf", uni=True)
        pdf.set_font("ArialUnicode", size=12)

        pdf.cell(200, 10, txt="견적서", ln=True, align="C")
        pdf.ln(10)

        pdf.set_font("ArialUnicode", size=10)
        pdf.cell(200, 10, txt=f"고객사: {customer_name} | 프로젝트명: {project_name}", ln=True)
        pdf.cell(200, 10, txt=f"담당자: {contact_name} ({contact_title}) / {contact_tel} / {contact_email}", ln=True)
        pdf.cell(200, 10, txt=f"견적일자: {datetime.date.today()} | 납품기간: {delivery_period} | 하자기간: {warranty_period}", ln=True)
        pdf.cell(200, 10, txt=f"견적담당자: {our_contact_name} ({our_contact_title}) / {our_contact_tel} / {our_contact_email}", ln=True)
        pdf.ln(10)

        pdf.set_font("ArialUnicode", style='', size=10)
        for item in selected_items:
            line = f"- {item['항목코드']} | {item['품목명']} | 수량: {item['수량']} | 단가: {item['단가']:,} | 금액: {item['수량'] * item['단가']:,}"
            pdf.cell(200, 8, txt=line.encode('utf-8').decode('utf-8'), ln=True)

        pdf.ln(10)
        pdf.set_font("ArialUnicode", size=11)
        pdf.cell(200, 10, txt=f"총 금액 (VAT 별도): {total:,.0f}₩", ln=True)

        pdf_path = os.path.join(doc_folder, full_filename + ".pdf")
        pdf.output(pdf_path)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 PDF 다운로드",
                data=f,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )
