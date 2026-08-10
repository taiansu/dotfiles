set shell := ["zsh", "-cu"]
# set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default: homebrew mise vim npm bun omp finish

# 升級 homebrew
homebrew:
    -brew update
    -brew upgrade -y --greedy-latest

# 升級 vim 套件
vim:
    -nvim --headless "+Lazy! sync" +qa
    -nvim --headless -c "autocmd User MasonUpdateAllComplete quitall" -c "MasonUpdateAll"

# 升級 mise
mise:
    -@mise self-update
    -mise plugin update

# 升級 npm global 套件
npm:
    # @npm update -g npm
    -npm update -g

# 升級 bun global 套件
bun:
    -bun update -g

# 設定整個開發環境
bootstrap: ensure-brew install-tools setup-config
      @echo "🎉 Development environment ready!"

# 重新產生 omp 的 zsh 補全快取
omp:
    mkdir -p ~/.cache/zsh/completions
    omp completions zsh > ~/.cache/zsh/completions/omp.zsh

# 安裝／更新 peon-ping、預設音效包及套用本機 OMP adapter patch
peon-ping: ensure-brew
    #!/usr/bin/env bash
    set -euo pipefail
    brew install peonping/tap/peon-ping
    peon-ping-setup
    bash "$(brew --prefix peonping/tap/peon-ping)/libexec/adapters/omp.sh"

    readonly adapter_dir="$HOME/.omp/agent/extensions/peon-ping"
    readonly adapter_file="$adapter_dir/peon-ping.ts"
    readonly patch_file={{quote(justfile_directory())}}/patches/peon-ping/omp-notification-lifecycle.patch

    if [[ ! -f "$adapter_file" ]]; then
        printf 'Error: upstream OMP adapter not found: %s\n' "$adapter_file" >&2
        exit 1
    fi
    if [[ ! -f "$patch_file" ]]; then
        printf 'Error: tracked OMP adapter patch not found: %s\n' "$patch_file" >&2
        exit 1
    fi
    if ! git -C "$adapter_dir" apply --check "$patch_file"; then
        printf 'Error: peon-ping OMP adapter changed upstream; refresh patch: %s\n' "$patch_file" >&2
        exit 1
    fi

    git -C "$adapter_dir" apply "$patch_file"

# 使用環境變數設定 Pushover mobile notification
peon-ping-pushover:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${PUSHOVER_USER_KEY:?Set PUSHOVER_USER_KEY before running this recipe}"
    : "${PUSHOVER_APP_TOKEN:?Set PUSHOVER_APP_TOKEN before running this recipe}"
    peon mobile pushover "$PUSHOVER_USER_KEY" "$PUSHOVER_APP_TOKEN"
    peon mobile test

# 安裝／更新所有 Herdr plugins
herdr-plugins:
    herdr plugin install AltanS/collie --yes
    herdr plugin install cloudmanic/herdr-plus --yes


# 確保 brew 存在，不存在就安裝
[private]
ensure-brew:
    #!/usr/bin/env bash
    if ! command -v brew >/dev/null 2>&1; then
        echo "📦 Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    else
        echo "✓ Homebrew already installed"
    fi

[private]
install-tools: ensure-brew
      brew install git gh fzf fd ripgrep

[private]
setup-config:
      # @# 設定 dotfiles 之類的

[private]
finish:
    @printf '\n%.0s' {1,3}
    @printf '%.s─' $(seq 1 $(tput cols))
    @printf '%.s─' $(seq 1 $(tput cols))
    @printf '\n%.0s' {1,3}
    @fortune | $(just onesay)

[private]
onesay:
    @if command -v pokemonsay >/dev/null 2>&1; then \
        echo pokemonsay; \
    elif command -v cowsay >/dev/null 2>&1; then \
        echo cowsay; \
    else \
        echo echo; \
    fi
