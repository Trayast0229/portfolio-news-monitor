你要接手一個作品集專案：Portfolio News Monitor（澳股持股組合新聞監測器）。功能都已完成並公開在 GitHub。**現在的階段是「上傳前收尾」**：Codex 審核了還沒 push 的 commit，找到 R1–R6，大部分已修好，剩下幾項小問題修完、跑過 thermo-nuclear review，才能 push。之後的下一階段是**部署上線**，一律照上線標準判斷。

專案位置：這個 repo 的根目錄（portfolio-news-monitor/）

請先完整讀過 docs/HANDOFF.md（特別是開頭的「接手前先看」、第 4 節評分邏輯、第 5 節環境、第 6 節的「Codex 上傳前審核找到、待修」「Codex 檢查找到、待修」「已知但不修」「上線前必做」、第 7 節除錯技巧與 `/verify`、第 9 節工作習慣與 pstack 流程）與 docs/WORKFLOW.md。需要設計細節時再讀 docs/superpowers/specs/2026-10-21-portfolio-news-monitor-design.md。要了解某個修正的來龍去脈，用 `git log` 看 commit 訊息。

讀完後請做這些事：
1. 用 `lsof -ti tcp:8000` 和 `lsof -ti tcp:5173` 確認使用者的前後端是否在執行。沒有的話請使用者用 VS Code 的 Start app 任務啟動，或照 HANDOFF.md 第 5 節啟動。
2. 執行後端 pytest 和前端 npm test，確認全部通過，記下測試數量作為起點（上次結束時：後端 184、前端 57）。
3. 用 `git status --short` 確認沒有未 commit 的改動，用 `git log origin/main..HEAD --oneline` 確認還沒 push 的 commit（上次結束時有 26 個）。
4. 用繁體中文向使用者簡短回報狀態，然後建議下一步（見下方「目前進度」）。

目前進度（2026-11-03）：
- 上一輪 Codex 檢查找到 C1–C10：C1、C2、C3、C4、C6、C8 已修；C5、C10 低優先、不影響上線，留在待修；C7、C9 列為不修。
- 上傳前 Codex 審核找到 R1–R6：R1（還沒 push 的歷史裡有個人描述）已用改寫歷史處理，本機留有備份分支 `backup-before-r1`，**push 成功後提醒使用者可以刪掉**；R2（gzip 尾端資料吃記憶體）、R3（`/verify` cleanup 可能關錯程式）已修；R5 列為不修。
- **下一步依序是**：
  1. `/pstack:tdd 修第 R4 項：HTML 註解裡的 meta charset 讓正確的編碼標頭失效`
  2. `/pstack:tdd 修第 R6 項：/verify 的 cdp.mjs 在 Chrome 分頁當掉時永遠等待`
  3. 跑一次 `/pstack:thermo-nuclear-review`。
  4. 使用者說「push」才上傳；上傳前再檢查一次沒有金鑰、本機絕對路徑與個人資訊（包括 commit 訊息）。
- 之後回到第 6 節「上線前必做」：第一步是改寫訪客會看到的開發者提示（`App.tsx` 的 `EngineNote`、`ResultPanel.tsx` 提到 Claude 的那句），上線版預設只勾 FinBERT。較大改動先給計畫，使用者說「可以開始」再動手。

工作流程（HANDOFF.md 第 9 節有完整說明）：
- 每個 bug 由使用者依序觸發：`/pstack:tdd 修第 N 項：…` → 使用者看改動、在瀏覽器測 → `/pstack:blast-radius` → （可省略）`/code-review low` → 使用者說「commit」。每一步做完就停下來等，不要自己往下走。
- tdd：先寫會失敗的測試並引用失敗內容（要是預期的那種失敗，不是程式出錯），再修，跑全部測試，再用真實程式或真實連線重跑重現腳本。
- blast-radius：找出改動安全的那一個關鍵事實，用腳本比對新舊版（`git show HEAD:檔案` 存成舊版來比）或真實連線證明，不要只寫推論。
- 使用者說「commit」時：同一個 commit 裡更新 HANDOFF.md 第 6 節（待修移到「已完成」、更新測試數），檢查沒有本機路徑、金鑰與個人描述後再 commit。
- 使用者會請 Codex（在使用者電腦上跑的多代理 agent）找 bug 或審核，Codex 只找問題、寫重現，不修。使用者要 Codex 的 prompt 時，照之前的格式寫：只讀、不改 repo、重現腳本放 `/tmp/` 下的專用資料夾、證據標準、多代理分工與交叉驗證、嚴重度、報告格式與編號（避開已用過的 C、R）。Codex 報告回來後，先讀它的腳本確認安全，再用真實程式全部重跑，重新評嚴重度，給使用者表格與建議順序，等使用者決定。
- 畫面相關的改動可以用 `/verify`（`.claude/skills/verify/`）自己在無頭 Chrome 操作網站：它開在 8100／5174／9223，Claude 預設關閉，用完一定要跑 `cleanup.sh`，不碰使用者的 8000／5173。仍要給使用者瀏覽器測試步驟（要做什麼、修好的樣子、沒修好的樣子）。
- 使用者希望省 token：不自己開子代理，不用 arena、interrogate、thermos 等多模型指令，回覆簡短。
- 先重現再判定是 bug；「怎樣才算對」不明確時，先說明取捨並給建議，等使用者決定。
- 找到但不打算馬上修的問題，記到 HANDOFF.md 第 6 節「已知但不修」。

重要提醒：
- 使用者用繁體中文溝通，網站介面是英文。說明要白話，給的指令要能直接貼上執行。
- 後端一律用 backend/.venv（Python 3.13）。系統 Python 3.15 跑不了 PyTorch。終端機是 zsh：陣列、`${!arr[@]}` 這類 bash 語法要用 `bash <<'EOF'` 包起來。
- backend/.env 裡有 ANTHROPIC_API_KEY，絕對不要印出或複述。上線版不放 key、不開 Claude（使用者決定）。
- 給上線訪客看的訊息不能提 port、終端機這類開發者資訊。
- 沒有使用者同意前，不要改變評分公式的語意。
- repo 是公開的：commit 的檔案與 commit 訊息不要寫入本機絕對路徑、對使用者的個人描述、信箱或金鑰。使用者說要上傳時才 git push。
