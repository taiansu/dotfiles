#!/bin/sh

DOTFILES=~/.dotfiles
BACKUPFILES=dotfiles_backup
OHMYZSH=~/.oh-my-zsh

cd
echo "Linking Zsh files..."
mv .zshrc $DOTFILES/$BACKUPFILES/zshrc.bk
mv .zshenv $DOTFILES/$BACKUPFILES/zshenv.bk
ln -s $DOTFILES/zshrc .zshrc
ln -s $DOTFILES/zshenv .zshenv
source ~/.zshrc

echo "Linking Git files..."
mv .gitignore $DOTFILES/$BACKUPFILES/gitignore.bk
mv .gitconfig $DOTFILES/$BACKUPFILES/gitconfig.bk
cp $DOTFILES/gitconfig.template $DOTFILES/gitconfig
ln -s $DOTFILES/gitignore .gitignore
ln -s $DOTFILES/gitconfig .gitconfig

echo "Linking Rails .gemrc & .irbrc..."
mv .gemrc $DOTFILES/$BACKUPFILES/gemrc.bk
mv .irbrc $DOTFILES/$BACKUPFILES/irbrc.bk
ln -s $DOTFILES/gemrc .gemrc
ln -s $DOTFILES/irbrc .irbrc

echo "Linking tmux.conf"
mv .tmux.conf $DOTFILES/$BACKUPFILES/tmux.conf.bk
ln -s $DOTFILES/tmux.conf .tmux.conf

echo "Copying oh-my-zsh custom files..."

if [ -d $OHMYZSH ]; then
  cd ~/.oh-my-zsh/custom
  cp -R $DOTFILES/ohmyzsh_custom/* ./
  source ~/.zshrc
fi

echo "=================================================="
echo "All the files are linked."
echo "Remember to edit the user info in .gitconfig, then you're ready to rock!"
echo "=================================================="
