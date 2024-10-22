{
  writeShellScriptBin,
  coreutils,
  openssh,
  rsync,
  lib,
  docs,
}:

writeShellScriptBin "deploy-docs" ''
  set -eu -o pipefail
  export PATH="${
    lib.makeBinPath [
      coreutils
      openssh
      rsync
    ]
  }"

  #########################################
  #                                       #
  # DO NOT PRINT THE SSH KEY TO THE LOGS  #
  #                                       #
  #########################################
  tmpdir=$(mktemp -d)
  trap "rm -rf $tmpdir" EXIT

  if [ -n "$SSH_HOMEPAGE_KEY" ]; then
    echo "$SSH_HOMEPAGE_KEY" > "$tmpdir/ssh_key"
    chmod 600 "$tmpdir/ssh_key"
    sshExtraArgs="-i $tmpdir/ssh_key"
  else
    sshExtraArgs=
  fi
  set -x
  ###########################
  #                         #
  #    END OF DANGER ZONE   #
  #                         #
  ###########################

  rsync \
    -e "ssh -o StrictHostKeyChecking=no $sshExtraArgs" \
    -a ${docs}/ \
    www@clan.lol:/var/www/docs.clan.lol

  if [ -e ./ssh_key ]; then
    rm ./ssh_key
  fi
''
