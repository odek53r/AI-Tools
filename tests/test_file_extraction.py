"""L1: 檔案解析驗證 — txt / md / pdf / xlsx 與不支援格式錯誤處理。"""
import io
import asyncio

import pytest
from starlette.datastructures import UploadFile, Headers

import main


def _upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": "application/octet-stream"}),
    )


def _extract(filename: str, content: bytes) -> str:
    return asyncio.run(main.extract_text_from_file(_upload(filename, content)))


def test_txt_extraction():
    text = _extract("plan.txt", "我想做一個 AI 客服".encode("utf-8"))
    assert "AI 客服" in text


def test_md_extraction():
    md = "# 標題\n\n- 功能 A\n- 功能 B".encode("utf-8")
    text = _extract("plan.md", md)
    assert "功能 A" in text and "功能 B" in text


def test_pdf_extraction():
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, "Hello PDF Feature Plan")
    raw = pdf.output()
    text = _extract("plan.pdf", bytes(raw))
    assert "Hello PDF Feature Plan" in text


def test_xlsx_extraction():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Plans"
    ws.append(["項目", "描述"])
    ws.append(["AI 客服", "自動回覆 FAQ"])
    buf = io.BytesIO()
    wb.save(buf)
    text = _extract("plan.xlsx", buf.getvalue())
    assert "工作表：Plans" in text
    assert "AI 客服" in text and "自動回覆 FAQ" in text


def test_unsupported_format_raises():
    with pytest.raises(ValueError, match="不支援的檔案格式"):
        _extract("plan.docx", b"whatever")
