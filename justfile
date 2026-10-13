set shell := ["zsh", "-cu"]
# set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default: homebrew mise vim npm bun uv omp finish

# Update Homebrew formulae and casks.
homebrew:
    -brew update
    -brew upgrade -y --greedy-latest

# Update Neovim plugins and Mason tools.
vim:
    -nvim --headless "+Lazy! sync" +qa
    -nvim --headless -c "autocmd User MasonUpdateAllComplete quitall" -c "MasonUpdateAll"

# Update mise and its plugins.
mise:
    -@mise self-update
    -mise plugin update

# Update global npm packages.
npm:
    # @npm update -g npm
    -npm update -g

# Update global Bun packages.
bun:
    -bun update -g

# Update uv-managed tools.
uv:
    -uv tool upgrade --all

# Bootstrap basic CLI tools.
bootstrap: ensure-brew install-tools setup-config
      @echo "🎉 Development environment ready!"

# Regenerate the OMP zsh completion cache.
omp:
    mkdir -p ~/.cache/zsh/completions
    omp completions zsh > ~/.cache/zsh/completions/omp.zsh

# Install or update peon-ping with the local OMP adapter patch.
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

# Configure Pushover using credentials supplied via environment variables.
peon-ping-pushover:
    #!/usr/bin/env bash
    set -euo pipefail
    : "${PUSHOVER_USER_KEY:?Set PUSHOVER_USER_KEY before running this recipe}"
    : "${PUSHOVER_APP_TOKEN:?Set PUSHOVER_APP_TOKEN before running this recipe}"
    peon mobile pushover "$PUSHOVER_USER_KEY" "$PUSHOVER_APP_TOKEN"
    peon mobile test

# Install or update Collie and Herdr Plus.
herdr-plugins:
    herdr plugin install AltanS/collie --yes
    herdr plugin install cloudmanic/herdr-plus --yes

# Invoke a Collie action through Herdr.
collie action:
    herdr plugin action invoke {{quote(action)}} --plugin herdr.collie

# Accept Tailscale DNS settings and refresh the macOS DNS cache.
tail-dns-on:
  tailscale set --accept-dns=true
  dscacheutil -flushcache

# Stop accepting Tailscale DNS settings and refresh the macOS DNS cache.
tail-dns-off:
  tailscale set --accept-dns=false
  dscacheutil -flushcache

karabiner_repo := justfile_directory() / "home/dot-config/karabiner/karabiner.json"
karabiner_live := home_directory() / ".config/karabiner/karabiner.json"

# Sync the newer Karabiner file; the app replaces symlinks when saving.
karabiner-sync:
    #!/usr/bin/env bash
    set -euo pipefail
    repo="{{karabiner_repo}}"; live="{{karabiner_live}}"
    if [[ -L "$live" ]]; then rm "$live"; fi
    if [[ ! -e "$live" ]]; then
        install -m 600 "$repo" "$live"; echo "repo → live (live was missing)"; exit 0
    fi
    jq empty "$repo" "$live"
    if (( $(wc -c < "$live") < 1000 )); then
        echo "refusing: live file looks like Karabiner's empty default; run again after fixing it" >&2; exit 1
    fi
    if diff -q <(jq -S . "$repo") <(jq -S . "$live") >/dev/null; then
        echo "in sync"; exit 0
    fi
    if [[ "$live" -nt "$repo" ]]; then
        cp "$live" "$repo"; echo "live → repo"
        git -C "{{justfile_directory()}}" --no-pager diff --stat -- home/dot-config/karabiner/karabiner.json
    else
        install -m 600 "$repo" "$live"; echo "repo → live"
    fi

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
