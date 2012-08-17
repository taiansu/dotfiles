#!/bin/sh

#DOTFILES=~/.dotfiles
 DOTFILES=~/Code/dotfiles
OHMYZSH=~/.oh-my-zsh

cd
echo "Linking Zsh files..."
rm .zshrc
rm .zshenv
#ln -s $DOTFILES/zshrc .zshrc
#ln -s $DOTFILES/zshenv .zshenv
#source ~/.zshrc

echo "Linking Git files..."
rm .gitignore
#rm .gitconfig
ln -s $DOTFILES/gitignore .gitignore
#cp $DOTFILES/gitconfig_template .gitconfig

echo "Linking Rails .gemrc & .irbrc..."
rm .gemrc
ln -s $DOTFILES/gemrc .gemrc
ln -s $DOTFILES/irbrc .irbrc

echo "Linking oh-my-zsh custom files..."

if [ -d $OHMYZSH ]; then
  cd ~/.oh-my-zsh/custom
  cp -R $DOTFILES/ohmyzsh_custom/* ./
  source ~/.zshrc
fi

echo "=================================================="
echo "All the files are linked."
echo "Remember to edit the user info in .gitconfig, then you're ready to rock!"
echo "=================================================="
