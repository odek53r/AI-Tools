from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT, build_evaluation_prompt
import os

app = FastAPI(title="AI Tools", version="0.2.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

gemini_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    global gemini_client
    if gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        gemini_client = genai.Client(api_key=api_key)
    return gemini_client


async def extract_text_from_file(file: UploadFile) -> str:
    filename = file.filename.lower()
    content = await file.read()

    if filename.endswith(".txt") or filename.endswith(".md"):
        return content.decode("utf-8")

    if filename.endswith(".pdf"):
        from PyPDF2 import PdfReader
        import io

        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)

    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        from openpyxl import load_workbook
        import io

        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheets = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                sheets.append(f"[工作表：{sheet_name}]\n" + "\n".join(rows))
        wb.close()
        return "\n\n".join(sheets) if sheets else "（Excel 檔案無內容）"

    raise ValueError(f"不支援的檔案格式：{filename}。僅支援 .txt、.md、.pdf、.xlsx")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/evaluate")
async def evaluate(
    text: str = Form(default=""),
    file: UploadFile | None = File(default=None),
):
    parts = []

    if file and file.filename:
        try:
            file_text = await extract_text_from_file(file)
            parts.append(f"[檔案：{file.filename}]\n{file_text}")
        except ValueError as e:
            return {"error": str(e)}
        except Exception:
            return {"error": "檔案解析失敗，請確認檔案格式正確。"}

    if text.strip():
        parts.append(text.strip())

    if not parts:
        return {"error": "請輸入功能描述或上傳檔案。"}

    combined = "\n\n".join(parts)

    try:
        ai = get_gemini_client()
    except ValueError:
        return {"error": "尚未設定 Gemini API Key，請聯繫管理員。"}

    try:
        response = await ai.aio.models.generate_content(
            model="gemini-3-flash-preview",
            contents=build_evaluation_prompt(combined),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0,
                max_output_tokens=4000,
            ),
        )
        result = response.text
        return {"result": result}
    except Exception as e:
        return {"error": f"AI 分析時發生錯誤：{str(e)}"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
