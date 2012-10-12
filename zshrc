# CCL_DEFAULT_DIRECTORY="/Applications/Clozure\ CL.app/Contnts/Resources/ccl/scripts"

# Path to your oh-my-zsh configuration.
ZSH=$HOME/.oh-my-zsh

# Set name of the theme to load.
# Look in ~/.oh-my-zsh/themes/
# Optionally, if you set this to "random", it'll load a random theme each
# time that oh-my-zsh is loaded.
ZSH_THEME="mh"
setopt extended_glob
setopt INTERACTIVE_COMMENTS
unsetopt correct_all

# Aliases
source ~/.dotfiles/aliases.conf
alias rake="noglob rake"

# Set to this to use case-sensitive completion
# CASE_SENSITIVE="true"

# Comment this out to disable weekly auto-update checks
# DISABLE_AUTO_UPDATE="true"

# Uncomment following line if you want to disable colors in ls
# DISABLE_LS_COLORS="true"

# Uncomment following line if you want to disable autosetting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment following line if you want red dots to be displayed while waiting for completion
# COMPLETION_WAITING_DOTS="true"

# Which plugins would you like to load? (plugins can be found in ~/.oh-my-zsh/plugins/*)
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
plugins=(autojump codefolder git-flow heroku node npm osx rails3 taskwarrior textmate)

source $ZSH/oh-my-zsh.sh

typeset -A abbreviations
abbreviations=(
	"Im"    "| more"
        "Ia"    "| awk"
        "Ig"    "| grep"
        "Ieg"   "| egrep"
        "Iag"   "| agrep"
        "Igr"   "| groff -s -p -t -e -Tlatin1 -mandoc"
        "Ip"    "| $PAGER"
        "Ih"    "| head"
        "Ik"    "| keep"
        "It"    "| tail"
        "Is"    "| sort"
        "Iv"    "| ${VISUAL:-${EDITOR}}"
        "Iw"    "| wc"
        "Ix"    "| xargs"

	"HEAD^"     "HEAD\\^"
	"HEAD^^"    "HEAD\\^\\^"
	"HEAD^^^"   "HEAD\\^\\^\\^"
	"HEAD^^^^"  "HEAD\\^\\^\\^\\^\\^"
	"HEAD^^^^^" "HEAD\\^\\^\\^\\^\\^"
)

magic-abbrev-expand () {
	local MATCH
	LBUFFER=${LBUFFER%%(#m)[-_a-zA-Z0-9^]#}
	LBUFFER+=${abbreviations[$MATCH]:-$MATCH}
}

magic-abbrev-expand-and-insert () {
	magic-abbrev-expand
	zle self-insert
}

magic-abbrev-expand-and-accept () {
	magic-abbrev-expand
	zle accept-line
}

no-magic-abbrev-expand () {
	LBUFFER+=' '
}

zle -N magic-abbrev-expand
zle -N magic-abbrev-expand-and-insert
zle -N magic-abbrev-expand-and-accept
zle -N no-magic-abbrev-expand
bindkey "\r"  magic-abbrev-expand-and-accept # M-x RET はできなくなる
bindkey "^J"  accept-line # no magic
bindkey " "   magic-abbrev-expand-and-insert
bindkey "."   magic-abbrev-expand-and-insert
bindkey "^x " no-magic-abbrev-expand

# export EDITOR="/usr/local/Cellar/emacs/24.1/Emacs.app/Contents/MacOS/Emacs"
# Customize to your needs...
export CC=/usr/local/bin/gcc-4.2
