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
