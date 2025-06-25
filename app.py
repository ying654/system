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
import sqlite3, os, hashlib

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
# 建立一個 OpenAI 客戶端實例
client = OpenAI(api_key=api_key)
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

DB_NAME = "users.db"


# 儲存聊天資料
@app.route("/chat", methods=["POST"])
def chat():
    if "username" not in session:
        return jsonify({"error": "未登入"}), 401

    username = session["username"]
    user_message = request.json.get("message")

    try:
        msgs = [
            {
                "role": "system",
                "content": (
                    "你是一位有耐心、善於引導的中文老師。"
                    "當學生提出問題時，你要用繁體中文回答，"
                    "語氣像在課堂上啟發學生思考，"
                    "並幫助他們一步步理解概念，不能直接告訴學生答案。"
                ),
            },
            {"role": "user", "content": user_message},
        ]
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=msgs,
        )
        reply = resp.choices[0].message.content

        # 儲存到資料庫
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO conversations (username, user_message, bot_reply) VALUES (?, ?, ?)",
            (username, user_message, reply),
        )
        conn.commit()
        conn.close()

        return jsonify({"reply": reply})

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
        "SELECT user_message, bot_reply FROM conversations WHERE username = ? ORDER BY timestamp ASC",
        (username,),
    )
    rows = c.fetchall()
    conn.close()

    history = []
    for user_msg, bot_reply in rows:
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "ai", "content": bot_reply})

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
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
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
