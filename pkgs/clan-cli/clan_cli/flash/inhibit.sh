#!/usr/bin/env bash

# A function to log error messages
log_fatal() {
  echo "FATAL: $*" >&2
}

# A function to log warning messages
log_warning() {
  echo "WARNING: $*" >&2
}


# Function to enable inhibition (pause automounting)
enable_inhibition() {
  local devices=("$@")

  if ! command -v udevadm &> /dev/null; then
    log_fatal "udev is required to disable automounting"
    exit 1
  fi

  if [ "$EUID" -ne 0 ]; then
    log_fatal "Root privileges are required to disable automounting"
    exit 1
  fi

  local rules_dir="/run/udev/rules.d"
  mkdir -p "$rules_dir"

  for device in "${devices[@]}"; do
    local devpath="$device"
    local rule_file="$rules_dir/90-udisks-inhibit-${devpath//\//_}.rules"
    echo 'SUBSYSTEM=="block", ENV{DEVNAME}=="'"$devpath"'*", ENV{UDISKS_IGNORE}="1"' > "$rule_file"
    sync
  done

  udevadm control --reload
  udevadm trigger --settle --subsystem-match=block
}

# Function to disable inhibition (cleanup)
disable_inhibition() {
  local devices=("$@")
  local rules_dir="/run/udev/rules.d"
  
  for device in "${devices[@]}"; do
    local devpath="$device"
    local rule_file="$rules_dir/90-udisks-inhibit-${devpath//\//_}.rules"
    rm -f "$rule_file" || log_warning "Could not remove file: $rule_file"
  done

  udevadm control --reload || log_warning "Could not reload udev rules"
  udevadm trigger --settle --subsystem-match=block || log_warning "Could not trigger udev settle"
}

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 [enable|disable] /dev/sdX ..."
  exit 1
fi

action=$1
shift
devices=("$@")

case "$action" in
  enable)
    enable_inhibition "${devices[@]}"
    ;;
  disable)
    disable_inhibition "${devices[@]}"
    ;;
  *)
    echo "Invalid action: $action"
    echo "Usage: $0 [enable|disable] /dev/sdX ..."
    exit 1
    ;;
esac