"""L1: 後端控制流程驗證 (mock LLM / 搜尋層, 不需真實金鑰)。

驗證 endpoints、SSE 事件序列、工具呼叫迴圈、搜尋上限、錯誤路徑。
"""
import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main


# ---------------------------------------------------------------------------
# SSE 解析工具
# ---------------------------------------------------------------------------
def parse_sse(text: str):
    """將 SSE 原始文字解析成 [(event, data_dict), ...]，忽略 keep-alive 註解。"""
    events = []
    cur_event = None
    cur_data = None
    for line in text.split("\n"):
        if line.startswith("event: "):
            cur_event = line[len("event: "):]
        elif line.startswith("data: "):
            cur_data = line[len("data: "):]
        elif line == "":
            if cur_event is not None and cur_data is not None:
                events.append((cur_event, json.loads(cur_data)))
            cur_event = None
            cur_data = None
    return events


def event_names(events):
    return [e for e, _ in events]


@pytest.fixture
def client():
    return TestClient(main.app)


# ---------------------------------------------------------------------------
# 基本 endpoints
# ---------------------------------------------------------------------------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_home_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "功能計畫評估器" in r.text


# ---------------------------------------------------------------------------
# 錯誤路徑
# ---------------------------------------------------------------------------
def test_empty_input_errors(client):
    r = client.post("/api/evaluate", data={"text": "   "})
    events = parse_sse(r.text)
    assert ("error", {"error": "請輸入功能描述或上傳檔案。"}) in events


def test_unsupported_file_errors(client):
    files = {"file": ("plan.docx", io.BytesIO(b"junk"), "application/octet-stream")}
    r = client.post("/api/evaluate", data={"text": ""}, files=files)
    events = parse_sse(r.text)
    assert any(e == "error" and "不支援的檔案格式" in d["error"] for e, d in events)


def test_missing_gemini_key_friendly_error(client, monkeypatch):
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")

    def _raise():
        raise ValueError("GEMINI_API_KEY not set")

    monkeypatch.setattr(main, "get_gemini_client", _raise)
    r = client.post("/api/evaluate", data={"text": "做一個 AI 功能"})
    events = parse_sse(r.text)
    assert any(e == "error" and "Gemini API Key" in d["error"] for e, d in events)


def test_missing_openai_key_friendly_error(client, monkeypatch):
    monkeypatch.setattr(main, "LLM_PROVIDER", "openai")

    def _raise():
        raise ValueError("OPENAI_API_KEY not set")

    monkeypatch.setattr(main, "get_openai_client", _raise)
    r = client.post("/api/evaluate", data={"text": "做一個 AI 功能"})
    events = parse_sse(r.text)
    assert any(e == "error" and "OpenAI API Key" in d["error"] for e, d in events)


# ---------------------------------------------------------------------------
# Gemini 假 client
# ---------------------------------------------------------------------------
def _gemini_fc(query):
    return SimpleNamespace(name="web_search", args={"query": query})


def _gemini_response(function_calls=None, text=""):
    return SimpleNamespace(
        function_calls=function_calls or [],
        text=text,
        candidates=[SimpleNamespace(content=SimpleNamespace(role="model", parts=[]))],
    )


class FakeGeminiClient:
    def __init__(self, responses):
        self._responses = list(responses)

        async def _gen(model, contents, config):
            return self._responses.pop(0)

        self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=_gen))


def test_gemini_happy_path_with_one_search(client, monkeypatch):
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")
    responses = [
        _gemini_response(function_calls=[_gemini_fc("AI customer service market size")]),
        _gemini_response(text="## 最終裁決\n🔴 No-Go"),
    ]
    monkeypatch.setattr(main, "get_gemini_client", lambda: FakeGeminiClient(responses))

    async def fake_search(q):
        return f"[精選摘要] result for {q}"

    monkeypatch.setattr(main, "web_search", fake_search)

    r = client.post("/api/evaluate", data={"text": "AI 客服"})
    events = parse_sse(r.text)
    names = event_names(events)

    assert "search" in names
    search_events = [d for e, d in events if e == "search"]
    assert search_events[0]["query"] == "AI customer service market size"
    # 最終要有 result，且內容來自模型
    results = [d for e, d in events if e == "result"]
    assert results and "No-Go" in results[-1]["result"]
    # status 應在 result 之前出現
    assert names.index("status") < names.index("result")


def test_gemini_search_cap_enforced(client, monkeypatch):
    """模型每輪要求 2 次搜尋且永不停止 → 總搜尋數必須被夾在 5 次。"""
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")
    # 4 輪 (MAX_SEARCH_ROUNDS+1)，每輪 2 個 function call
    responses = [
        _gemini_response(function_calls=[_gemini_fc(f"q{i}a"), _gemini_fc(f"q{i}b")])
        for i in range(main.MAX_SEARCH_ROUNDS + 1)
    ]
    monkeypatch.setattr(main, "get_gemini_client", lambda: FakeGeminiClient(responses))

    calls = []

    async def fake_search(q):
        calls.append(q)
        return "result"

    monkeypatch.setattr(main, "web_search", fake_search)

    r = client.post("/api/evaluate", data={"text": "多項目"})
    events = parse_sse(r.text)
    search_events = [d for e, d in events if e == "search"]

    # 實際執行的搜尋次數與 emit 的 search 事件都不得超過上限
    assert len(calls) <= main.MAX_TOTAL_SEARCHES
    assert len(search_events) <= main.MAX_TOTAL_SEARCHES
    assert len(calls) == main.MAX_TOTAL_SEARCHES  # 該情境下應剛好打滿


def test_gemini_no_search_needed(client, monkeypatch):
    """模型直接回答、不呼叫工具 → 不應有 search 事件。"""
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")
    responses = [_gemini_response(text="## 最終裁決\n🟢 Go")]
    monkeypatch.setattr(main, "get_gemini_client", lambda: FakeGeminiClient(responses))
    monkeypatch.setattr(main, "web_search", lambda q: (_ for _ in ()).throw(AssertionError("should not search")))

    r = client.post("/api/evaluate", data={"text": "純技術重構"})
    events = parse_sse(r.text)
    assert "search" not in event_names(events)
    results = [d for e, d in events if e == "result"]
    assert results and "Go" in results[-1]["result"]


# ---------------------------------------------------------------------------
# OpenAI 假 client
# ---------------------------------------------------------------------------
def _openai_tool_call(call_id, query):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(arguments=json.dumps({"query": query})),
    )


def _openai_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _openai_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAIClient:
    def __init__(self, responses):
        self._responses = list(responses)

        async def _create(model, messages, tools=None, temperature=0.0, stream=False):
            return self._responses.pop(0)

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))


def test_openai_happy_path_with_search(client, monkeypatch):
    monkeypatch.setattr(main, "LLM_PROVIDER", "openai")
    responses = [
        _openai_response(_openai_message(tool_calls=[_openai_tool_call("c1", "saas market")])),
        _openai_response(_openai_message(content="## 最終裁決\n🟡 有條件 Go")),
    ]
    monkeypatch.setattr(main, "get_openai_client", lambda: FakeOpenAIClient(responses))

    async def fake_search(q):
        return f"result for {q}"

    monkeypatch.setattr(main, "web_search", fake_search)

    r = client.post("/api/evaluate", data={"text": "做一個 SaaS"})
    events = parse_sse(r.text)
    names = event_names(events)
    assert "search" in names
    results = [d for e, d in events if e == "result"]
    assert results and "有條件 Go" in results[-1]["result"]


def test_openai_search_cap_enforced(client, monkeypatch):
    monkeypatch.setattr(main, "LLM_PROVIDER", "openai")
    responses = [
        _openai_response(
            _openai_message(
                tool_calls=[_openai_tool_call(f"c{i}a", f"q{i}a"), _openai_tool_call(f"c{i}b", f"q{i}b")]
            )
        )
        for i in range(main.MAX_SEARCH_ROUNDS + 1)
    ]
    monkeypatch.setattr(main, "get_openai_client", lambda: FakeOpenAIClient(responses))

    calls = []

    async def fake_search(q):
        calls.append(q)
        return "result"

    monkeypatch.setattr(main, "web_search", fake_search)

    r = client.post("/api/evaluate", data={"text": "多項目"})
    events = parse_sse(r.text)
    search_events = [d for e, d in events if e == "search"]
    assert len(calls) <= main.MAX_TOTAL_SEARCHES
    assert len(search_events) <= main.MAX_TOTAL_SEARCHES


# ---------------------------------------------------------------------------
# keep-alive 包裝器
# ---------------------------------------------------------------------------
def test_keepalive_emits_heartbeat():
    """慢回應 (> interval) 時應插入 keep-alive 心跳，且原始事件仍完整送達。"""
    import asyncio

    async def slow_gen():
        await asyncio.sleep(0.2)
        yield "event: a\ndata: {}\n\n"
        await asyncio.sleep(0.2)
        yield "event: b\ndata: {}\n\n"

    async def run():
        out = []
        async for chunk in main.with_keepalive(slow_gen(), interval=0.05):
            out.append(chunk)
        return out

    chunks = asyncio.run(run())
    assert any(c == ": keep-alive\n\n" for c in chunks)
    assert "event: a\ndata: {}\n\n" in chunks
    assert "event: b\ndata: {}\n\n" in chunks


def test_keepalive_no_heartbeat_when_fast():
    """快回應 (< interval) 時不應插入心跳。"""
    import asyncio

    async def fast_gen():
        yield "event: done\ndata: {}\n\n"

    async def run():
        return [c async for c in main.with_keepalive(fast_gen(), interval=5)]

    chunks = asyncio.run(run())
    assert ": keep-alive\n\n" not in chunks
    assert chunks == ["event: done\ndata: {}\n\n"]
