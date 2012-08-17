#!/bin/sh
DOTFILES=~/.dotfiles

warn() {
    echo "$1" >&2
}

die() {
    warn "$1"
    exit 1
}

[ -e "$DOTFILES" ] && die "$DOTFILES already exists."

git clone git://github.com/taiansu/dotfiles.git "$DOTFILES"
cd "$DOTFILES"

./link-dotfiles.sh

echo "dotfiles succeffully linked"
