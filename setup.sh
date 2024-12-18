#!/bin/zsh

# 設定 dotfiles 目錄和目標目錄
DOTFILES_DIR="$HOME/.dotfiles"
TARGET_DIR="$HOME"

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 檢查 .dotfiles 目錄是否存在
if [[ ! -d "$DOTFILES_DIR" ]]; then
    echo "${RED}Error: $DOTFILES_DIR 目錄不存在${NC}"
    exit 1
fi

# 函數：建立軟連結
create_symlink() {
    local source="$1"
    local target="$2"
    
    # 如果目標已存在且是一般檔案，先備份
    if [[ -f "$target" && ! -L "$target" ]]; then
        mv "$target" "${target}.backup"
        echo "已備份 $target 到 ${target}.backup"
    fi
    
    # 如果軟連結已存在，先移除
    if [[ -L "$target" ]]; then
        rm "$target"
    fi
    
    # 建立軟連結
    ln -s "$source" "$target"
    echo "${GREEN}已建立連結: $target -> $source${NC}"
}

# 主要處理邏輯
echo "開始設定 dotfiles..."

files = [
  "git/gitconfig",
  "git/gitignore",
  "git/githudrc",
  "zsh/zshenv",
  "zsh/zprofile",
  "zsh/zshrc",
]
# 處理所有 dotfiles
for file in files; do
    # 設定目標路徑
    target="$TARGET_DIR/.${file:t}"
    
    # 建立軟連結
    create_symlink "$file" "$target"
done

echo "${GREEN}完成！所有 dotfiles 都已設定。${NC}"
