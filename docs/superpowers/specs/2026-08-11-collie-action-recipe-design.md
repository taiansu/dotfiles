# Collie action recipe 設計

## 問題

目前 `justfile` 有一個尚未提交的 `collie-start` recipe，只能啟動 Collie。使用者希望改用一致的參數形式，例如 `just collie start` 與 `just collie stop`，並能呼叫 Collie 提供的其他 Herdr plugin actions。

## 範圍

將 `collie-start` 替換為單一參數化 recipe：

```just
collie action:
    herdr plugin action invoke {{quote(action)}} --plugin herdr.collie
```

這個 recipe 支援目前及未來所有由 `herdr.collie` 註冊的 action，例如：

```text
just collie start
just collie stop
just collie restart
just collie status
just collie update
just collie url
just collie version
```

## 行為與錯誤處理

- `quote(action)` 讓 action 以單一 shell argument 安全傳入。
- 未提供 `action` 時，由 Just 的必要參數檢查拒絕執行。
- 未知 action、plugin 不可用或 action 執行失敗時，直接保留 Herdr 的錯誤輸出與 exit status。
- 不在 `justfile` 複製 Collie action allowlist；Herdr plugin registry 是 action 名稱的唯一來源，因此新增 action 不需修改 recipe。

## 驗證

1. `just --dry-run collie start` 展開為 `herdr plugin action invoke start --plugin herdr.collie`。
2. `just --dry-run collie stop` 展開為 `herdr plugin action invoke stop --plugin herdr.collie`。
3. `just collie version` 能實際建立 `version` action invocation，證明參數已送到 `herdr.collie`。
4. `just collie` 因缺少 `action` 而非零結束。

## 非目標

- 不新增 `collie-start`、`collie-stop` 等別名。
- 不在 Just 層驗證或維護 action 清單。
- 不改變 Collie、Herdr 或 plugin config。
- 驗證時不實際停止正在執行的 Collie bridge。
