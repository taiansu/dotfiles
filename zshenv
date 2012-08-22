#export CC=/usr/local/bin/gcc-4.2
export PATH="$(rbenv prefix)/bin:/opt/X11/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
if which rbenv > /dev/null; then eval "$(rbenv init -)"; fi
