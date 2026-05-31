# Install and Update

`mq-hal` installs as a symlink to this checkout. The scripts do not install
daemons, download models, or manage credentials.

## Install

```bash
git clone https://github.com/MCamner/mq-hal.git ~/mq-hal
cd ~/mq-hal
./install.sh
```

By default this creates:

```text
~/bin/mq-hal -> ~/mq-hal/bin/mq-hal
```

Use a different target directory with:

```bash
MQ_HAL_PREFIX=/usr/local/bin ./install.sh
```

## PATH

Add this to `~/.zshrc` if `~/bin` is not already on PATH:

```bash
export PATH="$HOME/bin:$PATH"
```

Then open a new terminal or run:

```bash
source ~/.zshrc
```

## Shell Completion Notes

There is no generated completion script yet. The stable top-level commands are
listed with:

```bash
mq-hal tools
```

For zsh users, a lightweight helper is:

```bash
alias mqh='mq-hal'
```

## Update

Preview the update command:

```bash
mq-hal update
```

Run the update:

```bash
mq-hal update --confirm
```

The bundled wrapper is equivalent:

```bash
./upgrade.sh
```

## Config Check

Validate local configuration:

```bash
mq-hal config-check
mq-hal config-check --strict
```

`--strict` fails when configured repo paths do not exist.

## Clean Reinstall

```bash
cd ~/mq-hal
./uninstall.sh
cd ..
mv mq-hal mq-hal.bak
git clone https://github.com/MCamner/mq-hal.git ~/mq-hal
cd ~/mq-hal
./install.sh
mq-hal config-check
```

## Uninstall

```bash
cd ~/mq-hal
./uninstall.sh
```

The uninstall script only removes the symlink it owns. It refuses to remove a
regular file at the target path.

## Optional Homebrew Formula Plan

A future Homebrew formula should install the checkout files under Homebrew's
prefix, link `bin/mq-hal`, run `mq-hal config-check` as a caveat, and avoid
starting background services or downloading models.
