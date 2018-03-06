export PATH=/usr/local/sbin:$PATH

# GO
export GOPATH=$HOME/projects/gocode/bin
export GO_CUSTOM_PATH=/usr/local/opt/go/libexec/bin

[ -d $GOPATH ] && export PATH=$PATH:$GOPATH

[ -d $GO_CUSTOM_PATH ] && export PATH=$PATH:$GO_CUSTOM_PATH

# ANDROID
export ANDROID_HOME=/usr/local/opt/android-sdk

[ -d $ANDROID_HOME ] && export PATH=$PATH:$ANDROID_HOME

# NODE
# export NODE_PATH=/usr/local/lib/node_modules

# [-d $NODE_PATH ] && export PATH=$PATH:$NODE_PATH

# HASKELL
export HASKELL_PATH=$HOME/Library/Haskell/bin

[ -d $HASKELL_PATH ] && export PATH=$PATH:$HASKELL_PATH

# ANACONDA
export ANACONDA_PATH=/usr/local/anaconda3/bin

[ -d $ANACONDA_PATH ] && export PATH=$PATH:$ANACONDA_PATH

# Yarn
export YARN_PATH=$HOME/.config/yarn/global/node_modules/.bin

[ -d $YARN_PATH ] && export PATH=$PATH:$YARN_PATH

# Erlang
export ERL_AFLAGS="-kernel shell_history enabled"

# export PATH=/usr/local/sbin:$PATH:$GOPATH/bin:$ANDROID_TOOLS:$ANDROID_PLATFORM::$HOME/Library/Haskell/bin:$ANACONDA_PATH
export HOMEBREW_CASK_OPTS="--appdir=/Applications"

# FZF
export FZF_DEFAULT_COMMAND='ag -l'

# Open another tab of same directory
alias n="open -a iTerm ."
alias re="repeat"

function tagjs() {
  find . -type f -iregex ".*\.js$" -not -path "./node_modules/*" -exec jsctags {} -f \; | sed '/^$/d' | sort > tags
}
# git
alias g="git"
