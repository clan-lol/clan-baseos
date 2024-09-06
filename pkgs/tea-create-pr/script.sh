#!/usr/bin/env bash
set -euo pipefail

remoteFork="${1:-origin}"
remoteUpstream="${2:-upstream}"
targetBranch="${3:-main}"
shift && shift && shift
TMPDIR="$(mktemp -d)"
currentBranch="$(git rev-parse --abbrev-ref HEAD)"
user_unparsed="$(tea whoami)"
user="$(echo "$user_unparsed" | tr -d '\n' | cut -f4 -d' ')"
tempRemoteBranch="$user-$currentBranch"


# Function to check if a remote exists
check_remote() {
  if git remote get-url "$1" > /dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

# Check if the remote 'upstream' is defined
if ! check_remote "$remoteUpstream"; then
  echo "Error: $remoteUpstream remote is not defined."
  echo "Please fork the repository and add the $remoteUpstream remote."
  echo "$ git remote add $remoteUpstream <upstream-url>"
  exit 1
fi

treefmt --fail-on-change --no-cache

upstream_url=$(git remote get-url "$remoteUpstream")
set -x
git fetch "$remoteUpstream" && git rebase "$remoteUpstream"/main --autostash
set +x
repo=$(echo "$upstream_url" | sed -E 's#.*:([^/]+/[^.]+)\.git#\1#')


git log --reverse --pretty="format:%s%n%n%b%n%n" "$remoteUpstream/$targetBranch..HEAD" > "$TMPDIR"/commit-msg


"$EDITOR" "$TMPDIR"/commit-msg

COMMIT_MSG=$(cat "$TMPDIR"/commit-msg)

firstLine=$(echo "$COMMIT_MSG" | head -n1)
rest=$(echo "$COMMIT_MSG" | tail -n+2)

if [[ "$firstLine" == "$rest" ]]; then
  rest=""
fi

git push --force -u "$remoteFork" HEAD:refs/heads/"$tempRemoteBranch"


tea pr create \
  --repo "$repo" \
  --head "$user:$tempRemoteBranch" \
  --title "$firstLine" \
  --description "$rest" \
  "$@"
