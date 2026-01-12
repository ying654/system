// 書籍推薦功能
async function getBookRecommendations(userMessage) {
    try {
        const response = await fetch('/get_book_recommendations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userMessage }),
        });

        const data = await response.json();
        displayBookRecommendations(data.books, data.keywords);
    } catch (error) {
        console.error('獲取書籍推薦失敗:', error);
    }
}

function displayBookRecommendations(books, keywords) {
    const booksList = document.getElementById('booksList');

    if (!books || books.length === 0) {
        booksList.innerHTML = '<div class="no-books">暫無相關書籍推薦</div>';
        return;
    }

    let html = '';

    if (keywords) {
        html += `<div class="keywords-display"><strong>關鍵詞:</strong> ${keywords}</div>`;
    }

    books.forEach(book => {
        html += `
            <a id="bookstore" href="${book.link}">
                <div class="book-item">
                    <img class="book-cover" src="${book.image}" alt="${book.title}">
                    <div class="book-info">
                        <div class="book-title">${book.title}</div>
                        <div class="book-author">作者: ${book.author}</div>
                        <div class="book-source">${book.source || '推薦書籍'}</div>
                    </div>
                </div> 
            </a>
        `;
    });

    booksList.innerHTML = html;
}

function showBookLoading() {
    const booksList = document.getElementById('booksList');
    booksList.innerHTML = '<div class="loading-books">🔍 正在搜尋相關書籍...</div>';
}

// 格式化訊息內容，支援 HTML 和程式碼區塊
function formatMessage(text) {
    if (!text) return '';

    // 處理 HTML 標籤（如 <pre><code>）
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = text;

    // 為所有 <pre><code> 區塊添加複製按鈕
    const codeBlocks = tempDiv.querySelectorAll('pre code');
    codeBlocks.forEach((codeBlock, index) => {
        const pre = codeBlock.parentElement;

        // 創建包裝器
        const wrapper = document.createElement('div');
        wrapper.className = 'code-block-wrapper';

        // 創建複製按鈕
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-code-btn';
        copyBtn.textContent = '複製';
        copyBtn.type = 'button';  // 防止觸發表單提交

        // 將程式碼內容存儲在按鈕的 data 屬性中
        copyBtn.setAttribute('data-code', codeBlock.textContent);

        // 將 pre 包裝起來
        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(pre);
        wrapper.appendChild(copyBtn);
    });

    return tempDiv.innerHTML;
}

// 加入訊息至聊天框（改進版，支援時間戳記）
function addMessage(sender, text, showTimestamp = false) {
    const chatMessages = document.getElementById('chat-messages');
    const messageRow = document.createElement("div");
    messageRow.classList.add("message-row", sender);

    const bubble = document.createElement("div");
    bubble.classList.add("bubble", sender);

    // 使用 innerHTML 以支援 HTML 標籤
    const formattedText = formatMessage(text);
    bubble.innerHTML = formattedText;

    messageRow.appendChild(bubble);

    // 可選：添加時間戳記
    if (showTimestamp) {
        const timestamp = document.createElement("div");
        timestamp.classList.add("timestamp");
        const now = new Date();
        timestamp.textContent = now.toLocaleTimeString('zh-TW', {
            hour: '2-digit',
            minute: '2-digit'
        });
        messageRow.appendChild(timestamp);
    }

    chatMessages.appendChild(messageRow);

    // 平滑滾動到底部
    chatMessages.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: 'smooth'
    });
}

// 綜合所有 DOMContentLoaded 的初始化內容
window.addEventListener("DOMContentLoaded", function () {
    // dropdown 點擊展開/收合
    const dropdowns = document.querySelectorAll(".dropdown-btn");
    dropdowns.forEach(btn => {
        btn.addEventListener("click", function () {
            const content = this.nextElementSibling;
            const arrow = this.querySelector(".arrow");
            const isOpen = content.style.display === "block";
            content.style.display = isOpen ? "none" : "block";
            arrow.innerHTML = isOpen ? "&#9660;" : "&#9650;";
        });
    });

    // 點擊影片按鈕切換 iframe src 與標題
    const buttons = document.querySelectorAll(".dropdown-content button");
    const iframe = document.getElementById("videoPlayer");
    buttons.forEach(btn => {
        btn.addEventListener("click", function () {
            const videoUrl = this.getAttribute("data-src");
            iframe.src = videoUrl;

            const title = document.querySelector(".main h2");
            title.textContent = "機器學習 - " + this.textContent + " by 國立屏東大學林彥廷老師";

            buttons.forEach(b => b.classList.remove("active"));
            this.classList.add("active");
        });
    });

    // sidebar 滾動特效
    const sidebar = document.querySelector('.sidebar');
    sidebar.addEventListener('mouseenter', () => sidebar.classList.add('scrollable'));
    sidebar.addEventListener('mouseleave', () => sidebar.classList.remove('scrollable'));

    // 使用事件委派處理複製按鈕點擊（支援動態添加的按鈕）
    document.addEventListener('click', function (e) {
        if (e.target && e.target.classList.contains('copy-code-btn')) {
            const btn = e.target;
            const code = btn.getAttribute('data-code');

            if (code) {
                // 使用 Clipboard API
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(code).then(() => {
                        const originalText = btn.textContent;
                        btn.textContent = '✓ 已複製';
                        btn.classList.add('copied');
                        setTimeout(() => {
                            btn.textContent = '複製';
                            btn.classList.remove('copied');
                        }, 2000);
                    }).catch(err => {
                        console.error('複製失敗:', err);
                        // 降級方案
                        fallbackCopy(code, btn);
                    });
                } else {
                    // 降級方案：使用舊的 execCommand
                    fallbackCopy(code, btn);
                }
            }
        }
    });

    // 初始歡迎訊息與歷史紀錄載入
    addMessage('ai', '你好！有什麼我可以幫忙的嗎？');
    fetch('/chat/history')
        .then(res => res.json())
        .then(history => {
            if (Array.isArray(history)) {
                for (const msg of history) {
                    if (msg.content !== '[已清除]') {
                        addMessage(msg.role, msg.content);
                    }
                }
            } else if (history.error) {
                addMessage('ai', '⚠️ 無法載入歷史紀錄：' + history.error);
            }
        })
        .catch(() => addMessage('ai', '⚠️ 載入紀錄時出錯。'));
});

// 降級複製方案（適用於不支援 Clipboard API 的瀏覽器）
function fallbackCopy(text, btn) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            btn.textContent = '已複製!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.textContent = '複製';
                btn.classList.remove('copied');
            }, 2000);
        } else {
            btn.textContent = '複製失敗';
            setTimeout(() => {
                btn.textContent = '複製';
            }, 2000);
        }
    } catch (err) {
        console.error('降級複製也失敗:', err);
        btn.textContent = '複製失敗';
        setTimeout(() => {
            btn.textContent = '複製';
        }, 2000);
    }

    document.body.removeChild(textArea);
}

// 切換聊天視窗顯示/隱藏（添加動畫效果）
function toggleChat() {
    const chatWindow = document.getElementById("chatWindow");
    const botBtn = document.querySelector(".aiRobot-btn");
    const isHidden = chatWindow.classList.contains("hidden");

    if (isHidden) {
        chatWindow.classList.remove("hidden");
        botBtn.style.display = "none";
        // 添加彈出動畫
        chatWindow.style.animation = "popIn 0.3s ease";
    } else {
        // 添加收起動畫
        chatWindow.style.animation = "popOut 0.2s ease";
        setTimeout(() => {
            chatWindow.classList.add("hidden");
            botBtn.style.display = "block";
        }, 200);
    }
}

// 添加動畫 keyframes（需要在 CSS 中定義，或通過 style 標籤動態添加）
if (!document.getElementById('chat-animations')) {
    const style = document.createElement('style');
    style.id = 'chat-animations';
    style.textContent = `
        @keyframes popIn {
            from {
                opacity: 0;
                transform: scale(0.8) translateY(20px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        
        @keyframes popOut {
            from {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
            to {
                opacity: 0;
                transform: scale(0.8) translateY(20px);
            }
        }
    `;
    document.head.appendChild(style);
}

// 清除聊天紀錄
const clearBtn = document.getElementById('clearBtn');
clearBtn.addEventListener('click', async () => {
    const chatMessages = document.getElementById('chat-messages');
    const chatInput = document.getElementById('chat-input');

    chatMessages.innerHTML = '';
    chatInput.value = '';

    const booksList = document.getElementById('booksList');
    booksList.innerHTML = '<div class="no-books">開始對話即可獲得書籍推薦 ✨</div>';

    try {
        const res = await fetch('/chat/clear', { method: 'POST' });
        const result = await res.json();

        if (result.success) {
            addMessage('ai', '你好！有什麼我可以幫忙的嗎？');
        } else {
            addMessage('ai', '清除記錄失敗：' + (result.error || '未知錯誤'));
        }
    } catch (e) {
        addMessage('ai', '清除時發生錯誤');
        console.error(e);
    }
});

// 提交訊息處理
const chatForm = document.getElementById('chat-form');
chatForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    const chatInput = document.getElementById('chat-input');
    const text = chatInput.value.trim();
    if (!text) return;

    // 加入使用者訊息
    addMessage('user', text);
    chatInput.value = '';
    chatInput.focus();

    // 顯示書籍推薦載入狀態
    showBookLoading();

    // 顯示 AI 輸入中
    const chatMessages = document.getElementById('chat-messages');
    const typingRow = document.createElement("div");
    typingRow.classList.add("message-row", "ai");
    typingRow.setAttribute("id", "typingIndicator");

    const typingBubble = document.createElement("div");
    typingBubble.classList.add("bubble", "ai", "typing");
    typingBubble.innerHTML = "<span></span><span></span><span></span>";

    typingRow.appendChild(typingBubble);
    chatMessages.appendChild(typingRow);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        // 同時發送聊天和書籍推薦請求
        const [chatResponse] = await Promise.all([
            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text }),
            }),
            getBookRecommendations(text)
        ]);

        const chatData = await chatResponse.json();

        // 移除輸入中提示
        const typingEl = document.getElementById("typingIndicator");
        if (typingEl) typingEl.remove();

        // 加入 AI 真正的回覆
        if (chatData.reply) {
            addMessage('ai', chatData.reply);
        } else if (chatData.error) {
            addMessage('ai', '錯誤：' + chatData.error);
        }
    } catch (error) {
        const typingEl = document.getElementById("typingIndicator");
        if (typingEl) typingEl.remove();

        addMessage('ai', '伺服器錯誤，請稍後再試。');

        const booksList = document.getElementById('booksList');
        booksList.innerHTML = '<div class="no-books">獲取推薦失敗，請稍後再試</div>';
    }
});

// 拖曳聊天視窗
window.addEventListener("DOMContentLoaded", () => {
    const chatWindow = document.getElementById("chatWindow");
    const chatHeader = chatWindow.querySelector(".chat-header");
    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    chatHeader.addEventListener("mousedown", (e) => {
        // 避免在點擊關閉按鈕時觸發拖曳
        if (e.target.classList.contains('close-btn') || e.target.closest('.close-btn')) {
            return;
        }

        isDragging = true;
        offsetX = e.clientX - chatWindow.offsetLeft;
        offsetY = e.clientY - chatWindow.offsetTop;
        chatWindow.style.transition = "none";
        chatHeader.style.cursor = "grabbing";
    });

    document.addEventListener("mousemove", (e) => {
        if (isDragging) {
            const newLeft = e.clientX - offsetX;
            const newTop = e.clientY - offsetY;

            // 限制視窗不超出螢幕範圍
            const maxLeft = window.innerWidth - chatWindow.offsetWidth;
            const maxTop = window.innerHeight - chatWindow.offsetHeight;

            chatWindow.style.left = `${Math.max(0, Math.min(newLeft, maxLeft))}px`;
            chatWindow.style.top = `${Math.max(0, Math.min(newTop, maxTop))}px`;
            chatWindow.style.bottom = "auto";
            chatWindow.style.right = "auto";
            chatWindow.style.position = "fixed";
        }
    });

    document.addEventListener("mouseup", () => {
        if (isDragging) {
            isDragging = false;
            chatWindow.style.transition = "";
            chatHeader.style.cursor = "move";
        }
    });

    // ========== 調整大小功能 ==========
    initializeResize();
});

// 初始化調整大小功能
function initializeResize() {
    const chatWindow = document.getElementById("chatWindow");

    // 創建調整大小的控制點
    const handles = [
        { class: 'corner', cursor: 'nwse-resize' },
        { class: 'right', cursor: 'ew-resize' },
        { class: 'bottom', cursor: 'ns-resize' },
        { class: 'left', cursor: 'ew-resize' },
        { class: 'top', cursor: 'ns-resize' },
        { class: 'corner-bl', cursor: 'nesw-resize' },
        { class: 'corner-tr', cursor: 'nesw-resize' },
        { class: 'corner-tl', cursor: 'nwse-resize' }
    ];

    handles.forEach(handle => {
        const element = document.createElement('div');
        element.className = `resize-handle ${handle.class}`;
        chatWindow.appendChild(element);
    });

    // 調整大小邏輯
    let isResizing = false;
    let currentHandle = null;
    let startX, startY, startWidth, startHeight, startLeft, startTop;

    const minWidth = 320;
    const minHeight = 400;
    const maxWidth = window.innerWidth * 0.9;
    const maxHeight = window.innerHeight * 0.85;

    chatWindow.addEventListener('mousedown', (e) => {
        if (e.target.classList.contains('resize-handle')) {
            isResizing = true;
            currentHandle = e.target;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = chatWindow.offsetWidth;
            startHeight = chatWindow.offsetHeight;

            // 轉換位置為 left/top 格式（第一次調整時）
            const rect = chatWindow.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;

            // 立即切換到 left/top 定位方式
            chatWindow.style.left = `${startLeft}px`;
            chatWindow.style.top = `${startTop}px`;
            chatWindow.style.bottom = 'auto';
            chatWindow.style.right = 'auto';

            chatWindow.classList.add('resizing');
            e.preventDefault();
            e.stopPropagation();
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;

        const deltaX = e.clientX - startX;
        const deltaY = e.clientY - startY;

        const handleClass = currentHandle.className;

        // 右下角
        if (handleClass.includes('corner') && !handleClass.includes('corner-')) {
            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + deltaX));
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight + deltaY));
            chatWindow.style.width = `${newWidth}px`;
            chatWindow.style.height = `${newHeight}px`;
        }
        // 右側
        else if (handleClass.includes('right')) {
            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + deltaX));
            chatWindow.style.width = `${newWidth}px`;
        }
        // 底部
        else if (handleClass.includes('bottom')) {
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight + deltaY));
            chatWindow.style.height = `${newHeight}px`;
        }
        // 左側
        else if (handleClass.includes('left')) {
            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth - deltaX));
            const widthDelta = newWidth - startWidth;
            chatWindow.style.width = `${newWidth}px`;
            chatWindow.style.left = `${startLeft - widthDelta}px`;
        }
        // 頂部
        else if (handleClass.includes('top')) {
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight - deltaY));
            const heightDelta = newHeight - startHeight;
            chatWindow.style.height = `${newHeight}px`;
            chatWindow.style.top = `${startTop - heightDelta}px`;
        }
        // 左下角
        else if (handleClass.includes('corner-bl')) {
            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth - deltaX));
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight + deltaY));
            const widthDelta = newWidth - startWidth;
            chatWindow.style.width = `${newWidth}px`;
            chatWindow.style.left = `${startLeft - widthDelta}px`;
            chatWindow.style.height = `${newHeight}px`;
        }
        // 右上角
        else if (handleClass.includes('corner-tr')) {
            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + deltaX));
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight - deltaY));
            const heightDelta = newHeight - startHeight;
            chatWindow.style.width = `${newWidth}px`;
            chatWindow.style.height = `${newHeight}px`;
            chatWindow.style.top = `${startTop - heightDelta}px`;
        }
        // 左上角
        else if (handleClass.includes('corner-tl')) {
            const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth - deltaX));
            const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeight - deltaY));
            const widthDelta = newWidth - startWidth;
            const heightDelta = newHeight - startHeight;
            chatWindow.style.width = `${newWidth}px`;
            chatWindow.style.left = `${startLeft - widthDelta}px`;
            chatWindow.style.height = `${newHeight}px`;
            chatWindow.style.top = `${startTop - heightDelta}px`;
        }
    });

    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            currentHandle = null;
            chatWindow.classList.remove('resizing');
        }
    });
}