import pandas as pd
import os
from datetime import datetime
from database import Database

class DataManager:
    def __init__(self, base_csv_file="기초_견적항목_테이블.csv", doc_folder="견적서_이력"):
        self.base_csv_file = base_csv_file
        self.doc_folder = doc_folder
        os.makedirs(doc_folder, exist_ok=True)
        self.db = Database()
        
    def load_base_items(self):
        """기초 견적 항목 데이터 로드"""
        return pd.read_csv(self.base_csv_file)
        
    def save_estimate(self, meta_data, selected_items, filename, parent_id=None):
        """견적서 데이터 저장"""
        try:
            # 데이터베이스에 저장
            estimate_id = self.db.save_estimate(
                customer_info={
                    '고객사명': meta_data['고객사명'],
                    '건명': meta_data['건명'],
                    '담당자명': meta_data['담당자명'],
                    '직위': meta_data['직위'],
                    '이메일': meta_data['이메일'],
                    '전화번호': meta_data['전화번호'],
                    '견적일자': meta_data['견적일자'].strftime("%Y-%m-%d"),
                    '납품기간': meta_data['납품기간'],
                    '하자기간': meta_data['하자기간']
                },
                company_info={
                    '견적담당자명': meta_data['견적담당자명'],
                    '견적담당자직위': meta_data['견적담당자직위'],
                    '견적담당자이메일': meta_data['견적담당자이메일'],
                    '견적담당자전화번호': meta_data['견적담당자전화번호'],
                    '특이사항': meta_data.get('특이사항', '')
                },
                items=selected_items,
                total_amount=meta_data['총금액'],
                filename=filename,
                parent_id=parent_id,
                is_final=meta_data.get('is_final', False)
            )
            
            if not estimate_id:
                raise Exception("견적서 저장에 실패했습니다.")
                
            return estimate_id
            
        except Exception as e:
            raise Exception(f"견적서 저장 중 오류가 발생했습니다: {str(e)}")
        
    def load_estimate(self, estimate_id):
        """견적서 불러오기"""
        return self.db.load_estimate(estimate_id)
        
    def get_estimate_history(self):
        """견적서 이력 조회"""
        history = self.db.get_estimate_history()
        
        # 이력이 없는 경우 빈 리스트 반환
        if not history:
            return []
            
        # 이미 올바른 형식으로 반환되므로 그대로 반환
        return history
        
    def save_estimate_csv(self, meta_data, selected_items, filename):
        """견적서 데이터 CSV 저장"""
        meta_df = pd.DataFrame([meta_data])
        item_df = pd.DataFrame(selected_items)
        combined_df = pd.concat([meta_df, item_df], axis=1)
        
        save_path = os.path.join(self.doc_folder, f"{filename}.csv")
        combined_df.to_csv(save_path, index=False, encoding="utf-8-sig")
        return save_path
        
    def load_estimate_history(self, filename):
        """저장된 견적서 불러오기"""
        file_path = os.path.join(self.doc_folder, filename)
        return pd.read_csv(file_path)
        
    def get_saved_files(self):
        """저장된 견적서 파일 목록 조회"""
        return sorted([f for f in os.listdir(self.doc_folder) if f.endswith(".csv")])
        
    def get_estimate_version(self, estimate_id):
        """견적서의 현재 버전 번호 조회"""
        return self.db.get_estimate_version(estimate_id) 