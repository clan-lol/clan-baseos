#! /bin/sh

# create temp dir and ensure it is always cleaned
trap 'clean_temp_dir' EXIT
temp_dir=$(mktemp -d)

clean_temp_dir() {
  rm -rf "$temp_dir"
}

is_installed() {
  name=$1
  if [ -n "$(command -v "$name")" ]; then
    return 0
  else
    return 1
  fi
}

install_nix() {
  if is_installed curl; then
    curl --proto '=https' --tlsv1.2 -sSf -L \
        https://install.determinate.systems/nix \
      > "$temp_dir"/install_nix.sh
  elif is_installed wget; then
    wget -qO- \
        https://install.determinate.systems/nix \
      > "$temp_dir"/install_nix.sh
  else
    echo "Either curl or wget is required to install Nix. Exiting."
    exit 1
  fi
  NIX_INSTALLER_DIAGNOSTIC_ENDPOINT="" sh "$temp_dir"/install_nix.sh install
}

ask_then_install_nix() {
  echo "Clan requires Nix to be installed. Would you like to install it now? (y/n)"
  read -r response
  if [ "$response" = "y" ]; then
    install_nix
  else
    echo "Clan cannot run without Nix. Exiting."
    exit 1
  fi
}

ensure_nix_installed() {
  if ! is_installed nix; then
    ask_then_install_nix
  fi
}

start_clan_gui() {
  PATH="${PATH:+$PATH:}/nix/var/nix/profiles/default/bin" \
    exec nix run \
      https://git.clan.lol/clan/clan-core/archive/main.tar.gz#clan-app \
      --no-accept-flake-config \
      --extra-experimental-features "flakes nix-command" -- "$@"
}

main() {
  ensure_nix_installed
  start_clan_gui "$@"
}

main "$@"
