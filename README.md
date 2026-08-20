## Structure

`home/` is the only GNU Stow package. Everything else is repository
maintenance and is never installed.

```
.
├── home/                        # stow package: mirrors $HOME
│   ├── dot-Brewfile
│   ├── dot-asdfrc
│   ├── dot-credo.exs
│   ├── dot-ctags
│   ├── dot-default-gems
│   ├── dot-default-mix-commands
│   ├── dot-default-npm-packages
│   ├── dot-gemrc
│   ├── dot-gitconfig
│   ├── dot-gitignore
│   ├── dot-gnuplot
│   ├── dot-iex.exs
│   ├── dot-zprofile
│   ├── dot-zshenv
│   ├── dot-zshrc
│   ├── dot-agents/
│   │   └── AGENTS.md
│   ├── dot-omp/agent/
│   │   ├── config.yml
│   │   └── no-superpowers.yml
│   ├── dot-pi/agent/
│   │   ├── extensions/exit-alias.ts
│   │   └── settings.json
│   ├── dot-local/
│   │   ├── bin/rust
│   │   └── libexec/dotfiles/
│   │       ├── fzf_listoldfiles.sh
│   │       ├── vimr_wait.sh
│   │       └── zoxide_openfiles_nvim.sh
│   └── dot-config/
│       ├── btop/btop.conf
│       ├── cabal/config
│       ├── cmux/cmux.json
│       ├── ghostty/config
│       ├── git/ignore
│       ├── gwx/config.toml
│       ├── herdr/
│       │   ├── config.toml
│       │   └── plugins/config/
│       │       ├── cloudmanic.herdr-plus/quick-actions/
│       │       └── herdr.collie/dot-env.example
│       ├── karabiner/karabiner.json
│       ├── kitty/
│       │   ├── current-theme.conf
│       │   ├── kitty.app.icns
│       │   └── kitty.conf
│       ├── lazygit/config.yml
│       ├── mactop/config.json
│       ├── mise/config.toml
│       ├── superfile/
│       │   ├── config.toml
│       │   ├── hotkeys.toml
│       │   └── theme/
│       ├── tidewave/app.toml
│       ├── zed/
│       │   ├── keymap.json
│       │   └── settings.json
│       └── zsh/aliasrc
├── docs/                        # design notes, plans, migration steps
├── patches/                     # third-party patches applied by justfile
├── templates/                   # machine-local file templates
├── tests/                       # repository tests
├── dotfiles_backup/
├── fzf-git.zsh                  # submodule
├── git-prompt.zsh               # submodule
├── justfile
├── setup.sh
└── README.md
```

## Install

```shell
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding -R home
```

Preview first with `--simulate --verbose`; it lists every `LINK` and aborts on
conflicts without touching the filesystem. `--no-folding` is required so that
`~/.config` and other shared directories stay real directories instead of
becoming symlinks into this repository.

Machine-local files stay outside the package: Git identity in
`~/.config/dotfiles/git-userinfo` (see `templates/git-userinfo_template`) and
shell credentials in `~/.config/dotfiles/credential`.

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
