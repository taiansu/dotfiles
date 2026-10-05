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

Homebrew initialization uses the shell CPU architecture: `.zshenv` defines
`x86_64` → `/usr/local` and `arm64` → `/opt/homebrew`; `.zprofile` evaluates
`brew shellenv` only when the selected prefix's `bin/brew` is executable.
Rosetta shells use the x86_64 prefix. Custom Homebrew installation paths are
not detected automatically.

Login shell setup preserves the inherited PATH order, appends missing baseline
paths (`/usr/local/bin`, `/usr/local/sbin`, `/usr/bin`, `/bin`, `/usr/sbin`,
`/sbin`), and keeps the tied Zsh `path`/`PATH` variables unique. Homebrew and
tool-specific initialization can still prepend their paths afterward.
When `~/.local/bin` exists, login shell setup prepends it using
`path_prepend_if_dir`, allowing user-installed and stowed commands to resolve
without adding a nonexistent directory or duplicate entries.

Optional LLVM and cross-compiler paths use the selected `HOMEBREW_PATH` and are
prepended only when their directories exist. Version choices and precedence are
unchanged: `arm-none-eabi-binutils`, `arm-none-eabi-gcc@8`, `avr-binutils`,
`avr-gcc@8`, then `llvm@12`. Missing toolchains are not installed automatically.
PostgreSQL versioned `bin` directories are also resolved under `HOMEBREW_PATH`;
the existing glob ordering and first-match selection are retained, rather than
automatically selecting the newest version.
The macos-trash `bin` directory likewise uses `HOMEBREW_PATH` and is prepended
only when it exists.
Idris 2's `~/.idris2/bin` and `~/.idris2/lib` are checked independently.
Only an existing `bin` directory is added through `path_prepend_if_dir`; an
existing `lib` directory is added to `LD_LIBRARY_PATH` without replacing the
inherited list or inserting duplicate entries.

Interactive Zsh activates mise only when its executable is available on PATH.
It does not assume `~/.local/bin/mise`, so Homebrew installations are also
supported. Missing mise is skipped; shell startup does not install it.
gwx's directory-changing wrapper and completion are likewise loaded only when
`gwx` is available on PATH; missing gwx is skipped without installation.
Login shells source `~/.railway/env` only when it is readable; missing or
unreadable Railway environment files are skipped without installation or login.
OrbStack's `~/.orbstack/shell/init.zsh` is also sourced only when readable.
Missing or unreadable files are skipped; errors from a present initialization
script are not silenced.

Fast syntax highlighting loads only when its plugin file is present, and token
style overrides are applied only after successful sourcing. Missing plugins
are skipped without creating a substitute style array; load errors remain
visible and do not trigger style customization.

Zsh's `compinit` dump is stored at `$XDG_CACHE_HOME/zsh/.zcompdump`, falling back
to `~/.cache/zsh/.zcompdump` when `XDG_CACHE_HOME` is unset or empty. Its parent
directory is created before initialization; `bashcompinit` remains enabled.
Old dumps under HOME or `ZDOTDIR` are left untouched and are no longer loaded.

rustup completion is cached at `$XDG_CACHE_HOME/zsh/completions/rustup.bash`,
falling back to `~/.cache/zsh/completions/rustup.bash` when `XDG_CACHE_HOME` is
unset or empty. Old caches under `~/.config/rustlang/autocomplete` are left
untouched and are no longer loaded.
When rustup is installed and the cache is missing or empty, completion output is
written to a temporary file and published only after successful, nonempty
generation. Every interactive shell loads a readable, nonempty cache through
`bashcompinit`, including when rustup is no longer on PATH.

OMP completion follows the same cache lifecycle at
`$XDG_CACHE_HOME/zsh/completions/omp.zsh`, falling back to
`~/.cache/zsh/completions/omp.zsh` when `XDG_CACHE_HOME` is unset or empty.
Generation requires `omp` on PATH and successful, nonempty output. Readable,
nonempty caches are loaded on every interactive shell startup; missing OMP is
not installed automatically. With a custom cache directory, the old fixed
`~/.cache` completion file is left untouched and is not loaded.

Both completion generators use `_dotfiles_source_completion_cache` in
`.zshrc`. The helper accepts a cache path followed by the generator's argv,
executes that argv directly without `eval`, and shares the safe write/cleanup
and cache-loading behavior.

Shell setup preserves inherited `TERM` and `COLORTERM`; it neither forces
`xterm-256color` nor supplies a `truecolor` declaration when `COLORTERM` is unset.
`GPG_TTY` is updated from `tty` only when stdin is a terminal. Without a
terminal, its inherited value is preserved, or it remains unset.
Home, End, Insert, Delete, Left and Right bindings are installed only when
their terminfo capability is nonempty; basic terminals retain native editing
without empty-key binding errors.

Locale defaults live in `.zshenv`: `LANG` defaults to `en_US.UTF-8` only when
unset or empty. Existing `LANG`, `LC_ALL`, and category-specific `LC_*` values
are preserved; `.zprofile` does not override them.

Shell startup raises the soft open-file limit toward 4096 only when it is lower,
capped by the current hard limit. Higher soft limits and the hard limit itself
are preserved.

Go defaults are supplied only when the variables are unset:
`GOPATH=$XDG_DATA_HOME/go` and `GOBIN=$HOME/.local/bin`. Explicit custom values
and empty strings are preserved.

`XDG_CONFIG_DIRS` defaults to `/etc/xdg` only when unset or empty. Existing
directory lists and their search order are preserved, so nested shells do not
repeatedly prepend `/etc/xdg`.

Erlang shell history is enabled by default through
`ERL_AFLAGS="-kernel shell_history enabled"` only when `ERL_AFLAGS` is unset.
Explicit startup flags, including an empty value or disabled history, are
preserved rather than replaced or extended.

Shell setup does not set `OBJC_DISABLE_INITIALIZE_FORK_SAFETY` globally.
If a specific tool needs this compatibility workaround, scope it to that
command invocation rather than disabling Objective-C fork safety for all
descendant processes. Explicitly inherited values are not overridden.

## Branches

`main` is the development branch. `kaisian` is a curated release branch: it is
the ref the [kaisian](https://kaisian.phx.tw) installer checks out by default
and the branch the web generator reads `.kaisian.json` from. Select
self-contained commits for shared installation behavior; personal agent
settings and machine-specific changes stay on `main` unless explicitly approved
for release. The branches may diverge; do not force-reset `kaisian` to `main`.

Use a separate worktree so publishing does not change the checkout used by
your live Stow symlinks. Set `COMMIT` to an approved `main` commit, then:

```shell
git worktree add ../dotfiles-release kaisian
git -C ../dotfiles-release cherry-pick "$COMMIT"
git push origin main kaisian
git worktree remove ../dotfiles-release
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

Native Zsh history is enabled with or without Atuin. `HISTSIZE` and `SAVEHIST`
are both 100,000; history is stored in `$XDG_CACHE_HOME/shell_history` (normally
`~/.cache/shell_history`), with its parent directory created on shell startup.
History is shared between shells, older duplicate commands are removed, and
leading-space commands are omitted from native history. The leading-space rule
is not a guarantee that other history tools will exclude the same command.

Atuin integration is enabled only when `atuin` is installed. Without it, native
Zsh history bindings remain available. Install with `brew install atuin`, apply
the Stow package, and open a new shell. Existing history is not imported
automatically; optionally import it once:

```shell
HISTFILE="$HISTFILE" atuin import zsh
```

- When Atuin is available, `Ctrl-R` and `Up` open Atuin; `Enter` inserts the
  selected command for editing rather than executing it immediately.
- When fzf is installed and stdout is a terminal, its integration provides
  `Ctrl-T` file search and `Alt-C` directory selection. fzf's `Ctrl-R` binding
  is disabled so Atuin or native Zsh history search remains in control.
  When installed, fd supplies file/directory searches and completion candidates;
  otherwise fzf keeps its built-in search. bat enables file previews and eza
  enables directory-tree previews independently. Missing preview tools are
  skipped instead of being invoked.
  Preview commands are defined once per tool; `_fzf_comprun` selects the
  appropriate preview, builds an argument array, and invokes fzf once, preserving
  caller argument quoting.
- fzf-git uses `Ctrl-G` as a prefix and double `Ctrl-G` for cancellation only
  after its readable plugin script is successfully sourced. Missing or unreadable
  plugins leave native single `Ctrl-G` cancellation unchanged. Load errors remain
  visible and do not trigger these extra key remappings.
- Automatic sync and update checks are disabled; upgrades use Homebrew.
  Login and sync are never initiated by shell setup; manual sync remains possible.
- Atuin's `?` AI binding is disabled.
- Configuration lives in `home/dot-config/atuin/config.toml`; its history database
  is stored in `$XDG_DATA_HOME/atuin` (normally `~/.local/share/atuin`), outside this
  repository. Zsh continues to maintain its own `$HISTFILE`.

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
