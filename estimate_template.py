from jinja2 import Template
import datetime
import os

class EstimateTemplate:
    @staticmethod
    def get_html_template():
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>견적서</title>
    <style>
        body { font-family: 'Malgun Gothic', sans-serif; margin: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .logo { width: 150px; }
        .title { 
            background-color: #90EE90;
            text-align: center;
            padding: 10px;
            font-size: 24px;
            margin: 20px 0;
        }
        .info-section {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .info-box {
            width: 48%;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            border: 1px solid black;
            padding: 8px;
            text-align: center;
        }
        th {
            background-color: #FFD700;
        }
        td.text-right {
            text-align: right;
        }
        td.text-left {
            text-align: left;
        }
        .total {
            text-align: right;
            font-weight: bold;
            margin: 20px 0;
        }
        .footer {
            margin-top: 30px;
            font-size: 0.9em;
        }
        .remarks {
            margin: 20px 0;
        }
        .company-info {
            text-align: center;
            margin-top: 30px;
            font-size: 0.8em;
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="https://www.solu.co.kr/images/common/logo.png" alt="SOLU TECH" class="logo">
        <div style="text-align: right;">Leader of Voice & P</div>
    </div>
    
    <div class="title">QUOTATION</div>
    
    <div class="info-section">
        <div class="info-box">
            <strong>Attention to : </strong>{{ customer_info['고객사명'] }}<br>
            건명: {{ customer_info['건명'] }}<br>
            담당자: {{ customer_info['담당자명'] }} {{ customer_info['직위'] }}<br>
            이메일: {{ customer_info['이메일'] }}<br>
            전화번호: {{ customer_info['전화번호'] }}<br>
            작성일자: {{ today }}<br>
            유효기간: {{ validity_period }}
        </div>
        <div class="info-box" style="text-align: right;">
            <strong>Contact us : </strong>솔루텍<br>
            서울시 강남구 거치대치길 1층 123 STV-V<br>
            Office: 02-2169-0100<br>
            담당자: {{ company_info['견적담당자명'] }} {{ company_info['견적담당자직위'] }}<br>
            Mobile: {{ company_info['견적담당자전화번호'] }}<br>
            이메일: {{ company_info['견적담당자이메일'] }}<br>
            홈페이지: {{ company_info['홈페이지'] }}
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>No</th>
                <th>품목/규격</th>
                <th>단위</th>
                <th>수량</th>
                <th>단가</th>
                <th>금액</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ loop.index }}</td>
                <td class="text-left">
                    [{{ item['항목코드'] }}] {{ item['품목명'] }}
                </td>
                <td>{{ item['단위'] }}</td>
                <td class="text-right">{{ item['수량'] }}</td>
                <td class="text-right">{{ "{:,}".format(item['단가']) }}원</td>
                <td class="text-right">{{ "{:,}".format(item['금액']) }}원</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="total">
        공급가액 합계: {{ "{:,}".format(total) }}원 (VAT 별도)
    </div>

    <div class="remarks">
        <strong>특이사항</strong>
        <ol>
            <li>납품기간: {{ customer_info['납품기간'] }}</li>
            <li>하자보증: {{ customer_info['하자기간'] }}</li>
            <li>부가세는 별도입니다.</li>
            {% if company_info['특이사항'] %}
            {% for line in company_info['특이사항'].split('\n') %}
            <li>{{ line }}</li>
            {% endfor %}
            {% endif %}
        </ol>
    </div>

    <div class="company-info">
        서울특별시 금천구 가산디지털 1로 128 STV-V<br>
        솔루텍 | TEL: 02-2169-0108 | FAX: 02-2169-0099
    </div>
</body>
</html>
"""

    @staticmethod
    def generate_html(customer_info, company_info, items, total):
        template = Template(EstimateTemplate.get_html_template())
        today = datetime.date.today().strftime("%Y년 %m월 %d일")
        
        # 유효기간 설정 (작성일로부터 30일)
        validity_date = datetime.date.today() + datetime.timedelta(days=30)
        validity_period = validity_date.strftime("%Y년 %m월 %d일")

        # HTML 생성
        html_content = template.render(
            customer_info=customer_info,
            company_info=company_info,
            items=items,
            total=total,
            today=today,
            validity_period=validity_period
        )
        
        return html_content

    @staticmethod
    def save_html(html_content, filename, doc_folder):
        """HTML 파일 저장"""
        os.makedirs(doc_folder, exist_ok=True)
        file_path = os.path.join(doc_folder, f"{filename}.html")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return file_path 