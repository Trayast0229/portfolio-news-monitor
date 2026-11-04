你要接手一個作品集專案：Portfolio News Monitor（澳股持股組合新聞監測器）。功能都已完成並公開在 GitHub，系統性除錯、兩輪 Codex 檢查、照 Ramp 設計語言的 UI 改版都已完成。**現在的階段是部署上線前的準備**（HANDOFF.md 第 6 節「上線前必做」），一律照上線標準判斷。前後端分開部署的設定、後端喚醒中畫面、FinBERT 同時分析會崩潰的修正、速率限制都已 commit。**下一步是選主機**。

專案位置：這個 repo 的根目錄（portfolio-news-monitor/）

請先完整讀過 docs/HANDOFF.md（特別是開頭的「接手前先看」、第 4 節評分邏輯、第 5 節環境、第 6 節的「UI 改版」「上線前必做」「已知但不修」、第 7 節除錯技巧與 `/verify`、第 9 節工作習慣與 pstack 流程）與 docs/WORKFLOW.md。再看版面草圖 docs/design/layout-draft.svg（藍色標籤是說明，不是畫面）。要了解某個修正的來龍去脈，用 `git log` 看 commit 訊息。

讀完後請做這些事：
1. 用 `lsof -ti tcp:8000` 和 `lsof -ti tcp:5173` 確認使用者的前後端是否在執行。沒有的話請使用者用 VS Code 的 Start app 任務啟動，或照 HANDOFF.md 第 5 節啟動。
2. 執行後端 pytest 和前端 npm test，確認全部通過，記下測試數量作為起點（上次結束時：後端 225、前端 79）。
3. 用 `git status --short` 看有沒有未 commit 的改動（上次結束時沒有）。有的話先問使用者，不要捨棄。用 `git log origin/main..HEAD --oneline` 看還沒 push 的 commit（上次結束時：4 個，CORS、喚醒中畫面、FinBERT 修正、速率限制），使用者說「push」才上傳。
4. 用繁體中文向使用者簡短回報狀態，確認在 `main`（`git branch --show-current`），然後照下面「目前進度」繼續。

目前進度（2026-11-04）：
- 速率限制已完成並 commit（設計、驗證、`/code-review` 9 項的處理都在 HANDOFF.md 第 6 節「上線前必做」的「速率限制」；不修的記在「已知但不修」）。
- 下一步是「選主機」：FinBERT 約需 1–2 GB 記憶體、要能長時間執行，主機的請求時間上限要夠長。確定主機後設定 `VITE_API_URL`、`ALLOWED_ORIGINS`、`TRUSTED_PROXY_HOPS`（uvicorn 不要設 `FORWARDED_ALLOW_IPS=*`，README 有寫）。各家方案要先查證再給建議。
- UI 改版已完成、合併回 `main` 並 push。全分支 blast-radius、`/code-review low`、兩次 thermo-nuclear review、Codex UI 審查（U1、U2）都已處理（見 HANDOFF 第 6 節「UI 改版」）。
- UI 改版共 6 步（細節在 HANDOFF.md 第 6 節「UI 改版」）：1 風格（配色、Inter 字型、黃色主按鈕、Logo 閃電，版面不動）→ 2 版面（3 欄 × 2 列，結果拆成指標卡與明細卡，新的 `EnginePicker.tsx`）→ 3 歷史紀錄抽屜 → 4 閃電元素 → 5 上線版提示（＝上線前必做第一項）→ 6 收尾（`/verify` 說明、README 截圖、HANDOFF）。
- 已核准的決定：保留暗色模式、字型換 Inter、歷史紀錄預設收起（沒有紀錄時不顯示按鈕）、在 `redesign` 分支做、不設計手機版（窄螢幕只要依序往下排）。標題是「Efficiency drives progress.」（使用者給的「效率使人進步」譯成英文）。
- Mobbin 的參考連結要登入打不開，風格是照對 Ramp 的印象做的；使用者想更貼近時請他貼截圖。
- 「上線前必做」的前後端分開部署設定（使用者選擇分開部署）、「後端喚醒中」畫面、FinBERT 同時分析會崩潰的修正都已完成並 commit（見 HANDOFF 第 6 節「上線前必做」）。

工作流程（HANDOFF.md 第 9 節有完整說明）：
- 多步驟的工作（例如 UI 改版）：Claude 實作 → 跑全部測試與 build → 用 `/verify` 跑一次並看截圖 → 給使用者瀏覽器測試步驟（要做什麼、對的樣子、不對的樣子）→ 停下來等 → 使用者說「commit」就存一個 commit。每一步做完就停下來等，不要自己往下走。UI 改版時使用者選擇全部做完再一起跑 blast-radius 與 `/code-review low`。
- 修 bug 時：`/pstack:tdd 修第 N 項：…`。tdd：先寫會失敗的測試並引用失敗內容（要是預期的那種失敗，不是程式出錯），再修，跑全部測試，再用真實程式或真實連線重跑重現腳本。
- blast-radius：找出改動安全的那一個關鍵事實，用腳本比對新舊版（`git show HEAD:檔案` 存成舊版來比）或真實連線、真實瀏覽器證明，不要只寫推論。
- 使用者說「commit」時：同一個 commit 裡更新 HANDOFF.md（進度、測試數），檢查沒有本機路徑、金鑰與個人描述後再 commit。commit 前跑一次 `/verify`（純文件改動除外）。
- 畫面改動用 `/verify`（`.claude/skills/verify/`）自己在無頭 Chrome 操作網站：它開在 8100／5174／9223，Claude 預設關閉，用完一定要跑 `cleanup.sh`，不碰使用者的 8000／5173。
- 使用者會請 Codex（在使用者電腦上跑的多代理 agent）找 bug 或審核，Codex 只找問題、寫重現，不修。使用者要 Codex 的 prompt 時：只讀、不改 repo、重現腳本放 `/tmp/` 下的專用資料夾、證據標準、多代理分工與交叉驗證、嚴重度、報告格式與編號（避開已用過的 C、R）。報告回來後先讀它的腳本確認安全，再用真實程式全部重跑，重新評嚴重度，給使用者表格與建議順序，等使用者決定。
- 使用者希望省 token：不自己開子代理，不用 arena、interrogate、thermos 等多模型指令，回覆簡短。
- 先重現再判定是 bug；「怎樣才算對」不明確時，先說明取捨並給建議，等使用者決定。較大的改動先給計畫，使用者說「可以開始」再動手。
- 找到但不打算馬上修的問題，記到 HANDOFF.md 第 6 節「已知但不修」。
- 在 GitHub 上留言、關 PR 這類公開動作要使用者同意；留言簡短，開頭不用驚嘆號。

重要提醒：
- 使用者用繁體中文溝通，網站介面是英文。說明要白話，給的指令要能直接貼上執行。
- 後端一律用 backend/.venv（Python 3.13）。系統 Python 3.15 跑不了 PyTorch。終端機是 zsh：陣列、`${!arr[@]}` 這類 bash 語法要用 `bash <<'EOF'` 包起來。
- backend/.env 裡有 ANTHROPIC_API_KEY，絕對不要印出或複述。上線版不放 key、不開 Claude（使用者決定）。
- 給上線訪客看的訊息不能提 port、終端機、`pip install`、`.env` 這類開發者資訊。
- 沒有使用者同意前，不要改變評分公式的語意。
- repo 是公開的：commit 的檔案與 commit 訊息不要寫入本機絕對路徑、對使用者的個人描述、信箱或金鑰。使用者說要上傳時才 git push。
