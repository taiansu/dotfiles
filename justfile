set shell := ["zsh", "-cu"]
# set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default: homebrew finish

homebrew:
    -brew update
    -brew upgrade --greedy-latest

vim:
    -nvim --headless "+Lazy! sync" +qa
    -nvim --headless "+MasonUpdateAll" +qa

mise:
    -@mise self-update
    -mise plugin update --all

npm:
    # @npm update -g npm
    -npm update -g

_onesay:
    @if command -v pokemonsay >/dev/null 2>&1; then \
        echo pokemonsay; \
    elif command -v cowsay >/dev/null 2>&1; then \
        echo cowsay; \
    else \
        echo echo; \
    fi

finish:
    @printf '\n%.0s' {1,3}
    @printf '%.s─' $(seq 1 $(tput cols))
    @printf '\n%.0s' {1,3}
    @fortune | $(just _onesay)
