### fisher
if not functions -q fisher
    set -q XDG_CONFIG_HOME
    or set XDG_CONFIG_HOME ~/.config
    curl https://git.io/fisher --create-dirs -sLo $XDG_CONFIG_HOME/fish/functions/fisher.fish
    fish -c fisher
end

# fisher add laughedelic/pisces rafaelrinaldi/pure franciscolourenco/done jorgebucaran/fish-bax jethrokuan/fzf jethrokuan/z
set fish_greeting

## pure
# set -U pure_symbol_prompt '𝝺'
# set -U pure_color_prompt_on_success $pure_color_light
# set -U pure_color_git_dirty $pure_color_warning
# set -U pure_symbol_git_dirty "₊"
# set -U pure_symbol_title_bar_separator ":"

## Variables
set -x LC_ALL zh_TW.UTF-8
set -x LANG zh_TW.UTF-8

ulimit -n 4096

set -U WORDCHARS '*?[]~=&;!#$%^(){}<>'

set -U EDITOR nvim

set -U ERL_AFLAGS "-kernel shell_history enabled"

# vagrant
set -U VAGRANT_DEFAULT_PROVIDER 'virtualbox'

# FZF
set -U FZF_DEFAULT_COMMAND 'ag -l'

# pisces
set -U pisces_pairs '(,)' '","' '\',\'' '<<,>>'

### Path
set PATH $PATH /usr/local/sbin

#GOPATH
set -U GOPATH $HOME/projects/gocode/bin
set -U GO_CUSTOM_PATH /usr/local/opt/go/libexec/bin

[ -d $GOPATH ]
and set PATH $PATH $GOPATH
[ -d $GO_CUSTOM_PATH ]
and set PATH $PATH $GO_CUSTOM_PATH

# Yarn
# set -U YARN_PATH $HOME/.config/yarn/global/node_modules/.bin
# [ -d $YARN_PATH ]; and set PATH $PATH $YARN_PATH

### functions
function expand-dot-to-parent-directory-path -d 'expand ... to ../.. etc'
    # Get commandline up to cursor
    set -l cmd (commandline --cut-at-cursor)

    # Match last line
    switch $cmd[-1]
        case '*..'
            commandline --insert '/.'
        case '*'
            commandline --insert '.'
    end
end

bind . 'expand-dot-to-parent-directory-path'

function fish_right_prompt
    date "+%T"
    set_color normal
end

# mkcd
function mkcd -d 'create and switch to directory'
    mkdir $argv[1] && cd $argv[1]
end


### aliases

alias cleanOpenWith "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user"

### abbreviations
abbr o "open"

abbr n "tab"

abbr v "nvim"

abbr ll "ls -al"

abbr g "hub"

abbr tl "tail"

# Headless Browsers
abbr chrome "/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome"
abbr firefox "/Applications/Firefox.app/Contents/MacOS/firefox"

# Youtube mp3
abbr youtube-mp3 "youtube-dl --extract-audio --audio-format mp3"

# less
abbr lf "less +F"

# Make unified diff syntax the default
abbr diff "diff -u"

# octal+text permissions for files
abbr perms "stat -c '%A %a %n'"

# bundle & rake
abbr k "rake"
abbr b "bundle"
abbr br "bundle exec rake"

# mix
abbr m "mix"
abbr im "iex -S mix"
abbr imt "env MIX_ENV=test iex -S mix"
abbr imp "env MIX_ENV=prod iex -S mix"

# vagrant
abbr vg "vagrant"

# please
alias please "sudo"

[ -f ~/.iterm2_shell_integration.fish ]
and source ~/.iterm2_shell_integration.fish
[ -f ~/.asdf/asdf.fish ]
and source ~/.asdf/asdf.fish
[ -f /usr/local/share/autojump/autojump.fish ]
and source /usr/local/share/autojump/autojump.fish
