set shell := ["zsh", "-cu"]
# set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default: homebrew finish

# 升級 homebrew
homebrew:
    -brew update
    -brew upgrade -y --greedy-latest

# 升級 vim 套件
vim:
    -nvim --headless "+Lazy! sync" +qa
    -nvim --headless "+MasonUpdateAll" +qa

# 升級 mise
mise:
    -@mise self-update
    -mise plugin update --all

# 升級 npm global 套件
npm:
    # @npm update -g npm
    -npm update -g

# 設定整個開發環境
bootstrap: ensure-brew install-tools setup-config
      @echo "🎉 Development environment ready!"


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
