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

// 加入訊息至聊天框（改進版）
function addMessage(sender, text) {
    const chatMessages = document.getElementById('chat-messages');
    const messageRow = document.createElement("div");
    messageRow.classList.add("message-row", sender);

    const bubble = document.createElement("div");
    bubble.classList.add("bubble", sender);

    // 使用 innerHTML 以支援 HTML 標籤
    const formattedText = formatMessage(text);
    bubble.innerHTML = formattedText;

    messageRow.appendChild(bubble);
    chatMessages.appendChild(messageRow);
    chatMessages.scrollTop = chatMessages.scrollHeight;
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
                        btn.textContent = '已複製!';
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

// 切換聊天視窗顯示/隱藏
function toggleChat() {
    const chatWindow = document.getElementById("chatWindow");
    const botBtn = document.querySelector(".aiRobot-btn");
    const isHidden = chatWindow.classList.contains("hidden");
    chatWindow.classList.toggle("hidden", !isHidden);
    botBtn.style.display = isHidden ? "none" : "block";
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
        isDragging = true;
        offsetX = e.clientX - chatWindow.offsetLeft;
        offsetY = e.clientY - chatWindow.offsetTop;
        chatWindow.style.transition = "none";
    });

    document.addEventListener("mousemove", (e) => {
        if (isDragging) {
            chatWindow.style.left = `${e.clientX - offsetX}px`;
            chatWindow.style.top = `${e.clientY - offsetY}px`;
            chatWindow.style.bottom = "auto";
            chatWindow.style.right = "auto";
            chatWindow.style.position = "fixed";
        }
    });

    document.addEventListener("mouseup", () => {
        isDragging = false;
        chatWindow.style.transition = "";
    });
});