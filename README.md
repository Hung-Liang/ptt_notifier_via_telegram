# ptt_notifier_via_telegram

- 透過Telegram將熱門PTT文章傳給使用者
    - 根據不同版分門別類
    - 根據不同版設定閥值
    - 根據不同用戶設定不同版不同閥值

### 安裝

- 安裝 [uv](https://docs.astral.sh/uv/) 後設定環境
```
uv sync
```
- 設定`.env`檔案
    - 在根目錄設定檔案名為`.env`的檔案
    - 範例
    ```
    telegram_token="Telegram機器人Token"
    admin_id="ADMIN的Telegram ID"
    ```


### 啟動

- `uv run main.py`

### 使用 Docker 啟動

- 先依上方說明設定`.env`
- `docker compose up -d --build`
- 查看日誌：`docker compose logs -f`
- `assets/`與`logs/`會掛載到容器中，使用者資料與日誌保留在主機上

### 指令介紹

- `/start` 開始使用
- `/me` 顯示你訂閱的看板
- `/add` 增加你訂閱的看板，並設定閥值
- `/delete` 刪除某個你訂閱的看板
- `/delete_me` 刪除自己在機器人Host端的資料
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
