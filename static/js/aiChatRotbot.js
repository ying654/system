const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
document.getElementById('clearBtn').addEventListener('click', async () => {
    // 清除畫面訊息
    chatMessages.innerHTML = '';
    chatInput.value = '';

    // 呼叫後端清除 API
    try {
        const res = await fetch('/chat/clear', { method: 'POST' });
        const result = await res.json();

        if (result.success) {
            addMessage('ai', '你好！有什麼我可以幫忙的嗎？');
        } else {
            addMessage('ai', '清除紀錄失敗：' + (result.error || '未知錯誤'));
        }
    } catch (e) {
        addMessage('ai', '清除伺服器紀錄時發生錯誤');
        console.error(e);
    }
});

// 加入訊息到畫面
function addMessage(role, content) {
    const div = document.createElement('div');
    div.classList.add('bubble', role);
    div.textContent = content;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 載入初始 AI 訊息
window.addEventListener('DOMContentLoaded', () => {
    addMessage('ai', '你好！有什麼我可以幫忙的嗎？');
});

// 表單送出事件
chatForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    // 加入使用者訊息
    addMessage('user', text);
    chatInput.value = '';
    chatInput.focus();

    // 顯示 AI 三個點動畫
    const typingBubble = document.createElement('div');
    typingBubble.classList.add('bubble', 'ai', 'typing');
    typingBubble.setAttribute('id', 'typingIndicator');
    typingBubble.innerHTML = "<span></span><span></span><span></span>";
    chatMessages.appendChild(typingBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 呼叫後端 API
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });

        const data = await response.json();

        // 移除輸入中動畫
        const typingEl = document.getElementById('typingIndicator');
        if (typingEl) typingEl.remove();

        // 顯示 AI 回覆
        if (data.reply) {
            addMessage('ai', data.reply);
        } else if (data.error) {
            addMessage('ai', '錯誤：' + data.error);
        }
    } catch (error) {
        // 移除動畫
        const typingEl = document.getElementById('typingIndicator');
        if (typingEl) typingEl.remove();

        addMessage('ai', '伺服器錯誤，請稍後再試。');
    }
});


// 載入初始訊息 & 歷史紀錄
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/chat/history');
        const history = await res.json();

        if (Array.isArray(history)) {
            for (const msg of history) {
                addMessage(msg.role, msg.content);
            }
        } else if (history.error) {
            addMessage('ai', '⚠️ 無法載入歷史紀錄：' + history.error);
        }
    } catch (err) {
        addMessage('ai', '⚠️ 載入紀錄時出錯。');
    }
});
function logout() {
    window.location.href = '/'; // 跳轉到 home.html
}
function goToVideo() {
    window.location.href = '/video';
}