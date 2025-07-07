import streamlit as st
import pandas as pd
from data_manager import DataManager
from estimate_handler import EstimateHandler
from estimate_template import EstimateTemplate
import datetime
import webbrowser
import os
import re
from database import Database

class MainApp:
    def __init__(self):
        st.set_page_config(page_title="AI 견적서 생성기", layout="wide")
        self.data_manager = DataManager()
        self.estimate_handler = EstimateHandler()
        self.df = self.data_manager.load_base_items()
        # expanded 상태를 session state에 초기화
        st.session_state.setdefault('expanded_categories', {})

    def format_history_item(self, item):
        """견적서 이력 항목 포맷팅"""
        # 파일명��� 있는 경우 파일명을 기반으로 표시
        if item['파일명']:
            return f"{item['파일명']} - {item['총금액']:,.0f}원"
        
        # 파일명이 없는 경우 기존 형식으로 표시 (이전 데이터 호환성)
        status = item['최신본여부']
        date_str = item['견적일자'] if item['견적일자'] else item['생성일자'][:10]
        return f"{item['고객사명']} - {item['건명']} ({date_str}) {status}"

    def render_sidebar(self):
        """사이드바 렌더링 - 견적서 이력 관리"""
        st.sidebar.subheader("📁 견적서 이력")
        history = self.data_manager.get_estimate_history()
        
        if history:
            # 견적서 이력을 최신 순으로 정렬 (생성일자 기준)
            formatted_history = sorted(history, 
                key=lambda x: x['생성일자'], reverse=True)
            
            # 선택된 견적서 불러오기
            selected_estimate = st.sidebar.selectbox(
                "견적 이력 선택",
                formatted_history,
                format_func=self.format_history_item
            )
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("📂 견적 불러오기"):
                    estimate_data, items_data = self.data_manager.load_estimate(selected_estimate['estimate_id'])
                    self.load_estimate_to_session(estimate_data, items_data)
                    st.success(f"✅ 불러오기 완료: {selected_estimate['건명']} → 편집 가능 상태로 전환되었습니다.")
            
            with col2:
                if st.button("🔄 초기화"):
                    self.clear_session_state()
                    st.rerun()
        else:
            st.sidebar.info("저장된 견적 이력이 없습니다.")
            if st.sidebar.button("🔄 초기화"):
                self.clear_session_state()
                st.rerun()

    def clear_session_state(self, silent=False):
        """세션 스테이트 초기화"""
        # 1. 일반 정보 필드와 관련된 키를 세션에서 삭제
        keys_to_delete = [
            key for key in st.session_state.keys()
            if not key.startswith('_') and not key.startswith('qty_')
        ]
        for key in keys_to_delete:
            del st.session_state[key]

        # 2. 모든 수량 위젯의 상태를 0으로 강제 설정
        for key in list(st.session_state.keys()):
            if key.startswith('qty_'):
                st.session_state[key] = 0
        
        # 3. Expander 상태 초기화 (모두 닫기)
        st.session_state['expanded_categories'] = {}
        
        if not silent:
            st.session_state.message = "✨ 모든 입력 필드가 초기화되었습니다."

    def render_customer_info(self):
        """고객 정보 입력 섹션"""
        st.subheader("👤 고객 정보")
        
        # 고객 정보를 한 컬럼으로 통합
        customer_info = {
            "고객사명": st.text_input("고객사명", 
                value=st.session_state.get('customer_company_name', ''),
                key="customer_company_name"),
            "건명": st.text_input("건명 (프로젝트명)", 
                value=st.session_state.get('customer_project_name', ''),
                key="customer_project_name"),
            "담당자명": st.text_input("담당자명/직위", 
                value=st.session_state.get('customer_manager_name', ''),
                key="customer_manager_name"),
            "이메일": st.text_input("이메일", 
                value=st.session_state.get('customer_email', ''),
                key="customer_email"),
            "전화번호": st.text_input("전화번호", 
                value=st.session_state.get('customer_phone', ''),
                key="customer_phone"),
            "견적일자": st.date_input("견적일자",
                value=st.session_state.get('estimate_date', datetime.date.today()),
                key="estimate_date"),
            "납품기간": st.text_input("납품기간", 
                value=st.session_state.get('delivery_period', ''),
                key="delivery_period"),
            "하자기간": st.text_input("하자기간", 
                value=st.session_state.get('warranty_period', ''),
                key="warranty_period")
        }
            
        # 담당자명/직위 분리
        if '/' in customer_info['담당자명']:
            customer_info['담당자명'], customer_info['직위'] = map(str.strip, customer_info['담당자명'].split('/'))
        else:
            # 공백으로 구분된 경우 마지막 단어를 직위로 처리
            parts = customer_info['담당자명'].strip().split()
            if len(parts) > 1:
                customer_info['직위'] = parts[-1]
                customer_info['담당자명'] = ' '.join(parts[:-1])
            else:
                customer_info['직위'] = ''
            
        return customer_info

    def render_company_info(self):
        """당사 정보 입력 섹션"""
        st.subheader("🏢 당사 정보")
        
        # 당사 정보를 한 컬럼으로 통합
        company_info = {
            "견적담당자명": st.text_input("담당자명/직위", 
                value=st.session_state.get('company_manager_name', ''),
                key="company_manager_name"),
            "견적담당자이메일": st.text_input("이메일", 
                value=st.session_state.get('company_email', ''),
                key="company_email"),
            "견적담당자전화번호": st.text_input("전화번호", 
                value=st.session_state.get('company_phone', ''),
                key="company_phone"),
            "특이사항": st.text_area("특이사항", 
                value=st.session_state.get('special_notes', ''),
                height=150,
                help="견적서에 포함될 특이사항을 입력하세요. (예: 납품조건, 결제조건 등)",
                key="special_notes"),
            "홈페이지": "http://www.solu.co.kr"
        }
            
        # 담당자명/직위 분리
        if '/' in company_info['견적담당자명']:
            name, position = map(str.strip, company_info['견적담당자명'].split('/'))
            company_info['견적담당자명'] = name
            company_info['견적담당자직위'] = position
        else:
            # 공백으로 구분된 경우 마지막 단어를 직위로 처리
            parts = company_info['견적담당자명'].strip().split()
            if len(parts) > 1:
                company_info['견적담당자직위'] = parts[-1]
                company_info['견적담당자명'] = ' '.join(parts[:-1])
            else:
                company_info['견적담당자직위'] = ''
            
        return company_info

    def render_item_selection(self):
        """견적 항목 선택 및 검색 섹션"""
        st.subheader("1️⃣ 견적 항목 선택")
        
        # 검색어 입력
        search_term = st.text_input("항목 검색 (품목명, 코드, 설명)", 
                                    key="search_term", 
                                    value=st.session_state.get('search_term', ''))
        
        # 검색어에 따라 데이터프레임 필터링
        if search_term:
            filtered_df = self.df[
                self.df['품목명'].str.contains(search_term, case=False, na=False) |
                self.df['항목코드'].str.contains(search_term, case=False, na=False) |
                self.df['설명'].str.contains(search_term, case=False, na=False)
            ]
        else:
            filtered_df = self.df

        selected_quantities = {}
        
        # 초기화 시 모든 expander를 닫기 위해 상태 관리
        if 'expanded_categories' not in st.session_state:
            st.session_state['expanded_categories'] = {cat: False for cat in filtered_df['분류'].unique()}

        for cat in filtered_df['분류'].unique():
            # 각 expander의 상태를 session_state에서 가져옴
            is_expanded = st.session_state['expanded_categories'].get(cat, False)
            
            with st.expander(f"📂 {cat} 항목 보기", expanded=is_expanded):
                sub_df = filtered_df[filtered_df['분류'] == cat].reset_index(drop=True)
                for i, row in sub_df.iterrows():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**[{row['품목명']}] {row['항목코드']}**")
                        st.markdown(f"{row['설명']}")
                    with col2:
                        default_qty = st.session_state.get(f"qty_{cat}_{i}", 0)
                        qty = st.number_input(
                            f"수량 ({row['단위']}) - {row['항목코드']}", 
                            min_value=0, 
                            step=1,
                            value=default_qty,
                            key=f"qty_{cat}_{i}"
                        )
                        selected_quantities[f"qty_{cat}_{i}"] = qty
                        
        return selected_quantities

    def validate_inputs(self, customer_info, company_info):
        """입력값 유효성 검사"""
        # 필수 항목 검사
        if not customer_info['고객사명'] or not customer_info['건명']:
            st.warning("⚠️ '고객사명'과 '건명'은 필수 입력 항목입니다.")
            return False
            
        # 이메일 형식 검사
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if customer_info['이메일'] and not re.match(email_pattern, customer_info['이메일']):
            st.warning(f"⚠️ 고객 이메일 형식이 올바르지 않습니다: {customer_info['이메일']}")
            return False
        if company_info['견적담당자이메일'] and not re.match(email_pattern, company_info['견적담당자이메일']):
            st.warning(f"⚠️ 당사 담당자 이메일 형식이 올바르지 않습니다: {company_info['견적담당자이메일']}")
            return False
            
        # 전화번호 형식 검사 (간단한 숫자 및 하이픈 검사)
        phone_pattern = r"^[\d-]{10,13}$"
        if customer_info['전화번호'] and not re.match(phone_pattern, customer_info['전화번호']):
            st.warning(f"⚠️ 고객 전화번호 형식이 올바르지 않습니다: {customer_info['전화번호']}")
            return False
        if company_info['견적담당자전화번호'] and not re.match(phone_pattern, company_info['견적담당자전화번호']):
            st.warning(f"⚠️ 당사 담당자 전화번호 형식이 올바르지 않습니다: {company_info['견적담당자전화번호']}")
            return False
            
        return True

    def generate_filename(self, customer_info, version):
        """견적서 파일명 생성"""
        # 견적일자 가져오기
        estimate_date = customer_info['견적일자']
        if isinstance(estimate_date, str):
            try:
                estimate_date = datetime.datetime.strptime(estimate_date, "%Y-%m-%d").date()
            except ValueError:
                estimate_date = datetime.date.today()
        elif not isinstance(estimate_date, datetime.date):
            estimate_date = datetime.date.today()
            
        # 날짜 형식 변환 (YYYY-MM-DD)
        date_str = estimate_date.strftime("(%Y-%m-%d)")
        
        # 고객사명과 건명 가져오기 (특수문자 제거)
        company_name = ''.join(e for e in customer_info['고객사명'] if e.isalnum() or e.isspace())
        project_name = ''.join(e for e in customer_info['건명'] if e.isalnum() or e.isspace())
        
        # 공백 제거 및 기본값 설정
        company_name = company_name.strip()
        project_name = project_name.strip()
        
        if not company_name:
            company_name = "NoCompany"
        if not project_name:
            project_name = "NoProject"
            
        # 건명은 앞 4자리만 사용
        project_name = project_name[:4]
            
        # 파일명 구성: (YYYY-MM-DD)고객사명_건명4자_버전
        return f"{date_str}{company_name}_{project_name}_{version}"

    def render_results(self, selected_items, customer_info, company_info):
        """견적 결과 및 저장 섹션"""
        if not selected_items:
            return
            
        st.subheader("2️⃣ 견적 결과")
        total = self.estimate_handler.calculate_total(selected_items)
        
        # 견적 테이블 표시
        result_df = pd.DataFrame(selected_items)
        
        # 일련번호 추가 (1부터 시작)
        result_df.index = range(1, len(result_df) + 1)
        result_df.index.name = 'No'
        
        # 단가와 금액에 천단위 구분 콤마와 통화 표시 추가
        result_df["수량"] = result_df["수량"].astype(int)
        result_df["단가"] = result_df["단가"].apply(lambda x: f"{x:,.0f}₩")
        result_df["금액"] = result_df["금액"].apply(lambda x: f"{x:,.0f}₩")
        
        # 테이블 스타일 설정
        st.markdown("""
            <style>
            .dataframe td:nth-child(5), 
            .dataframe td:nth-child(6),
            .dataframe td:nth-child(7) {
                text-align: right !important;
            }
            .dataframe th {
                text-align: center !important;
            }
            .dataframe td:first-child {
                text-align: center !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.table(result_df)
        st.success(f"💰 총 견적 금액 (VAT 별도): {total:,.0f}₩")

        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 현재 견적서의 버전 정보 확인
            current_id = st.session_state.get('current_estimate_id')
            if current_id:
                current_version = self.data_manager.get_estimate_version(current_id)
                next_version = f"v{current_version + 1}" if not st.session_state.get('is_final') else "final"
            else:
                next_version = "v1"
            
            version = st.text_input("버전", 
                value=next_version,
                key="version_input",
                disabled=st.session_state.get('is_final', False))
        
        with col2:
            is_final = st.checkbox("최종본", 
                value=st.session_state.get('is_final', False),
                key="is_final_checkbox")
            
            if is_final:
                version = "final"
                
        # 견적서 파일명 생성
        filename = self.generate_filename(customer_info, version)

        # --- 버튼 섹션 ---
        col1, col2, col3, col4 = st.columns(4)

        # 견적서 저장
        with col1:
            if st.button("💾 견적서 저장"):
                if self.validate_inputs(customer_info, company_info):
                    meta_data = {**customer_info, **company_info, "총금액": total, "is_final": is_final}
                    parent_id = st.session_state.get('current_estimate_id')
                    try:
                        estimate_id = self.data_manager.save_estimate(
                            meta_data, 
                            selected_items, 
                            filename,
                            parent_id
                        )
                        if estimate_id:
                            st.session_state['current_estimate_id'] = estimate_id
                            st.session_state['is_final'] = is_final
                            st.success(f"✅ 견적서 저장 완료: {filename}")
                            st.session_state['refresh_sidebar'] = True
                            st.rerun()
                        else:
                            st.error("견적서 저장에 실패했습니다.")
                    except Exception as e:
                        st.error(f"견적서 저장 중 오류가 발생했습니다: {str(e)}")

        # HTML 견적서 생성
        with col2:
            if st.button("📄 견적서 HTML 생성"):
                html_content = EstimateTemplate.generate_html(
                    customer_info, company_info, selected_items, total
                )
                html_path = EstimateTemplate.save_html(html_content, filename, self.data_manager.doc_folder)
                webbrowser.open(f'file://{os.path.abspath(html_path)}')
                st.success(f"✅ 견적서 HTML 생성 완료: {html_path}")

        # PDF 생성
        with col3:
            if st.button("📄 견적서 PDF 다운로드"):
                pdf_path = self.estimate_handler.generate_pdf(
                    filename, customer_info, company_info, selected_items, total
                )
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=f,
                        file_name=f"{filename}.pdf",
                        mime="application/pdf"
                    )
        
        # 견적서 미리보기
        with col4:
            if st.button("👁️ 견적서 미리보기"):
                st.session_state['show_preview'] = True

        if st.session_state.get('show_preview', False):
            with st.expander("견적서 미리보기", expanded=True):
                html_content = EstimateTemplate.generate_html(
                    customer_info, company_info, selected_items, total
                )
                st.markdown(html_content, unsafe_allow_html=True)
                if st.button("미리보기 닫기"):
                    st.session_state['show_preview'] = False
                    st.rerun()


    def load_estimate_to_session(self, estimate_data, items_data):
        """불러온 견적서 데이터를 세션에 저장"""
        # 기존 세션 초기화 (메시지 없이)
        self.clear_session_state(silent=True)
        
        # 불러온 데이터로 세션 업데이트
        st.session_state['loaded_items'] = items_data
        st.session_state['current_estimate_id'] = estimate_data.get('estimate_id')
        st.session_state['is_final'] = estimate_data.get('is_final', False)
        
        # 고객 정보와 회사 정보를 세션에 저장
        for key, value in estimate_data.items():
            session_key_map = {
                '고객사명': 'customer_company_name', '건명': 'customer_project_name',
                '담당자명': 'customer_manager_name', '이메일': 'customer_email',
                '전화번호': 'customer_phone', '납품기간': 'delivery_period',
                '하자기간': 'warranty_period', '견적담당자명': 'company_manager_name',
                '견적담당자이메일': 'company_email', '견적담당자전화번호': 'company_phone',
                '특이사항': 'special_notes'
            }
            if key in session_key_map:
                st.session_state[session_key_map[key]] = value
            
            if key == '견적일자' and value:
                st.session_state['estimate_date'] = datetime.datetime.strptime(value, "%Y-%m-%d").date()

        # 수량 정보 업데이트
        for item in items_data:
            for cat in self.df['분류'].unique():
                sub_df = self.df[self.df['분류'] == cat].reset_index(drop=True)
                for i, row in sub_df.iterrows():
                    if row['항목코드'] == item['항목코드']:
                        st.session_state[f"qty_{cat}_{i}"] = item['수량']


    def run(self):
        """메인 애플리케이션 실행"""
        st.title("📄 견적서 생성 및 이력 관리")
        
        if 'message' in st.session_state:
            st.success(st.session_state.message, icon="🧼")
            del st.session_state.message
            
        # 사이드바 너비 조정을 위한 CSS 주입
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] {
                width: 540px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        self.render_sidebar()
        customer_info = self.render_customer_info()
        company_info = self.render_company_info()
        selected_quantities = self.render_item_selection()
        
        selected_items = self.estimate_handler.process_selected_items(self.df, selected_quantities)
        self.render_results(selected_items, customer_info, company_info)

if __name__ == "__main__":
    app = MainApp()
    app.run() 