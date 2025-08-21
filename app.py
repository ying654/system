from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from openai import OpenAI
from dotenv import load_dotenv
import sqlite3, os, hashlib, json, requests
from bs4 import BeautifulSoup
import re
import time
import secrets
from urllib.parse import quote

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# 建立一個 OpenAI 客戶端實例
client = OpenAI(api_key=api_key)
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

DB_NAME = "users.db"

###################################################################### 鷹架理論相關的學習單元定義
LEARNING_UNITS = {
    "資料預處理": {
        "keywords": [
            "資料清洗",
            "缺失值",
            "異常值",
            "標準化",
            "正規化",
            "特徵選擇",
            "資料轉換",
            "資料預處理",
            "自變量",
            "應變量",
            "資料遺漏值",
            "切分",
        ],
        "difficulty_level": "基礎",
        "prerequisites": [],
    },
    "線性回歸": {
        "keywords": [
            "回歸分析",
            "最小平方法",
            "相關係數",
            "預測",
            "線性關係",
            "斜率",
            "截距",
            "資料集",
        ],
        "difficulty_level": "基礎",
        "prerequisites": ["資料預處理"],
    },
    "多元線性回歸": {
        "keywords": [
            "多變數",
            "多元回歸",
            "變數選擇",
            "共線性",
            "調整R平方",
            "虛擬變量",
        ],
        "difficulty_level": "中等",
        "prerequisites": ["線性回歸"],
    },
    "多項式回歸": {
        "keywords": ["非線性", "多項式", "曲線擬合", "過度擬合", "複雜度", "degree"],
        "difficulty_level": "中等",
        "prerequisites": ["線性回歸"],
    },
    "支援向量機": {
        "keywords": ["SVM", "核函數", "支援向量", "分類", "決策邊界", "margin"],
        "difficulty_level": "進階",
        "prerequisites": ["線性回歸", "分類概念"],
    },
    "貝氏分類": {
        "keywords": ["貝氏定理", "條件機率", "Naive Bayes", "特徵獨立性"],
        "difficulty_level": "中等",
        "prerequisites": ["機率統計"],
    },
    "決策樹": {
        "keywords": ["樹狀結構", "資訊增益", "熵", "分支", "葉節點", "剪枝"],
        "difficulty_level": "中等",
        "prerequisites": ["分類概念"],
    },
    "隨機森林": {
        "keywords": ["ensemble", "決策樹集合", "隨機抽樣", "投票機制", "特徵隨機性"],
        "difficulty_level": "進階",
        "prerequisites": ["決策樹"],
    },
    "K平均分群": {
        "keywords": ["分群", "無監督學習", "中心點", "距離", "收斂", "群集"],
        "difficulty_level": "中等",
        "prerequisites": ["資料預處理"],
    },
    "交叉驗證": {
        "keywords": ["驗證", "過度擬合", "模型評估", "K-fold", "泛化能力"],
        "difficulty_level": "中等",
        "prerequisites": ["模型評估概念"],
    },
    "網格搜尋": {
        "keywords": ["超參數調整", "參數最佳化", "模型調校", "Grid Search"],
        "difficulty_level": "進階",
        "prerequisites": ["交叉驗證", "模型評估"],
    },
    "SVM": {
        "keywords": ["支持向量機", "分類器", "超平面", "Support Vector Machine"],
        "difficulty_level": "進階",
        "prerequisites": ["資料預處理", "線性回歸"],
    },
    "邏輯回歸": {
        "keywords": ["Logistic Regression", "二元分類", "機率模型", "Sigmoid 函數"],
        "difficulty_level": "中階",
        "prerequisites": ["監督式學習", "線性回歸", "機率與統計"],
    },
}


# 從對話去猜，使用者有問題的單元
def identify_learning_unit(user_message):
    """識別使用者訊息中的學習單元"""
    message_lower = user_message.lower()

    for unit, info in LEARNING_UNITS.items():
        # 檢查單元名稱
        if unit.lower() in message_lower:
            return unit

        # 檢查關鍵詞
        for keyword in info["keywords"]:
            if keyword.lower() in message_lower:
                return unit

    return "通用概念"  # 預設單元


def get_user_learning_history(username):
    """獲取使用者的學習歷史記錄"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        SELECT user_message, learning_unit, scaffolding_type, understanding_level 
        FROM conversations 
        WHERE username = ? 
        ORDER BY timestamp DESC 
        LIMIT 10
    """,
        (username,),
    )

    history = c.fetchall()
    conn.close()

    return history


def analyze_scaffolding_need(user_message, learning_unit, user_history, username):
    """分析需要何種鷹架支持"""

    # 準備分析用的資料
    analysis_prompt = f"""
你是一位機器學習教育專家，需要判斷學生需要何種鷹架支持。請根據以下資訊分析：

學習單元：{learning_unit}
單元難度：{LEARNING_UNITS.get(learning_unit, {}).get('difficulty_level', '未知')}
前置需求：{LEARNING_UNITS.get(learning_unit, {}).get('prerequisites', [])}
學生問題：{user_message}

學習歷史：
{[f"問題：{h[0]}，單元：{h[1]}，鷹架類型：{h[2]}，理解程度：{h[3]}" for h in user_history[:5]]}

請判斷學生需要以下哪種鷹架支持：

1. **差異鷹架（Differentiated Scaffolding）**：
   - 適用於：學生對概念完全陌生，需要從基礎開始建構
   - 特徵：提問基礎概念、缺乏前置知識、表達困惑

2. **重複鷹架（Repetitive Scaffolding）**：
   - 適用於：學生有基本理解但需要加深印象和鞏固
   - 特徵：重複詢問類似問題、理解不夠深入、需要練習

3. **協同鷹架（Collaborative Scaffolding）**：
   - 適用於：學生有良好基礎，可以進行深入討論和應用
   - 特徵：提出進階問題、想要實際應用、能夠思辨

請只回答以下格式：
鷹架類型：[差異鷹架/重複鷹架/協同鷹架]
理由：[簡短說明為何選擇此鷹架類型]
理解程度：[初學者/進階學習者/熟練者]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "你是鷹架理論專家，專門分析學生的學習需求。",
                },
                {"role": "user", "content": analysis_prompt},
            ],
            max_tokens=200,
            temperature=0.3,
        )

        analysis_result = response.choices[0].message.content.strip()

        # 解析回應
        scaffolding_type = "差異鷹架"  # 預設值
        understanding_level = "初學者"  # 預設值

        if "重複鷹架" in analysis_result:
            scaffolding_type = "重複鷹架"
            understanding_level = "進階學習者"
        elif "協同鷹架" in analysis_result:
            scaffolding_type = "協同鷹架"
            understanding_level = "熟練者"
        elif "差異鷹架" in analysis_result:
            scaffolding_type = "差異鷹架"
            understanding_level = "初學者"

        return scaffolding_type, understanding_level, analysis_result

    except Exception as e:
        print(f"鷹架分析錯誤: {e}")
        return "差異鷹架", "初學者", "分析失敗，使用預設鷹架"


def generate_scaffolded_response(
    user_message, learning_unit, scaffolding_type, understanding_level
):
    """根據鷹架類型生成適當的回應"""

    # 根據不同鷹架類型設計不同的系統提示
    scaffolding_prompts = {
        "差異鷹架": f"""
你是一位耐心的機器學習導師，正在使用「差異鷹架」策略教導初學者。

教學重點：
- 從最基礎的概念開始解釋
- 使用生活化的比喻和例子
- 將複雜概念分解成簡單步驟
- 多問「你知道嗎？」、「想像一下...」等引導式問題
- 確認學生理解每個步驟後才繼續

當前學習單元：{learning_unit}
單元基礎知識：{LEARNING_UNITS.get(learning_unit, {}).get('keywords', [])}
前置需求：{LEARNING_UNITS.get(learning_unit, {}).get('prerequisites', [])}

回應風格：
- 像和朋友聊天一樣親切
- 用「讓我們想想...」、「這就像...」開頭
- 提供具體範例和視覺化描述
- 鼓勵學生提問
""",
        "重複鷹架": f"""
你是一位機器學習導師，正在使用「重複鷹架」策略幫助學生鞏固理解。

教學重點：
- 用不同方式重複核心概念
- 提供多個相似但漸進的例子
- 強調重點知識的應用情境
- 設計練習題讓學生實作
- 連結之前學過的概念

當前學習單元：{learning_unit}
核心概念：{LEARNING_UNITS.get(learning_unit, {}).get('keywords', [])}

回應風格：
- 「讓我們再看一個例子...」
- 「這個概念的另一種理解方式是...」
- 「你可以這樣練習...」
- 強化記憶的重複模式
""",
        "協同鷹架": f"""
你是一位機器學習專家，正在使用「協同鷹架」策略與有基礎的學生進行深度對話。

教學重點：
- 引導學生自主思考和發現
- 提出開放性和挑戰性問題
- 鼓勵批判性思考
- 連結理論與實際應用
- 討論進階主題和最新發展

當前學習單元：{learning_unit}
進階概念：{LEARNING_UNITS.get(learning_unit, {}).get('keywords', [])}

回應風格：
- 「你認為為什麼...？」
- 「如果我們改變這個條件會怎樣？」
- 「在實際應用中，這會遇到什麼挑戰？」
- 促進深度思考的蘇格拉底式對話
""",
    }

    system_prompt = scaffolding_prompts.get(
        scaffolding_type, scaffolding_prompts["差異鷹架"]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"回應生成錯誤: {e}")
        return "抱歉，我遇到了一些技術問題。能請你再說一次你的問題嗎？"


#########################################################################################
def extract_keywords_from_message(user_message):
    """使用OpenAI提取用戶訊息中的關鍵詞"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "你是一個關鍵詞提取專家。從用戶的訊息中提取與機器學習、資料科學、程式設計相關的關鍵詞。只回傳最重要的1-2個關鍵詞，用逗號分隔。如果沒有相關關鍵詞，回傳'機器學習'。",
                },
                {"role": "user", "content": f"請從這段話提取關鍵詞：{user_message}"},
            ],
            max_tokens=50,
            temperature=0.3,
        )
        keywords = response.choices[0].message.content.strip()
        return keywords
    except Exception as e:
        print(f"關鍵詞提取錯誤: {e}")
        return "機器學習"


def search_books_google(keywords):
    """使用Google搜索相關書籍"""
    # 將關鍵字編碼，組成搜尋 URL
    url = f"https://search.books.com.tw/search/query/key/{quote(keywords)}/cat/all"
    print(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    }

    # 發送 GET 請求
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()  # 如果有錯誤直接拋出

    soup = BeautifulSoup(resp.text, "html.parser")
    # 找到 table-td 裡面的 <a> 標籤
    a_tag = soup.select_one(".table-td a")
    author = soup.select_one(".author a")
    img_tag = soup.select_one(".table-td img")
    if a_tag and a_tag.has_attr("title"):
        title_text = a_tag["title"]  # 直接取 title 屬性
        href = a_tag["href"]
        if img_tag.has_attr("data-src"):  # 懶加載用 data-src
            img_src = img_tag["data-src"]
        else:  # 一般情況直接 src
            img_src = img_tag["src"]
    books = []
    books.append(
        {
            "title": title_text,
            "author": author.text,
            "image": img_src,
            "link": href,
            "source": "博客來",
        }
    )
    return books


@app.route("/get_book_recommendations", methods=["POST"])
def get_book_recommendations():
    """獲取書籍推薦的API端點"""
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    data = request.json
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"books": []})

    # 提取關鍵詞
    keywords = extract_keywords_from_message(user_message)
    print(f"提取的關鍵詞: {keywords}")

    # 搜索相關書籍
    books = search_books_google(keywords)

    return jsonify({"books": books, "keywords": keywords})


# 儲存聊天資料 - 加入鷹架理論分析
@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    user_message = request.json.get("message")

    try:
        # 1. 識別學習單元
        learning_unit = identify_learning_unit(user_message)

        # 2. 獲取使用者學習歷史
        user_history = get_user_learning_history(username)

        # 3. 分析需要的鷹架類型
        scaffolding_type, understanding_level, analysis_reason = (
            analyze_scaffolding_need(
                user_message, learning_unit, user_history, username
            )
        )

        # 4. 根據鷹架類型生成回應
        reply = generate_scaffolded_response(
            user_message, learning_unit, scaffolding_type, understanding_level
        )

        # 5. 儲存到資料庫（包含鷹架資訊）
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO conversations 
            (username, user_message, bot_reply, learning_unit, scaffolding_type, understanding_level, analysis_reason) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                username,
                user_message,
                reply,
                learning_unit,
                scaffolding_type,
                understanding_level,
                analysis_reason,
            ),
        )
        conn.commit()
        conn.close()

        return jsonify(
            {
                "reply": reply,
                "learning_unit": learning_unit,
                "scaffolding_type": scaffolding_type,
                "understanding_level": understanding_level,
                "analysis_reason": analysis_reason,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 對話紀錄
@app.route("/chat/history")
def chat_history():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """
        SELECT user_message, bot_reply, learning_unit, scaffolding_type, understanding_level 
        FROM conversations 
        WHERE username = ? 
        ORDER BY timestamp ASC
    """,
        (username,),
    )
    rows = c.fetchall()
    conn.close()

    history = []
    for (
        user_msg,
        bot_reply,
        learning_unit,
        scaffolding_type,
        understanding_level,
    ) in rows:
        history.append({"role": "user", "content": user_msg})
        history.append(
            {
                "role": "ai",
                "content": bot_reply,
                "learning_unit": learning_unit,
                "scaffolding_type": scaffolding_type,
                "understanding_level": understanding_level,
            }
        )

    return jsonify(history)


# 獲取學習分析報告
@app.route("/learning_analytics")
def learning_analytics():
    """提供學習分析數據"""
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 統計不同鷹架類型的使用次數
    c.execute(
        """
        SELECT scaffolding_type, COUNT(*) as count 
        FROM conversations 
        WHERE username = ? AND scaffolding_type IS NOT NULL
        GROUP BY scaffolding_type
    """,
        (username,),
    )
    scaffolding_stats = dict(c.fetchall())

    # 統計學習單元的涵蓋情況
    c.execute(
        """
        SELECT learning_unit, COUNT(*) as count 
        FROM conversations 
        WHERE username = ? AND learning_unit IS NOT NULL
        GROUP BY learning_unit
    """,
        (username,),
    )
    unit_stats = dict(c.fetchall())

    # 統計理解程度變化
    c.execute(
        """
        SELECT understanding_level, COUNT(*) as count 
        FROM conversations 
        WHERE username = ? AND understanding_level IS NOT NULL
        GROUP BY understanding_level
    """,
        (username,),
    )
    level_stats = dict(c.fetchall())

    conn.close()

    return jsonify(
        {
            "scaffolding_usage": scaffolding_stats,
            "learning_units": unit_stats,
            "understanding_levels": level_stats,
        }
    )


# 清除對話紀錄
@app.route("/chat/clear", methods=["POST"])
def clear_chat():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE username = ?", (username,))
    conn.commit()
    conn.close()

    return jsonify({"success": True})


# 建立資料庫，儲存帳號密碼、對話紀錄等
def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_reply TEXT NOT NULL,
                learning_unit TEXT,
                scaffolding_type TEXT,
                understanding_level TEXT,
                analysis_reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.commit()
        conn.close()
    else:
        # 檢查是否需要更新資料庫結構
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 檢查是否有新的欄位
        c.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in c.fetchall()]

        new_columns = [
            ("learning_unit", "TEXT"),
            ("scaffolding_type", "TEXT"),
            ("understanding_level", "TEXT"),
            ("analysis_reason", "TEXT"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in columns:
                c.execute(f"ALTER TABLE conversations ADD COLUMN {col_name} {col_type}")
                print(f"已新增欄位: {col_name}")

        conn.commit()
        conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# 登入註冊畫面
@app.route("/")
def home():
    return render_template("home.html")


# 影片區
@app.route("/video")
def video():
    if "username" not in session:
        return redirect(url_for("home"))
    return render_template("video.html", username=session["username"])


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password),
            )
            conn.commit()
            conn.close()
            flash("註冊成功，請登入！", "alert alert-success")
            return render_template("home.html")
        except sqlite3.IntegrityError:
            flash("使用者名稱已存在", "alert alert-danger")
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        )
        user = c.fetchone()
        conn.close()

        if user:
            session["username"] = username
            return redirect(url_for("video"))
        else:
            flash("帳號或密碼錯誤", "alert alert-danger")
            return redirect(url_for("home"))  # 導回首頁，再顯示錯誤訊息

    return redirect(url_for("home"))


# AI聊天
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return render_template("home.html")
    return render_template("aiChatRotbot.html", username=session["username"])


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("已登出", "alert alert-success")
    return render_template("home.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
