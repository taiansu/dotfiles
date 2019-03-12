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

# Open another tab of same directory
alias n="open -a iTerm ."
alias re="repeat"
alias oa="open -a"

function tagjs() {
  find . -type f -iregex ".*\.js$" -not -path "./node_modules/*" -exec jsctags {} -f \; | sed '/^$/d' | sort > tags
}

# git
if type "hub" > /dev/null; then
  alias g="hub"
else
  alias g="git"
fi
