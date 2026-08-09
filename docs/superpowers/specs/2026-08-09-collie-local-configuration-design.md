# Collie 本機設定設計

## 問題

Collie 的 launchd LaunchAgent 已載入，但 bridge 持續以 exit code 1 結束。`collie.log` 顯示 `error: bun not found on PATH`。launchd 的預設 `PATH` 是 `/usr/bin:/bin:/usr/sbin:/sbin`，而本機 Bun 由 mise 安裝於 `/Users/tai/.local/share/mise/installs/bun/latest/bin/bun`；Collie 目前的 Bun 搜尋候選路徑不包含 mise。

## 範圍

只修正本機持久化設定，不修改 `config/herdr/plugins/github/herdr.collie-1edf0e1e987e` 內會在外掛更新時被覆蓋的程式碼，也不準備上游 patch。

## 設定

在 Herdr 的 Collie 設定目錄 `config/herdr/plugins/config/herdr.collie/.env` 寫入：

```dotenv
BUN_INSTALL=/Users/tai/.local/share/mise/installs/bun/latest
COLLIE_TRUSTED_USER=taiansu@gmail.com
COLLIE_PUBLIC_HOSTS=tai-macbook-m5.neko-hake.ts.net
```

- `BUN_INSTALL` 讓 `collie-ctl.sh` 在 launchd 的最小環境中解析到 `${BUN_INSTALL}/bin/bun`。
- `COLLIE_TRUSTED_USER` 僅允許指定的 Tailscale 登入身分操作 Collie。
- `COLLIE_PUBLIC_HOSTS` 將 Host header 限制為目前的 MagicDNS 名稱。
- `.env` 權限設為 `0600`，符合 Collie 對可能包含私密金鑰之設定檔的預期。

## 啟動流程

執行已安裝 checkout 的 `scripts/collie-ctl.sh restart`。控制腳本會先載入 `.env`，重新產生並 bootstrap `~/Library/LaunchAgents/herdr.collie.plist`，launchd 再以同一設定目錄執行 `_exec-bridge`。

## 驗證

1. `collie-ctl.sh status` 顯示 bridge 正在回應，且 launchd 狀態為 active。
2. `launchctl print gui/$(id -u)/herdr.collie` 顯示執行中 PID 與成功啟動狀態。
3. `http://127.0.0.1:8787` 回傳 HTTP 成功狀態。
4. `https://tai-macbook-m5.neko-hake.ts.net` 經 Tailscale Serve 回傳 HTTP 成功狀態。
5. `collie-ctl.sh logs` 不再新增 `bun not found on PATH`，並顯示 bridge listening 訊息。

## 非目標

- 不修改 Collie 上游的 launchd plist 產生方式。
- 不變更連接埠、Serve 模式、Herdr socket 或多 session 行為。
- 不設定 Web Push、反向代理或公開網路存取。
