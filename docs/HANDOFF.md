# 交接文件：Portfolio News Monitor（澳股持股組合新聞監測器）

最後更新：2026-11-03。對象：接手這個專案的下一段 Claude Code 對話。

**接手前先看**：2026-10-24 到 2026-10-27 做完了系統性除錯的三區（評分邊界、FinBERT 比對、Claude 引擎），修了 17 個問題，全部已 push。剩下的「抓文章」「前端」「前後端連線」三區已在 2026-10-29 讀過程式碼，找出 11 個問題。2026-11-03 修好第 1 項（localStorage 白畫面），也修好在 Safari 發現的第 12 項（指針歪掉）、第 4 項（後端晚好時名稱不重查）、第 5 項（後端出錯被說成沒開）、第 8＋6 項（沒有總時間上限）、第 2＋3 項（晚到的回應、歷史紀錄的網址）、第 9 項（非 UTF-8 網頁亂碼）、第 10 項（轉址到非網頁位址）與第 11 項（非英文文章加提醒），第 7 項查證後不會發生。「前端」「前後端連線」「抓文章」三區的確認項目都已修完，第 6 節「已找到、待修」只剩前端幾個推測項目。從 `6db0e09` 之後的 commit 都**還沒 push**。2026-11-03 已跑過 `/pstack:thermo-nuclear-review`，修好它找到的 charset 問題；它找到的前端「讀回應內容沒有逾時」（第 6 節「已找到、待修」）還等使用者決定修或不修。建議下一步：問使用者這一項，處理後使用者同意才 push。**專案最後要部署上線**（作業要求），修正一律照上線標準判斷，部署前要做的事在第 6 節「上線前必做」。之前的對話都**沒有瀏覽器工具**，有幾個畫面改動只靠測試與 build 驗證，清單在第 6 節「待瀏覽器確認」。

## 1. 這是什麼、為什麼做

- 使用者輸入澳股（ASX）持股與權重，貼上一則新聞。系統判斷這則新聞對**整個持股組合**是看好、中立還是看壞，給出三類百分比與 0–100 分數，並用 Stocktwits 風格的半圓儀表盤呈現。
- 這是使用者的**作品集／學習專題**，重點是「能完整跑起來、畫面好看、評分邏輯講得清楚」。Claude 與 FinBERT 兩種引擎可以並排比較，這是展示亮點。
- 使用者用**繁體中文**溝通，網站介面是**英文**。
- 說明要白話，指令要直接給可貼上執行的完整命令。

## 2. 目前狀態（全部完成並已驗證）

| 項目 | 狀態 |
|---|---|
| 後端（FastAPI）| 完成，170 個 pytest 全部通過 |
| 前端（Vite + React + TS）| 完成，53 個 Vitest 通過，`npm run build` 成功 |
| FinBERT 模式 | 在瀏覽器實測通過 |
| Claude 模式 | 用真實 API 實測通過，每次約 10 秒 |
| 並排比較 | 在瀏覽器實測通過，切換按鈕正常 |
| 手機版、亮色／暗色模式 | 實測通過，沒有水平捲動 |
| README（含截圖）| 完成 |
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
  src/App.tsx                主畫面、表單驗證、引擎狀態輪詢
  src/components/            SentimentGauge, ResultPanel, HoldingBreakdown, HoldingsEditor, HistoryList
  src/lib/gauge.ts(+test)    儀表盤幾何與分區
  src/lib/api.ts             型別與 fetch
  src/lib/history.ts(+test)  歷史紀錄去重、分數顯示文字、待查公司名稱（純函式）
  src/lib/holdings.ts(+test) 哪些持股列算數（有代號才算）、權重總和、送出前的持股檢查（純函式）
  src/lib/assessment.ts(+test) 「Not assessed／Not affected」標籤與「Claude skipped …」提醒文字（純函式）
  src/lib/format.ts          百分比與時間的顯示格式
  src/lib/storage.ts(+test) localStorage（持股、引擎選擇、最近 20 筆紀錄），存取都包 try/catch，讀取時檢查形狀
  src/lib/examples.ts        3 則虛構範例新聞
  src/styles.css             設計 token、亮暗主題、RWD
docs/
  superpowers/specs/2026-10-21-portfolio-news-monitor-design.md   原始設計與計畫（已核准）
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
- 上一段對話結束時，前後端**都沒有在執行**。接手時先用 `lsof -ti tcp:8000` 與 `lsof -ti tcp:5173` 確認，沒有就照上面的方式啟動。使用者自己則是用 VS Code 的 **Start app** 任務啟動（見 `docs/WORKFLOW.md`）。
- **API key** 在 `backend/.env`。**絕對不要印出或複述 key 的內容**；要檢查格式時只看長度與前綴（`sk-ant-`）。
- 沒有安裝 Docker，所以原計畫中的 docker-compose 刻意沒做（不附沒驗證過的設定）。
- 已用 Homebrew 安裝 `gh` 並登入 Trayast0229，git 透過它以 https 推送。這個 repo 的 `user.email` 設為 GitHub 隱私信箱 `344183369+Trayast0229@users.noreply.github.com`，不要改回個人信箱。commit 後用 `git push` 上傳。

## 6. 系統性除錯進度與下一步

每個 bug 先重現、寫出會失敗的測試，再修，每個單獨 commit。進度如下（2026-10-27）：

**待瀏覽器確認**（上一段對話沒有瀏覽器工具，以下只用測試與 build 驗證過）
- 持股編輯器：清空某列代號但保留權重時，「Total」應該跟著變少並提示會縮放。
- 某檔權重打 150 按 Analyze，應顯示「Keep each weight at 100% or less.」。
- 只勾 FinBERT，貼「BHP shares surged to a record and CBA shares plunged after a profit warning.」（前面補一句湊滿 50 字），兩檔的原因後面都應出現「A sentence used here also names …」提醒。
- 「Not assessed」狀態與「Claude skipped …」提醒：真實 Claude 很少漏回持股，不容易在瀏覽器重現；後端已用模擬回答驗證 API 回傳正確。

**已完成**（細節見 `git log`，規則已寫進第 4 節）
- **評分邊界**：前後端分區一致；權重總和 99.5／100.5 視為 100；30 檔上限正常。修正：編輯器總和不算沒填代號的列、前端擋下權重 >100、.5 一律進位。
- **FinBERT 比對**：修正：直撇號與彎撇號、新聞縮寫 ticker（AFL、NRL、SPP 等 20 個）、James Hardie 與 a2 Milk 別名、地名與賽事排除、`Ltd.`／`U.S.` 不斷句、同一句多家公司按轉折詞切開、長句只取提及處前後、切不開時在原因加提醒。
- **Claude 引擎**：修正：`BHP.AX`／`ASX: BHP` 比對、回答沒有任何持股時重試再報錯、逾時訊息、API 錯誤說明、重試次數 2 → 1、漏掉的持股顯示「Not assessed」。
- **前端**（2026-11-03 起）：修正：localStorage 形狀不對時改用預設值或丟掉壞的那筆，不再白畫面（第 1 項，已在 Safari 實測）。Safari 儀表盤指針偏離圓心（第 12 項）：`transformOrigin` 用 px 時 Safari 當成螢幕像素，改成指針畫在原點、以 `0 0` 旋轉再移到圓心，Safari 與 Chrome 實測通過。清空的權重存成 `null`，讀回來是 `NaN`。引擎名稱用 `Object.hasOwn` 比對，`"toString"` 這類內建名稱不算。晚到的回應（第 2 項）：`App.tsx` 用 `edits` 計數，抓文章途中任何修改（打字、改網址、點範例或歷史）都讓那次抓取作廢；分析途中只有整則新聞被換掉（範例、歷史、抓到新文章）才不顯示結果，但仍存進歷史。歷史紀錄的網址（第 3 項）：`history.ts` 的 `storySource()`，只有網址欄與文字框都還是 Fetch 回來的原樣才存網址（使用者接受刪改內文後就不存網址）。兩項都已在瀏覽器實測。
- **前後端連線**（2026-11-03 起）：修正：後端比前端晚好時，查不到的公司名稱每 3 秒重查（`history.ts` 的 `lookUpName()`），健康檢查失敗也每 3 秒重試，所以後端一好名稱就自己出現、「FinBERT is loading」也會顯示（第 4 項，已在瀏覽器實測）。後端預料外的錯誤改回 JSON 的 `detail`（`main.py` 的 `unexpected_error`），前端會顯示「Something went wrong on the analysis server…」；Vite 代理在後端沒開時回的是空白 500，仍顯示「isn't available right now」（第 5 項）。抓文章整個過程（含 DNS 與轉址）最多 20 秒（`article.py` 的 `TOTAL_SECONDS`；`httpx.Timeout` 是每一步各自的上限，已用本機慢速伺服器實測會被拖住）。前端每個請求 30 秒、分析 2 分鐘（使用者 2026-11-03 決定；正常約 10 秒）後放棄並顯示「took too long」（第 8＋6 項）。前端的「port 8000」提示只在開發模式出現（`import.meta.env.DEV`），正式 build 裡沒有。

- **抓文章**（2026-11-03 起）：非 UTF-8 網頁亂碼（第 9 項）：trafilatura 2.3.1 不看回應標頭，只靠 charset_normalizer 猜，但它會讀網頁內的 `<meta charset>`。所以只有「編碼只寫在標頭」的頁面會猜錯（Shift_JIS 被當成韓文、`crème` 變 `crčme`）。`article.py` 的 `_decode()` 依序：內容是合法 UTF-8 就照 UTF-8 → 前 5000 bytes 有 meta 就交給 trafilatura（和以前一樣；標頭和 meta 衝突時以 meta 為準，使用者 2026-11-03 選擇，因為舊伺服器常對所有網頁送 ISO-8859-1）→ 照標頭的編碼讀，但只接受瀏覽器支援的網頁編碼（`WEB_ENCODINGS` 白名單，照 WHATWG；ISO-8859-1、Shift_JIS、TIS-620 等照瀏覽器改用較大的編碼，例如 cp1252、cp932、cp874）→ 都不行才交給 trafilatura 猜。白名單是 thermo-nuclear review 找到的：原本接受 Python 認得的任何編碼名稱，網站寫 `charset=punycode` 時解碼 3MB 要約 59 秒，期間整台後端停住（同步計算，20 秒上限擋不住）；`charset=undefined` 會丟出 `UnicodeError` 變成 500。名單裡 34 個編碼對近 3MB 的刁鑽內容最慢約 10 毫秒。Python 不認得的瀏覽器別名（`windows-874`、`x-mac-cyrillic`）交給 trafilatura 猜。已用腳本確認一般 UTF-8 頁面（含沒標示的 gzip 內容）抽出結果與修改前完全相同。轉址到非網頁位址（第 10 項）：轉到 `ftp://` 原本說成使用者網址打錯（`_redirect_target()` 改成 `BAD_REDIRECT`）；轉到 `mailto:`、`javascript:`、`data:` 這類沒有主機的位址時，httpx 即使不自動跟隨轉址也會先算下一個網址並丟出 `InvalidURL`，原本漏成 500，現在 `_follow()` 接住也顯示 `BAD_REDIRECT`。使用者自己的網址進 `stream()` 前已解析好，不會觸發這個錯誤（已用奇怪網址與真實連線驗證）。非英文文章（第 11 項，使用者 2026-11-03 選擇只提醒、不擋）：用真實 FinBERT 重現，中文新聞寫「必和必拓」判為無關，夾英文「BHP」的大好消息只給 55 中立。`assessment.ts` 的 `languageNotice()`：FinBERT 的結果、文章字母超過 3 成不是英文字母時（數字母不數字，所以夾幾個英文代號的中文仍會提醒、引用中文名的英文不會），在「有分數」與「Not related」畫面最上方顯示「FinBERT reads English only, so it may have missed this story.」，Claude 不顯示。`App.tsx` 的 `shown` 把結果和當時分析的文字綁在一起，分析後再改文字框不影響提醒，歷史紀錄用該筆的文字。已在瀏覽器實測。

**已知但不修**
- 人名會被當成公司（「Sarah Goodman」→ Goodman Group）、沒寫 FC 的球隊名（「Santos beat Corinthians」）。
- 同一句提到多家公司且沒有轉折詞（「BHP rose and CBA fell」）時分數相同，只加提醒。使用者決定不用 LLM 切句。
- 同時輸入「BHP」與「BHP.AX」，前端不擋，但後端回的訊息清楚。
- 編輯器「Total」只顯示到小數一位，例如 100.54 顯示「100.5%」卻同時提示會縮放。
- 歷史紀錄只檢查到每個結果的外層欄位，不檢查每檔持股分數裡的欄位（例如 `reason`）。手動改壞這些欄位時，點開那筆紀錄仍可能出錯。
- 第 3 項修好前存的歷史紀錄可能帶著沒抓過的網址；點開這種舊紀錄再分析，新紀錄會沿用那個網址。最多 20 筆，會被新紀錄擠掉。
- 第 4 項的重試沒有次數上限、也不能取消（`/code-review low` 指出，影響小）：後端沒開時打代號，每個打到一半、查詢失敗的字（B、BH、BHP）都會各自每 3 秒重試，直到後端好；超過 40 字的代號（只有手動改壞 localStorage 才會有）會一直收到 422 而永遠重試；開發模式的 StrictMode 下健康檢查可能同時輪詢兩份。後端一好就停，持股編輯器也不會被卸載。
- 轉址的 `Location` port 不是數字（`http://a.example:x/`）時，httpx 先擋下並轉成 `RemoteProtocolError`，畫面顯示「The site didn't respond」，不精確但不算錯。
- 法文、德文這類也用英文字母的非英文文章偵測不到，不會出現第 11 項的提醒。FinBERT 判為無關時每檔持股仍寫「Not mentioned in the article.」，和提醒的「可能漏看」語氣有點衝突，提醒排在前面所以先不改。

**已找到、待修**（2026-10-29 讀程式碼找出，還沒動手。「已確認」＝讀程式碼確定會發生或已實測；「推測」＝要先重現。編號沿用給使用者的清單）

前端
- **讀回應內容沒有逾時與取消保護**（2026-11-03 thermo-nuclear review 找到，已確認但可能性低，待使用者決定）。`api.ts` 的 `request()` 在收到回應標頭後的 `finally` 就清掉計時器與外部取消的監聽，之後的 `res.json()` 不受保護：伺服器送了標頭卻卡住內容時前端會一直等；打字查代號時被取消的舊查詢理論上仍可能蓋上舊建議。後端的 JSON 與標頭一起送出，所以很少發生。修法：把讀內容也放進受保護的範圍。
- 推測沒問題、補測試確認即可：快速連按 Analyze／Fetch（按鈕會停用，`fetchStory` 也有擋）；歷史滿 20 筆（`mergeHistory` 有 `slice`）。
- `crypto.randomUUID()`（`storage.ts` 的 `addHistory`）只在 https 或 localhost 可用；用區網 IP 或 http 部署時，分析成功卻會顯示錯誤（推測，目前開發伺服器不對區網開放）。
- 結果區的引擎切換宣告為 `role="tablist"`，但不能用方向鍵切換（`ResultPanel.tsx`），要用 VoiceOver 實測。


已確認沒問題：`::ffff:127.0.0.1`（IPv4-mapped）與帶 scope 的 IPv6 都會被 `is_global` 正確擋下（Python 3.13 實測）；每次轉址都重新檢查位址，`http` 轉 `https`、換網域已有測試；只有標題的頁面會顯示 `NO_TEXT`。原列第 7 項「`Content-Length` 不是數字就回 500」在真實連線不會發生：httpx 0.28.1 底層的 h11 會先拒絕非數字的值（變成 `RemoteProtocolError`，已顯示成網站沒回應），重複的相同值（`38, 38`）會合併成一個數字；只有測試用的 `MockTransport` 會跳過這層檢查（2026-11-03 用本機 socket 伺服器實測）。

**上線前必做**（2026-11-03 與使用者討論。部署是作業要求；不是 bug，部署時再做）
- **上線版不開 Claude**（使用者決定，避免訪客用掉 API 費用）：伺服器上不設定 `ANTHROPIC_API_KEY`，Claude 狀態就是 `unavailable`，完全不會呼叫。Claude 比較留在本機與 GitHub（README 截圖）展示。程式碼不刪。
- 改寫上線版看到的開發者提示：`App.tsx` 的 `EngineNote` 叫訪客把 key 加到 `backend/.env`、FinBERT 不可用的提示也要檢查；改成「Claude analysis is available when you run the project locally. See the README.」之類，並考慮上線版預設只勾 FinBERT。FinBERT 判為無關時的提示「…Claude can also pick up indirect effects…」（`ResultPanel.tsx`）也提到 Claude，上線版要改寫。
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
- zsh 會把 `--include=*.py` 和 `echo =====` 當成特殊語法而報錯，前者加引號，後者別用。

## 8. 參考來源

- 視覺：Stocktwits Sentiment 儀表盤（refero.design）。配色 Dark Mint / Grapefruit / Silver / Night / Cotton，字型 Source Sans 3。
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
