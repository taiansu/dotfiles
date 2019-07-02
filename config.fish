### fisher
if not functions -q fisher
    set -q XDG_CONFIG_HOME; or set XDG_CONFIG_HOME ~/.config
    curl https://git.io/fisher --create-dirs -sLo $XDG_CONFIG_HOME/fish/functions/fisher.fish
    fish -c fisher
end

# fisher add laughedelic/pisces rafaelrinaldi/pure franciscolourenco/done jorgebucaran/fish-bax jethrokuan/fzf jethrokuan/z

## pure
set -U pure_symbol_prompt '𝝺'

## Variables
set -U WORDCHARS '*?[]~=&;!#$%^(){}<>'

set -U EDITOR nvim

set -U ERL_AFLAGS "-kernel shell_history enabled"

# vagrant
set -U VAGRANT_DEFAULT_PROVIDER 'virtualbox'

# FZF
set -U FZF_DEFAULT_COMMAND 'ag -l'

## z
set -U Z_CMD "j"

### Path

#GOPATH
set -U GOPATH $HOME/projects/gocode/bin
set -U GO_CUSTOM_PATH /usr/local/opt/go/libexec/bin

[ -d $GOPATH ]; and set PATH $PATH $GOPATH
[ -d $GO_CUSTOM_PATH ]; and set PATH $PATH $GO_CUSTOM_PATH

# Yarn
# set -U YARN_PATH $HOME/.config/yarn/global/node_modules/.bin
# [ -d $YARN_PATH ]; and set PATH $PATH $YARN_PATH

### aliases
alias v "nvim"

alias ll "ls -al"

alias g "git"

alias tl "tail"

# Headless Browsers
alias chrome "/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome"
alias firefox "/Applications/Firefox.app/Contents/MacOS/firefox"

# Youtube mp3
alias youtube-mp3 "youtube-dl --extract-audio --audio-format mp3"

# less
alias lf "less +F"

# Make unified diff syntax the default
alias diff "diff -u"

# octal+text permissions for files
alias perms "stat -c '%A %a %n'"

#clean open_with
alias cleanOpenWith "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user"

# bundle & rake
alias k "rake"
alias b "bundle"
alias br "bundle exec rake"

# mix
alias m "mix"
alias im "iex -S mix"

# [ -f /usr/local/share/autojump/autojump.fish ]; and source /usr/local/share/autojump/autojump.fish
[ -f ~/.iterm2_shell_integration.fish ]; and source ~/.iterm2_shell_integration.fish
[ -f ~/.asdf/asdf.fish ]; and source ~/.asdf/asdf.fish
