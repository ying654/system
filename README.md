在終端機 輸入 python app.py 執行

app.py 是 主要程式。

home.jpg , homeStyle.css , home.html 是 登入註冊系統

aiChat.js , aiStyle.css , aiChatRotbot 是 ChatGpt聊天頁面

video.html 是 暫時頁面 之後會更改成影片區 //已新增

users.db 存放 使用者帳號密碼 ， 對話紀錄 等等
查詢帳號 要下載 sqlite-tools-win-x64-3490200.zip ， 解壓縮後放到 C:\底下。

1  cd C:\sqlite

2  .\sqlite3.exe "users.db的路徑"

3  SELECT * FROM users; //(記得分號)
