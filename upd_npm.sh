#!/bin/sh

set -e
set -x

for package in $(npm -g outdated --parseable --depth=0 | cut -d: -f2)
do
  # echo "$package"
  if [[ ! "$package" =~ ^npm.*$ ]]; then
    npm -g install "$package"
  fi
done
