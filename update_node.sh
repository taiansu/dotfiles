#!/bin/bash
source $(brew --prefix nvm)/nvm.sh
newest_version="$(nvm version-remote node)"
current_version="$(nvm version node)"

if [[ $newest_version != $current_version ]]; then
    echo "New version found, update from $current_version to $newest_version"
    $(nvm install node --reinstall-packages-from=$current_version)
    echo "Remove old version $current_version"
    $(nvm use node && nvm uninstall $current_version)
else
    echo "The current version $current_version is update to date."
fi
