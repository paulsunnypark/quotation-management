import sqlite3
import uuid
from datetime import datetime
import os
import json

class Database:
    def __init__(self, db_file="quotation.db"):
        self.db_file = db_file
        self.create_tables()
    
    def get_connection(self):
        """데이터베이스 연결 생성"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하도록 설정
        return conn
    
    def create_tables(self):
        """데이터베이스 테이블 생성"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # estimates 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS estimates (
                estimate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                root_id INTEGER,
                parent_id INTEGER,
                filename TEXT NOT NULL,
                customer_info TEXT NOT NULL,
                company_info TEXT NOT NULL,
                total_amount REAL,
                is_final BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES estimates(estimate_id),
                FOREIGN KEY (root_id) REFERENCES estimates(estimate_id)
            )
            ''')
            
            # estimate_items 테이블 생성
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS estimate_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                estimate_id INTEGER NOT NULL,
                item_code TEXT,
                item_name TEXT,
                unit TEXT,
                quantity INTEGER,
                unit_price REAL,
                amount REAL,
                FOREIGN KEY (estimate_id) REFERENCES estimates(estimate_id)
            )
            ''')
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def get_estimate_version(self, estimate_id):
        """견적서의 현재 버전 번호 조회"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM estimates 
                WHERE root_id = (
                    SELECT root_id 
                    FROM estimates 
                    WHERE estimate_id = ?
                )
                AND created_at <= (
                    SELECT created_at 
                    FROM estimates 
                    WHERE estimate_id = ?
                )
            """, (estimate_id, estimate_id))
            version = cursor.fetchone()[0]
            return version
        finally:
            cursor.close()
            conn.close()

    def save_estimate(self, customer_info, company_info, items, total_amount, filename, parent_id=None, is_final=False):
        """견적서 저장"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 트랜잭션 시작
            conn.execute("BEGIN TRANSACTION")
            
            # 최상위 부모 ID 찾기 또는 설정
            root_id = None
            if parent_id:
                cursor.execute("SELECT root_id FROM estimates WHERE estimate_id = ?", (parent_id,))
                result = cursor.fetchone()
                if result:
                    root_id = result[0]
            
            # final 버전이 있는지 확인
            estimate_id = None
            if root_id:
                cursor.execute("""
                    SELECT estimate_id FROM estimates 
                    WHERE root_id = ? AND is_final = 1
                """, (root_id,))
                final_id = cursor.fetchone()
                
                if final_id and is_final:
                    # final 버전이 있으면 해당 ID를 사용
                    estimate_id = final_id[0]
                    # final 버전 업데이트
                    cursor.execute("""
                        UPDATE estimates SET
                        customer_info = ?,
                        company_info = ?,
                        total_amount = ?,
                        filename = ?,
                        updated_at = CURRENT_TIMESTAMP
                        WHERE estimate_id = ?
                    """, (json.dumps(customer_info), json.dumps(company_info), 
                         total_amount, filename, estimate_id))
                else:
                    # 새 버전 저장
                    cursor.execute("""
                        INSERT INTO estimates (
                            customer_info, company_info, total_amount, filename,
                            parent_id, root_id, is_final, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (json.dumps(customer_info), json.dumps(company_info), 
                         total_amount, filename, parent_id, root_id, is_final))
                    estimate_id = cursor.lastrowid
            else:
                # 최초 저장
                cursor.execute("""
                    INSERT INTO estimates (
                        customer_info, company_info, total_amount, filename,
                        is_final, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (json.dumps(customer_info), json.dumps(company_info), 
                     total_amount, filename, is_final))
                estimate_id = cursor.lastrowid
                
                # root_id 설정
                if estimate_id:
                    cursor.execute("""
                        UPDATE estimates SET root_id = ? WHERE estimate_id = ?
                    """, (estimate_id, estimate_id))
            
            if estimate_id:
                # 기존 아이템 삭제 (final 버전 업데이트의 경우)
                cursor.execute("DELETE FROM estimate_items WHERE estimate_id = ?", (estimate_id,))
                
                # 새 아이템 저장
                for item in items:
                    cursor.execute("""
                        INSERT INTO estimate_items (
                            estimate_id, item_code, item_name, unit, 
                            quantity, unit_price, amount
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (estimate_id, item['항목코드'], item['품목명'], 
                         item['단위'], item['수량'], item['단가'], item['금액']))
            
            # 트랜잭션 커밋
            conn.commit()
            return estimate_id
            
        except Exception as e:
            # 오류 발생 시 롤백
            conn.rollback()
            print(f"견적서 저장 중 오류 발생: {str(e)}")
            raise e
        finally:
            cursor.close()
            conn.close()

    def load_estimate(self, estimate_id):
        """견적서 불러오기"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 견적서 기본 정보 조회
            cursor.execute("""
                SELECT customer_info, company_info, total_amount, is_final, estimate_id
                FROM estimates WHERE estimate_id = ?
            """, (estimate_id,))
            row = cursor.fetchone()
            
            if not row:
                return None, None
                
            customer_info = json.loads(row[0])
            company_info = json.loads(row[1])
            estimate_data = {
                **customer_info,
                **company_info,
                'estimate_id': row[4],
                'is_final': row[3]
            }
            
            # 견적 항목 조회
            cursor.execute("""
                SELECT item_code, item_name, unit, quantity, unit_price, amount
                FROM estimate_items WHERE estimate_id = ?
            """, (estimate_id,))
            
            items = []
            for item_row in cursor.fetchall():
                items.append({
                    '항목코드': item_row[0],
                    '품목명': item_row[1],
                    '단위': item_row[2],
                    '수량': item_row[3],
                    '단가': item_row[4],
                    '금액': item_row[5]
                })
                
            return estimate_data, items
            
        finally:
            cursor.close()
            conn.close()

    def get_estimate_history(self):
        """견적서 이력 조회"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                WITH LatestVersions AS (
                    SELECT 
                        root_id, 
                        MAX(created_at) as latest_created_at,
                        MAX(CASE WHEN is_final = 1 THEN estimate_id ELSE NULL END) as final_id,
                        COUNT(*) as version_count
                    FROM estimates
                    GROUP BY root_id
                ),
                VersionNumbers AS (
                    SELECT 
                        e.estimate_id,
                        e.root_id,
                        ROW_NUMBER() OVER (PARTITION BY e.root_id ORDER BY e.created_at) as version_num
                    FROM estimates e
                )
                SELECT 
                    e.estimate_id,
                    json_extract(e.customer_info, '$.고객사명') as customer_name,
                    json_extract(e.customer_info, '$.건명') as subject,
                    json_extract(e.customer_info, '$.견적일자') as estimate_date,
                    e.total_amount,
                    e.filename,
                    CASE 
                        WHEN e.is_final = 1 THEN 'final'
                        ELSE 'v' || vn.version_num
                    END as version_status,
                    e.created_at,
                    vn.version_num,
                    lv.version_count,
                    e.is_final,
                    CASE 
                        WHEN e.is_final = 1 THEN TRUE
                        WHEN e.created_at = lv.latest_created_at THEN TRUE
                        ELSE FALSE
                    END as is_latest
                FROM estimates e
                LEFT JOIN LatestVersions lv ON e.root_id = lv.root_id
                LEFT JOIN VersionNumbers vn ON e.estimate_id = vn.estimate_id
                ORDER BY e.created_at DESC
            """)
            
            history = []
            rows = cursor.fetchall()
            
            if rows:
                for row in rows:
                    status = row[6]  # version_status
                    is_latest = row[11]  # is_latest
                    
                    if row[10]:  # is_final
                        display_status = 'final'
                    else:
                        display_status = status
                        if is_latest:
                            display_status = f"{status} [최신]"
                    
                    history.append({
                        'estimate_id': row[0],
                        '고객사명': row[1] or '',
                        '건명': row[2] or '',
                        '견적일자': row[3] or '',
                        '총금액': row[4] or 0,
                        '파일명': row[5] or '',
                        '최신본여부': display_status,
                        '생성일자': row[7],
                        '버전': row[8]
                    })
            
            return history
            
        except Exception as e:
            print(f"견적서 이력 조회 중 오류 발생: {str(e)}")
            return []
            
        finally:
            cursor.close()
            conn.close() 