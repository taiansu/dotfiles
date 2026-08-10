# Peon-ping OMP adapter patch 設計

## 問題

Peon-ping 的上游 OMP adapter 將每個 `turn_end` 都映射為 `Stop`。OMP 的單一 prompt 可能包含多個模型回合與工具呼叫，因此同一項工作會產生多次 `task.complete`／`done` 通知。期望行為是只在需要使用者回答、主工作完整停止或工具出錯時通知。

直接修改 `~/.omp/agent/extensions/peon-ping/peon-ping.ts` 會在下一次執行上游 adapter installer 時被覆蓋。Dotfiles 需要保留一份可審查的本地差異，並在每次更新上游後重新套用。

## 目標

- 以 tracked unified diff 保存 OMP adapter 的本地通知語意。
- 每次 `just peon-ping` 更新並安裝上游 adapter 後，自動檢查及套用 patch。
- Patch 與新版上游不相容時立即失敗，不允許靜默略過。
- 主工作只產生一次完成通知；`ask` 與工具錯誤仍能立即通知。

## 非目標

- 不 fork 或複製整份 peon-ping 專案。
- 不追蹤完整的上游 adapter 檔案。
- 不自動解決 patch conflict 或執行三方合併。
- 不修改 peon-ping 的通知音效包、Pushover credentials 或其他個人設定。
- 不變更 OMP 或 peon-ping 的上游 API。

## 儲存結構

新增：

```text
patches/peon-ping/omp-notification-lifecycle.patch
```

Patch 路徑以 adapter 安裝目錄 `~/.omp/agent/extensions/peon-ping` 為工作目錄，目標檔案為 `peon-ping.ts`。Patch 不包含安裝路徑、使用者 home path 或產生時的暫存路徑。

## Adapter 行為差異

Patch 僅保留以下本地差異：

1. `firePeon` 接受可省略的 detail object，並將 `notification_type`、`tool_name` 與 `error` 寫入 payload。
2. 移除 `turn_end → Stop`。Main-only 的 `session_stop` 只標記待完成狀態；其後 `agent_end` 僅在 `willContinue !== true` 時送出 `Stop`。若其他 stop hook 安排 continuation，先清除待完成狀態，避免提早或重複通知；task/subagent 不會收到 `session_stop`，因此其 `agent_end` 不會送出完成通知。
3. 監聽已通過 `tool_call` middleware 的 `tool_execution_start`；只有 main UI 執行 `ask` 且 event args 完整符合 ask schema 時才送出 `Notification / elicitation_dialog`。這會排除 middleware block 與 OMP 為 schema validation failure 合成的 execution-start 事件。
4. `tool_result` error 將實際工具名稱與文字整理為非空 `error`，並把 `tool_name` 正規化為 peon.sh Claude-hook schema 用來路由 `task.error` 的 `Bash` sentinel。
5. 同步更新 adapter 頂端的 event mapping 註解，避免文件與實作分歧。

## 安裝與套用流程

`justfile` 的 `peon-ping` recipe 維持原有 Homebrew 更新及上游 adapter 安裝順序，接著執行：

```text
brew install/update peon-ping
→ peon-ping-setup
→ 執行上游 OMP adapter installer
→ git apply --check tracked patch
→ git apply tracked patch
```

`git apply` 的工作目錄固定為 `~/.omp/agent/extensions/peon-ping`。Patch 路徑由 dotfiles repo 根目錄解析，不依賴呼叫 `just` 時的目前目錄。

套用前必須先執行 `git apply --check`。檢查失敗時 recipe 立即以非零狀態結束，輸出 adapter 路徑與 patch 路徑，且不嘗試 fuzzy apply、三方合併或忽略錯誤。這讓上游語意改動成為明確的人工維護事件。

## 衝突維護流程

當新版上游使 patch 無法套用時：

1. 讀取新版 `peon-ping.ts` 並確認上游是否已原生提供相同行為。
2. 若上游已修正，刪除已不需要的 patch 與套用步驟。
3. 若仍需本地差異，在新版 adapter 的副本上重新實作差異。
4. 以 `git diff --no-index` 產生新的 unified diff，正規化路徑為 `a/peon-ping.ts` 與 `b/peon-ping.ts`。
5. 重新執行完整驗證後提交更新後的 patch。

## 錯誤處理

- 上游 installer 失敗：保留其非零狀態，不執行 patch。
- Adapter 或 patch 不存在：立即失敗並顯示缺少的路徑。
- `git apply --check` 失敗：立即失敗；不執行 `git apply`。
- `git apply` 在成功檢查後仍失敗：立即失敗並保留錯誤輸出。
- Recipe 不設計成可對已 patch 的 adapter 重複執行 `git apply`；每次 recipe 都先由上游 installer 寫入乾淨 adapter，再套用一次。

## 驗證

1. 對上游剛安裝的 adapter 執行 `git apply --check`，結果成功。
2. 套用 patch 後確認 `git apply --reverse --check` 成功，證明完整 patch 已存在。
3. 確認 adapter 不再註冊 `turn_end` 或 `tool_call` 通知，並註冊 `session_stop`、terminal `agent_end` 與 `ask` 的 `tool_execution_start` 通知。
4. 模擬 `session_stop → agent_end(willContinue: true) → session_stop → agent_end(willContinue: false)`，只捕捉一次 `Stop` payload。
5. 啟動 OMP smoke test，確認 extension 可載入且沒有 TypeScript/runtime 載入錯誤。
6. 觸發已開始執行且 schema-valid 的 `ask`，收到一次 `input.required` payload；middleware-blocked 或 schema-invalid 的 `ask` 不通知。
7. 觸發工具錯誤，payload 包含 peon.sh 路由 `task.error` 所需的非空 `error` 與 `tool_name: "Bash"`。
8. 使用刻意不相容的 adapter 副本執行 `git apply --check`，確認流程以非零狀態停止且不修改副本。

## 安全與私密資料

Patch 與 recipe 不讀取、輸出或提交 `config.json` 內的 mobile notification credentials。所有 tracked 檔案只包含公開的 adapter 程式差異與本機無關的相對路徑。
