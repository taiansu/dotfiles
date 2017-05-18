# go
export GOPATH=$HOME/projects/gocode

# ANDROID
export ANDROID_HOME=/usr/local/opt/android-sdk

# NODE
export NODE_PATH=/usr/local/lib/node_modules:/Users/tai/.asdf/shims

export PATH=/usr/local/sbin:$PATH:$GOPATH/bin:/usr/local/opt/go/libexec/bin:$ANDROID_TOOLS:$ANDROID_PLATFORM:$HOME/.config/yarn/global/node_modules/.bin:$HOME/Library/Haskell/bin
export HOMEBREW_CASK_OPTS="--appdir=/Applications"

# Open another tab of same directory
alias n="open -a iTerm ."
alias re="repeat"

function tagjs() {
  find . -type f -iregex ".*\.js$" -not -path "./node_modules/*" -exec jsctags {} -f \; | sed '/^$/d' | sort > tags
}
# git
alias g="git"
