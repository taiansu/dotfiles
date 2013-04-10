CODE_FOLDER="Code"
c() { cd ~/$CODE_FOLDER/$1;  }
_c() { _files -W ~/$CODE_FOLDER -/; }
compdef _c c

CLOUD_FOLDER="Copy"
o() { cd ~/$CLOUD_FOLDER/$1;  }
_o() { _files -W ~/$CLOUD_FOLDER -/; }
compdef _o o
