export PATH=/usr/local/bin:/usr/local/sbin:$PATH

# GO
export GOPATH=$HOME/Projects/gocode/bin
export GO_CUSTOM_PATH=/usr/local/opt/go/libexec/bin

# [ -d $GOPATH ] && export PATH=$PATH:$GOPATH
# [ -d $GO_CUSTOM_PATH ] && export PATH=$PATH:$GO_CUSTOM_PATH

# Haskell
export HASKELL_INSTALL_PATH=$HOME/.local/bin
[ -d $HASKELL_INSTALL_PATH ] && export PATH=$PATH:$HASKELL_INSTALL_PATH

# ANDROID
export ANDROID_HOME=/usr/local/share/android-sdk
# [ -d $ANDROID_HOME ] && export PATH=$PATH:$ANDROID_HOME

# MONO
export MONO_GAC_PREFIX="/usr/local"
export FrameworkPathOverride=/usr/local/Cellar/mono/5.4.1.6/lib/mono/4.5

# ANACONDA
export ANACONDA_PATH=/usr/local/anaconda3/bin
[ -d $ANACONDA_PATH ] && export PATH=$PATH:$ANACONDA_PATH

# ANSIBLE
export ANSIBLE_NOCOWS=1
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Yarn
export YARN_PATH=$HOME/.local/share/yarn/global/node_modules/.bin
[ -d $YARN_PATH ] && export PATH=$PATH:$YARN_PATH

# Erlang
export ERL_AFLAGS="-kernel shell_history enabled"

# Rust
# export RUST_SRC_PATH=$HOME/Projects/source/rust

function tagjs() {
  find . -type f -iregex ".*\.js$" -not -path "./node_modules/*" -exec jsctags {} -f \; | sed '/^$/d' | sort > tags
}

# git
if type "hub" > /dev/null; then
  alias g="hub"
else
  alias g="git"
fi


# Check if $LANG is badly set as it causes issues
if [[ $LANG == "C"  || $LANG == "" ]]; then
  # >&2 echo "$fg[red]The \$LANG variable is not set. This can cause a lot of problems.$reset_color"
  export LANG=en_US.UTF-8
fi

# autojump
[ -f /usr/local/etc/profile.d/autojump.sh ] && . /usr/local/etc/profile.d/autojump.sh

if [ -n "$INSIDE_EMACS" ]; then
  chpwd() { print -P "\033AnSiTc %d" }
  print -P "\033AnSiTu %n"
  print -P "\033AnSiTc %d"
else
  test -e "${HOME}/.iterm2_shell_integration.zsh" && source "${HOME}/.iterm2_shell_integration.zsh"
fi

if [[ -n $INSIDE_EMACS && $(uname) == 'Darwin' ]]; then
  stty ek
fi

# source homebrew github api token
if [[ -f ~/.homebrew_github_api_token ]]; then
  source ~/.homebrew_github_api_token
fi

# source google-cloud-sdk
if [[ -s /usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.bash.inc ]]; then
  source '/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/path.zsh.inc'
  source '/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/completion.zsh.inc'
fi

if [[ -f ~/.fzf.zsh ]]; then
  source ~/.fzf.zsh

  # Use fd (https://github.com/sharkdp/fd) instead of the default find
  # command for listing path candidates.
  # - The first argument to the function ($1) is the base path to start traversal
  # - See the source code (completion.{bash,zsh}) for the details.
  _fzf_compgen_path() {
    fd --hidden --follow --exclude ".git" . "$1"
  }

  # Use fd to generate the list for directory completion
  _fzf_compgen_dir() {
    fd --type d --hidden --follow --exclude ".git" . "$1"
  }
fi

# asdf
if [[ -f ~/.asdf/asdf.sh ]]; then
  source $HOME/.asdf/asdf.sh
  source $HOME/.asdf/completions/asdf.bash
fi

# zsh-history-substring-search
[[ -s /usr/local/share/zsh-history-substring-search/zsh-history-substring-search.zsh ]] && source /usr/local/share/zsh-history-substring-search/zsh-history-substring-search.zsh

# zsh-syntax-highlighting
[[ -s /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source /usr/local/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

[[ -s /usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source /usr/local/share/zsh-autosuggestions/zsh-autosuggestions.zsh

bindkey "$terminfo[kcuu1]" history-substring-search-up
bindkey "$terminfo[kcud1]" history-substring-search-down

source ~/.dotfiles/aliasrc
