FOLDER = "Code"

c() { cd ~/$FOLDER/$1;  }

_c() { _files -W ~/$FOLDER -/; }
compdef _c c
