# Dotfiles 改為 GNU Stow 結構：搬移與掛載步驟

本文件只處理本機 config 結構調整：把現有檔案搬進 stow package，改掉 4 處 shell 引用，然後用 `stow` 建立 `$HOME` 連結。

- Stow directory：`~/.dotfiles`
- Target：`$HOME`
- 命名慣例：package 內以 `dot-` 開頭的路徑元件，安裝後變成 `$HOME` 的 `.` 開頭路徑
- 未列在下面的檔案（`setup.sh`、`justfile`、`README.md`、`docs/`、`patches/`、`tests/`、`templates/`、`.maintenance/`、`git-prompt.zsh` submodule、各種 lock/backup/release-notes）都不搬；因為 `stow` 只會處理指令中明確列出的 package 名稱。

## 0. 前置

```bash
brew install stow
stow --version | head -1   # 需要 >= 2.3.0（--dotfiles 支援）
cd ~/.dotfiles
```

## 1. 建立 package 目錄

```bash
mkdir -p shell/dot-config/zsh shell/dot-local/libexec/dotfiles
mkdir -p git/dot-config/git
mkdir -p mise/dot-config/mise
mkdir -p terminal/dot-config/ghostty terminal/dot-config/kitty terminal/dot-config/cmux
mkdir -p editors/dot-config/zed
mkdir -p agents/dot-omp/agent agents/dot-pi/agent/extensions agents/dot-claude
mkdir -p cli/dot-config/btop cli/dot-config/mactop cli/dot-config/superfile \
         cli/dot-config/tidewave cli/dot-config/lazygit cli/dot-config/cabal \
         cli/dot-config/herdr/plugins/config
mkdir -p macos/dot-config/karabiner macos/dot-config/paneru
mkdir -p homebrew
mkdir -p dev/dot-local/bin
```

## 2. 搬移檔案

### shell

```bash
git mv zsh/zshrc            shell/dot-zshrc
git mv zsh/zprofile         shell/dot-zprofile
git mv zsh/zshenv           shell/dot-zshenv
git mv zsh/aliasrc          shell/dot-config/zsh/aliasrc
git mv scripts/fzf-git.sh              shell/dot-local/libexec/dotfiles/fzf-git.sh
git mv scripts/fzf_listoldfiles.sh     shell/dot-local/libexec/dotfiles/fzf_listoldfiles.sh
git mv scripts/vimr_wait.sh            shell/dot-local/libexec/dotfiles/vimr_wait.sh
git mv scripts/zoxide_openfiles_nvim.sh shell/dot-local/libexec/dotfiles/zoxide_openfiles_nvim.sh
```

### git

```bash
git mv git/gitconfig        git/dot-gitconfig
git mv git/gitignore        git/dot-gitignore
git mv config/git/ignore    git/dot-config/git/ignore
```

### mise

```bash
git mv config/mise/config.toml       mise/dot-config/mise/config.toml
git mv mise/asdfrc                   mise/dot-asdfrc
git mv mise/default-gems             mise/dot-default-gems
git mv mise/default-mix-commands     mise/dot-default-mix-commands
git mv mise/default-npm-packages     mise/dot-default-npm-packages
```

### terminal

```bash
git mv config/ghostty/config          terminal/dot-config/ghostty/config
git mv config/kitty/kitty.conf        terminal/dot-config/kitty/kitty.conf
git mv config/kitty/current-theme.conf terminal/dot-config/kitty/current-theme.conf
git mv config/kitty/kitty.app.icns    terminal/dot-config/kitty/kitty.app.icns
git mv config/cmux/cmux.json          terminal/dot-config/cmux/cmux.json
```

### editors

```bash
git mv config/zed/settings.json  editors/dot-config/zed/settings.json
git mv config/zed/keymap.json    editors/dot-config/zed/keymap.json
# config/zed/settings_backup.json 不搬（備份檔）
```

### agents

```bash
git mv omp/agent/config.yml           agents/dot-omp/agent/config.yml
git mv omp/agent/no-superpowers.yml   agents/dot-omp/agent/no-superpowers.yml
git mv pi/agent/settings.json         agents/dot-pi/agent/settings.json
git mv pi/agent/extensions/exit-alias.ts agents/dot-pi/agent/extensions/exit-alias.ts
git mv claude_codex_instructions.md   agents/dot-claude/CLAUDE.md
# omp/agent/config.yml.lock、pi/agent/npm/.gitignore 不搬（lock 與隱藏檔）
# AGENTS.md 保留在 repo root；若也想放進 $HOME：
#   cp AGENTS.md agents/dot-omp/agent/AGENTS.md && git add agents/dot-omp/agent/AGENTS.md
```

### cli

```bash
git mv config/btop/btop.conf         cli/dot-config/btop/btop.conf
git mv config/mactop/config.json     cli/dot-config/mactop/config.json
git mv config/superfile/config.toml  cli/dot-config/superfile/config.toml
git mv config/superfile/hotkeys.toml cli/dot-config/superfile/hotkeys.toml
git mv config/superfile/theme        cli/dot-config/superfile/theme
git mv config/tidewave/app.toml      cli/dot-config/tidewave/app.toml
git mv config/lazygit/config.yml     cli/dot-config/lazygit/config.yml
git mv config/cabal/config           cli/dot-config/cabal/config
git mv config/herdr/config.toml      cli/dot-config/herdr/config.toml
git mv config/herdr/plugins/config/cloudmanic.herdr-plus \
       cli/dot-config/herdr/plugins/config/cloudmanic.herdr-plus
# config/herdr/.plugins.lock、release-notes.json、plugins/.../.env.example 不搬
```

### macos

```bash
git mv config/karabiner/karabiner.json macos/dot-config/karabiner/karabiner.json
git mv config/paneru/paneru.toml       macos/dot-config/paneru/paneru.toml
```

### homebrew

```bash
git mv homebrew/Brewfile homebrew/dot-Brewfile
```

### dev

```bash
git mv ctags      dev/dot-ctags
git mv gemrc      dev/dot-gemrc
git mv gnuplot    dev/dot-gnuplot
git mv agignore   dev/dot-agignore
git mv iex.exs    dev/dot-iex.exs
git mv credo.exs  dev/dot-credo.exs
git mv rust       dev/dot-local/bin/rust
```

## 2.5 更新 `.gitignore`

原有忽略規則綁在舊路徑（`config/herdr/...`、`pi/agent/...`）。搬移後這些位置會由 `$HOME` 連結寫入 package 內，需追加對應規則，避免機器本機狀態或 `.env` 被 commit：

```gitignore
cli/dot-config/herdr/plugins.json
cli/dot-config/herdr/.plugins.lock
cli/dot-config/herdr/session-history.json
cli/dot-config/herdr/session.json
cli/dot-config/herdr/plugins/github/
cli/dot-config/herdr/plugins/config/*/.env
cli/dot-config/herdr/plugins/config/*/.env.*
cli/dot-config/herdr/plugins/config/*/serve.out
cli/dot-config/herdr/plugins/config/*/tailscale-managed-handler
cli/dot-config/lazygit/state.yml
editors/dot-config/zed/conversations
editors/dot-config/zed/embeddings
editors/dot-config/zed/prompts
macos/dot-config/karabiner/automatic_backups
agents/dot-omp/agent/config.yml.lock
agents/dot-pi/agent/auth.json
agents/dot-pi/agent/models-store.json
agents/dot-pi/agent/sessions/
agents/dot-pi/agent/skills/
agents/dot-pi/agent/extensions/herdr-agent-state.ts
```

`hashrc` 仍在 ignore 清單內；要使用就直接放 `~/.config/zsh/hashrc`（`--no-folding` 會把 `~/.config/zsh` 建成真實目錄）。

## 3. 修改 shell 內的 4 處引用

`shell/dot-zshrc`

```zsh
# 原本第 17-18 行
source ~/.dotfiles/zsh/aliasrc
[[ -f ~/.dotfiles/zsh/hashrc ]] && source ~/.dotfiles/zsh/hashrc
# 改為
source ${XDG_CONFIG_HOME:-$HOME/.config}/zsh/aliasrc
[[ -f ${XDG_CONFIG_HOME:-$HOME/.config}/zsh/hashrc ]] && source ${XDG_CONFIG_HOME:-$HOME/.config}/zsh/hashrc
```

```zsh
# 原本第 303 行
[[ -f "$HOME/.dotfiles/scripts/fzf-git.sh" ]] && source "$HOME/.dotfiles/scripts/fzf-git.sh"
# 改為
[[ -f "$HOME/.local/libexec/dotfiles/fzf-git.sh" ]] && source "$HOME/.local/libexec/dotfiles/fzf-git.sh"
```

`shell/dot-zshenv`

```zsh
# 原本第 10-11 行
if [[ -f ~/.dotfiles/credential ]]; then
  source ~/.dotfiles/credential
# 改為
if [[ -f ~/.config/dotfiles/credential ]]; then
  source ~/.config/dotfiles/credential
```

第 139 行的 `source ~/.dotfiles/git-prompt.zsh/git-prompt.zsh` 不用改：submodule 仍留在 `~/.dotfiles/git-prompt.zsh`，不屬於任何 package。

## 4. 先讓現有 `$HOME` 檔案讓位

`stow` 遇到已存在的實體檔案會直接報 conflict，不會覆蓋。先把會衝突的搬開：

```bash
for f in ~/.zshrc ~/.zprofile ~/.zshenv ~/.gitconfig ~/.gitignore ~/.ctags ~/.gemrc ~/.gnuplot ~/.agignore ~/.iex.exs ~/.credo.exs ~/.Brewfile; do
  [ -e "$f" ] && [ ! -L "$f" ] && mv "$f" "$f.pre-stow"
done
```

`~/.config/...` 下的既有檔案同理（例如 `mv ~/.config/ghostty/config ~/.config/ghostty/config.pre-stow`）。

## 5. 執行 stow

先預覽（不動檔案）：

```bash
cd ~/.dotfiles
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding --simulate --verbose \
  shell git mise terminal editors agents cli macos homebrew dev
```

確認輸出只有預期的 `LINK` 後，實際安裝：

```bash
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding \
  shell git mise terminal editors agents cli macos homebrew dev
```

常用變化：

```bash
# 只裝核心三個
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding shell git mise

# 檔案增刪後重新套用（同時清掉已消失的舊連結）
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding --compat -R \
  shell git mise terminal editors agents cli macos homebrew dev

# 移除某個 package 的連結
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding -D cli
```

## 6. 輕量驗證

```bash
# 連結指向正確來源
readlink ~/.zshrc                      # → …/.dotfiles/shell/dot-zshrc
readlink ~/.config/zsh/aliasrc         # → …/.dotfiles/shell/dot-config/zsh/aliasrc
readlink ~/.gitconfig                  # → …/.dotfiles/git/dot-gitconfig

# 目錄是真目錄、不是被折疊成單一連結
test -d ~/.config && test ! -L ~/.config && echo config-ok

# 語法與實際啟動
zsh -n ~/.zshrc && echo zshrc-syntax-ok
zsh -i -c 'exit' && echo interactive-ok

# repo 狀態
cd ~/.dotfiles && git status --short
```

`zsh -i -c exit` 沒有 `command not found` 或錯誤訊息即可視為完成。

## 7. 提交

```bash
cd ~/.dotfiles
git add -A
git commit -m "refactor: restructure dotfiles as stow packages"
```

## 回復方式

```bash
cd ~/.dotfiles
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding -D \
  shell git mise terminal editors agents cli macos homebrew dev
# 再把步驟 4 產生的 *.pre-stow 檔改回原名
```
