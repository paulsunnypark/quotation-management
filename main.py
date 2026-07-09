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
from catalog_db import CatalogDB
import cpq_engine as cpq

class MainApp:
    def __init__(self):
        st.set_page_config(page_title="AI 견적서 생성기", layout="wide")
        self.data_manager = DataManager()
        self.estimate_handler = EstimateHandler()
        self.df = self.data_manager.load_base_items()
        # Track B 카탈로그: package_price.xlsx(또는 CSV)로부터 매 기동 시 재생성 → 수정 즉시 반영
        self.catalog = CatalogDB()
        self.catalog.rebuild()
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
                placeholder="예) 홍길동 / 부장",
                key="customer_manager_name"),
            "이메일": st.text_input("이메일",
                value=st.session_state.get('customer_email', ''),
                placeholder="예) hong@example.co.kr",
                key="customer_email"),
            "전화번호": st.text_input("전화번호",
                value=st.session_state.get('customer_phone', ''),
                placeholder="예) 010-1234-5678",
                key="customer_phone"),
            "견적일자": st.date_input("견적일자",
                value=st.session_state.get('estimate_date', datetime.date.today()),
                key="estimate_date"),
            "납품기간": st.text_input("납품기간",
                value=st.session_state.get('delivery_period', ''),
                placeholder="예) 발주 후 30일",
                key="delivery_period"),
            "하자기간": st.text_input("하자기간",
                value=st.session_state.get('warranty_period', ''),
                placeholder="예) 구축 후 12개월",
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
                placeholder="예) 황호성 / 이사",
                key="company_manager_name"),
            "견적담당자이메일": st.text_input("이메일",
                value=st.session_state.get('company_email', ''),
                placeholder="예) sales@solu.co.kr",
                key="company_email"),
            "견적담당자전화번호": st.text_input("전화번호",
                value=st.session_state.get('company_phone', ''),
                placeholder="예) 010-7672-4006",
                key="company_phone"),
            "특이사항": st.text_area("특이사항",
                value=st.session_state.get('special_notes', ''),
                height=150,
                placeholder="예) 1. 결제조건: 현금결제\n2. 유효기간: 견적 후 1개월",
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
                        qty_key = f"qty_{row['항목코드']}"
                        default_qty = st.session_state.get(qty_key, 0)
                        qty = st.number_input(
                            f"수량 ({row['단위']}) - {row['항목코드']}", 
                            min_value=0, 
                            step=1,
                            value=default_qty,
                            key=qty_key
                        )
                        selected_quantities[qty_key] = qty
                        
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
                
        # 견적서 파일명 생성 (트랙 표기 TB-A + 버전)
        filename = self.generate_filename(customer_info, f"TB-A_{version}")

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


    def render_track_b(self, customer_info, company_info):
        """Track B - 신규 패키지 CPQ 견적 (명분 추천 + 예산대 프리셋 + 이중가격 + 할인검증)"""
        # 0) 공공가치(명분) 기반 제안
        st.subheader("0️⃣ 공공가치 / 사업 명분 선택")
        svcs = self.catalog.get_service_packages()
        svc_labels = {f"{s['순위']}. {s['서비스명']} ({s['목표가격대']})": s for s in svcs}
        svc_label = st.selectbox("공공 서비스 명분 (선택)", ["(선택 안 함)"] + list(svc_labels.keys()))
        recommended = None
        if svc_label != "(선택 안 함)":
            svc = svc_labels[svc_label]
            recommended = cpq.suggest_preset(svc['서비스명'])
            st.markdown(f"**공공 명분:** {svc['공공명분']}")
            st.markdown(f"**조합 제품:** {svc['조합제품']}  ·  **주요 수요처:** {svc['주요수요처']}")
            st.success(f"📑 납품요구명 예시: **{svc['납품요구명_예시']}**  → 추천 예산대 **{recommended}**")

        st.subheader("1️⃣ 예산대 패키지 선택")

        presets = self.catalog.get_connection()
        try:
            preset_rows = [dict(r) for r in presets.execute(
                'SELECT * FROM package_presets ORDER BY "프리셋코드"')]
        finally:
            presets.close()

        labels = {f"{p['프리셋코드']}. {p['패키지명']} (권장 {p['권장가격대']})": p['프리셋코드']
                  for p in preset_rows}
        label_keys = list(labels.keys())
        default_idx = 0
        if recommended:
            default_idx = next((i for i, k in enumerate(label_keys)
                                if labels[k] == recommended), 0)
        chosen_label = st.selectbox("예산대 프리셋", label_keys, index=default_idx)
        preset_code = labels[chosen_label]

        # 프리셋 변경 시 라인 새로 적재 (불러온 견적은 1회 보존)
        if st.session_state.pop('tb_loaded', False):
            st.session_state['tb_preset'] = preset_code
        elif st.session_state.get('tb_preset') != preset_code:
            st.session_state['tb_preset'] = preset_code
            st.session_state['tb_lines'] = cpq.load_preset_lines(preset_code, self.catalog)

        lines = st.session_state['tb_lines']

        st.subheader("2️⃣ 구성 항목 (수량 조정 가능)")
        edit_df = pd.DataFrame([{
            '항목코드': l.get('항목코드', ''),
            '계층': l['계층'], '품목명': l['품목명'], '조달상태': l['조달상태'],
            '식별번호': l['식별번호'], '단위': l['단위'],
            '수량': l['수량'], '제안단가': l['제안단가'], '공급단가': l['공급단가'],
        } for l in lines])
        edited = st.data_editor(
            edit_df, key='tb_editor', use_container_width=True, hide_index=True,
            disabled=['항목코드', '계층', '품목명', '조달상태', '식별번호', '단위', '제안단가', '공급단가'],
            column_config={
                '수량': st.column_config.NumberColumn("수량", min_value=0, step=1, format="%d"),
                '제안단가': st.column_config.NumberColumn(format="%d"),
                '공급단가': st.column_config.NumberColumn(format="%d"),
            })
        # 수량 반영 후 재계산
        for i, l in enumerate(lines):
            l['수량'] = int(edited.iloc[i]['수량'])
            cpq.recompute_line(l)

        st.subheader("3️⃣ 할인 및 가격")
        col1, col2 = st.columns(2)
        with col1:
            grade = st.selectbox("파트너 등급", [
                '일반 리셀러', '인증 파트너', '전략 파트너', 'KT급 우호 파트너'])
        with col2:
            discount = st.slider("할인율(%)", 0, 30, 0, 1, format="%d%%") / 100

        ok, limit, msg = cpq.validate_discount(discount, grade, self.catalog)
        (st.success if ok else st.error)(msg)

        totals = cpq.compute_totals(lines, discount)
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**제안 합계**<br>{totals['제안합계']:,}원", unsafe_allow_html=True)
        c2.markdown(f"**할인 후 제안가 ({discount:.0%})**<br>{totals['제안가_할인후']:,}원", unsafe_allow_html=True)
        c3.markdown(f"**유통 공급가**<br>{totals['공급합계']:,}원", unsafe_allow_html=True)
        c4.markdown(f"**예상 마진**<br>{totals['마진']:,}원", unsafe_allow_html=True)

        # 녹취 기반 검증 (신규 standalone vs 기존 add-on)
        existing_customer = st.checkbox(
            "기존 IPX-Series 보유 고객 (녹취 기반 보유 → 분석 add-on 견적)",
            key='tb_existing')
        if not existing_customer and cpq.recording_base_status(lines) == "missing":
            st.error(f"⚠️ {cpq.RECORDING_MISSING_MSG}")

        # VR 중복방지 문구
        note = cpq.vr_overlap_note(lines)
        if note:
            st.info(f"📌 중복과금 방지 표준문구\n\n{note}")

        # 6계층 구성 요약 (사업전략 v4: 단일 SKU → 6계층)
        tb = cpq.tier_breakdown(lines)
        if tb:
            st.markdown("🧱 **계층별 구성:** " +
                        "  ·  ".join(f"{t} {amt:,}원" for t, amt in tb.items()))

        # 식별번호 조합표
        bd = cpq.reg_status_breakdown(lines)
        with st.expander("📋 식별번호 조합 (등록/신규후보/커스터마이징)"):
            for status, items in bd.items():
                if items:
                    st.markdown(f"**{status}**: {', '.join(items)}")

        # 4) 제출 전 체크리스트
        st.subheader("4️⃣ 제출 전 체크리스트")
        svc_name = customer_info.get('건명') or (
            svc_label if svc_label != "(선택 안 함)" else "")
        approver = st.text_input("할인 승인권자 (할인 적용 시 필수)", key='tb_approver')
        checks = cpq.submission_checklist(lines, svc_name, discount, approver,
                                          existing_customer=existing_customer)
        all_ok = all(ok for _, ok in checks)
        for label, ok in checks:
            st.markdown(f"{'✅' if ok else '⚠️'} {label}")

        # 5) 견적 저장 (Track B, track='B' + 확장 컬럼)
        st.subheader("5️⃣ 견적 저장")
        if st.button("💾 Track B 견적 저장"):
            if self.validate_inputs(customer_info, company_info):
                items_payload = [{
                    '항목코드': l.get('항목코드') or l['식별번호'] or l['품목명'][:20],
                    '품목명': l['품목명'], '단위': l['단위'],
                    '수량': l['수량'], '단가': l['제안단가'], '금액': l['제안금액'],
                    'tier': l['계층'], 'identifier_no': l['식별번호'],
                    'reg_status': l['조달상태'], 'proposed_price': l['제안단가'],
                    'supply_price': l['공급단가'], 'discount_rate': discount,
                } for l in lines]
                meta = {**customer_info, **company_info,
                        '총금액': totals['제안가_할인후'], 'is_final': False}
                # 버전 계산 (재저장 시 누적)
                tb_id = st.session_state.get('tb_estimate_id')
                ver = f"v{self.data_manager.get_estimate_version(tb_id) + 1}" if tb_id else "v1"
                save_name = self.generate_filename(customer_info, f"TB-B-{preset_code}_{ver}")
                try:
                    eid = self.data_manager.save_estimate(
                        meta, items_payload, save_name,
                        parent_id=tb_id, track='B')
                    st.session_state['tb_estimate_id'] = eid
                    st.success(f"✅ Track B 견적 저장 완료: {save_name} (id={eid})")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

        # 6) 견적서 출력 (업체용/소비자용 2종)
        st.subheader("6️⃣ 견적서 출력")
        import quote_export as qx
        os.makedirs(self.data_manager.doc_folder, exist_ok=True)
        base = self.generate_filename(customer_info, f"TB-{preset_code}")
        if st.button("📊 Excel 견적서 생성 (업체용+소비자용 2시트)"):
            if not all_ok:
                st.warning("⚠️ 체크리스트 미통과 항목이 있습니다. 확인 후 제출하세요.")
            path = os.path.join(self.data_manager.doc_folder, f"{base}.xlsx")
            qx.export_excel(path, customer_info, company_info, lines, note=note)
            with open(path, "rb") as f:
                st.download_button("📥 Excel 다운로드", f.read(), file_name=f"{base}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.success(f"✅ 생성 완료: {path}")
        if st.button("📄 PDF 견적서 생성 (소비자용)"):
            path = os.path.join(self.data_manager.doc_folder, f"{base}.pdf")
            qx.export_pdf(path, customer_info, company_info, lines, kind="소비자용", note=note)
            with open(path, "rb") as f:
                st.download_button("📥 PDF 다운로드", f.read(), file_name=f"{base}.pdf",
                                   mime="application/pdf")
            st.success(f"✅ 생성 완료: {path}")

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

        # Track B 견적이면 패키지 편집기로 복원
        if estimate_data.get('track') == 'B':
            lines = []
            for it in items_data:
                proposed = it.get('proposed_price') or it['단가']
                supply = it.get('supply_price') or round(proposed * 0.6)
                ratio = round(supply / proposed, 4) if proposed else 0.6
                lines.append({
                    '항목코드': it.get('항목코드') or it.get('item_code') or '',
                    '품목명': it['품목명'], '계층': it.get('tier') or 'Module',
                    '조달상태': it.get('reg_status') or '', '식별번호': it.get('identifier_no') or '',
                    '단위': it['단위'], '수량': it['수량'],
                    '제안단가': proposed, '제안금액': proposed * it['수량'],
                    '공급가율': ratio, '공급단가': supply, '공급금액': supply * it['수량'],
                    '비고': '', '매칭': True,
                })
            st.session_state['tb_lines'] = lines
            st.session_state['tb_loaded'] = True            # 프리셋 재적재 방지
            st.session_state['tb_estimate_id'] = estimate_data.get('estimate_id')
            st.session_state['quote_mode'] = "신규 패키지 CPQ (Track B)"
            return

        # Track A: 모드 전환 + 수량 정보 업데이트
        st.session_state['quote_mode'] = "레거시 단가합산 (Track A)"
        for item in items_data:
            for cat in self.df['분류'].unique():
                sub_df = self.df[self.df['분류'] == cat].reset_index(drop=True)
                for i, row in sub_df.iterrows():
                    if row['항목코드'] == item['항목코드']:
                        st.session_state[f"qty_{row['항목코드']}"] = item['수량']


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

        # 견적 모드 선택 (이원화) - 불러온 Track B 견적은 자동 전환(key='quote_mode')
        mode = st.radio(
            "견적 모드",
            ["레거시 단가합산 (Track A)", "신규 패키지 CPQ (Track B)"],
            horizontal=True,
            key='quote_mode',
            help="Track A: 기존 단가합산 방식 / Track B: 예산대 패키지·이중가격·할인검증",
        )

        customer_info = self.render_customer_info()
        company_info = self.render_company_info()

        if mode.startswith("신규"):
            self.render_track_b(customer_info, company_info)
        else:
            selected_quantities = self.render_item_selection()
            selected_items = self.estimate_handler.process_selected_items(self.df, selected_quantities)
            self.render_results(selected_items, customer_info, company_info)

if __name__ == "__main__":
    app = MainApp()
    app.run()
