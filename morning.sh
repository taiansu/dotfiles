#!/bin/sh

# function countdown
# {
#         local SECONDS=$1
#         local START=$(date +%s)
#         local END=$((START + SECONDS))
#         local CUR=$START

#         while [[ $CUR -lt $END ]]
#         do
#                 CUR=$(date +%s)
#                 LEFT=$((END-CUR))

#                 printf "\r%01d" \
#                         $((LEFT%60))

#                 sleep 1
#         done
#         echo "        "
# }

# countdown '5'

echo 'updating Homebrew...'
brew update
echo 'upgrading Homebrew...'
brew upgrade
brew cleanup
echo 'updating node plugins'
npm update -g
echo 'updating vim plugins...'
vim -s ~/Code/vimrc/update_plugins.vim
echo 'updating prezto'
cd ~/.zprezto
git stash -u
git pull
git stash pop

