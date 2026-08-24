const API_BASE = '/api';
let conversationId = 'sess_' + Math.random().toString(36).substr(2, 9);

// Elements
const chatHistory = document.getElementById('chat-history');
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const contextContent = document.getElementById('context-content');

// Status Elements
const healthStatus = document.getElementById('health-status');
const statusText = document.querySelector('.status-text');
const dot = document.querySelector('.dot');
const dbStatus = document.getElementById('db-status');
const embeddingProvider = document.getElementById('embedding-provider');

// Initialize
async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        
        if (data.status === 'ok') {
            dot.className = 'dot ok';
            statusText.textContent = 'Online';
            dbStatus.textContent = data.database === 'test_mode' ? 'Test Mode (In-Memory)' : 'Oracle 23ai';
            embeddingProvider.textContent = data.embedding_provider;
        } else {
            dot.className = 'dot error';
            statusText.textContent = 'Issues Detected';
        }
    } catch (e) {
        dot.className = 'dot error';
        statusText.textContent = 'Disconnected';
    }
}
checkHealth();

function setQuery(text) {
    queryInput.value = text;
    queryInput.focus();
}

function appendUserMessage(text) {
    const msg = document.createElement('div');
    msg.className = 'message user-message';
    msg.innerHTML = `<div class="message-content">${escapeHTML(text)}</div>`;
    chatHistory.appendChild(msg);
    scrollToBottom();
}

function appendSystemMessage(contentHTML) {
    const msg = document.createElement('div');
    msg.className = 'message system-message';
    msg.innerHTML = `<div class="message-content">${contentHTML}</div>`;
    chatHistory.appendChild(msg);
    scrollToBottom();
    return msg;
}

function appendLoader() {
    const msg = document.createElement('div');
    msg.className = 'message system-message';
    msg.id = 'loader';
    msg.innerHTML = `
        <div class="message-content" style="padding: 16px;">
            <div class="typing-indicator"><span></span><span></span><span></span></div>
        </div>
    `;
    chatHistory.appendChild(msg);
    scrollToBottom();
    return msg;
}

function removeLoader() {
    const loader = document.getElementById('loader');
    if (loader) loader.remove();
}

function scrollToBottom() {
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function updateContextPanel(data) {
    if (!data.explanation) {
        contextContent.innerHTML = `<div class="empty-context"><p>No context available for this turn.</p></div>`;
        return;
    }

    const exp = data.explanation;
    let html = '';

    // Retrieval Mode
    html += `
        <div class="context-section">
            <h4>Retrieval Engine</h4>
            <div class="detail-row">
                <span class="detail-label">Mode</span>
                <span class="pill ${exp.retrieval.mode}">${exp.retrieval.mode}</span>
            </div>
            ${exp.retrieval.alpha !== undefined ? `
            <div class="detail-row">
                <span class="detail-label">Hybrid Alpha (Semantic Weight)</span>
                <span>${exp.retrieval.alpha}</span>
            </div>` : ''}
        </div>
    `;

    // Intent
    if (exp.intent) {
        html += `<div class="context-section"><h4>Extracted Intent</h4>`;
        if (exp.intent.structured_filters && exp.intent.structured_filters.length > 0) {
            html += `<div class="detail-row"><span class="detail-label">SQL Filters</span></div>`;
            exp.intent.structured_filters.forEach(f => {
                html += `<div style="font-size: 13px; margin-bottom: 4px; padding-left: 8px; border-left: 2px solid var(--primary);">${escapeHTML(f)}</div>`;
            });
        }
        if (exp.intent.semantic_query) {
            html += `
            <div class="detail-row" style="margin-top: 12px;">
                <span class="detail-label">Vector Search Query</span>
            </div>
            <div style="font-size: 13px; font-style: italic;">"${escapeHTML(exp.intent.semantic_query)}"</div>`;
        }
        html += `</div>`;
    }

    // SQL
    if (exp.generated_sql) {
        html += `
        <div class="context-section">
            <h4>Generated SQL (QueryIR)</h4>
            <div class="code-block">${escapeHTML(exp.generated_sql)}</div>
        </div>
        `;
    }

    // Performance
    if (exp.timing) {
        html += `
        <div class="context-section">
            <h4>Performance</h4>
            ${exp.timing.sql_ms ? `<div class="detail-row"><span class="detail-label">SQL Latency</span><span>${exp.timing.sql_ms} ms</span></div>` : ''}
            ${exp.timing.vector_ms ? `<div class="detail-row"><span class="detail-label">Vector Latency</span><span>${exp.timing.vector_ms} ms</span></div>` : ''}
            ${exp.timing.total_ms ? `<div class="detail-row"><span class="detail-label">Total Time</span><span>${exp.timing.total_ms} ms</span></div>` : ''}
        </div>
        `;
    }

    contextContent.innerHTML = html;
}

queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = queryInput.value.trim();
    if (!text) return;

    queryInput.value = '';
    appendUserMessage(text);
    appendLoader();
    submitBtn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: conversationId,
                query: text,
                top_k: 10
            })
        });

        const data = await res.json();
        removeLoader();

        if (data.status === 'clarification_required') {
            let html = `<h3>Clarification Needed</h3><p>${escapeHTML(data.message)}</p>`;
            if (data.options && data.options.length > 0) {
                html += `<div class="suggestions">`;
                data.options.forEach(opt => {
                    html += `<button class="suggestion-chip" onclick="submitClarification('${escapeHTML(text)}', '${escapeHTML(opt)}')">${escapeHTML(opt)}</button>`;
                });
                html += `</div>`;
            }
            appendSystemMessage(html);
        } else if (data.status === 'unanswerable') {
            appendSystemMessage(`<h3>Cannot Answer</h3><p>${escapeHTML(data.message)}</p>`);
        } else {
            // Success
            let html = `<h3>Found ${data.result_count} results in ${data.latency_ms}ms</h3>`;
            
            if (data.results && data.results.length > 0) {
                html += `<div class="result-list">`;
                data.results.forEach((r, idx) => {
                    html += `
                    <div class="result-item">
                        <div class="result-title">${idx + 1}. ${escapeHTML(r.title)}</div>
                        <div class="result-meta">
                            <span class="meta-tag">📄 ID: ${r.paper_id}</span>
                            ${r.year ? `<span class="meta-tag">📅 ${r.year}</span>` : ''}
                            ${r.citation_count !== null ? `<span class="meta-tag">📊 ${r.citation_count} citations</span>` : ''}
                            ${r.score !== null ? `<span class="meta-tag">🎯 Score: ${r.score.toFixed(3)}</span>` : ''}
                            ${r.source ? `<span class="meta-tag" style="background: rgba(138, 43, 226, 0.15); color: #cda2ff; border-color: rgba(138, 43, 226, 0.3);">🌐 ${escapeHTML(r.source)}</span>` : ''}
                        </div>
                    </div>`;
                });
                html += `</div>`;
            } else {
                html += `<p>No papers matched your query.</p>`;
            }
            appendSystemMessage(html);
            
            if (data.explanation) {
                updateContextPanel(data);
            }
        }
    } catch (e) {
        removeLoader();
        appendSystemMessage(`<h3>Error</h3><p>Could not connect to the backend server.</p>`);
    } finally {
        submitBtn.disabled = false;
        queryInput.focus();
    }
});

async function submitClarification(originalQuery, clarification) {
    appendUserMessage(clarification);
    appendLoader();
    
    try {
        const res = await fetch(`${API_BASE}/clarify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                conversation_id: conversationId,
                original_query: originalQuery,
                clarification: clarification
            })
        });

        const data = await res.json();
        removeLoader();
        
        let html = `<h3>Found ${data.result_count} results in ${data.latency_ms}ms</h3>`;
        if (data.results && data.results.length > 0) {
            html += `<div class="result-list">`;
            data.results.forEach((r, idx) => {
                html += `
                <div class="result-item">
                    <div class="result-title">${idx + 1}. ${escapeHTML(r.title)}</div>
                    <div class="result-meta">
                        <span class="meta-tag">📄 ID: ${r.paper_id}</span>
                        ${r.year ? `<span class="meta-tag">📅 ${r.year}</span>` : ''}
                        ${r.citation_count !== null ? `<span class="meta-tag">📊 ${r.citation_count} citations</span>` : ''}
                        ${r.score !== null ? `<span class="meta-tag">🎯 Score: ${r.score.toFixed(3)}</span>` : ''}
                        ${r.source ? `<span class="meta-tag" style="background: rgba(138, 43, 226, 0.15); color: #cda2ff; border-color: rgba(138, 43, 226, 0.3);">🌐 ${escapeHTML(r.source)}</span>` : ''}
                    </div>
                </div>`;
            });
            html += `</div>`;
        }
        appendSystemMessage(html);
        if (data.explanation) updateContextPanel(data);
    } catch (e) {
        removeLoader();
        appendSystemMessage(`<h3>Error</h3><p>Could not submit clarification.</p>`);
    }
}
