## Structure

`home/` is the base GNU Stow package and one `prompt-*` package supplies the
shell prompt layout. Everything else is repository maintenance and is never
installed.

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
│       ├── atuin/config.toml
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
│       └── zsh/
│           ├── aliasrc
│           └── prompt-engine.zsh  # async git status (gitstatus); calls prompt_git_render
├── prompt-default/              # stow package: one prompt layout, pick exactly one
│   └── dot-config/zsh/prompt.zsh
├── prompt-pure/                 #   … same shape for pure, bracketed, nerd-font,
├── prompt-bracketed/            #   jetpack, tokyo-night
├── prompt-nerd-font/
├── prompt-jetpack/
├── prompt-tokyo-night/
├── .kaisian.json                # manifest for kaisian.phx.tw: groups, fonts, tools, features
├── docs/                        # design notes, plans, migration steps
├── patches/                     # third-party patches applied by justfile
├── templates/                   # machine-local file templates
├── tests/                       # repository tests
├── dotfiles_backup/
├── fzf-git.zsh                  # submodule
├── justfile
├── setup.sh
└── README.md
```

## Install

```shell
stow --dir "$HOME/.dotfiles" --target "$HOME" --dotfiles --no-folding -R home prompt-default
```

`home` is always stowed; exactly one `prompt-*` package goes with it. Switch
layouts by restowing a different one (`stow -D prompt-default; stow prompt-pure`).
[kaisian](https://kaisian.phx.tw) reads `.kaisian.json` and does the same from a
generated one-line command; when a font is chosen it writes
`~/.config/ghostty/kaisian.conf`, which `home/dot-config/ghostty/config` includes.

Preview first with `--simulate --verbose`; it lists every `LINK` and aborts on
conflicts without touching the filesystem. `--no-folding` is required so that
`~/.config` and other shared directories stay real directories instead of
becoming symlinks into this repository.

Machine-local files stay outside the package: Git identity in
`~/.config/dotfiles/git-userinfo` (see `templates/git-userinfo_template`),
shell credentials in `~/.config/dotfiles/credential`, and shell overrides in
`~/.config/zsh/local.zsh`, which `.zshrc` sources before the prompt when present.
`PROMPT_CHAR` set there replaces the input marker in every `prompt-*` layout:

```shell
echo 'PROMPT_CHAR=❯' > ~/.config/zsh/local.zsh
```

## Karabiner-Elements

`home/dot-config/karabiner/` is excluded from Stow (`home/.stow-local-ignore`):
Karabiner saves its config atomically and replaces a symlink with a real file.
The repository copy and the live file are kept equal by `just karabiner-sync`,
which copies whichever is newer over the other (and refuses to import
Karabiner's empty default config). Run it after editing in the GUI or in the
repository.

```shell
just karabiner-sync
```

## Shell history

Atuin manages local history search in Zsh. Install it with `brew install atuin`,
apply the Stow package, and open a new shell. Import existing Zsh history once:

```shell
HISTFILE="$HISTFILE" atuin import zsh
```

- `Ctrl-R` and `Up` open Atuin; `Enter` inserts the selected command for editing
  rather than executing it immediately.
- fzf still provides `Ctrl-T` file search and `Alt-C` directory selection.
- Automatic sync and update checks are disabled; upgrades use Homebrew.
- Atuin's `?` AI binding is disabled.
- Configuration lives in `home/dot-config/atuin/config.toml`; history stays in
  `$XDG_DATA_HOME/atuin` (normally `~/.local/share/atuin`), outside this repository.
  Zsh continues to maintain its original `$HISTFILE`.

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
