# ptt_notifier_via_telegram

- 透過Telegram將熱門PTT文章傳給使用者
    - 根據不同版分門別類
    - 根據不同版設定閥值
    - 根據不同用戶設定不同版不同閥值

### 安裝

- 設定環境
```
pip install -r requirements.txt
```
- 設定`.env`檔案
    - 在根目錄設定檔案名為`.env`的檔案
    - 範例
    ```
    tg_token="Telegram機器人Token"
    admin_id="ADMIN的Telegram ID"
    ```


### 啟動

- `Python main.py`

### 指令介紹

- `/start` 開始使用
- `/me` 顯示你訂閱的看板
- `/add` 增加你訂閱的看板，並設定閥值
- `/delete` 刪除某個你訂閱的看板
- `/deleteMe` 刪除自己在機器人Host端的資料
- `/stop` 停止機器人 //ADMIN專用指令
- `/users` 查看目前用戶 //ADMIN專用指令

### 修改看板列表
- 在`boards.json`中可以修改看板資料，以六個為一組，此順序為`/add`指令出現的順序
```
"1": [
        "Gossiping",
        "C_Chat",
        "marvel",
        "CFantasy",
        "Lifeismoney",
        "Beauty"
    ]
```
- 看板名稱為`https://www.ptt.cc/bbs/**看板名稱**/index.html`
