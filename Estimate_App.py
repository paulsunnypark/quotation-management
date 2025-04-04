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
st.title("📄 견적서 생성 및 이력 관리")

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

        # 기존 입력 화면 기능 유지 → Session State만 반영
        st.session_state['loaded_items'] = loaded_df[loaded_df['항목코드'].notnull()].to_dict(orient='records')
        st.session_state['base_filename'] = selected_file.replace(".csv", "")

        meta_row = loaded_df.iloc[0]
        st.session_state['고객사명'] = str(meta_row.get('고객사명', ''))
        st.session_state['프로젝트명'] = str(meta_row.get('프로젝트명', ''))
        st.session_state['담당자명'] = str(meta_row.get('담당자명', ''))
        st.session_state['직위_고객'] = str(meta_row.get('직위', ''))
        st.session_state['전화_고객'] = str(meta_row.get('전화번호', ''))
        st.session_state['이메일_고객'] = str(meta_row.get('이메일', ''))
        st.session_state['납품기간'] = str(meta_row.get('납품기간', ''))
        st.session_state['하자기간'] = str(meta_row.get('하자기간', ''))
        st.session_state['건명'] = str(meta_row.get('건명', ''))
        st.session_state['견적담당자명'] = str(meta_row.get('견적담당자명', ''))
        st.session_state['직위_당사'] = str(meta_row.get('견적담당자직위', ''))
        st.session_state['전화_당사'] = str(meta_row.get('견적담당자전화번호', ''))
        st.session_state['이메일_당사'] = str(meta_row.get('견적담당자이메일', ''))

        st.success(f"✅ 불러오기 완료: {selected_file} → 편집 가능 상태로 전환되었습니다.")
else:
    st.sidebar.info("저장된 견적 이력이 없습니다.")

# 고객 정보 입력
st.subheader("👤 고객 및 프로젝트 정보")
col1, col2 = st.columns(2)
with col1:
    customer_name = st.text_input("고객사명", value=st.session_state.get('고객사명', ''))
    project_name = st.text_input("프로젝트명", value=st.session_state.get('프로젝트명', ''))
    contact_name = st.text_input("담당자명", value=st.session_state.get('담당자명', ''))
    if '직위_고객' not in st.session_state:
        st.session_state['직위_고객'] = ''
    contact_title = st.text_input("직위", key="직위_고객", value=str(st.session_state.get('직위_고객') or ''))
    if '전화_고객' not in st.session_state:
        st.session_state['전화_고객'] = ''
    contact_tel = st.text_input("전화번호", key="전화_고객", value=str(st.session_state.get('전화_고객') or ''))
with col2:
    if '이메일_고객' not in st.session_state:
        st.session_state['이메일_고객'] = ''
    contact_email = st.text_input("이메일", key="이메일_고객", value=str(st.session_state.get('이메일_고객') or ''))
    delivery_period = st.text_input("납품기간 (예: 발주 후 30일 이내)", value=st.session_state.get('납품기간', ''))
    warranty_period = st.text_input("하자기간 (예: 구축 후 1년)", value=st.session_state.get('하자기간', ''))
    document_title = st.text_input("건명", value=st.session_state.get('건명', ''))

# 당사 정보 입력
st.subheader("🏢 당사 정보")
col3, col4 = st.columns(2)
with col3:
    our_contact_name = st.text_input("견적 담당자명", value=st.session_state.get('견적담당자명', ''))
    if '직위_당사' not in st.session_state:
        st.session_state['직위_당사'] = ''
    our_contact_title = st.text_input("직위", key="직위_당사", value=str(st.session_state.get('직위_당사') or ''))
    if '전화_당사' not in st.session_state:
        st.session_state['전화_당사'] = ''
    our_contact_tel = st.text_input("전화번호", key="전화_당사", value=str(st.session_state.get('전화_당사') or ''))
with col4:
    if '이메일_당사' not in st.session_state:
        st.session_state['이메일_당사'] = ''
    our_contact_email = st.text_input("이메일", key="이메일_당사", value=str(st.session_state.get('이메일_당사') or ''))
    homepage = "http://www.solu.co.kr"

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

# 파일명 구성
    today_str = datetime.date.today().strftime("%Y%m%d")
    base_filename = st.session_state.get('base_filename', f"{today_str}_{customer_name}_{project_name}".replace(" ", "_"))

    # 버전 지정 입력
    version = st.text_input("버전 (예: v1, v2, final 등)", value="v1")
    full_filename = f"{base_filename}_{version}"

    # 견적 CSV 저장 기능
    # 고객/프로젝트/담당자 등 메타데이터 포함 저장
    meta = {
        "고객사명": customer_name,
        "프로젝트명": project_name,
        "담당자명": contact_name,
        "직위": contact_title,
        "전화번호": contact_tel,
        "이메일": contact_email,
        "납품기간": delivery_period,
        "하자기간": warranty_period,
        "건명": document_title,
        "견적담당자명": our_contact_name,
        "견적담당자직위": our_contact_title,
        "견적담당자전화번호": our_contact_tel,
        "견적담당자이메일": our_contact_email,
        "홈페이지": homepage,
        "총금액": total
    }
    meta_df = pd.DataFrame([meta])
    item_df = pd.DataFrame(selected_items)
    combined_df = pd.concat([meta_df, item_df], axis=1)

    if st.button("💾 견적 CSV 저장"):
        csv_save_path = os.path.join(doc_folder, full_filename + ".csv")
        combined_df.to_csv(csv_save_path, index=False, encoding="utf-8-sig")
        st.success(f"고객/항목 포함 견적 CSV 저장 완료: {csv_save_path}")

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
