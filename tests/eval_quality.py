"""L2: 輸出品質驗證 harness (需要真實 API 金鑰)。

跑真實的 /api/evaluate，對輸出做「框架遵循度」與「計分規則正確性」的確定性檢查。
這是驗證的核心：確保分析結果正確、符合 prompts.py 定義的四關框架與最終裁決規則。

用法:
    python tests/eval_quality.py            # 跑全部 fixtures
    python tests/eval_quality.py ai_cs      # 只跑指定 fixture
非零退出碼代表有檢查失敗。原始輸出存到 tests/outputs/ 供人工 + LLM 評審。
"""
import os
import re
import sys
import json
import pathlib

# 載入 .env（main 也會載，但確保這裡的 print 能看到狀態）
from dotenv import load_dotenv

load_dotenv()

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "tests" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VERDICTS = ["🟢", "🟡", "🔵", "🔴"]

# 具名基準/研究來源 — 用來客觀衡量「評估是否扎根於可查證來源」而非憑感覺。
# 含框架內建基準 + live web_search 常見的市場研究機構。
NAMED_SOURCES = [
    "Benchmarkit", "KeyBanc", "Sapphire", "Bessemer", "High Alpha", "ICONIQ",
    "Pendo", "METR", "Bill Gross", "Glass", "Sean Ellis", "First Round", "Helmer",
    "Gartner", "Grand View", "Technavio", "Statista", "Forrester", "McKinsey", "IDC",
]

# C 區被否證數字 — 出現即代表用了不該用的「常被誤引」數據（BENCHMARKS.md C 區）。
REFUTED_PATTERNS = [
    (r"95\s*%[^。\n]{0,24}(失敗|新品|產品)", "95% 新品失敗（已否證）"),
    (r"Christensen[^。\n]{0,24}95", "Christensen 95%（已否證）"),
    (r"12\s*%[^。\n]{0,30}80\s*%[^。\n]{0,12}日活", "12%功能→80%日活（已否證）"),
    (r"a16z[^。\n]{0,40}50\s*[-–~]\s*60", "a16z AI 毛利 50-60%（已否證）"),
]


def extract_urls(text: str):
    return re.findall(r'https?://[^\s\)\]\>"，。、；]+', text)


def check_url_reachable(url: str):
    """回傳 (status, verdict)：verdict True=可達, False=死鏈(404/410/DNS), None=無法確認(403/429/5xx/逾時)。"""
    import httpx
    ua = {"User-Agent": "Mozilla/5.0 (compatible; eval-quality-harness)"}
    try:
        with httpx.Client(timeout=8, follow_redirects=True, headers=ua) as c:
            r = c.head(url)
            if r.status_code in (405, 403, 400):  # 有些站不支援 HEAD → 改 GET
                r = c.get(url)
            if r.status_code in (404, 410):
                return r.status_code, False
            if r.status_code >= 400:
                return r.status_code, None  # 403/429/5xx 多為反爬，無法判定死活
            return r.status_code, True
    except httpx.HTTPError:
        return None, None  # DNS/連線問題也可能是暫時性,保守記為無法確認


# ---------------------------------------------------------------------------
# Fixtures: (key, 是否多項目, 輸入文字, 預期最終裁決或 None)
# ---------------------------------------------------------------------------
FIXTURES = {
    # 高度商品化、平台原生化 → 框架預設應給 No-Go
    "ai_cs": {
        "multi": False,
        "expect_verdict": "🔴",
        "text": "我們想在 App 加入 AI 客服功能，自動回覆用戶常見問題（FAQ），支援多語言，"
                "並能在無法解答時轉接真人客服。目前沒有提供工單量、客服成本等數據。",
    },
    # 多項目：測試跨項目比較表與結論總表
    "multi": {
        "multi": True,
        "expect_verdict": None,
        "text": "請評估以下三個項目：\n"
                "1. AI 客服機器人：自動回覆 FAQ。\n"
                "2. 把後端從單體拆成微服務（純技術重構，不影響功能）。\n"
                "3. 為我們既有的 10 萬筆獨家醫療理賠資料，做一個 AI 理賠風險評分引擎，"
                "深度整合現有理賠工作流。",
    },
}


# ---------------------------------------------------------------------------
# 取得評估輸出（真實 LLM）
# ---------------------------------------------------------------------------
def run_evaluate(text: str) -> str:
    import main
    from fastapi.testclient import TestClient
    from tests.test_control_flow import parse_sse

    # 每次評估用新的 TestClient(新 event loop);重置快取的 LLM client,
    # 讓它在當前 loop 上重新建立,避免跨 loop 的 "Event loop is closed"。
    # (生產環境 uvicorn 為單一持久 loop,不受影響)
    main.gemini_client = None
    main.openai_client = None

    client = TestClient(main.app)
    r = client.post("/api/evaluate", data={"text": text})
    events = parse_sse(r.text)

    # 串接所有可能的輸出來源：result (一次給) 或 delta (串流)
    chunks = []
    for e, d in events:
        if e == "result":
            chunks.append(d.get("result", ""))
        elif e == "delta":
            chunks.append(d.get("content", ""))
        elif e == "error":
            raise RuntimeError(f"評估回傳錯誤: {d.get('error')}")
    return "".join(chunks)


# ---------------------------------------------------------------------------
# 解析輔助
# ---------------------------------------------------------------------------
def section(text: str, start_pat: str, end_pat: str | None) -> str:
    """擷取兩個標記之間的區段（找不到起點回空字串）。"""
    s = re.search(start_pat, text)
    if not s:
        return ""
    rest = text[s.start():]
    if end_pat:
        e = re.search(end_pat, rest[len(s.group(0)):])
        if e:
            return rest[: len(s.group(0)) + e.start()]
    return rest


def count_kill_filter_x(text: str) -> int:
    """數第一關 Kill Filter 區段內的 ❌ 數量（只在表格列內）。"""
    sec = section(text, r"第一關", r"第二關")
    rows = [ln for ln in sec.splitlines() if ln.strip().startswith("|")]
    return sum(ln.count("❌") for ln in rows)


def final_verdict(text: str) -> str | None:
    """從最終裁決區判定結論 emoji。優先用「判定依據」行，否則用最終裁決區最後出現的 emoji。"""
    final_sec = section(text, r"最終裁決", None)
    # 「判定依據」行最可靠
    for ln in final_sec.splitlines():
        if "判定依據" in ln or "觸發規則" in ln:
            for v in VERDICTS:
                if v in ln:
                    return v
    # 單一項目醒目結論 blockquote
    m = re.search(r">\s*\*\*結論[:：]\s*(" + "|".join(VERDICTS) + ")", text)
    if m:
        return m.group(1)
    # fallback: 最終裁決區最後一個 emoji
    found = [c for c in final_sec if c in VERDICTS]
    return found[-1] if found else None


# ---------------------------------------------------------------------------
# 檢查
# ---------------------------------------------------------------------------
def check(name, passed, detail=""):
    return {"name": name, "pass": bool(passed), "detail": detail}


def parse_comparison_rows(text: str):
    """從跨項目比較表抓出 (Kill Filter 通過數, 失敗數, 結論emoji)。

    比較表每列格式: | 項目 | N/5 | ... | 🔴/🟢/... 結論 |
    依據「該列含 N/5 且最後一格含結論 emoji」辨識,避免誤抓其他表格。
    """
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        kf_cell = next((c for c in cells if re.fullmatch(r"\d\s*/\s*5", c)), None)
        if not kf_cell:
            continue
        verdict = next((x for x in VERDICTS if x in cells[-1]), None)
        if verdict is None:
            continue
        passed = int(re.match(r"(\d)", kf_cell).group(1))
        rows.append({"pass": passed, "fail": 5 - passed, "verdict": verdict})
    return rows


def run_checks(fx_key: str, fx: dict, text: str) -> list[dict]:
    results = []

    def has(pat):
        return re.search(pat, text) is not None

    # --- 框架結構：四關都在（單/多項目皆適用，多項目為每項重複） ---
    results.append(check("第一關 Kill Filter 存在", has(r"第一關") and "Kill Filter" in text))
    results.append(check("第二關 問題與市場 存在", has(r"第二關")))
    results.append(check("第三關 防禦性 存在", has(r"第三關") and ("防禦" in text)))
    results.append(check("第四關 Pre-mortem 存在", has(r"第四關") and ("Pre-mortem" in text or "預驗屍" in text)))
    results.append(check("最終裁決 存在", has(r"最終裁決")))

    # --- Kill Filter 五項篩選 ---
    kf = section(text, r"第一關", r"第二關")
    kf_terms = ["問題真實性", "付費意願", "AI 商品化", "平台風險", "複製速度"]
    results.append(check("Kill Filter 含 5 項篩選", all(t in kf for t in kf_terms),
                         detail=str([t for t in kf_terms if t not in kf])))

    # --- 第二關五維度 ---
    dims = ["問題與市場", "團隊適配", "市場時機", "開發成本", "單位經濟"]
    results.append(check("第二關 含 5 維度", all(d in text for d in dims),
                         detail=str([d for d in dims if d not in text])))

    # --- 第三關 8 防禦層合計 ---
    results.append(check("第三關 含 /8 防禦合計", has(r"/\s*8")))

    # ===== 客觀性檢查（整合量化基準後新增）=====

    # (1) 套用具名基準/研究來源 — 評估是否扎根於可查證來源,而非憑感覺
    src_hits = sorted({s for s in NAMED_SOURCES if s in text})
    results.append(check(
        "扎根具名基準/來源 (≥2)",
        len(src_hits) >= 2,
        detail=f"命中: {src_hits}" if src_hits else "未引用任何具名來源",
    ))

    # (2) 無被否證數字 (BENCHMARKS.md C 區) — 出現即扣分
    viol = [msg for pat, msg in REFUTED_PATTERNS if re.search(pat, text)]
    results.append(check("無被否證數字 (C區)", not viol, detail="; ".join(viol)))

    # (3) 引用連結真實可達 — 死鏈(404/410)代表可能是幻覺來源
    urls = list(dict.fromkeys(extract_urls(text)))
    if urls:
        dead, unknown, alive = [], 0, 0
        for u in urls:
            _, ok = check_url_reachable(u)
            if ok is False:
                dead.append(u)
            elif ok is None:
                unknown += 1
            else:
                alive += 1
        results.append(check(
            "引用連結無死鏈",
            not dead,
            detail=(f"死鏈: {dead}" if dead else f"{len(urls)} 連結 (可達{alive}/無法確認{unknown})"),
        ))
    else:
        results.append(check("引用連結 (本次無 URL)", True, detail="無 URL（可能未觸發搜尋）"))

    if fx["multi"]:
        # ---------- 多項目專屬：跨項目表 + 結論總表 + 逐項計分一致性 ----------
        results.append(check("跨項目比較表存在", "跨項目" in text))
        results.append(check("結論總表存在", has(r"\|\s*#\s*\|") or "結論總表" in text or "一句話理由" in text))

        rows = parse_comparison_rows(text)
        results.append(check("跨項目表可解析出各項目列", len(rows) >= 2, detail=f"解析到 {len(rows)} 列"))

        # 核心：逐項計分規則 — Kill Filter 失敗 ≥2 的項目必須為 🔴
        violations = [r for r in rows if r["fail"] >= 2 and r["verdict"] != "🔴"]
        results.append(check(
            "逐項計分規則: Kill Filter 失敗≥2 → 須 🔴",
            not violations,
            detail=(f"違規: {violations}" if violations
                    else f"檢查 {len(rows)} 項，"
                         + ", ".join(f"{r['pass']}/5→{r['verdict']}" for r in rows)),
        ))
        # prompt 對多項目要求「優先級排序建議:資源有限該先做哪個」。
        # 偵測實質的優先級語意(模型表達方式多樣:優先/排序/集中/先做/唯一值得…)。
        priority_signals = ["優先", "排序", "先做", "集中到", "資源集中", "唯一值得", "優先順序", "最該做"]
        hit = [s for s in priority_signals if s in text]
        results.append(check("含優先級排序建議", bool(hit), detail=f"命中: {hit}"))
    else:
        # ---------- 單項目專屬 ----------
        v = final_verdict(text)
        results.append(check("最終裁決含結論 emoji", v is not None, detail=f"判定={v}"))
        results.append(check("含判定依據說明", "判定依據" in text or "觸發規則" in text))

        nx = count_kill_filter_x(text)
        if nx >= 2:
            results.append(check(
                f"計分規則: Kill Filter ❌={nx}(≥2) → 須為 🔴",
                v == "🔴",
                detail=f"❌={nx}, 實際判定={v}",
            ))
        else:
            results.append(check(f"計分規則前提 (❌={nx}<2, 規則1不適用)", True, detail=f"判定={v}"))

        if fx["expect_verdict"]:
            results.append(check(f"預期裁決 = {fx['expect_verdict']}", v == fx["expect_verdict"],
                                 detail=f"實際={v}"))
        results.append(check("單項目醒目結論 blockquote", has(r">\s*\*\*結論")))

    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main_run():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    key_name = "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
    if not os.environ.get(key_name):
        print(f"❌ 缺少 {key_name}（provider={provider}）。請先設定 .env 再跑 L2。")
        return 2
    if not os.environ.get("SERPER_API_KEY"):
        print("⚠️  缺少 SERPER_API_KEY，web_search 會失敗但評估仍會進行（品質可能下降）。")

    all_pass = True
    summary = []
    for key, fx in FIXTURES.items():
        if only and key != only:
            continue
        print(f"\n{'='*70}\n▶ Fixture: {key} (provider={provider})\n{'='*70}")
        try:
            text = run_evaluate(fx["text"])
        except Exception as e:
            print(f"  ❌ 執行失敗: {e}")
            all_pass = False
            summary.append((key, 0, 1))
            continue

        (OUT_DIR / f"{key}.md").write_text(text, encoding="utf-8")
        checks = run_checks(key, fx, text)
        npass = sum(c["pass"] for c in checks)
        ntotal = len(checks)
        for c in checks:
            mark = "✅" if c["pass"] else "❌"
            extra = f"  ({c['detail']})" if c["detail"] else ""
            print(f"  {mark} {c['name']}{extra}")
            if not c["pass"]:
                all_pass = False
        print(f"  → {npass}/{ntotal} 通過，輸出存於 tests/outputs/{key}.md")
        summary.append((key, npass, ntotal))

    print(f"\n{'='*70}\n總結:")
    for key, npass, ntotal in summary:
        print(f"  {key}: {npass}/{ntotal}")
    print("="*70)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main_run())
