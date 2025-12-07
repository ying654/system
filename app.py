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
from datetime import datetime, timedelta
from collections import Counter

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# 建立一個 OpenAI 客戶端實例
client = OpenAI(api_key=api_key)
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
DB_NAME = "users.db"


# 密碼 hash
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# 資料庫初始化
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

        # 添加預設的teacher帳號
        teacher_password = hash_password("teacher")  # 密碼也是teacher
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("teacher", teacher_password),
        )

        conn.commit()
        conn.close()
        print("資料庫初始化完成，已創建teacher帳號")
    else:
        # 檢查是否需要更新資料庫結構
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 檢查teacher帳號是否存在
        c.execute("SELECT * FROM users WHERE username = 'teacher'")
        teacher_exists = c.fetchone()

        if not teacher_exists:
            teacher_password = hash_password("teacher")
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("teacher", teacher_password),
            )
            print("已添加teacher帳號")

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


###########################################################################  => home
# 登入註冊畫面
@app.route("/")
def home():
    return render_template("home.html")


# 登入API
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
            # 如果是教師帳號，導向教師分析頁面
            if username == "teacher":
                return redirect(url_for("teacher_dashboard"))
            else:
                return redirect(url_for("video"))
        else:
            flash("帳號或密碼錯誤", "alert alert-danger")
            return redirect(url_for("home"))

    return redirect(url_for("home"))


# 註冊API
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


###########################################################################


###########################################################################  => video
# 影片區
@app.route("/video")
def video():
    if "username" not in session:
        return redirect(url_for("home"))
    return render_template("video.html", username=session["username"])


# 登出按鈕
@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("已登出", "alert alert-success")
    return render_template("home.html")


# 鷹架理論
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


# 儲存聊天資料 - 加入鷹架理論分析API
@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    user_message = request.json.get("message")

    try:
        learning_unit = identify_learning_unit(user_message)
        user_history = get_user_learning_history(username)

        scaffolding_type, understanding_level, analysis_reason = (
            analyze_scaffolding_need(
                user_message, learning_unit, user_history, username
            )
        )

        # 再次確保正確格式
        scaffolding_type = normalize_scaffolding_type(scaffolding_type)

        reply = generate_scaffolded_response(
            user_message, learning_unit, scaffolding_type, understanding_level
        )

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


# 給出對應的鷹架回應
def _postprocess_complete_sentences(text):
    """確保回覆不以半句收尾：截到最後完整句，若沒有則補上句號。"""
    if not text:
        return text
    text = text.replace("[[END]]", "").strip()
    if re.search(r"[。\.!?！\?]$", text):
        return text
    m = re.search(r"(.+[。\.!?！\?])", text)
    if m:
        return m.group(1).strip()
    return text + "。"


def format_code_blocks(text):
    # 將 ```python ... ``` 轉成 <pre><code class="language-python">...</code></pre>
    return re.sub(
        r"```python(.*?)```",
        r'<pre><code class="language-python">\1</code></pre>',
        text,
        flags=re.DOTALL,
    )


def generate_scaffolded_response(
    user_message, learning_unit, scaffolding_type, understanding_level
):
    """根據鷹架類型產生聚焦且可包含程式範例的回覆"""

    # 確保鷹架類型正確
    scaffolding_type = normalize_scaffolding_type(scaffolding_type)

    level_hint = {
        "初學者": "請使用淺顯語言與生活化比喻。",
        "進階學習者": "可使用部分專業詞彙與簡短程式範例。",
        "熟練者": "請提供技術細節、效率比較或延伸應用。",
    }.get(understanding_level, "")

    code_hint = "如果學生的問題涉及實作或語法，請附上一段簡短的 Python 程式碼區塊，程式碼長度不超過15行。"

    scaffolding_prompts = {
        "差異鷹架": f"""
你是一位機器學習導師，正在使用「差異鷹架」策略，
目的是根據學生的理解程度與學習風格給予適性化引導。

教學原則：
- 從基礎概念開始，說明簡單清楚
- 使用生活化比喻幫助學生連結經驗
- 若學生提到程式相關問題，可提供範例程式碼
- 結尾鼓勵學生反思或再提問

請用 3–4 句自然語氣回答，每句不超過 25 字。
{level_hint}
{code_hint}
主題：{learning_unit}
學生提問：{user_message}
回答結束時輸出 [[END]]
""",
        "重複鷹架": f"""
你是一位機器學習導師，正在使用「重複鷹架」策略，
幫助學生透過多種說明方式鞏固同一概念。

教學原則：
- 用不同例子與語境重述核心概念
- 可提供對照式程式碼範例
- 鼓勵學生自己試著寫出類似程式
- 結尾附上「練習方向」

請用 3–4 句回答，每句不超過 25 字。
{level_hint}
{code_hint}
主題：{learning_unit}
學生提問：{user_message}
回答結束時輸出 [[END]]
""",
        "協同鷹架": f"""
你是一位機器學習專家，正在使用「協同鷹架」策略，
協助學生整合跨領域知識並進行高層次思考。

教學原則：
- 先點出核心邏輯或理論關聯
- 再提出延伸應用或挑戰問題
- 若相關，可附上示範程式片段
- 結尾以「你覺得呢？」、「是否能延伸到…？」收尾

請用 3–5 句回答，每句不超過 30 字。
{level_hint}
{code_hint}
主題：{learning_unit}
學生提問：{user_message}
回答結束時輸出 [[END]]
""",
    }

    system_prompt = scaffolding_prompts.get(
        scaffolding_type, scaffolding_prompts["差異鷹架"]
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=300,
            temperature=0.35,
            stop=["[[END]]"],
        )

        raw = response.choices[0].message.content
        processed = _postprocess_complete_sentences(raw)
        return format_code_blocks(processed)

    except Exception as e:
        print(f"回應生成錯誤: {e}")
        return "抱歉，我遇到了一些技術問題。能請你再說一次你的問題嗎？"


# 推薦書籍 爬蟲
# 關鍵字提取
def extract_keywords_from_message(user_message):
    """使用OpenAI提取用戶訊息中的關鍵詞"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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


# 書籍爬蟲
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


# 抓取書籍的API
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


###########################################################################


###########################################################################  => teacher_analytics
# 教師儀表板頁面 避免透過更改網址進入教師帳號
@app.route("/teacher")
def teacher_dashboard():
    if "username" not in session or session["username"] != "teacher":
        flash("無權限訪問", "alert alert-danger")
        return redirect(url_for("home"))
    return render_template("teacher_analytics.html", username=session["username"])


# 教師分析API
@app.route("/teacher_analytics")
def teacher_analytics():
    if "username" not in session or session["username"] != "teacher":
        return jsonify({"error": "無權限"}), 403

    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 活躍學生數、平均理解、熱門單元、對話次數
        stats = get_basic_stats(c)

        # 鷹架類型統計
        scaffolding_stats = get_scaffolding_stats(c)

        # 學習單元統計
        unit_stats = get_unit_stats(c)

        # 理解程度統計
        level_stats = get_level_stats(c)

        # 每日活動統計
        daily_activity = get_daily_activity(c)

        # 每個學生的 總對話次數、鷹架、理解程度、最常討論單元、上次登入時間
        students = get_student_details(c)

        conn.close()

        return jsonify(
            {
                "stats": stats,
                "scaffolding_stats": scaffolding_stats,
                "unit_stats": unit_stats,
                "level_stats": level_stats,
                "daily_activity": daily_activity,
                "students": students,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 獲取學生相關資料
def get_basic_stats(cursor):
    """獲取基本統計數據"""
    # 活躍學生數（過去7天）
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        SELECT COUNT(DISTINCT username) 
        FROM conversations 
        WHERE username != 'teacher' AND timestamp > ?
    """,
        (week_ago,),
    )
    # 過去7天的學生人數
    active_students = cursor.fetchone()[0]

    # 總對話次數
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE username != 'teacher'")
    total_conversations = cursor.fetchone()[0]

    # 最熱門的學習單元 挑出數量最多的學習單元
    cursor.execute(
        """
        SELECT learning_unit, COUNT(*) as count 
        FROM conversations 
        WHERE username != 'teacher' AND learning_unit IS NOT NULL 
        GROUP BY learning_unit 
        ORDER BY count DESC 
        LIMIT 1
    """
    )
    popular_result = cursor.fetchone()
    popular_unit = popular_result[0] if popular_result else "無"

    # 平均理解程度
    level_mapping = {"初學者": 1, "進階學習者": 2, "熟練者": 3}
    cursor.execute(
        """
        SELECT understanding_level 
        FROM conversations 
        WHERE username != 'teacher' AND understanding_level IS NOT NULL
    """
    )
    levels = [level_mapping.get(row[0], 0) for row in cursor.fetchall()]
    avg_level = round(sum(levels) / len(levels), 1) if levels else 0

    return {
        "activeStudents": active_students,
        "totalConversations": total_conversations,
        "popularUnit": popular_unit,
        "avgLevel": avg_level,
    }


def get_scaffolding_stats(cursor):
    """獲取鷹架類型統計"""
    cursor.execute(
        """
        SELECT scaffolding_type, COUNT(*) as count 
        FROM conversations 
        WHERE username != 'teacher' AND scaffolding_type IS NOT NULL 
        GROUP BY scaffolding_type
    """
    )
    return dict(cursor.fetchall())


def get_unit_stats(cursor):
    """獲取學習單元統計"""
    cursor.execute(
        """
        SELECT learning_unit, COUNT(*) as count 
        FROM conversations 
        WHERE username != 'teacher' AND learning_unit IS NOT NULL 
        GROUP BY learning_unit 
        ORDER BY count DESC
    """
    )
    return dict(cursor.fetchall())


def get_level_stats(cursor):
    """獲取理解程度統計"""
    cursor.execute(
        """
        SELECT understanding_level, COUNT(*) as count 
        FROM conversations 
        WHERE username != 'teacher' AND understanding_level IS NOT NULL 
        GROUP BY understanding_level
    """
    )
    return dict(cursor.fetchall())


def get_daily_activity(cursor):
    """獲取每日活動統計（過去7天）"""
    daily_stats = {}
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")

        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM conversations 
            WHERE username != 'teacher' 
            AND DATE(timestamp) = ?
        """,
            (date_str,),
        )

        count = cursor.fetchone()[0]
        daily_stats[date.strftime("%m/%d")] = (
            count  # daily_stats[9/15] = 4 => 9/15 有 4個人
        )

    # 反轉順序，讓最舊的日期在前面
    return dict(reversed(list(daily_stats.items())))


def get_student_details(cursor):
    """獲取學生詳細資料"""
    cursor.execute(
        "SELECT DISTINCT username FROM conversations WHERE username != 'teacher'"
    )
    usernames = [row[0] for row in cursor.fetchall()]

    students = []

    # 把每個學生抓出來，看他的資訊
    for username in usernames:
        # 總對話次數
        cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE username = ?", (username,)
        )
        total_conversations = cursor.fetchone()[0]

        # 主要鷹架類型
        cursor.execute(
            """
            SELECT scaffolding_type, COUNT(*) as count 
            FROM conversations 
            WHERE username = ? AND scaffolding_type IS NOT NULL 
            GROUP BY scaffolding_type 
            ORDER BY count DESC 
            LIMIT 1
        """,
            (username,),
        )
        main_scaffolding_result = cursor.fetchone()
        main_scaffolding = (
            main_scaffolding_result[0] if main_scaffolding_result else "未知"
        )

        # 當前理解程度（最新的）
        cursor.execute(
            """
            SELECT understanding_level 
            FROM conversations 
            WHERE username = ? AND understanding_level IS NOT NULL 
            ORDER BY timestamp DESC 
            LIMIT 1
        """,
            (username,),
        )
        current_level_result = cursor.fetchone()
        current_level = current_level_result[0] if current_level_result else "未知"

        # 最常討論的單元
        cursor.execute(
            """
            SELECT learning_unit, COUNT(*) as count 
            FROM conversations 
            WHERE username = ? AND learning_unit IS NOT NULL 
            GROUP BY learning_unit 
            ORDER BY count DESC 
            LIMIT 1
        """,
            (username,),
        )
        favorite_unit_result = cursor.fetchone()
        favorite_unit = favorite_unit_result[0] if favorite_unit_result else "無"

        # 最後活動時間
        cursor.execute(
            """
            SELECT MAX(timestamp) 
            FROM conversations 
            WHERE username = ?
        """,
            (username,),
        )
        last_activity = cursor.fetchone()[0]

        students.append(
            {
                "username": username,
                "total_conversations": total_conversations,
                "main_scaffolding": main_scaffolding,
                "current_level": current_level,
                "favorite_unit": favorite_unit,
                "last_activity": last_activity,
            }
        )

    # 按總對話次數排序
    students.sort(key=lambda x: x["total_conversations"], reverse=True)
    return students


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


import json
import re
from openai import OpenAI

client = OpenAI()


def normalize_scaffolding_type(scaffolding_type):
    """統一鷹架類型名稱，移除所有「性」字"""
    if not scaffolding_type:
        return "差異鷹架"

    mapping = {
        "差異性鷹架": "差異鷹架",
        "重複性鷹架": "重複鷹架",
        "協同性鷹架": "協同鷹架",
        "差異鷹架": "差異鷹架",
        "重複鷹架": "重複鷹架",
        "協同鷹架": "協同鷹架",
    }

    return mapping.get(scaffolding_type, "差異鷹架")


# 修改 analyze_scaffolding_need 函數
def analyze_scaffolding_need(user_message, learning_unit, user_history, username):
    """
    改良版：以量化平均方式判斷理解層級，GPT 主導鷹架判斷。
    """

    # === Step 1: 根據歷史紀錄量化理解層級 ===
    level_score_map = {"初學者": 1, "進階學習者": 2, "熟練者": 3}

    valid_scores = [
        level_score_map[h[3]] for h in user_history if h[3] in level_score_map
    ]

    if valid_scores:
        avg_score = sum(valid_scores) / len(valid_scores)
    else:
        avg_score = 1

    if avg_score < 1.5:
        understanding_level = "初學者"
    elif avg_score < 2.5:
        understanding_level = "進階學習者"
    else:
        understanding_level = "熟練者"

    # === Step 2: 讓 GPT 主導判斷鷹架類型 ===
    refinement_prompt = f"""
你是一位機器學習教育專家。
根據鷹架理論，請判斷此學生目前最需要的鷹架類型。

鷹架理論定義如下：
- 差異鷹架：當學生對相同主題理解程度不一，或學習風格不同時，提供不同角度、難度與範例引導。
- 重複鷹架：當學生針對特定主題需要鞏固理解，提供多元說明方式或多種做法，協助反覆練習。
- 協同鷹架：當學生處理需要整合多項知識與技能的高層次任務，協助整合概念與策略。

學生目前理解層級：{understanding_level}
學習單元：{learning_unit}
學生提問：{user_message}

歷史紀錄摘要：
{[f"問題：{h[0]}，單元：{h[1]}，理解：{h[3]}" for h in user_history[-5:]]}

**重要：scaffolding_type 必須只能是以下三個值之一（不可加「性」字）：**
- 差異鷹架
- 重複鷹架
- 協同鷹架

回傳 JSON 格式（不要任何 markdown 語法）：
{{
    "scaffolding_type": "差異鷹架",
    "understanding_level": "初學者",
    "reason": "簡短說明"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是教育心理學助理。回覆必須是純 JSON，不要使用 markdown。鷹架類型只能是：差異鷹架、重複鷹架、協同鷹架（不可加性字）。",
                },
                {"role": "user", "content": refinement_prompt},
            ],
            max_tokens=250,
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()
        # 移除可能的 markdown 標記
        text = text.replace("```json", "").replace("```", "").strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            scaffolding_type = normalize_scaffolding_type(
                data.get("scaffolding_type", "差異鷹架")
            )
            understanding_level = data.get("understanding_level", understanding_level)
            reason = data.get("reason", "標準鷹架分析")

            return scaffolding_type, understanding_level, reason
        else:
            print(f"無法解析 GPT 回 覆: {text}")
            return "差異鷹架", understanding_level, "無法解析 GPT 回覆，使用預設結果。"

    except Exception as e:
        print(f"鷹架分析錯誤: {e}")
        return "差異鷹架", understanding_level, "分析時發生錯誤。"


def analyze_scaffolding_need(user_message, learning_unit, user_history, username):
    """
    改良版：以量化平均方式判斷理解層級，GPT 主導鷹架判斷。
    """

    # === Step 1: 根據歷史紀錄量化理解層級 ===
    level_score_map = {"初學者": 1, "進階學習者": 2, "熟練者": 3}

    # 過濾掉未知紀錄，換算成分數
    valid_scores = [
        level_score_map[h[3]] for h in user_history if h[3] in level_score_map
    ]

    if valid_scores:
        avg_score = sum(valid_scores) / len(valid_scores)
    else:
        avg_score = 1  # 若沒有紀錄，預設初學者

    # 根據平均分數決定目前理解層級
    if avg_score < 1.5:
        understanding_level = "初學者"
    elif avg_score < 2.5:
        understanding_level = "進階學習者"
    else:
        understanding_level = "熟練者"

    # === Step 2: 讓 GPT 主導判斷鷹架類型 ===
    refinement_prompt = f"""
    你是一位機器學習教育專家。
    根據鷹架理論，請判斷此學生目前最需要的鷹架類型。

    鷹架理論定義如下：
    - 差異鷹架：當學生對相同主題理解程度不一，或學習風格不同時，ChatGPT 應提供不同角度、難度與範例引導。
    - 重複鷹架：當學生針對特定主題需要鞏固理解，ChatGPT 應提供多元說明方式或多種做法，協助反覆練習。
    - 協同鷹架：當學生處理需要整合多項知識與技能的高層次任務，ChatGPT 應協助整合概念與策略，促進整體思考與應用。

    學生目前理解層級：{understanding_level}
    學習單元：{learning_unit}
    學生提問：{user_message}

    歷史紀錄摘要：
    {[f"問題：{h[0]}，單元：{h[1]}，理解：{h[3]}" for h in user_history[-5:]]}

    請依據以上內容判斷：
    1. 學生最適合的鷹架類型（必須是以下三種之一：差異鷹架、重複鷹架、協同鷹架）
    2. 理由（簡短說明學生為何需要這類鷹架）
    3. 若有需要，可根據問題語意調整理解層級。

    重要：scaffolding_type 必須完全符合以下格式（不可有任何變化）：
    - "差異鷹架"
    - "重複鷹架"
    - "協同鷹架"

    回傳 JSON 格式：
    {{
        "scaffolding_type": "差異鷹架",
        "understanding_level": "初學者",
        "reason": "簡短中文說明"
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "你是一位教育心理學助理。請嚴格遵守鷹架類型的命名規範。",
                },
                {"role": "user", "content": refinement_prompt},
            ],
            max_tokens=250,
            temperature=0.3,
        )

        text = response.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            scaffolding_type = data["scaffolding_type"]

            # 🔥 修正：統一鷹架類型名稱，移除「性」字
            scaffolding_mapping = {
                "差異性鷹架": "差異鷹架",
                "重複性鷹架": "重複鷹架",
                "協同性鷹架": "協同鷹架",
                "差異鷹架": "差異鷹架",
                "重複鷹架": "重複鷹架",
                "協同鷹架": "協同鷹架",
            }

            # 如果 GPT 返回了帶「性」的版本，自動修正
            scaffolding_type = scaffolding_mapping.get(scaffolding_type, "差異鷹架")

            return scaffolding_type, data["understanding_level"], data["reason"]
        else:
            return (
                "差異鷹架",
                understanding_level,
                "無法解析 GPT 回覆，使用預設結果。",
            )

    except Exception as e:
        print(f"鷹架分析錯誤: {e}")
        return "差異鷹架", understanding_level, "分析時發生錯誤。"


###########################################################################


###########################################################################  => aiChatRobot
# AI聊天
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return render_template("home.html")
    return render_template("aiChatRobot.html", username=session["username"])


###########################################################################


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


# 個人學習分析頁面
@app.route("/my_learning")
def my_learning():
    if "username" not in session:
        return redirect(url_for("home"))
    return render_template("my_learning.html", username=session["username"])


# 個人學習分析 API
@app.route("/my_learning_analytics")
def my_learning_analytics():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]

    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 獲取使用者所有對話記錄
        c.execute(
            """
            SELECT learning_unit, understanding_level, user_message, scaffolding_type, timestamp
            FROM conversations 
            WHERE username = ? 
            ORDER BY timestamp DESC
        """,
            (username,),
        )
        conversations = c.fetchall()
        conn.close()

        if not conversations:
            return jsonify(
                {
                    "unit_progress": {},
                    "weakness_analysis": {},
                    "overall_stats": {
                        "total_conversations": 0,
                        "units_studied": 0,
                        "avg_level": "初學者",
                        "most_discussed_unit": "無",
                    },
                    "scaffolding_stats": {},  # 新增鷹架統計
                    "timeline": [],
                }
            )

        # 分析各單元的理解程度
        unit_progress = analyze_unit_progress(conversations)

        # 分析各單元的弱點
        weakness_analysis = analyze_unit_weakness(conversations, username)

        # 整體統計
        overall_stats = calculate_overall_stats(conversations)

        # 鷹架類型統計 (新增)
        scaffolding_stats = calculate_scaffolding_stats(conversations)

        # 學習時間軸
        timeline = generate_learning_timeline(conversations)

        return jsonify(
            {
                "unit_progress": unit_progress,
                "weakness_analysis": weakness_analysis,
                "overall_stats": overall_stats,
                "scaffolding_stats": scaffolding_stats,  # 新增
                "timeline": timeline,
            }
        )

    except Exception as e:
        print(f"個人分析錯誤: {e}")
        return jsonify({"error": str(e)}), 500


def calculate_scaffolding_stats(conversations):
    """計算使用者的鷹架類型統計"""
    scaffolding_counter = Counter()

    for unit, level, message, scaffolding, timestamp in conversations:
        if scaffolding:
            # 確保統一格式
            scaffolding = normalize_scaffolding_type(scaffolding)
            scaffolding_counter[scaffolding] += 1

    # 計算百分比
    total = sum(scaffolding_counter.values())
    scaffolding_stats = {}

    if total > 0:
        for scaffolding_type, count in scaffolding_counter.items():
            scaffolding_stats[scaffolding_type] = {
                "count": count,
                "percentage": round((count / total) * 100, 1),
            }

    return scaffolding_stats


def calculate_overall_stats(conversations):
    """計算整體學習統計"""
    level_scores = {"初學者": 1, "進階學習者": 2, "熟練者": 3}

    units = set([c[0] for c in conversations if c[0] and c[0] != "通用概念"])
    levels = [level_scores.get(c[1], 0) for c in conversations if c[1]]

    avg_level_score = sum(levels) / len(levels) if levels else 0
    avg_level_name = get_level_name(round(avg_level_score))

    # 最常討論的單元
    unit_counter = Counter([c[0] for c in conversations if c[0] and c[0] != "通用概念"])
    most_discussed = unit_counter.most_common(1)[0][0] if unit_counter else "無"

    # 主要鷹架類型 (新增)
    scaffolding_counter = Counter(
        [normalize_scaffolding_type(c[3]) for c in conversations if c[3]]
    )
    main_scaffolding = (
        scaffolding_counter.most_common(1)[0][0] if scaffolding_counter else "無"
    )

    return {
        "total_conversations": len(conversations),
        "units_studied": len(units),
        "avg_level": avg_level_name,
        "most_discussed_unit": most_discussed,
        "main_scaffolding": main_scaffolding,  # 新增
    }


def analyze_unit_progress(conversations):
    """分析各學習單元的理解程度進展"""
    unit_data = {}
    level_scores = {"初學者": 1, "進階學習者": 2, "熟練者": 3, "未知": 0}

    for unit, level, _, scaffolding, timestamp in conversations:
        if not unit or unit == "通用概念":
            continue

        if unit not in unit_data:
            unit_data[unit] = {
                "conversations": 0,
                "levels": [],
                "scaffolding_types": [],
                "first_seen": timestamp,
                "last_seen": timestamp,
            }

        unit_data[unit]["conversations"] += 1
        unit_data[unit]["levels"].append(level_scores.get(level, 0))
        unit_data[unit]["scaffolding_types"].append(scaffolding)
        unit_data[unit]["last_seen"] = timestamp

    # 計算各單元的平均理解程度和進步趨勢
    result = {}
    for unit, data in unit_data.items():
        avg_level = sum(data["levels"]) / len(data["levels"]) if data["levels"] else 0

        # 計算進步趨勢（最近3次 vs 最早3次）
        recent_levels = data["levels"][: min(3, len(data["levels"]))]
        early_levels = data["levels"][-min(3, len(data["levels"])) :]

        trend = "持平"
        if len(data["levels"]) >= 3:
            recent_avg = sum(recent_levels) / len(recent_levels)
            early_avg = sum(early_levels) / len(early_levels)

            if recent_avg > early_avg + 0.3:
                trend = "進步中"
            elif recent_avg < early_avg - 0.3:
                trend = "需加強"

        # 最常使用的鷹架類型
        scaffolding_counter = Counter([s for s in data["scaffolding_types"] if s])
        most_common_scaffolding = (
            scaffolding_counter.most_common(1)[0][0] if scaffolding_counter else "未知"
        )

        result[unit] = {
            "conversations": data["conversations"],
            "avg_level": round(avg_level, 2),
            "current_level": (
                get_level_name(data["levels"][0]) if data["levels"] else "未知"
            ),
            "trend": trend,
            "most_scaffolding": most_common_scaffolding,
            "last_studied": data["last_seen"],
        }

    return result


def analyze_unit_weakness(conversations, username):
    """使用 GPT 分析各單元的弱點"""
    unit_conversations = {}

    # 按單元分組對話
    for unit, level, message, scaffolding, timestamp in conversations:
        if not unit or unit == "通用概念":
            continue

        if unit not in unit_conversations:
            unit_conversations[unit] = []

        unit_conversations[unit].append(
            {"message": message, "level": level, "scaffolding": scaffolding}
        )

    weakness_result = {}

    for unit, convs in unit_conversations.items():
        # 只分析有足夠對話記錄的單元（至少3次對話）
        if len(convs) < 3:
            weakness_result[unit] = {
                "weakness": "對話次數不足，尚無法分析弱點",
                "suggestions": ["建議多與 AI 討論此單元的內容"],
                "confidence": "低",
            }
            continue

        # 取最近5次對話進行分析
        recent_convs = convs[:5]

        # 構建 GPT 分析提示
        analysis_prompt = f"""
你是一位機器學習教育專家。請根據學生在「{unit}」單元的學習記錄，分析其可能的弱點。

學習記錄：
{chr(10).join([f"- 問題：{c['message']} (理解程度：{c['level']}，鷹架：{c['scaffolding']})" for c in recent_convs])}

請分析：
1. 學生在此單元最主要的弱點或困難（1-2句話）
2. 3個具體的改善建議
3. 弱點分析的信心程度（高/中/低）

回傳 JSON 格式：
{{
    "weakness": "主要弱點描述",
    "suggestions": ["建議1", "建議2", "建議3"],
    "confidence": "高/中/低"
}}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是教育分析專家，專門分析學生的學習弱點。",
                    },
                    {"role": "user", "content": analysis_prompt},
                ],
                max_tokens=300,
                temperature=0.3,
            )

            result_text = response.choices[0].message.content.strip()

            # 解析 JSON
            import re

            match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if match:
                analysis = json.loads(match.group(0))
                weakness_result[unit] = analysis
            else:
                weakness_result[unit] = {
                    "weakness": "分析失敗",
                    "suggestions": ["請繼續學習"],
                    "confidence": "低",
                }

        except Exception as e:
            print(f"單元 {unit} 弱點分析錯誤: {e}")
            weakness_result[unit] = {
                "weakness": "系統分析時發生錯誤",
                "suggestions": ["請稍後再試"],
                "confidence": "低",
            }

    return weakness_result


def calculate_overall_stats(conversations):
    """計算整體學習統計"""
    level_scores = {"初學者": 1, "進階學習者": 2, "熟練者": 3}

    units = set([c[0] for c in conversations if c[0] and c[0] != "通用概念"])
    levels = [level_scores.get(c[1], 0) for c in conversations if c[1]]

    avg_level_score = sum(levels) / len(levels) if levels else 0
    avg_level_name = get_level_name(round(avg_level_score))

    # 最常討論的單元
    unit_counter = Counter([c[0] for c in conversations if c[0] and c[0] != "通用概念"])
    most_discussed = unit_counter.most_common(1)[0][0] if unit_counter else "無"

    return {
        "total_conversations": len(conversations),
        "units_studied": len(units),
        "avg_level": avg_level_name,
        "most_discussed_unit": most_discussed,
    }


def generate_learning_timeline(conversations):
    """生成學習時間軸（最近10次重要學習事件）"""
    timeline = []

    # 篩選出有明確學習單元的對話
    filtered = [
        (c[0], c[1], c[4]) for c in conversations if c[0] and c[0] != "通用概念"
    ]

    # 取最近10次
    for unit, level, timestamp in filtered[:10]:
        timeline.append({"unit": unit, "level": level, "timestamp": timestamp})

    return timeline


def get_level_name(score):
    """根據分數返回理解程度名稱"""
    if score >= 2.5:
        return "熟練者"
    elif score >= 1.5:
        return "進階學習者"
    else:
        return "初學者"


# 清除對話紀錄
@app.route("/chat/clear", methods=["POST"])
def clear_chat():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        """UPDATE conversations 
           SET user_message = '[已清除]', bot_reply = '[已清除]' 
           WHERE username = ?""",
        (username,),
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
