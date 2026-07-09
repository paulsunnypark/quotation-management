"""
카탈로그 참조 DB (Track B - 신규 패키지 CPQ)

catalog/ 디렉토리의 시드 CSV를 읽어 읽기전용 참조 SQLite(catalog.db)로 적재한다.
package_price.xlsx가 우선 진실 원본(source of truth)이며 catalog.db는 언제든 재생성 가능하다.

- 기존 quotation.db(Track A 레거시)는 일절 건드리지 않는다.
- `python catalog_db.py` 실행 시 catalog.db를 재빌드하고 요약을 출력한다.
"""
import csv
import os
import sqlite3

CATALOG_DIR = "catalog"
PRICE_XLSX = "package_price.xlsx"  # 단일 가격 소스 (우선). 부재 시 catalog/*.csv fallback
LEGACY_PRICE_XLSX = "가격표.xlsx"

# 테이블명 -> (엑셀 시트명 / CSV 파일명, 정수 컬럼, 실수 컬럼)
TABLES = {
    "products": (
        "base_product(B)", "products.csv",
        {"순번", "대외기준가", "권장제안가", "표준유통공급가", "전략파트너하한"},
        {"공급가율"},
    ),
    "registered_skus": (
        "registered_skus", "registered_skus.csv",
        {"식별번호", "가격_VAT포함"},
        set(),
    ),
    "service_packages": (
        "service_packages", "service_packages.csv",
        {"순위"},
        set(),
    ),
    "package_presets": (
        "package_presets", "package_presets.csv",
        {"산출합계"},
        set(),
    ),
    "package_preset_items": (
        "package_preset_items", "package_preset_items.csv",
        {"수량", "단가_VAT포함", "금액"},
        set(),
    ),
    "discount_policy": (
        "discount_policy", "discount_policy.csv",
        set(),
        {"할인승인_한도"},
    ),
}

LEGACY_SHEETS = {
    "base_product(B)": "products",
    "base_item(A)": "기초견적항목",
}


class CatalogDB:
    def __init__(self, catalog_dir=CATALOG_DIR, db_file="catalog.db", price_xlsx=PRICE_XLSX):
        self.catalog_dir = catalog_dir
        self.db_file = db_file
        self.price_xlsx = price_xlsx

    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _coerce(value, int_cols, float_cols, header):
        """CSV 문자열 값을 컬럼 유형에 맞게 캐스팅."""
        if value is None or value == "":
            return None
        if header in int_cols:
            try:
                return int(str(value).replace(",", "").strip())
            except ValueError:
                return value
        if header in float_cols:
            try:
                return float(str(value).replace(",", "").strip())
            except ValueError:
                return value
        return value

    def _source_rows(self, table, sheet, fname):
        """package_price.xlsx 시트(우선) 또는 catalog/*.csv(fallback)에서 (headers, rows) 반환."""
        price_path = self.price_xlsx
        if not os.path.exists(price_path) and self.price_xlsx == PRICE_XLSX:
            if os.path.exists(LEGACY_PRICE_XLSX):
                price_path = LEGACY_PRICE_XLSX

        if os.path.exists(price_path):
            import build_price_master as bpm
            try:
                dicts = bpm.read_sheet_rows(sheet, price_path)
            except KeyError:
                legacy_sheet = LEGACY_SHEETS.get(sheet)
                if not legacy_sheet:
                    raise
                dicts = bpm.read_sheet_rows(legacy_sheet, price_path)
            if dicts:
                headers = list(dicts[0].keys())
                return headers, dicts
            # 빈 시트면 CSV fallback 시도
        path = os.path.join(self.catalog_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"가격 소스 없음: {self.price_xlsx}#{sheet} / {path}")
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            return headers, list(reader)

    def rebuild(self):
        """package_price.xlsx(우선) 또는 CSV로부터 catalog.db를 전면 재생성한다."""
        conn = self.get_connection()
        cursor = conn.cursor()
        summary = {}
        try:
            for table, (sheet, fname, int_cols, float_cols) in TABLES.items():
                headers, rows = self._source_rows(table, sheet, fname)
                if not headers:
                    raise ValueError(f"빈 소스: {table}")

                cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
                cols_ddl = ", ".join(f'"{h}"' for h in headers)
                cursor.execute(f'CREATE TABLE "{table}" ({cols_ddl})')

                placeholders = ", ".join("?" for _ in headers)
                insert_sql = (
                    f'INSERT INTO "{table}" '
                    f'({", ".join(chr(34) + h + chr(34) for h in headers)}) '
                    f"VALUES ({placeholders})"
                )
                count = 0
                for row in rows:
                    values = [
                        self._coerce(row.get(h), int_cols, float_cols, h)
                        for h in headers
                    ]
                    cursor.execute(insert_sql, values)
                    count += 1
                summary[table] = count

            conn.commit()
            return summary
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    # --- 조회 헬퍼 (Phase 1 CPQ 엔진에서 사용) ---
    def get_products(self):
        conn = self.get_connection()
        try:
            return [dict(r) for r in conn.execute('SELECT * FROM products ORDER BY "순번"')]
        finally:
            conn.close()

    def get_preset_items(self, preset_code):
        conn = self.get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM package_preset_items WHERE "프리셋코드" = ?',
                (preset_code,),
            )
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_service_packages(self):
        conn = self.get_connection()
        try:
            return [dict(r) for r in conn.execute('SELECT * FROM service_packages ORDER BY "순위"')]
        finally:
            conn.close()

    def get_discount_limit(self, partner_grade):
        conn = self.get_connection()
        try:
            row = conn.execute(
                'SELECT "할인승인_한도" FROM discount_policy WHERE "파트너등급" = ?',
                (partner_grade,),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()


if __name__ == "__main__":
    catalog = CatalogDB()
    summary = catalog.rebuild()
    print("[OK] catalog.db rebuilt")
    for table, count in summary.items():
        print(f"  - {table}: {count} rows")
