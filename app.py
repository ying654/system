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



# 根據學生理解程度給出簡短提示片段（會附加到 system prompt）
DIFFICULTY_HINT = {
    "初學者": "請用淺顯易懂的語句、生活化比喻與簡短範例說明。",
    "中階者": "可以使用術語並提供一個實務上的簡短例子。",
    "進階者": "使用專業術語並引導學生做延伸思考或探討限制條件。",
}

# header 標籤對應各鷹架（避免每次都用「重點」）
HEADER_LABEL = {
    "差異鷹架": "重點",
    "重複鷹架": "重申",
    "協同鷹架": "思考",
}

def format_concise_reply(raw_text, scaffolding_type, max_points=3):
    """
    改良版：
    - 避免重複【重點】【重申】【思考】
    - 移除 GPT 原輸出中的多餘符號 (-、•、*)
    - 保留原有短條列與下一步提示
    """
    if not raw_text:
        return f"【{HEADER_LABEL.get(scaffolding_type, '重點')}】暫無內容。"

    # 移除多餘空白與符號
    cleaned = re.sub(r'^[\s\-•*]+', '', raw_text.strip())

    # 切句
    pieces = [p.strip() for p in re.split(r'[\n。；]+', cleaned) if p.strip()]
    header = HEADER_LABEL.get(scaffolding_type, "重點")

    # 決定 title
    raw_title = pieces[0] if pieces else ""
    # 若 GPT 已含有【重點】等標籤，移除重複
    raw_title = re.sub(r'^【?(重點|重申|思考)】?', '', raw_title).strip()
    title = raw_title if len(raw_title) <= 60 else raw_title[:60] + "…"

    # 擷取要點
    points = []
    for p in pieces[1:]:
        subs = re.split(r'[，,；;：:]\s*', p)
        for s in subs:
            s = re.sub(r'^[\-\*•\d\.]+\s*', '', s.strip())  # 清除開頭的符號或編號
            if s:
                s_clean = s if len(s) <= 60 else s[:60] + "…"
                points.append(s_clean)
        if len(points) >= max_points:
            break

    if not points:
        candidates = [c.strip() for c in re.split(r'[，,；;。\n]+', cleaned) if c.strip()]
        points = candidates[1:1 + max_points] if len(candidates) > 1 else candidates[:max_points]
    points = points[:max_points]

    # 下一步依鷹架類型不同
    if scaffolding_type == "差異鷹架":
        next_hint = "→ 下一步：試用不同角度重新描述此概念。"
    elif scaffolding_type == "重複鷹架":
        next_hint = "→ 練習：做 1 題類似練習並比對答案。"
    else:
        next_hint = "→ 延伸：試著將此概念應用到實際情境。"

    # 組合輸出
    lines = [f"【{header}】{title}"]
    for i, pt in enumerate(points, start=1):
        lines.append(f"{i}. {pt}")
    lines.append(next_hint)

    reply = "\n".join(lines)
    if len(reply) > 800:
        reply = reply[:790] + "…"
    return reply



def generate_scaffolded_response(
    user_message, learning_unit, scaffolding_type, understanding_level
):
    """根據鷹架類型生成適當且簡潔的回應（改良版）"""

    # 把理解層級的提示接到 system prompt（如果有就加上）
    difficulty_append = DIFFICULTY_HINT.get(understanding_level, "")

    scaffolding_prompts = {
        "差異鷹架": f"""
你是一位親切的機器學習導師，正在使用「差異鷹架」幫助初學者。

請用簡短條列格式回答：
- 第一行為標籤與一句話標題（如：【重點】一句話）
- 接著列出 1–3 個要點（每點不超過 25–60 字）
- 最後以「→ 下一步：」給 1 行具體建議
- 語氣：溫和、引導式，盡量使用生活化比喻

{difficulty_append}

主題：{learning_unit}
學生提問：{user_message}
""",

        "重複鷹架": f"""
你是一位耐心的導師，使用「重複鷹架」協助學生鞏固概念。

請用簡短條列格式回答：
- 第一行為標籤與一句話標題（如：【重申】一句話）
- 接著列出 1–3 個要點（可包含例子）
- 最後以「→ 練習：」提供 1 行練習建議
- 語氣：穩定、有節奏感，像複習筆記

{difficulty_append}

主題：{learning_unit}
學生提問：{user_message}
""",

        "協同鷹架": f"""
你是一位機器學習專家，使用「協同鷹架」與學生共同探討進階問題。

請用簡短條列格式回答：
- 第一行為標籤與一句話標題（如：【思考】一句話）
- 接著列出 1–3 個關鍵啟發（每點不超過 25–60 字）
- 最後以「→ 延伸：」提出 1 行思考方向
- 語氣：啟發式、對話感強，可用「你覺得…？」、「是否可能…？」

{difficulty_append}

主題：{learning_unit}
學生提問：{user_message}
"""
    }

    system_prompt = scaffolding_prompts.get(scaffolding_type, scaffolding_prompts["差異鷹架"])

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=200,     # 稍微放寬一點，讓 GPT-4o-mini 有空間輸出 4 行內容
            temperature=0.15,   # 緊湊且穩定
        )

        full_reply = response.choices[0].message.content  # 原始完整回覆（可存）
        concise = format_concise_reply(full_reply, scaffolding_type, max_points=3)

        # 如果你想同時回傳完整回覆給呼叫端：可以改成 return {"short": concise, "full": full_reply}
        # 現階段為兼容現有程式流程，我們仍回傳 concise 字串
        # 若你要儲存完整回覆，可在這裡加入 DB 儲存邏輯，例如 save_full_reply(user_id, full_reply)
        return concise

    except Exception as e:
        print(f"回應生成錯誤: {e}")
        return "抱歉，我遇到了一些技術問題。能請你再說一次你的問題嗎？"



# # 給出對應的鷹架回應
# def generate_scaffolded_response(
#     user_message, learning_unit, scaffolding_type, understanding_level
# ):
#     """根據鷹架類型生成適當的回應"""

#     # 根據不同鷹架類型設計不同的系統提示
#     scaffolding_prompts = {
#         "差異鷹架": f"""
# 你是一位耐心的機器學習導師，正在使用「差異鷹架」策略教導初學者。

# 教學重點：
# - 從最基礎的概念開始解釋
# - 使用生活化的比喻和例子
# - 將複雜概念分解成簡單步驟
# - 多問「你知道嗎？」、「想像一下...」等引導式問題
# - 確認學生理解每個步驟後才繼續

# 當前學習單元：{learning_unit}
# 單元基礎知識：{LEARNING_UNITS.get(learning_unit, {}).get('keywords', [])}
# 前置需求：{LEARNING_UNITS.get(learning_unit, {}).get('prerequisites', [])}

# 回應風格：
# - 像和朋友聊天一樣親切
# - 用「讓我們想想...」、「這就像...」開頭
# - 提供具體範例和視覺化描述
# - 鼓勵學生提問
# """,
#         "重複鷹架": f"""
# 你是一位機器學習導師，正在使用「重複鷹架」策略幫助學生鞏固理解。

# 教學重點：
# - 用不同方式重複核心概念
# - 提供多個相似但漸進的例子
# - 強調重點知識的應用情境
# - 設計練習題讓學生實作
# - 連結之前學過的概念

# 當前學習單元：{learning_unit}
# 核心概念：{LEARNING_UNITS.get(learning_unit, {}).get('keywords', [])}

# 回應風格：
# - 「讓我們再看一個例子...」
# - 「這個概念的另一種理解方式是...」
# - 「你可以這樣練習...」
# - 強化記憶的重複模式
# """,
#         "協同鷹架": f"""
# 你是一位機器學習專家，正在使用「協同鷹架」策略與有基礎的學生進行深度對話。

# 教學重點：
# - 引導學生自主思考和發現
# - 提出開放性和挑戰性問題
# - 鼓勵批判性思考
# - 連結理論與實際應用
# - 討論進階主題和最新發展

# 當前學習單元：{learning_unit}
# 進階概念：{LEARNING_UNITS.get(learning_unit, {}).get('keywords', [])}

# 回應風格：
# - 「你認為為什麼...？」
# - 「如果我們改變這個條件會怎樣？」
# - 「在實際應用中，這會遇到什麼挑戰？」
# - 促進深度思考的蘇格拉底式對話
# """,
#     }

#     system_prompt = scaffolding_prompts.get(
#         scaffolding_type, scaffolding_prompts["差異鷹架"]
#     )

#     try:
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_message},
#             ],
#             max_tokens=500,
#             temperature=0.7,
#         )

#         return response.choices[0].message.content

#     except Exception as e:
#         print(f"回應生成錯誤: {e}")
#         return "抱歉，我遇到了一些技術問題。能請你再說一次你的問題嗎？"


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
            model="gpt-4o-mini",
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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
