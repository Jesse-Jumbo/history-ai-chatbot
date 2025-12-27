#!/usr/bin/env python3
"""
從 backend/訪談逐字稿/ 資料夾匯入老人訪談逐字稿 PDF，寫入資料庫的 Document 表。

- category 固定為 "elderly_interview"
- source 使用檔名（含副檔名），方便之後追蹤
- 可以重複執行，已存在相同 source 的資料會被略過
"""

from pathlib import Path
from typing import List

from pypdf import PdfReader

from database import add_document, SessionLocal, Document


BASE_DIR = Path(__file__).resolve().parent
TRANSCRIPTS_DIR = BASE_DIR / "訪談逐字稿"

ELDERLY_CATEGORY = "elderly_interview"


def extract_text_from_pdf(path: Path) -> str:
    """從單一 PDF 檔案抽取全部文字。"""
    reader = PdfReader(str(path))
    texts: List[str] = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        txt = txt.strip()
        if txt:
            texts.append(txt)
    return "\n\n".join(texts)


def import_elderly_interviews() -> None:
    """匯入 backend/訪談逐字稿/ 底下所有 PDF 到資料庫。"""
    if not TRANSCRIPTS_DIR.exists():
        print(f"資料夾不存在：{TRANSCRIPTS_DIR}")
        return

    db = SessionLocal()
    try:
        # 收集已經存在的來源，避免重複匯入
        existing_sources = {
            (doc.source or "").strip()
            for doc in db.query(Document)
            .filter(Document.category == ELDERLY_CATEGORY)
            .all()
        }

        count_new = 0
        for pdf_path in TRANSCRIPTS_DIR.glob("*.pdf"):
            source_id = pdf_path.name  # 直接以檔名當作來源 ID
            if source_id in existing_sources:
                print(f"已存在，略過：{source_id}")
                continue

            print(f"匯入：{source_id}")
            text = extract_text_from_pdf(pdf_path)
            if not text.strip():
                print(f"  無文字內容，略過：{source_id}")
                continue

            title = pdf_path.stem  # 去掉副檔名的檔名

            add_document(
                title=title,
                content=text,
                category=ELDERLY_CATEGORY,
                source=source_id,
            )
            count_new += 1

        print(f"完成，新增 {count_new} 筆老人訪談資料")
    finally:
        db.close()


if __name__ == "__main__":
    import_elderly_interviews()


