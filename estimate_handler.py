from fpdf import FPDF
import datetime
import os

class EstimateHandler:
    def __init__(self, doc_folder="견적서_이력"):
        self.doc_folder = doc_folder
        
    def process_selected_items(self, df, selected_quantities):
        """선택된 항목 처리 및 계산"""
        selected_items = []
        # 컬럼명 공백 제거
        df.columns = df.columns.str.strip()
        
        for cat in df['분류'].unique():
            sub_df = df[df['분류'] == cat].reset_index(drop=True)
            for i, row in sub_df.iterrows():
                qty = selected_quantities.get(f"qty_{cat}_{i}", 0)
                if qty > 0:
                    # 기본단가에서 쉼표 제거하고 숫자로 변환
                    unit_price = int(str(row['기본단가']).replace(',', '').strip())
                    selected_items.append({
                        "항목코드": row['항목코드'],
                        "품목명": row['품목명'],
                        "단위": row['단위'],
                        "수량": qty,
                        "단가": unit_price,
                        "금액": qty * unit_price
                    })
        return selected_items

    def calculate_total(self, selected_items):
        """총액 계산"""
        return sum([item['수량'] * item['단가'] for item in selected_items])

    def generate_pdf(self, filename, customer_info, company_info, selected_items, total):
        """PDF 견적서 생성"""
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("ArialUnicode", '', "arialuni.ttf", uni=True)
        pdf.set_font("ArialUnicode", size=12)

        # 제목
        pdf.cell(200, 10, txt="견적서", ln=True, align="C")
        pdf.ln(10)

        # 고객 정보
        pdf.set_font("ArialUnicode", size=10)
        pdf.cell(200, 10, txt=f"고객사: {customer_info['고객사명']} | 건명: {customer_info['건명']}", ln=True)
        pdf.cell(200, 10, txt=f"담당자: {customer_info['담당자명']} ({customer_info['직위']}) / {customer_info['전화번호']} / {customer_info['이메일']}", ln=True)
        pdf.cell(200, 10, txt=f"견적일자: {datetime.date.today()} | 납품기간: {customer_info['납품기간']} | 하자기간: {customer_info['하자기간']}", ln=True)
        
        # 당사 정보
        pdf.cell(200, 10, txt=f"견적담당자: {company_info['견적담당자명']} ({company_info['견적담당자직위']}) / {company_info['견적담당자전화번호']} / {company_info['견적담당자이메일']}", ln=True)
        pdf.ln(10)

        # 견적 항목 테이블 헤더
        pdf.set_font("ArialUnicode", style='', size=10)
        pdf.cell(10, 8, txt="No", border=1, align='C')
        pdf.cell(30, 8, txt="항목코드", border=1, align='C')
        pdf.cell(60, 8, txt="품목명", border=1, align='C')
        pdf.cell(20, 8, txt="단위", border=1, align='C')
        pdf.cell(20, 8, txt="수량", border=1, align='C')
        pdf.cell(30, 8, txt="단가", border=1, align='C')
        pdf.cell(30, 8, txt="금액", border=1, align='C')
        pdf.ln()

        # 견적 항목 데이터
        for idx, item in enumerate(selected_items, 1):
            pdf.cell(10, 8, txt=str(idx), border=1, align='C')
            pdf.cell(30, 8, txt=item['항목코드'], border=1, align='C')
            pdf.cell(60, 8, txt=item['품목명'], border=1, align='L')
            pdf.cell(20, 8, txt=item['단위'], border=1, align='C')
            pdf.cell(20, 8, txt=str(item['수량']), border=1, align='R')
            pdf.cell(30, 8, txt=f"{item['단가']:,}", border=1, align='R')
            pdf.cell(30, 8, txt=f"{item['수량'] * item['단가']:,}", border=1, align='R')
            pdf.ln()

        # 총액
        pdf.ln(10)
        pdf.set_font("ArialUnicode", size=11)
        pdf.cell(200, 10, txt=f"총 금액 (VAT 별도): {total:,.0f}₩", ln=True, align='R')

        # 특이사항
        pdf.ln(10)
        pdf.set_font("ArialUnicode", size=10)
        pdf.cell(200, 10, txt="특이사항:", ln=True)
        pdf.ln(5)
        
        # 기본 특이사항
        pdf.cell(200, 8, txt=f"1. 납품기간: {customer_info['납품기간']}", ln=True)
        pdf.cell(200, 8, txt=f"2. 하자보증: {customer_info['하자기간']}", ln=True)
        pdf.cell(200, 8, txt="3. 부가세는 별도입니다.", ln=True)
        
        # 추가 특이사항
        if company_info.get('특이사항'):
            for idx, line in enumerate(company_info['특이사항'].split('\n'), 4):
                if line.strip():
                    pdf.cell(200, 8, txt=f"{idx}. {line.strip()}", ln=True)

        # PDF 저장
        pdf_path = os.path.join(self.doc_folder, f"{filename}.pdf")
        pdf.output(pdf_path)
        return pdf_path 