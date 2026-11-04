# 交接文件：Portfolio News Monitor（澳股持股組合新聞監測器）

最後更新：2026-11-03。對象：接手這個專案的下一段 Claude Code 對話。

**接手前先看**：系統性除錯全部完成，所有修正都已 push（2026-11-03，`main` 與 GitHub 同步）。Codex 兩輪檢查找到的 C1–C10、R1–R6 都已處理或列為不修；外部 PR #1（RyanT0306）已審閱並關閉：兩個後端 commit 原樣收進來（C10 的 Claude 格式錯誤重試、FinBERT 沒安裝的提示），`randomUUID` 備案與輪詢停止改寫後收進來，其餘 `main` 已有。**現在在做 UI 改版**（第 6 節「UI 改版」，使用者已核准計畫與所有決定），在 `redesign` 分支上，6 步全部做完並 commit（2026-11-04）。使用者決定全部設計完再一起除錯，所以**下一步是對整個 `redesign` 分支（`git diff main...redesign`）跑 `/pstack:blast-radius` 與 `/code-review low`**，修找到的問題，使用者在瀏覽器完整測一輪，再合併回 `main`；使用者說「push」才上傳（見第 6 節「UI 改版」的流程）。改版的第 5 步就是「上線前必做」的第一項（開發者提示）。改版做完再回到第 6 節「上線前必做」的其他項目（部署設定、速率限制、主機）。本機的 `backup-before-r1` 分支已經用不到（R1 改寫歷史的備份，push 已成功），提醒使用者可以 `git branch -D backup-before-r1`。可以用 `/verify` 自己在無頭 Chrome 操作網站（見第 7 節）。

## 1. 這是什麼、為什麼做

- 使用者輸入澳股（ASX）持股與權重，貼上一則新聞。系統判斷這則新聞對**整個持股組合**是看好、中立還是看壞，給出三類百分比與 0–100 分數，並用 Stocktwits 風格的半圓儀表盤呈現。
- 這是使用者的**作品集／學習專題**，重點是「能完整跑起來、畫面好看、評分邏輯講得清楚」。Claude 與 FinBERT 兩種引擎可以並排比較，這是展示亮點。
- 使用者用**繁體中文**溝通，網站介面是**英文**。
- 說明要白話，指令要直接給可貼上執行的完整命令。

## 2. 目前狀態（全部完成並已驗證）

| 項目 | 狀態 |
|---|---|
| 後端（FastAPI）| 完成，188 個 pytest 全部通過 |
| 前端（Vite + React + TS）| 完成，64 個 Vitest 通過，`npm run build` 成功 |
| FinBERT 模式 | 在瀏覽器實測通過 |
| Claude 模式 | 用真實 API 實測通過，每次約 10 秒 |
| 並排比較 | 在瀏覽器實測通過，切換按鈕正常 |
| 手機版、亮色／暗色模式 | 實測通過，沒有水平捲動 |
| README（含截圖）| 完成，截圖已換成改版後的畫面（2026-11-04）|
| 貼網址抓文章 | 完成。`POST /api/article`，用真實網站實測：ABC News 成功、Reuters 顯示被擋的說明、localhost 被拒 |
| GitHub | 公開 repo，MIT 授權，已檢查沒有金鑰與個人資訊 |
| 歷史紀錄 | 同一則新聞＋持股＋引擎只留最新一筆；引擎錯誤顯示「Error」（滑過看訊息），無關顯示「Unrelated」；還原後會補查公司名稱 |

實測結果（持股 BHP 40／CBA 30／CSL 30）：

| 新聞 | Claude | FinBERT |
|---|---|---|
| 鐵礦砂跌價（沒有點名公司）| 16 強烈看壞（透過鐵礦砂價格連到 BHP）| 判為無關 |
| CBA 創紀錄獲利 | 76 看好 | 96 強烈看好 |
| CSL 調降財測 | （未測）| 2 強烈看壞 |
| 澳洲央行升息、澳幣升值 | 42 中立（BHP 32、CBA 60、CSL 35）| 判為無關 |

## 3. 位置與結構

專案根目錄：這個 repo 的根目錄。它自己是一個 git repo，公開放在 GitHub：https://github.com/Trayast0229/portfolio-news-monitor （`origin`，MIT 授權）。

```
backend/
  app/models.py              Pydantic 資料結構（API 輸入輸出、引擎介面）
  app/aggregate.py           評分公式，純函式
  app/asx.py                 ASX 公司名單、搜尋、「這句話有沒有提到這家公司」的比對
  app/engines/base.py        Engine Protocol、EngineError（可直接顯示給使用者的錯誤）
  app/engines/finbert_engine.py
  app/engines/claude_engine.py
  app/article.py             貼網址抓文章：安全檢查（只抓公開位址、80/443、每次轉址都重查）、trafilatura 取出標題與內文
  app/main.py                路由 /api/health、/api/tickers、/api/article、/api/analyze
  data/asx_companies.csv     ASX 官方清單，約 2,051 家
  scripts/build_asx_list.py  從 asx.com.au 重新產生 CSV，ALIASES 字典放常見俗稱
  tests/                     test_aggregate / test_asx / test_finbert_engine / test_claude_engine / test_article / test_api
  .env                       使用者的 ANTHROPIC_API_KEY（已被 gitignore）
  .env.example
frontend/
  src/App.tsx                主畫面（3 欄 × 2 列卡片）、表單驗證、引擎狀態輪詢、歷史抽屜開關
  src/components/            SentimentGauge, ResultPanel（指標卡＋明細卡）, HoldingBreakdown, HoldingsEditor,
                             HistoryList（HistoryToggle＋抽屜）, EnginePicker（引擎＋Analyze）, Bolt（閃電圖示）
  src/lib/engines.ts(+test)  哪些引擎能用（伺服器回 unavailable 就變灰、不送出）（純函式）
  src/lib/gauge.ts(+test)    儀表盤幾何與分區
  src/lib/api.ts             型別與 fetch
  src/lib/history.ts(+test)  歷史紀錄去重、分數顯示文字、待查公司名稱（純函式）
  src/lib/holdings.ts(+test) 哪些持股列算數（有代號才算）、權重總和、送出前的持股檢查（純函式）
  src/lib/assessment.ts(+test) 「Not assessed／Not affected」標籤與「Claude skipped …」提醒文字（純函式）
  src/lib/format.ts          百分比與時間的顯示格式
  src/lib/storage.ts(+test) localStorage（持股、引擎選擇、最近 20 筆紀錄），存取都包 try/catch，讀取時檢查形狀
  src/lib/examples.ts        3 則虛構範例新聞
  src/styles.css             設計 token（黃色重點色 --accent）、亮暗主題、grid 版面（1024px 以下一欄）
docs/
  superpowers/specs/2026-10-21-portfolio-news-monitor-design.md   原始設計與計畫（已核准）
  design/layout-draft.svg    UI 改版的版面草圖（藍色標籤是說明）
  screenshot-light.jpg / screenshot-dark.jpg
  HANDOFF.md（本檔）/ HANDOFF_PROMPT.md
README.md
```

## 4. 核心邏輯（不要隨意改變語意）

1. 每個引擎對每檔持股回傳 `HoldingSentiment`：`relevant`、`assessed`（引擎有沒有回這檔，預設 true）與三類機率（總和為 1）。
2. 使用者輸入的權重總和偏離 100 超過 0.5 個百分點時，按比例縮放並回傳 `weights_adjusted=true`。
3. **無關的持股排除不算**（使用者的決定），相關持股的權重重新分配成總和 1。
4. 組合機率 = 加權平均。`score = 50 + 50 × (bull − bear)`，.5 一律進位（60.5 → 61，使用者 2026-10-24 決定）。
5. 分區：`<20` 強烈看壞、`20–39` 看壞、`40–60` 中立、`61–80` 看好、`>80` 強烈看好。前端 `gauge.ts` 的 `zoneFor()` 與後端 `label_for()` 必須一致，兩邊都有測試。
6. `exposure` = 相關持股的原始權重總和，畫面顯示為「Affects X% of your portfolio」。
7. 沒有任何相關持股時，`status="unrelated"`。單一引擎失敗會回 `status="error"` 與錯誤訊息，不影響另一個引擎。

### Claude 引擎
- 使用 `client.beta.messages.parse(output_format=ClaudeAnalysis, output_config={"effort":"low"}, betas=["server-side-fallback-2026-07-01"], fallbacks="default")`。
- 模型預設 `claude-opus-5-5`，可用 `CLAUDE_MODEL` 覆蓋。anthropic SDK 版本是 1.17.0。
- Schema 刻意不放數值上下限，改在後端 clamp 並重新正規化。不在輸入清單內的 ticker 丟掉，缺少的 ticker 標成 `assessed=false`（見下方）。
- `stop_reason == "refusal"` 會丟出 EngineError；`parsed_output` 為 None，或回答裡沒有任何一檔輸入的持股時，重試 1 次，再失敗就顯示錯誤（不會顯示成 Unrelated）。
- Claude 回傳的 ticker 會先去掉 `.AX`、`ASX:` 再比對。漏掉的持股標成 `assessed=false`，一樣不算進分數，但畫面顯示「Not assessed」並在結果上方提醒，不會說成「Not affected」。舊的歷史紀錄沒有這個欄位，前端視為 `true`。
- API 錯誤各有訊息：逾時、連線失敗、key 錯誤、限流、5xx／529（忙碌）、404（`CLAUDE_MODEL` 打錯）；其他 4xx 附上 API 自己的說明。
- System prompt 的分析紀律參考 `jordan5226/tw_stock_news_ai_monitor`：區分事實與推論、間接影響要寫出管道、不確定就判為無關、不誇大一次性消息、不給目標價。

### FinBERT 引擎
- 使用 `ProsusAI/finbert`，`transformers` pipeline 搭配 `top_k=None`。伺服器啟動時在背景執行緒預先載入（`FINBERT_PRELOAD=1`），首次會下載約 440MB。
- 先斷句，只對有提到該持股的句子做判斷，再取平均。`Ltd.`、`U.S.` 這類縮寫後面的句點不算句尾。
- 一句話提到兩家以上持股時，在 while／but／whereas／although／分號處切開，每家只用提到自己的那段。切不開時（例如「BHP rose and CBA fell」），原因後面會加一句提醒，說明這句也提到哪家持股、分數可能混在一起。不改用 LLM 切句是使用者 2026-10-24 的決定，目的是讓 FinBERT 維持免費、在本機執行。
- 超過 200 個字的段落只取第一次提到公司的前後各 100 個字，避免 FinBERT 的 512 token 上限把提及處截掉。
- 比對規則在 `asx.mentions()`（`asx.find_mention()` 另外回傳位置）：
  - ticker 必須大寫、完整單字比對。
  - **容易和一般英文單字或新聞縮寫混淆的 ticker**（`CAR`、`WOW`、`ORG`、`AFL`、`NRL`、`SPP`、`CPU` 等 69 個，見 `_AMBIGUOUS_TICKERS`）必須帶交易所標記，例如 `ASX: CAR` 或 `CAR.AX`。
  - 公司名稱與別名**區分大小寫**，另外接受全大寫的標題寫法，例如「Origin」會比對，「origin」不會。直撇號與彎撇號（`'`／`’`）都算。
  - **長得像公司名的地名與賽事**（`_LOOKALIKES`，例如 `State of Origin`、`Port Macquarie`、`Rio de Janeiro`、`Santos FC`）會先從文字中挖掉再比對，所以同一句裡真的提到公司時仍然算。這份清單只能逐條補。已知擋不到：人名（例如「Sarah Goodman」會比對到 Goodman Group）、沒寫 FC 的球隊名（「Santos beat Corinthians」）。

## 5. 環境注意事項（很重要）

- **系統 Python 是 3.15，PyTorch 不支援**。所以安裝了 `uv`（Homebrew），後端虛擬環境是 `backend/.venv`（Python 3.13）。一律用 `backend/.venv/bin/python`、`.venv/bin/pytest`、`.venv/bin/uvicorn`，不要用系統的 `python3` 跑後端。
- 安裝依賴：`cd backend && uv pip install -e ".[dev,finbert]"`。
- **VS Code**：請開 `portfolio-news-monitor` 資料夾（不是上一層資料夾）。`.vscode/settings.json` 已指定 `backend/.venv` 的 Python，並讓測試面板以 `backend/` 為工作目錄執行 pytest。
- **macOS 權限限制**：App 預覽工具（`preview_start`）無法執行桌面資料夾裡的 `.venv/bin/uvicorn`（會出現 Operation not permitted）。所以後端要用 Bash 背景執行：
  `cd backend && .venv/bin/uvicorn app.main:app --port 8000`
- 前端可以用 `preview_start` 啟動，設定名稱是 `frontend`，設定檔在專案上一層資料夾的 `.claude/launch.json`，注意不在專案資料夾裡。其中的 `backend` 設定在這台電腦上會失敗。
- 前端開發伺服器把 `/api` 代理到 `:8000`。後端沒開時，代理會回 500，前端會顯示「Make sure the backend is running on port 8000」。
- 上一段對話結束時，前後端**還在執行**（使用者可能已經關掉）。接手時先用 `lsof -ti tcp:8000` 與 `lsof -ti tcp:5173` 確認，沒有就照上面的方式啟動。使用者自己則是用 VS Code 的 **Start app** 任務啟動（見 `docs/WORKFLOW.md`）。
- **API key** 在 `backend/.env`。**絕對不要印出或複述 key 的內容**；要檢查格式時只看長度與前綴（`sk-ant-`）。
- 沒有安裝 Docker，所以原計畫中的 docker-compose 刻意沒做（不附沒驗證過的設定）。
- 已用 Homebrew 安裝 `gh` 並登入 Trayast0229，git 透過它以 https 推送。這個 repo 的 `user.email` 設為 GitHub 隱私信箱 `344183369+Trayast0229@users.noreply.github.com`，不要改回個人信箱。commit 後用 `git push` 上傳。

## 6. 系統性除錯進度與下一步

每個 bug 先重現、寫出會失敗的測試，再修，每個單獨 commit。進度如下（2026-11-03）：

**待瀏覽器確認**（以下只用測試與 build 驗證過；現在可以用 `/verify` 自己操作瀏覽器確認，見第 7 節。持股編輯器清空代號時 Total 變少、權重 150 的錯誤訊息，已於 2026-11-03 用 `/verify` 確認）
- 只勾 FinBERT，貼「BHP shares surged to a record and CBA shares plunged after a profit warning.」（前面補一句湊滿 50 字），兩檔的原因後面都應出現「A sentence used here also names …」提醒。
- 「Not assessed」狀態與「Claude skipped …」提醒：真實 Claude 很少漏回持股，不容易在瀏覽器重現；後端已用模擬回答驗證 API 回傳正確。

**已完成**（細節見 `git log`，規則已寫進第 4 節）
- **評分邊界**：前後端分區一致；權重總和 99.5／100.5 視為 100；30 檔上限正常。修正：編輯器總和不算沒填代號的列、前端擋下權重 >100、.5 一律進位。總和剛好 99.5／100.5 時的浮點誤差（Codex C6，2026-11-03）：Python 的 `sum()` 有誤差補償、JavaScript 逐一相加，兩邊錯在不同組合（`0.35, 19.58, 79.57` 後端算成 99.4999…、`30.6, 34.45, 34.45` 前端算成 99.5000…1），編輯器和結果的縮放提示會互相矛盾。後端 `normalize_weights()` 與前端 `weightTotal()` 都先取到小數 9 位再比較；已用 55,140 組隨機權重確認前後端答案全部一致、權重本身不變。
- **FinBERT 比對**：修正：直撇號與彎撇號、新聞縮寫 ticker（AFL、NRL、SPP 等 20 個）、James Hardie 與 a2 Milk 別名、地名與賽事排除、`Ltd.`／`U.S.` 不斷句、同一句多家公司按轉折詞切開、長句只取提及處前後、切不開時在原因加提醒。`GPT` 列為縮寫代號（Codex C4，2026-11-03）：AI 新聞的「GPT-5」原本被當成 GPT Group 的消息，真 FinBERT 給 92.5% 看好；現在要寫「GPT Group」、「ASX: GPT」或「GPT.AX」才算。已用腳本比對全部 2,051 家公司各 9 種寫法，只有 GPT 單獨出現的 4 句結果改變。
- **Claude 引擎**：修正：`BHP.AX`／`ASX: BHP` 比對、回答沒有任何持股時重試再報錯、逾時訊息、API 錯誤說明、重試次數 2 → 1、漏掉的持股顯示「Not assessed」。格式錯誤也重試（Codex C10，2026-11-03 收自外部 PR #1，作者 RyanT0306）：anthropic SDK 在 `messages.parse()` 裡就驗證 JSON，截斷或形狀不對時丟出 pydantic `ValidationError`，不會回 `parsed_output=None`；`_call()` 接住後重試一次，再失敗顯示「didn't match the expected format」。純文字的拒絕一樣走這條路，所以仍顯示格式錯誤，不是「Claude declined…」。
- **區網與輪詢**（2026-11-03，參考外部 PR #1）：`crypto.randomUUID()` 只在 https 或 localhost 有，手機用區網 http 網址打開時，分析成功卻顯示 `crypto.randomUUID is not a function`；`storage.ts` 的 `newId()` 沒有時改用時間加亂數（編號只當 React key，讀回只檢查是文字）。引擎狀態輪詢從 `App.tsx` 搬到 `api.ts` 的 `watchHealth()`，停止後還在路上的那次檢查不再排下一次，開發模式 StrictMode 掛載兩次時不再同時輪詢兩份（後端關著時 9.5 秒內 8 次 → 5 次，已用 `/verify` 實測；後端晚啟動時仍依序顯示載入中、準備好後停止輪詢）。
- **FinBERT 沒安裝**（2026-11-03 收自外部 PR #1）：沒裝 transformers／torch 時，沒提到任何持股的新聞不會載入模型，結果顯示「Not related」，好像 FinBERT 讀過一樣。`_analyze_sync()` 先檢查 `status()`，沒安裝就丟 EngineError。訊息改成給訪客看的「FinBERT isn't installed on the analysis server…」，不叫訪客跑 `pip install`（安裝步驟在 README）。`App.tsx` 的 FinBERT 提示仍寫 `pip install`，留給「上線前必做」一起改。
- **公開 repo**（Codex R1，2026-11-03）：還沒 push 的 `docs/HANDOFF_PROMPT.md` 曾寫入對使用者的個人描述。使用者選擇改寫還沒 push 的 23 個 commit（`git filter-branch --tree-filter`，先建 `backup-before-r1` 分支），15 個 commit 只差那一行、訊息與作者不變，其他 8 個 hash 不變；改寫後沒有任何 commit 含那句話，測試全部通過。push 成功後可刪掉 `backup-before-r1`。
- **`/verify` 工具**（Codex R6，2026-11-03）：`cdp.mjs` 等 Chrome 回應沒有上限，分頁卡住或當掉時 `waitFor()` 永遠等（用真 Chrome 的無限迴圈與 `Page.crash` 重現，給 2 秒、10 秒後仍在等）。`send()` 每個請求最多等 30 秒（第三個參數可改），`waitFor()` 把剩下的時間傳下去，連線關閉時還在等的請求馬上報錯。修好後兩種情況都在 2.0 秒停止；等 35 秒的 `waitFor` 與正常的 FinBERT 分析流程結果和舊版相同，關閉後程式照常馬上結束。
- **前端**（2026-11-03 起）：修正：localStorage 形狀不對時改用預設值或丟掉壞的那筆，不再白畫面（第 1 項，已在 Safari 實測）。Safari 儀表盤指針偏離圓心（第 12 項）：`transformOrigin` 用 px 時 Safari 當成螢幕像素，改成指針畫在原點、以 `0 0` 旋轉再移到圓心，Safari 與 Chrome 實測通過。清空的權重存成 `null`，讀回來是 `NaN`。引擎名稱用 `Object.hasOwn` 比對，`"toString"` 這類內建名稱不算。晚到的回應（第 2 項）：`App.tsx` 用 `edits` 計數，抓文章途中任何修改（打字、改網址、點範例或歷史）都讓那次抓取作廢；分析途中只有整則新聞被換掉（範例、歷史、抓到新文章）才不顯示結果，但仍存進歷史。歷史紀錄的網址（第 3 項）：`history.ts` 的 `storySource()`，只有網址欄與文字框都還是 Fetch 回來的原樣才存網址（使用者接受刪改內文後就不存網址）。兩項都已在瀏覽器實測。歷史紀錄只差持股順序（Codex C8，使用者 2026-11-03 決定算同一個分析）：`history.ts` 的 `runKey()` 先把持股照代號排序（複製一份，存下的紀錄仍是原本順序，點開時照原順序填回）。已用 20,000 組隨機歷史比對新舊版：只有「持股相同、只差順序」的舊紀錄被取代，沒有改動任何紀錄。
- **前後端連線**（2026-11-03 起）：修正：後端比前端晚好時，查不到的公司名稱每 3 秒重查（`history.ts` 的 `lookUpName()`），健康檢查失敗也每 3 秒重試，所以後端一好名稱就自己出現、「FinBERT is loading」也會顯示（第 4 項，已在瀏覽器實測）。後端預料外的錯誤改回 JSON 的 `detail`（`main.py` 的 `unexpected_error`），前端會顯示「Something went wrong on the analysis server…」；Vite 代理在後端沒開時回的是空白 500，仍顯示「isn't available right now」（第 5 項）。抓文章整個過程（含 DNS 與轉址）最多 20 秒（`article.py` 的 `TOTAL_SECONDS`；`httpx.Timeout` 是每一步各自的上限，已用本機慢速伺服器實測會被拖住）。前端每個請求 30 秒、分析 2 分鐘（使用者 2026-11-03 決定；正常約 10 秒）後放棄並顯示「took too long」（第 8＋6 項）。前端的「port 8000」提示只在開發模式出現（`import.meta.env.DEV`），正式 build 裡沒有。讀回應內容也受逾時與取消保護（thermo-nuclear review 找到）：原本 `api.ts` 在收到標頭後就清掉計時器與取消監聽，內容卡住會永遠等；現在 `request()` 負責計時與取消、`send()` 送出並讀完內容。已用 Node 的真 fetch 與送一半就停的本機伺服器驗證（取消 0.5 秒結束、卡住 30 秒顯示「took too long」），8 種正常回應的結果與訊息和修改前相同。驗證錯誤不再回 500（Codex C3）：權重送 `1e309`、`-1e309`、`NaN` 時，FastAPI 預設的 422 回應會把收到的值放回 `input`，JSON 寫不出 inf／nan，變成 500。`main.py` 的 `invalid_request` 改成回同樣的錯誤清單、只拿掉 `input`；已用腳本比對三個 API 的 18 種錯誤請求，新舊回應除了 `input` 完全相同。`ctx` 只放 `models.py` 寫死的有限上下限與錯誤物件，不會再出同樣的問題。

- **抓文章**（2026-11-03 起）：非 UTF-8 網頁亂碼（第 9 項）：trafilatura 2.3.1 不看回應標頭，只靠 charset_normalizer 猜，但它會讀網頁內的 `<meta charset>`。所以只有「編碼只寫在標頭」的頁面會猜錯（Shift_JIS 被當成韓文、`crème` 變 `crčme`）。`article.py` 的 `_decode()` 依序：內容是合法 UTF-8 就照 UTF-8 → 前 5000 bytes 有 meta 就交給 trafilatura（和以前一樣；標頭和 meta 衝突時以 meta 為準，使用者 2026-11-03 選擇，因為舊伺服器常對所有網頁送 ISO-8859-1）→ 照標頭的編碼讀，但只接受瀏覽器支援的網頁編碼（`WEB_ENCODINGS` 白名單，照 WHATWG；ISO-8859-1、Shift_JIS、TIS-620 等照瀏覽器改用較大的編碼，例如 cp1252、cp932、cp874）→ 都不行才交給 trafilatura 猜。白名單是 thermo-nuclear review 找到的：原本接受 Python 認得的任何編碼名稱，網站寫 `charset=punycode` 時解碼 3MB 要約 59 秒，期間整台後端停住（同步計算，20 秒上限擋不住）；`charset=undefined` 會丟出 `UnicodeError` 變成 500。名單裡 34 個編碼對近 3MB 的刁鑽內容最慢約 10 毫秒。Python 不認得的瀏覽器別名（`windows-874`、`x-mac-cyrillic`）交給 trafilatura 猜。已用腳本確認一般 UTF-8 頁面（含沒標示的 gzip 內容）抽出結果與修改前完全相同。轉址到非網頁位址（第 10 項）：轉到 `ftp://` 原本說成使用者網址打錯（`_redirect_target()` 改成 `BAD_REDIRECT`）；轉到 `mailto:`、`javascript:`、`data:` 這類沒有主機的位址時，httpx 即使不自動跟隨轉址也會先算下一個網址並丟出 `InvalidURL`，原本漏成 500，現在 `_follow()` 接住也顯示 `BAD_REDIRECT`。使用者自己的網址進 `stream()` 前已解析好，不會觸發這個錯誤（已用奇怪網址與真實連線驗證）。非英文文章（第 11 項，使用者 2026-11-03 選擇只提醒、不擋）：用真實 FinBERT 重現，中文新聞寫「必和必拓」判為無關，夾英文「BHP」的大好消息只給 55 中立。`assessment.ts` 的 `languageNotice()`：FinBERT 的結果、文章字母超過 3 成不是英文字母時（數字母不數字，所以夾幾個英文代號的中文仍會提醒、引用中文名的英文不會），在「有分數」與「Not related」畫面最上方顯示「FinBERT reads English only, so it may have missed this story.」，Claude 不顯示。`App.tsx` 的 `shown` 把結果和當時分析的文字綁在一起，分析後再改文字框不影響提醒，歷史紀錄用該筆的文字。已在瀏覽器實測。壓縮炸彈（Codex C1）與壞掉的壓縮內容（C2）：httpx 的 `aiter_bytes()` 會把每個網路 chunk 整塊解壓縮，解完才輪到我們檢查 3 MB 上限，`gzip, gzip` 的 791 bytes 回應就讓後端多吃 1.2 GB；壞掉的 gzip 丟出的 `DecodingError` 不是 `TransportError`，變成 500。`_read_limited()` 改用 `aiter_raw()` 自己用 zlib 解壓縮，每次最多解到上限多 1 byte，只接受 gzip、x-gzip、deflate（zlib 格式）與不壓縮，其他編碼與解壓縮錯誤都顯示 `NOT_HTML`；請求也明確送 `Accept-Encoding: gzip, deflate`，免得主機裝了 brotli 後 httpx 自動要 br。已用真實連線比對新舊版：12 種壓縮情況裡 11 種結果逐字相同（含 chunked、截斷、兩段 gzip，這些行為和 httpx 一樣），10 個真實新聞網站結果相同，炸彈只多 6 MB。壓縮資料結尾後的尾端資料（Codex R2）：zlib 會把結尾之後收到的東西全部留在 `unused_data`，每次還整段複製，200 MB 的尾端讓後端記憶體峰值多 7.8 GB、CPU 忙 20 秒。`_read_limited()` 讀到 `unpack.eof` 就停止接收；結尾之後的資料以前 httpx 也會丟掉，已用真實連線比對 12 種情況與 7 個真實網站，結果與修改前相同。註解裡的 `<meta charset>`（Codex R4）：`META_CHARSET` 原本直接搜尋原始 bytes，`<!-- <meta charset="windows-1250"> -->` 也算，交給 trafilatura 猜成別的編碼（`crème` → `crčme`）。`_decode()` 先用 `HTML_COMMENT` 拿掉前 5000 bytes 裡的註解（含沒關的註解與 `<!-->`）再找 meta。已用 2 萬個隨機網頁比對新舊版：結果不同的 1,033 個全都是「meta 只在註解裡」；16 個真實新聞網站（含 meta 前有註解的 Guardian、NPR）結果相同。

**已知但不修**
- 全文只寫「GPT」、沒寫「GPT Group」或「ASX: GPT」的 GPT Group 新聞會被判為無關（C4 的取捨，使用者 2026-11-03 同意，和 AFL、CPU 等縮寫代號相同）。
- 人名會被當成公司（「Sarah Goodman」→ Goodman Group）、沒寫 FC 的球隊名（「Santos beat Corinthians」）。
- 同一句提到多家公司且沒有轉折詞（「BHP rose and CBA fell」）時分數相同，只加提醒。使用者決定不用 LLM 切句。
- 同時輸入「BHP」與「BHP.AX」，前端不擋，但後端回的訊息清楚。
- 編輯器「Total」只顯示到小數一位，例如 100.54 顯示「100.5%」卻同時提示會縮放。
- 歷史紀錄只檢查到每個結果的外層欄位，不檢查每檔持股分數裡的欄位（例如 `reason`）。手動改壞這些欄位時，點開那筆紀錄仍可能出錯。
- 第 3 項修好前存的歷史紀錄可能帶著沒抓過的網址；點開這種舊紀錄再分析，新紀錄會沿用那個網址。最多 20 筆，會被新紀錄擠掉。
- 第 4 項的重試沒有次數上限、也不能取消（`/code-review low` 指出，影響小）：後端沒開時打代號，每個打到一半、查詢失敗的字（B、BH、BHP）都會各自每 3 秒重試，直到後端好；超過 40 字的代號（只有手動改壞 localStorage 才會有）會一直收到 422 而永遠重試。後端一好就停，持股編輯器也不會被卸載。
- 轉址的 `Location` port 不是數字（`http://a.example:x/`）時，httpx 先擋下並轉成 `RemoteProtocolError`，畫面顯示「The site didn't respond」，不精確但不算錯。
- ISO-2022-JP 編碼的日文網頁仍會亂碼：它只用 7-bit byte，剛好也是合法 UTF-8，`_decode()` 第一步就照 UTF-8 讀（GitHub 上的舊版也一樣）。這種編碼現在主要用在 email。
- `<script>` 裡出現 `<!--` 字樣、放在真的 `<meta charset>` 前面且後面沒有 `-->` 時，R4 的修正會把它當成註解開頭，連 meta 一起忽略（瀏覽器不會）。要網頁不是 UTF-8、標頭編碼又和 meta 不同才會亂碼（已實測）。meta 編碼照標準要寫在前 1024 bytes，實務上幾乎是 head 第一行，16 個真實網站都沒有這種情況。
- 法文、德文這類也用英文字母的非英文文章偵測不到，不會出現第 11 項的提醒。FinBERT 判為無關時每檔持股仍寫「Not mentioned in the article.」，和提醒的「可能漏看」語氣有點衝突，提醒排在前面所以先不改。
- 權重寫到小數第 10 位（例如 `50.5000000005`）時，前端 `Math.round(total * 1e9) / 1e9` 和後端 `round(total, 9)` 在第 9 位的進位可能不同，編輯器提示縮放但結果沒縮放（Codex R5，已實測）。沒有人會這樣輸入。
- 權重打 `1e-323` 這種極小正數會通過驗證，正規化後變成 0，相關新聞被回成「Unrelated」（Codex C7，已實測）。沒有人會這樣輸入。
- 標成 `Content-Encoding: deflate` 卻送 raw deflate（沒有 zlib 標頭）的舊伺服器，C1 修正後會顯示「isn't a news page」，以前 httpx 讀得到（已實測）。現代網站幾乎都用 gzip，使用者 2026-11-03 決定不支援。
- 瀏覽器的 localStorage 寫入失敗（例如空間滿了）時，`addHistory` 每次都從存檔重建清單，這次工作階段先前的紀錄會從畫面上消失（Codex C9，已用模擬的 `setItem` 例外實測）。只存 20 筆，現代瀏覽器很難碰到。
- `cdp.mjs` 的兩個訊息問題（R6 修正後 `/code-review low` 找到，使用者 2026-11-03 決定先不修，只影響開發工具出錯時）：`waitFor()` 到期前最後一次檢查只剩幾毫秒時，會報「no reply from Chrome … hung or crashed」，而不是自己的「timed out … waiting for …」；連線關閉後再呼叫 `send()`，WebSocket 照標準默默丟掉訊息、不報錯，要等滿 30 秒才報「no reply」，而不是馬上說連線已關。

**Codex 檢查找到、待修**（2026-11-03 由 Codex 多代理檢查找出，Claude 用真實程式全部重跑確認。嚴重度與順序由使用者同意。依建議順序列出）
- **C5【低】數字很多的長句，FinBERT 看不到公司名稱**：`finbert_engine.py` 的 `_focus()` 用空白分詞數字數，模型上限是 512 個 WordPiece token。104 個字、90 個金額連成一句時有 1,098 個 token，`BHP` 被截掉，真 FinBERT 給 91% 中立（單獨那句是 94% 看好）。真實新聞很少這樣寫。
- 推測、未驗證：結構很複雜的網頁可能讓 trafilatura 抽文字時卡住事件迴圈約 7 秒（Codex 初步量到，沒有交叉驗證）。

**已找到、待修**（2026-10-29 讀程式碼找出，還沒動手。「已確認」＝讀程式碼確定會發生或已實測；「推測」＝要先重現。編號沿用給使用者的清單）

前端
- 推測沒問題、補測試確認即可：快速連按 Analyze／Fetch（按鈕會停用，`fetchStory` 也有擋）；歷史滿 20 筆（`mergeHistory` 有 `slice`）。
- 結果區的引擎切換宣告為 `role="tablist"`，但不能用方向鍵切換（`ResultPanel.tsx`），要用 VoiceOver 實測。


已確認沒問題：`::ffff:127.0.0.1`（IPv4-mapped）與帶 scope 的 IPv6 都會被 `is_global` 正確擋下（Python 3.13 實測）；每次轉址都重新檢查位址，`http` 轉 `https`、換網域已有測試；只有標題的頁面會顯示 `NO_TEXT`。原列第 7 項「`Content-Length` 不是數字就回 500」在真實連線不會發生：httpx 0.28.1 底層的 h11 會先拒絕非數字的值（變成 `RemoteProtocolError`，已顯示成網站沒回應），重複的相同值（`38, 38`）會合併成一個數字；只有測試用的 `MockTransport` 會跳過這層檢查（2026-11-03 用本機 socket 伺服器實測）。

**UI 改版（6 步都完成，待全分支檢查。`redesign` 分支。使用者 2026-11-03 核准計畫並說「可以開始」）**

使用者想在上線前重新設計畫面，設計語言參照 Ramp（使用者給的 Mobbin 連結要登入，403 打不開；ramp.com 只讀得到文字。現在的風格是照 Claude 對 Ramp 的印象：米白底、白卡片、細邊框、大量留白、粗而緊的大標題、數字放大。使用者想更貼近時可以請他貼截圖）。版面草圖在 `docs/design/layout-draft.svg`（藍色標籤是說明，不是畫面），開始前先看一次。

版面（桌面寬度，CSS grid 3 欄 × 2 列，每塊一張卡片）：
- 最上面：Logo（黃色方塊＋黑色閃電）＋「Portfolio News Monitor」；右上角黑色膠囊按鈕「Recent analyses (N) ▾」展開／收起歷史紀錄。
- 第一列：左上「持股＋權重」；中上標題「Efficiency drives progress.」（使用者給的「效率使人進步」，因為介面是英文所以譯成英文；使用者若要中文再改）＋一句說明；右上「引擎選擇＋Analyze」。
- 第二列：左「新聞＋連結」（連結、Fetch、文字框、範例、字數）；中「指標」（儀表盤、Strongly bullish、三類百分比、Affects X%）；右「各持股明細」（By holding、Claude 的 summary／key points、How this score was worked out）。
- 閃電元素：Logo、標題背後淡黃色大閃電與黃色底線、Analyze 按鈕的閃電圖示、指標卡右上小閃電。主按鈕（Analyze）黃底黑字，重點色也是同一個黃色（草圖用 `#FFE135`）；次要按鈕是外框或黑色。
- 不設計手機版（使用者決定）：螢幕窄時只讓區塊依序往下排，不壞掉即可。

使用者已同意的決定：保留暗色模式（多定義一組暗色 token）；字型換成 Inter（第 1 步換完可再看）；歷史紀錄預設收起、按鈕顯示筆數、沒有紀錄時不顯示按鈕；在 `redesign` 分支做，全部做完、使用者在瀏覽器確認後再合併回 `main` 並 push。

做法：`ResultPanel` 改成一次輸出兩張卡片（中間指標、右邊明細），共用「目前看哪個引擎」的狀態，不必把 state 往上搬；引擎選擇＋Analyze＋表單錯誤從 `App.tsx` 拆成 `EnginePicker.tsx`。保留 `/verify` 依賴的 `.result`、`.exposure`、指標 `svg[role=img]` 的 `aria-label`、各輸入框的 `aria-label`。評分邏輯、API、後端都不動。

流程（使用者 2026-11-03 決定「全部設計完再來除錯」）：每步 Claude 自己跑全部測試、build 與 `/verify` 截圖，停下來請使用者在瀏覽器看一眼外觀，使用者說「commit」就各存一個 commit（方便單獨退回）。每步**不跑** `/pstack:blast-radius`。6 步都做完後，對整個 `redesign` 分支跑一次 `/pstack:blast-radius` 與 `/code-review low`，修找到的問題，使用者在瀏覽器完整測一輪，再合併回 `main`。第 5 步有新邏輯，照樣先寫測試。

步驟：
1. **（已完成）** 風格：配色 token（亮色＋暗色）、Inter 字型、黃色主按鈕／外框次要按鈕、Logo 閃電。版面先不動。檔案：`styles.css`、`index.html`、`App.tsx` 標題列。閃電圖案已先做成 `components/Bolt.tsx`（第 4 步直接沿用）。配色 token：`--accent`（黃）、`--accent-hover`、`--on-accent`（黃底上的字，兩個主題都是深色）、`--line-strong`；看好／看壞改成 `#2F7D57`／`#B4473A`（亮色）。儀表盤中間改成白底、外圈帶顏色。已用 `/verify` 在亮色與暗色截圖確認。
2. **（已完成）** 版面：3 欄 × 2 列 grid；結果拆成指標卡與明細卡；引擎＋Analyze 移到右上（新的 `EnginePicker.tsx`）。檢查分析、Fetch、範例、兩個引擎時的切換按鈕都正常。做法：`.layout` 用 `grid-template-areas`（holdings／hero／engine、news／result／detail），1024px 以下變一欄，順序 hero → holdings → news → engine → result → detail（`App.tsx` 的 `ONE_COLUMN` 與 CSS 斷點要一致，分析完會捲到 `.result`）。`ResultPanel` 輸出兩張卡：`.card.result`（儀表盤、三類百分比、Affects X%、提醒、Claude 的 summary，保留 `aria-live` 與 `aria-busy`）與 `.card.detail`（By holding、Key points 等、How this score was worked out；沒結果、分析中或引擎錯誤時顯示提示文字）。卡片同一列等高。歷史紀錄暫時留在最下面。已用 `/verify` 截圖確認亮色、暗色、1440 與 800 寬。
3. **（已完成）** 歷史紀錄：移到最上面的抽屜，按鈕展開／收起，展開時卡片排列；點一筆會填回表單並收起；Clear 正常。檔案：`HistoryList.tsx`、`App.tsx`、`styles.css`。做法：`HistoryList.tsx` 匯出 `HistoryToggle`（`.history-toggle`，`aria-expanded`、`aria-controls="history"`，沒紀錄時不渲染）與 `HistoryList`（`#history.history`，只在展開且有紀錄時渲染）；展開狀態 `historyOpen` 在 `App.tsx`，點紀錄或 Clear 都會收起。暗色模式的膠囊按鈕是淺色（用 `--ink` 底）。`/verify` 的 `analyze-finbert.mjs` 已改成先按 `.history-toggle` 再讀 `.history li`；`SKILL.md` 與 `features/history.md` 的說明留到第 6 步更新。
4. **（已完成）** 閃電元素：標題與閃電背景、黃色底線、Analyze 與指標卡的閃電圖示（用第 1 步做好的 `Bolt.tsx`）。做法：「Efficiency」獨立一行加黃色粗底線（`text-decoration`，不用螢光筆底色，因為暗色模式白字壓黃底看不清）；大閃電 `.hero-bolt` 透明度用 `--hero-bolt-opacity`（亮 0.35、暗 0.16），窄螢幕移到左邊文字後面；Analyze 文字前的閃電不影響 `/verify` 的 `text=Analyze`（svg 沒有文字）。
5. **（已完成）** 上線版提示（＝「上線前必做」第一項）：Claude 不可用時選項變灰、不能勾，寫「Available when you run the project locally.」；FinBERT 沒安裝的提示與 `ResultPanel.tsx` 裡提到 Claude 的那句改成訪客看得懂的話；給開發者的細節（key 怎麼設、要跑的指令）只在 `import.meta.env.DEV` 顯示（同 `api.ts` 的 `BACKEND_HINT` 做法）；預設只勾 FinBERT（本來就是）。「引擎不可用就變灰」寫成小函式並加測試。做法：`lib/engines.ts` 的 `isUsable()`／`usableEngines()`（5 個測試）：狀態是 `unavailable` 才算不能用，健康檢查還沒回應前都算能用；`App.tsx` 的 `run()` 只送能用的引擎，存檔的選擇不改（之後有 key，Claude 會自動回來）。`EnginePicker.tsx`：不能用的引擎按鈕 `disabled`、`aria-pressed=false`，說明換成 `UNAVAILABLE_HINTS`；key 設定與 `pip install` 的提示只在 `import.meta.env.DEV` 顯示。已確認正式版 bundle 裡沒有 `ANTHROPIC_API_KEY`、`pip install`、`backend/.env`、`port 8000`，並用 `vite preview`（`API_URL` 指向 `/verify` 的 8100）在無頭 Chrome 看過正式版畫面。後端 Claude 的「Add ANTHROPIC_API_KEY to backend/.env」錯誤訊息沒改：畫面上選不到 Claude，只有健康檢查還沒回應就按 Analyze、且存檔裡勾著 Claude 時才可能看到，最後的全分支檢查時再確認。
6. **（已完成）** 收尾：更新 `.claude/skills/verify/` 的 `SKILL.md` 與 `features/`（歷史紀錄要先按按鈕才看得到等新的操作方式）、重拍 README 的亮色與暗色截圖（可用 `/verify` 的 Chrome）、更新本檔。截圖是使用者同意後用 `VERIFY_CLAUDE=1` 跑一次真實 Claude（CommBank 範例，FinBERT 96／Claude 75，選 Claude 分頁），寬 1440、從頂端裁 1280 高（`sips --cropOffset` 會被忽略、從中間裁，改用 `ffmpeg -vf crop=1440:1280:0:0`）。`features/engines.md` 寫了怎麼用 `vite preview`（port 5175）看正式版畫面，`cleanup.sh` 不會關它，要自己關。

每步都跑前端全部測試（第 5 步後 64 個）＋`npm run build`、後端 188 個測試，並用 `/verify` 跑一次 `analyze-finbert` 流程與截圖。純樣式改動不寫測試，有新邏輯才補。

**上線前必做**（2026-11-03 與使用者討論。這些不是 bug，部署時再做）
- **上線版不開 Claude**（使用者決定，避免訪客用掉 API 費用）：伺服器上不設定 `ANTHROPIC_API_KEY`，Claude 狀態就是 `unavailable`，完全不會呼叫。Claude 比較留在本機與 GitHub（README 截圖）展示。程式碼不刪。
- **（已完成，UI 改版第 5 步）** 改寫上線版看到的開發者提示：`App.tsx` 的 `EngineNote` 叫訪客把 key 加到 `backend/.env`、FinBERT 不可用的提示也要檢查；改成「Claude analysis is available when you run the project locally. See the README.」之類，並考慮上線版預設只勾 FinBERT。FinBERT 判為無關時的提示「…Claude can also pick up indirect effects…」（`ResultPanel.tsx`）也提到 Claude，上線版要改寫。
- 前後端分開部署時：前端目前靠 Vite 代理 `/api`，上線要設定後端網址（例如環境變數）與 CORS。
- 速率限制：`/api/article` 會替訪客抓網頁、`/api/analyze` 會跑 FinBERT，都要限制次數。
- 主機：FinBERT 約需 1–2 GB 記憶體，部分免費方案不夠；主機自己的請求時間上限要比前端的 2 分鐘長或至少比正常分析時間長。部署時再查各家方案。
- 若之後上線版要開 Claude：後端要自己加每個引擎的總時間上限（目前 Claude 最壞約 4 分鐘，前端 2 分鐘放棄後後端仍在付費），並在 Anthropic 後台設每月費用上限。

### 其他備註
- 開發模式的 React StrictMode 會讓請求發兩次，只發生在開發環境，不影響正式版。
- 分數不用 Python 的 `round()`（銀行家捨入，60.5 會變成 60）。`score_from_probs()` 先取到小數 9 位消掉浮點誤差（22.5 可能算成 22.4999…），再 .5 進位。分數一律由後端計算，前端不重算。
- 可能的功能延伸（計畫中列為非目標）：docker-compose、即時股價、更多範例新聞。部署時注意 `/api/article` 會替使用者抓網頁，已擋內部位址，但仍建議加上速率限制。

## 7. 驗證方式

以下指令都在專案根目錄執行：

```bash
(cd backend && .venv/bin/pytest -q)
(cd frontend && npm test && npm run build)
```

端到端測試：啟動前後端，打開 http://localhost:5173，點範例新聞後按 Analyze。兩個引擎都勾選時，右上角會出現切換按鈕。

### 除錯時好用的做法與踩過的坑
- **不靠模型也能測 API**：用 FastAPI 的 `TestClient`，把 `app.state.engines` 換成假引擎；`tests/test_claude_engine.py` 的 `fake_client()`、`reply()`、`analysis()` 可以直接拿來模擬 Claude 的各種回答與 API 錯誤。腳本放專案外時要加 `PYTHONPATH=.`（在 `backend/` 執行）。
- **用真實 FinBERT 驗證**：模型已在本機快取，`cd backend && HF_HUB_OFFLINE=1 PYTHONPATH=. .venv/bin/python ...`，載入約幾秒。修 FinBERT 的 bug 時，測試用假分類器，修完再用真模型確認一次。
- **用真實 Claude 驗證錯誤訊息**：模型名稱打錯（404）與錯誤 key（401）不會產生費用。腳本裡用 `load_dotenv(".env")` 明確指定路徑；`load_dotenv()` 會從腳本所在資料夾找，放在專案外會讀不到 key。
- `backend/data/asx_companies.csv` 是 **CRLF 換行**（Python csv 模組預設），用 `sed` 比對整行會失敗，要用 Python 讀寫 bytes。改別名時 `scripts/build_asx_list.py` 的 `ALIASES` 與 CSV 兩邊都要改。
- **MockTransport 的 `httpx.Response(content=...)` 會在建立時就讀完並解壓縮內容**，所以 `test_article.py` 的 `fetch()` 先經過 `unread()` 改成未讀的 stream，壓縮的假網頁用 `packed()` 直接給原始 bytes；不然炸彈在測試裡就先解開了，`aiter_raw()` 也會丟 `StreamConsumed`。
- **用真實連線測抓文章**：在腳本裡用 `http.server` 開本機伺服器，回想測的標頭與內容（編碼、轉址、送一半就停），並把 `article._check_public` 暫時換成什麼都不做的函式，因為本機位址會被擋。MockTransport 會跳過 httpx 底層的檢查，結論可能不一樣（第 7 項就是這樣撤回的）。
- **後端的同步計算會卡住整台伺服器**：`async` 函式裡的解碼、trafilatura 抽文字都在事件迴圈上執行，`asyncio.timeout` 打斷不了。懷疑某段很慢時，另開一個每 0.1 秒跳一次的 task 量最長停頓（charset=punycode 就是這樣量出 59 秒）。
- **用 `/verify` 在真瀏覽器操作網站**（2026-11-03 起）：`.claude/skills/verify/` 會在 8100／5174 開一份自己的網站（Claude 關閉、不花錢），用無頭 Chrome 點按鈕、打字並截圖，不碰使用者的 8000／5173。步驟、畫面元素的定位方式與 5 個功能的操作清單都在該資料夾的 `SKILL.md` 與 `features/`；證據存在系統暫存資料夾的 `pnm-verify-evidence/`。畫面改動修完後先自己跑一次，再請使用者在瀏覽器確認。`cleanup.sh` 關程式前會用 `ps` 比對指令內容（`signature()`：`uvicorn app.main:app --port 8100`、`vite.js --port 5174`、這次的 Chrome 設定檔），不符就跳過，避免 PID 被系統重用時關錯程式（Codex R3）；**改 `launch.sh` 的 port 或啟動參數時要同步改 `signature()`**，否則清理會跳過自己的程式並警告 port 仍被佔用。`page.evaluate()` 每次最多等 30 秒（R6），真的要等更久的單一動作時傳第二個參數，例如 `page.evaluate(js, 120_000)`；要等畫面變化請用 `waitFor`。
- **跑前端真程式**：`cd frontend && npx vite-node 腳本.ts` 可以直接 import `src/lib` 的函式；`fetch` 用的是相對路徑，要先把 `globalThis.fetch` 包一層補上本機伺服器網址。
- zsh 會把 `--include=*.py` 和 `echo =====` 當成特殊語法而報錯，前者加引號，後者別用。

## 8. 參考來源

- 視覺：儀表盤參考 Stocktwits Sentiment（refero.design）。2026-11 UI 改版照 Ramp 的設計語言（米白底、白卡片、細邊框、粗而緊的標題、黃色 `#FFE135` 重點色），字型 Inter。
- 做法：https://github.com/jordan5226/tw_stock_news_ai_monitor 。借用其 JSON schema、五級情緒與提示詞紀律，沒有借用自動爬新聞。

## 9. 工作習慣（使用者偏好）

- commit 訊息結尾加上 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 先寫測試再實作（TDD）。後端測試一律 mock，不下載模型、不呼叫 API。
- 介面文字用英文、句首大寫，避免全大寫標籤，不放 emoji。
- 日常開發流程（VS Code 任務、檢查改動、commit、退回）寫在 `docs/WORKFLOW.md`，請照著做。
- 使用者裝了 pstack plugin（使用者層級，不在 repo 裡；自動注入 poteto-mode 的 session hook 已關閉，superpowers 目前停用）。**每個 bug 的流程由使用者觸發，Claude 每步做完就停下來等**：
  1. 使用者輸入 `/pstack:tdd 修第 N 項：…`：Claude 先寫會失敗的測試（引用失敗內容），再修、跑全部測試，能在瀏覽器看的就給使用者可照做的測試步驟。
  2. 使用者在 VS Code「原始碼控制」看改動、在瀏覽器測。
  3. 使用者輸入 `/pstack:blast-radius`：找出這次改動安全的關鍵事實，用腳本或真實連線證明（不要用 arena）。
  4. `/code-review low`：可省略，改動大時才跑。
  5. 使用者說「commit」：Claude 同時更新本檔第 6 節（移到「已完成」、更新測試數），檢查沒有本機路徑或金鑰後 commit。
  一整區修完、要上傳前，跑一次 `/pstack:thermo-nuclear-review`。使用者希望**省 token**：token 主要花在修 bug 和 code review，不自己開子代理，回覆簡短。
- **找 bug 時先用真實連線或真實程式重現**，不要只讀程式碼就判定「已確認」：2026-11-03 的第 7 項讀程式碼看起來會 500，實際上 httpx 會先擋下，最後撤回修正。pstack 的做法和本檔衝突時以本檔為準，並先問使用者。會同時跑多個模型的指令（`interrogate`、`arena`、`architect`、`thermos`）費用較高，使用者沒要求時不要用。pstack 若在專案裡新增檔案，commit 前先讓使用者確認。
- **這個 repo 是公開的**：commit 的檔案裡不要寫入本機絕對路徑、對使用者的個人描述、信箱或任何金鑰。路徑一律用相對專案根目錄的寫法。
- 修好的東西先在本機 commit；**使用者說要上傳時才 `git push`**。
