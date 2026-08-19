## Structure

```
.
├── AGENTS.md
├── agents
│   ├── dot-omp
│   │   └── agent
│   │       ├── config.yml
│   │       └── no-superpowers.yml
│   └── dot-pi
│       └── agent
│           ├── extensions
│           │   └── exit-alias.ts
│           └── settings.json
├── cli
│   └── dot-config
│       ├── btop
│       │   └── btop.conf
│       ├── cabal
│       │   └── config
│       ├── herdr
│       │   ├── config.toml
│       │   └── plugins
│       │       └── config
│       │           ├── cloudmanic.herdr-plus
│       │           │   └── quick-actions/
│       │           └── herdr.collie
│       │               └── dot-env.example
│       ├── lazygit
│       │   └── config.yml
│       ├── mactop
│       │   └── config.json
│       ├── superfile
│       │   ├── config.toml
│       │   ├── hotkeys.toml
│       │   └── theme/
│       └── tidewave
│           └── app.toml
├── dev
│   ├── dot-agignore
│   ├── dot-credo.exs
│   ├── dot-ctags
│   ├── dot-gemrc
│   ├── dot-gnuplot
│   ├── dot-iex.exs
│   └── dot-local
│       └── bin
│           └── rust
├── dotfiles_backup/
├── editors
│   └── dot-config
│       └── zed
│           ├── keymap.json
│           └── settings.json
├── git-prompt.zsh
├── git
│   ├── dot-config
│   │   └── git
│   │       └── ignore
│   ├── dot-gitconfig
│   └── dot-gitignore
├── homebrew
│   └── dot-Brewfile
├── justfile
├── macos
│   └── dot-config
│       └── karabiner
│           └── karabiner.json
├── mise
│   ├── dot-asdfrc
│   ├── dot-config
│   │   └── mise
│   │       └── config.toml
│   ├── dot-default-gems
│   ├── dot-default-mix-commands
│   └── dot-default-npm-packages
├── patches
│   └── peon-ping
│       └── omp-notification-lifecycle.patch
├── shell
│   ├── dot-config
│   │   └── zsh
│   │       └── aliasrc
│   ├── dot-local
│   │   └── libexec
│   │       └── dotfiles
│   │           ├── fzf-git.sh
│   │           ├── fzf_listoldfiles.sh
│   │           ├── vimr_wait.sh
│   │           └── zoxide_openfiles_nvim.sh
│   ├── dot-zprofile
│   ├── dot-zshenv
│   └── dot-zshrc
├── templates
│   └── git-userinfo_template
└── terminal
    └── dot-config
        ├── cmux
        │   └── cmux.json
        ├── ghostty
        │   └── config
        └── kitty
            ├── current-theme.conf
            ├── kitty.app.icns
            └── kitty.conf

## Completion

first execute
```shell
mkdir -p /usr/local/share/zsh/site-functions
```

### mise
```shell
mise completion zsh  > /usr/local/share/zsh/site-functions/_mise
```

### tailscale
```shell
tailscale completion zsh > /usr/local/share/zsh/site-functions/_tailscale
```

## Git FSMonitor

For large repositories, enable Git's built-in filesystem monitor per repository
to speed up `git status` and the Zsh Git prompt:

```shell
cd /path/to/large-repository
git config core.fsmonitor true
```

Do not use `--global`; small repositories such as this dotfiles repository do
not need it. Git starts the filesystem monitor daemon automatically when
needed.

To disable it:

```shell
git config --unset core.fsmonitor
```
