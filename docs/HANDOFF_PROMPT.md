你要接手一個作品集專案：Portfolio News Monitor（澳股持股組合新聞監測器）。功能都已完成並公開在 GitHub，目前正在**系統性地找出並修正 bug**。「評分邊界」「FinBERT 比對」「Claude 引擎」「前端」「前後端連線」五區已修完；「抓文章」區剩第 9、10 項，第 11 項待使用者決定。專案**最後要部署上線**（作業要求），修正一律照上線標準判斷。

專案位置：這個 repo 的根目錄（portfolio-news-monitor/）

請先完整讀過 docs/HANDOFF.md（特別是開頭的「接手前先看」、第 4 節評分邏輯、第 5 節環境、第 6 節除錯進度與「上線前必做」、第 9 節工作習慣與 pstack 流程）與 docs/WORKFLOW.md。需要設計細節時再讀 docs/superpowers/specs/2026-10-21-portfolio-news-monitor-design.md。要了解某個修正的來龍去脈，用 `git log` 看 commit 訊息。

讀完後請做這些事：
1. 用 `lsof -ti tcp:8000` 和 `lsof -ti tcp:5173` 確認前後端是否在執行。沒有的話照 HANDOFF.md 第 5 節啟動，或請使用者用 VS Code 的 Start app 任務啟動。
2. 執行後端 pytest 和前端 npm test，確認目前全部通過，記下測試數量作為起點（上次結束時：後端 158、前端 50）。
3. 用 `git log origin/main..HEAD --oneline` 確認還沒 push 的 commit（上次結束時有 9 個）。
4. 用繁體中文向使用者簡短回報狀態，然後建議下一步：修第 9 項（`/pstack:tdd 修第 9 項：非 UTF-8 網頁可能亂碼`）、第 10 項，再跑 `/pstack:thermo-nuclear-review`，使用者同意後才 push。

工作流程（HANDOFF.md 第 9 節有完整說明）：
- 每個 bug 由使用者依序觸發：`/pstack:tdd 修第 N 項：…` → 使用者看改動、在瀏覽器測 → `/pstack:blast-radius` → （可省略）`/code-review low` → 使用者說「commit」。每一步做完就停下來等，不要自己往下走。
- 一整區修完、上傳前跑一次 `/pstack:thermo-nuclear-review`。
- 使用者希望省 token：不自己開子代理，不用 arena、interrogate、thermos 等多模型指令，回覆簡短。
- 先重現再判定是 bug：用真實連線、真實程式或腳本確認，不要只讀程式碼。
- 「怎樣才算對」不明確時，先說明取捨並給建議，等使用者決定。
- 找到但不打算馬上修的問題，記到 HANDOFF.md 第 6 節「已知但不修」。修好的項目從「已找到、待修」移到「已完成」，和修正放在同一個 commit。
- 沒有瀏覽器工具時，給使用者可以照做的瀏覽器測試步驟（要做什麼、修好的樣子、沒修好的樣子）。

重要提醒：
- 使用者用繁體中文溝通，網站介面是英文。說明要白話，給的指令要能直接貼上執行。
- 後端一律用 backend/.venv（Python 3.13）。系統 Python 3.15 跑不了 PyTorch。
- backend/.env 裡有 ANTHROPIC_API_KEY，絕對不要印出或複述。上線版不放 key、不開 Claude（使用者決定）。
- 給上線訪客看的訊息不能提 port、終端機這類開發者資訊。
- 沒有使用者同意前，不要改變評分公式的語意。
- repo 是公開的：commit 的檔案不要寫入本機絕對路徑或個人資訊。使用者說要上傳時才 git push；上傳前要檢查沒有金鑰與個人資訊。
