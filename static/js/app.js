const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileRemove = document.getElementById('file-remove');
const evaluateInput = document.getElementById('evaluate-input');
const evaluateBtn = document.getElementById('evaluate-btn');
const resultBox = document.getElementById('evaluate-result');
const resultOutput = document.getElementById('evaluate-output');

let selectedFile = null;

// Real evaluation result used as example hint on page load
const EXAMPLE_RESULT = "## 0) 項目清單與市場通用類別對應（先定義再評估）\n\n| 內部想做的項目 | 市場通用產品類別 |\n|---|---|\n| App 內 AI 客服：自動回覆 FAQ、多語言、無法解答轉真人 | **AI Customer Service Chatbot / Customer Support Automation Platform（含 Human Handoff）** |\n\n### Web search（市場/競品/趨勢）摘要（僅引用相關）\n- 市場成長：Technavio 指出 **AI for customer service** 市場 2025-2029 將成長約 **USD 24.4B**、CAGR **25.4%**（來源：*AI For Customer Service Market* https://www.technavio.com/report/ai-for-customer-service-market-industry-analysis ）  \n- 市場規模：Grand View Research 預估 **AI customer service** 市場 2025-2033 CAGR **23.2%**，2033 達 **USD 83.9B**（來源：*AI Customer Service Market Report* https://www.grandviewresearch.com/industry-analysis/ai-customer-service-market-report ）  \n- 類別競爭極度擁擠：此類別典型競品包含 **Intercom、Zendesk、Salesforce Service Cloud、Freshdesk/Freshchat、Genesys、Five9** 等（屬於「客服平台 + AI」或「AI 客服」主流供應商；你要做的是它們的標準功能集合）。\n\n> 結論先講：**市場很大不等於你該做**。這類功能高度商品化、平台原生化速度快，除非你有「既有客服量 + 既有工單/知識庫/工作流」可直接吃到 ROI，否則預設 **No-Go**。\n\n---\n\n# 項目 1：App 內 AI 客服（FAQ 自動回覆 / 多語言 / 轉真人）\n\n## 第一關：致命問題篩選（Kill Filter）\n\n| 篩選項目 | 結果 | 理由 |\n|---|---|---|\n| 問題真實性 | ⚠️ | 幾乎所有 App 都有客服量，但你未提供：每月工單量、Top 20 問題占比、尖峰時段、目前回覆 SLA/CSAT；沒有 workaround 證據（例如客服爆量、回覆延遲、成本失控）。 |\n| 付費意願 | ⚠️ | 這通常是「內部降本」而非用戶付費；是否願意投入取決於你目前客服成本是否夠痛（例如每月客服人力成本、外包費、流失損失）。你未提供。 |\n| AI 商品化 | ❌ | 用 **ChatGPT/Claude + 你的 FAQ/知識庫** 就能解 80%「常見問題文字回覆」；多語言更是基礎能力。你做的若只是「包一層聊天介面」= 跟免費/現成工具競爭。 |\n| 平台風險 | ❌ | **Intercom/Zendesk/Freshdesk/Genesys** 等已把 GenAI 與人員轉接做成標配；模型/平台方也持續下放能力。你做的功能很容易被「客服平台原生」吃掉。 |\n| 複製速度 | ❌ | 以現成 LLM + RAG + 工單系統 webhook + handoff，成熟團隊 **2-4 週**可做出可用版本；核心功能複製 < 1 個月，護城河近乎 0。 |\n\n**結論（Kill Filter）：❌ = 3（≥2）→ 直接觸發 No-Go。** 後續分析僅作為「如果你硬要做，至少要怎麼做才不浪費」的參考，但最終結論不變。\n\n---\n\n## 第二關：問題、市場與可行性分析（參考用）\n\n### 總覽表格\n| 維度 | 等級 | 關鍵發現 |\n|---|---|---|\n| 問題與市場 | 💡 有需求 | 市場大且成長快（Technavio/GVR），但屬紅海標配功能，差異化空間小。 |\n| 團隊適配 | ❓ 資訊不足 | 需要：客服營運/知識庫治理、對話設計、LLM 評測與安全、工單系統整合能力。 |\n| 市場時機 | ⏰ 稍晚但還行 | 類別已成熟，現在做不是「搶窗口」，而是「追標配」。 |\n| 開發成本 | 🟡 中等（1-3 月） | 真正成本在：知識庫清理、權限/隱私、評測、監控、handoff、回覆品質與風險控管。 |\n| 單位經濟 | ❓ 無法估算 | 取決於：工單量、平均對話輪數、模型選型、命中率、轉人工比例；你未提供基線數據。 |\n\n### 逐項要害\n- **問題與市場：** 需求普遍存在，但「普遍」也代表「標配」。除非你能把它做成你產品的核心工作流（例如交易/訂單/帳務/權限等強整合），否則很難贏過既有客服平台。\n- **團隊適配：** 若沒有客服營運與知識庫治理能力，AI 只會把錯誤放大（幻覺、錯誤承諾、政策不一致）。需要能建立「可追責」的回覆策略與審計。\n- **市場時機：** 2025 之後平台原生 AI 會更強，你自建的相對優勢會被侵蝕；除非你有獨特資料/流程可做深。\n- **開發成本：** MVP 很快，但「可上線且不出事」很慢：多語言一致性、法務/隱私、敏感資訊遮罩、回覆邊界、升級與回歸測試。\n- **單位經濟：** 若你工單量不大，省下的人力不足以覆蓋推理成本 + 維運成本；反而變成「為了看起來先進而燒錢」。\n\n---\n\n## 第三關：AI 時代防禦性評估（參考用）\n\n| 防禦層 | 具備/可建立？ | 說明 |\n|---|---|---|\n| 領域專業化 | 🔜 | 只有在你有非常明確的領域規則（例如金融/醫療/電信資費/物流理賠）且能固化成策略/工具調用才可能。 |\n| 專有數據 | ⚠️/🔜 | 若你能累積「問題→解法→結果（是否解決/是否轉人工/CSAT）」的閉環資料才有價值；但多數團隊做不到治理。 |\n| 工作流整合 | 🔜 | 若能深度整合訂單、帳務、會員、退款、權限等「可執行動作」才有黏性；純問答沒有。 |\n| 網路效應 | ❌ | 多數客服機器人沒有網路效應，更多用戶不會自然讓產品變更好（除非你有強資料閉環與訓練管線）。 |\n| 品牌與信任 | ❌ | 客服信任通常歸因於主產品品牌，不會因為你做了機器人就形成新護城河。 |\n| 分發優勢 | ❓ | 你是做「自家 App 內功能」，不是對外賣平台；分發優勢不成立。 |\n| 轉換成本 | ❌ | 這類功能可被替換（接 Zendesk/Intercom 也能做），切換成本主要在工單系統與知識庫，不在你自建的 bot。 |\n| 營運卓越 | 🔜 | 若你能做到高可用、低延遲、合規、審計、風險控管，算能力壁壘；但成本高且不一定值得。 |\n| **合計** | **3/8（偏樂觀估）** | 多數是「可建立但很難」，且沒有單一極強防禦層。 |\n\n---\n\n## 第四關：預驗屍（Pre-mortem）\n\n| 失敗原因 | 發生機率 | 緩解策略 | 若無法緩解，是否致命？ |\n|---|---|---|---|\n| 回覆不準/幻覺導致客訴或合規風險 | 高 | 嚴格限制可回答範圍、只引用可追溯來源、敏感意圖直接轉人工、全量記錄與審計 | 是 |\n| 命中率不高，反而增加用戶挫折（多問幾輪才轉人工） | 高 | 設定「低信心/高風險」快速轉人工、用 Top 問題先做、A/B 測試 | 是 |\n| 維運成本（知識庫更新、評測、監控）超出節省的人力 | 中 | 先算 ROI、只覆蓋高頻問題、建立內容治理流程 | 是 |\n| 被現成客服平台功能碾壓，內部自建變成技術債 | 中 | 優先買/接入現成方案；自建只做你獨有的工作流動作 | 否（但會浪費資源） |\n\n---\n\n# 最終裁決\n\n| 評估環節 | 結果 |\n|---|---|\n| 第一關：Kill Filter | **2/5 通過**（❌=3） |\n| 第二關：問題與市場 | **💡 有需求** |\n| 第二關：團隊適配 | **❓ 資訊不足** |\n| 第二關：市場時機 | **⏰ 稍晚但還行** |\n| 第二關：開發成本 | **🟡 中等（1-3 月）** |\n| 第二關：單位經濟 | **❓ 無法估算** |\n| 第三關：防禦性 | **~3/8 層（且不強）** |\n| 第四關：致命風險數 | **3 個（多為「是」）** |\n| **最終結論** | **🔴 No-Go** |\n\n**判定依據：Kill Filter ❌ = 3（≥2）→ 觸發規則 1 → 🔴 No-Go。**\n\n> **結論：🔴 No-Go —— App 內 AI 客服（FAQ 自動回覆/多語言/轉真人）**  \n> 一句話理由：這是高度商品化且平台原生化的標配功能，你目前未提供足夠的「客服量/成本痛點/獨特工作流整合」證據，投入自建大概率變成技術債。\n\n---\n\n## 如果你不接受 No-Go：唯一合理的「不浪費」做法（替代方案）\n- **先買/接入**既有客服平台的 AI（Intercom/Zendesk/Freshdesk 等）或用現成客服 bot 方案，目標是 **4 週內**驗證 ROI，而不是自建。\n- 自建只做「你獨有且平台難做」的部分：例如 **在對話中直接查訂單/改地址/取消訂閱/退款/重設權限**（工具調用 + 權限控管 + 審計），把 bot 變成「可執行工作流」而非「會聊天」。\n\n### 終止條件（Kill Criteria）\n| 指標 | 門檻 | 檢查時間點 | 未達標行動 |\n|---|---|---|---|\n| 自助解決率（不轉人工且不回流） | ≥ 25%（先從 Top 20 問題） | 上線後 4 週 | 停止擴大範圍，改用現成方案/只保留 FAQ 搜尋 |\n| 轉人工前平均輪數 | ≤ 2.0 | 上線後 2 週 | 立即調整：低信心直接轉人工，避免折磨用戶 |\n| CSAT 不下降 | 與基線相比不下降（或下降 < 0.1） | 上線後 4 週 | 立刻下線自動回覆，改成「建議文章 + 一鍵轉人工」 |\n| 成本節省 | 節省的人力成本 ≥（推理+維運）成本的 2 倍 | 上線後 8 週 | 停止投入自建，改採購/縮小範圍 |\n\n---\n\n# 跨項目比較表（本次只有 1 個項目）\n\n| 項目 | Kill Filter | 市場 | 時機 | 成本 | 經濟 | 防禦性 | 致命風險 | 結論 |\n|---|---|---|---|---|---|---|---|---|\n| App 內 AI 客服（FAQ/多語言/轉真人） | **2/5** | 💡 | ⏰ | 🟡 | ❓ | ~3/8 | 3 | **🔴** |\n\n| # | 項目名稱 | 結論 | 一句話理由 |\n|---|---|---|---|\n| 1 | App 內 AI 客服（FAQ/多語言/轉真人） | 🔴 **No-Go** | 標配紅海 + 易被平台原生化 + 你未證明 ROI 痛點與不可替代整合。 |\n\n若你願意補 6 個數字（每月工單量、Top 20 問題占比、目前每單成本/人力、SLA、CSAT、主要語言分佈），我可以把「買現成 vs 自建」的 ROI 分界線算清楚，並給出是否能從 🔴 變 🟡 的條件。";

// Show example on page load
function showExample() {
    resultOutput.innerHTML = renderMarkdown(EXAMPLE_RESULT);
    resultBox.classList.remove('hidden');
    resultBox.classList.add('is-example');
}

function clearExample() {
    resultBox.classList.remove('is-example');
}

// Upload zone: click to select
uploadZone.addEventListener('click', () => fileInput.click());

// Upload zone: drag & drop
uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});
uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

// File input change
fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
    const allowed = ['.txt', '.md', '.pdf', '.xlsx', '.xls'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
        alert('不支援的檔案格式，僅支援 .txt、.md、.pdf、.xlsx');
        return;
    }
    if (file.size > 2 * 1024 * 1024) {
        alert('檔案大小超過 2MB 限制');
        return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileInfo.classList.remove('hidden');
    uploadZone.style.display = 'none';
}

// Remove file
fileRemove.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    uploadZone.style.display = '';
});

// Parse SSE lines from a text chunk, returning parsed events and any leftover partial line
function parseSSE(text) {
    const events = [];
    const lines = text.split('\n');
    let currentEvent = null;
    let currentData = null;

    for (const line of lines) {
        if (line.startsWith('event: ')) {
            currentEvent = line.slice(7);
        } else if (line.startsWith('data: ')) {
            currentData = line.slice(6);
        } else if (line === '' && currentEvent && currentData) {
            try {
                events.push({ event: currentEvent, data: JSON.parse(currentData) });
            } catch (e) {
                // skip malformed JSON
            }
            currentEvent = null;
            currentData = null;
        }
    }
    return events;
}

// Evaluate
evaluateBtn.addEventListener('click', async () => {
    const text = evaluateInput.value.trim();
    if (!text && !selectedFile) {
        alert('請輸入功能描述或上傳檔案');
        return;
    }

    clearExample();

    const formData = new FormData();
    formData.append('text', text);
    if (selectedFile) formData.append('file', selectedFile);

    evaluateBtn.disabled = true;
    evaluateBtn.innerHTML = '<span class="loading-spinner"></span>AI 分析中，請稍候...';
    resultOutput.innerHTML = '<p style="color:#94a3b8"><span class="loading-spinner"></span> 正在啟動分析...</p>';
    resultBox.classList.remove('hidden');

    let searchCount = 0;
    let streamedText = '';
    let renderTimer = null;

    try {
        const res = await fetch('/api/evaluate', { method: 'POST', body: formData });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            let boundary;
            while ((boundary = buffer.indexOf('\n\n')) !== -1) {
                const chunk = buffer.slice(0, boundary + 2);
                buffer = buffer.slice(boundary + 2);

                const events = parseSSE(chunk);
                for (const evt of events) {
                    if (evt.event === 'status') {
                        resultOutput.innerHTML = `<p style="color:#94a3b8"><span class="loading-spinner"></span> ${escapeHtml(evt.data.message)}</p>`;
                    } else if (evt.event === 'search') {
                        searchCount++;
                        evaluateBtn.innerHTML = `<span class="loading-spinner"></span>\uD83D\uDD0D ${escapeHtml(evt.data.query)}`;
                        resultOutput.innerHTML += `<p style="color:#94a3b8">\uD83D\uDD0D 搜尋 #${searchCount}：${escapeHtml(evt.data.query)}</p>`;
                    } else if (evt.event === 'delta') {
                        streamedText += evt.data.content;
                        if (!renderTimer) {
                            renderTimer = setTimeout(() => {
                                resultOutput.innerHTML = renderMarkdown(streamedText);
                                renderTimer = null;
                            }, 100);
                        }
                    } else if (evt.event === 'done') {
                        if (renderTimer) { clearTimeout(renderTimer); renderTimer = null; }
                        resultOutput.innerHTML = renderMarkdown(streamedText);
                    } else if (evt.event === 'result') {
                        resultOutput.innerHTML = renderMarkdown(evt.data.result);
                    } else if (evt.event === 'error') {
                        resultOutput.innerHTML = `<p style="color:#f87171">${escapeHtml(evt.data.error)}</p>`;
                    }
                }
            }
        }
        if (streamedText && renderTimer) {
            clearTimeout(renderTimer);
            resultOutput.innerHTML = renderMarkdown(streamedText);
        }
    } catch (e) {
        resultOutput.innerHTML = '<p style="color:#f87171">發生錯誤，請稍後再試。</p>';
    }

    evaluateBtn.disabled = false;
    evaluateBtn.textContent = '開始評估';
});

// Simple markdown to HTML
function renderMarkdown(md) {
    let html = escapeHtml(md);
    // Headings
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    // Horizontal rules
    html = html.replace(/^---$/gm, '<hr>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Unordered list items
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>');
    // Paragraphs: wrap remaining lines
    html = html.replace(/^(?!<[hHuUoOlL]|<hr)(.+)$/gm, '<p>$1</p>');
    // Clean up extra blank lines
    html = html.replace(/\n{2,}/g, '\n');
    return html;
}

function escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// Copy button
document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = document.getElementById(btn.dataset.target);
        navigator.clipboard.writeText(target.textContent).then(() => {
            btn.textContent = '已複製 ✓';
            setTimeout(() => btn.textContent = '複製', 1500);
        });
    });
});

// Show example hint on page load
showExample();
