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

// Evaluate
evaluateBtn.addEventListener('click', async () => {
    const text = evaluateInput.value.trim();
    if (!text && !selectedFile) {
        alert('請輸入功能描述或上傳檔案');
        return;
    }

    const formData = new FormData();
    formData.append('text', text);
    if (selectedFile) formData.append('file', selectedFile);

    evaluateBtn.disabled = true;
    evaluateBtn.innerHTML = '<span class="loading-spinner"></span>AI 分析中，請稍候...';
    resultBox.classList.add('hidden');

    try {
        const res = await fetch('/api/evaluate', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.error) {
            resultOutput.innerHTML = `<p style="color:#f87171">${escapeHtml(data.error)}</p>`;
        } else {
            resultOutput.innerHTML = renderMarkdown(data.result);
        }
        resultBox.classList.remove('hidden');
    } catch (e) {
        resultOutput.innerHTML = '<p style="color:#f87171">發生錯誤，請稍後再試。</p>';
        resultBox.classList.remove('hidden');
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
