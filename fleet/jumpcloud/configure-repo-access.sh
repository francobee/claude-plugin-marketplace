#!/usr/bin/env bash
# JumpCloud command (runs as root): give the console user read-only git access to the marketplace repo.
# The PAT arrives ONLY as the JumpCloud secret env var JC_CLAUDE_REPO_PAT at run time — it is never stored in this repo,
# and the credential is scoped to the single marketplace repo URL (fine-grained PAT, contents:read).
set -euo pipefail
REPO_SLUG="francobee/claude-plugin-marketplace"

if [ -z "${JC_CLAUDE_REPO_PAT:-}" ]; then
  echo "HEALTH FAIL [FLEET-007] Repo credential missing on the device (JC_CLAUDE_REPO_PAT was not provided to the configure command)"
  exit 56
fi
CUSER="$(stat -f%Su /dev/console)"
UHOME="$(dscl . -read "/Users/$CUSER" NFSHomeDirectory | awk '{print $2}')"
CRED_DIR="$UHOME/.config/claude-marketplace"
CRED_FILE="$CRED_DIR/git-credentials"

mkdir -p "$CRED_DIR"
umask 077
printf 'https://x-access-token:%s@github.com/%s\n' "$JC_CLAUDE_REPO_PAT" "$REPO_SLUG" > "$CRED_FILE"
chown -R "$CUSER" "$CRED_DIR"
chmod 600 "$CRED_FILE"
sudo -u "$CUSER" -H git config --global "credential.https://github.com/$REPO_SLUG.helper" "store --file=$CRED_FILE"
sudo -u "$CUSER" -H git config --global "credential.https://github.com/$REPO_SLUG.useHttpPath" "true"
echo "configure-repo-access: credential installed for $REPO_SLUG (user $CUSER)"
