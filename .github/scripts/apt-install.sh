#!/usr/bin/env bash
# Install Ubuntu packages on a GitHub-hosted runner, depending on the Ubuntu
# mirrors as little as the packages allow.
#
#   usage: bash .github/scripts/apt-install.sh PACKAGE...
#
# A package the runner image already has is left as it is: when every one is
# there, no apt-get runs at all, so no mirror outage, slow download or index
# fetch reaches the job. (The ubuntu-24.04 image has gfortran, gcc, make and
# jq; `apt-get install` of them only said "already the newest version".)
#
# Otherwise `apt-get update` and `apt-get install` of the missing packages
# run, up to three times, 30 s and then 60 s apart, but no attempt starts
# more than APT_INSTALL_BUDGET seconds (240) after the script did. That
# retries an error that comes back fast: a 503 answered at once, an index
# that fails its hash check while a mirror syncs (`apt-get update` exits 0
# on an index it could not fetch at all, and the next attempt fetches it
# again). apt's own three retries of a download are 1, 2 and 4 s apart
# (Acquire::Retries, 3 by default since apt 2.3). It does not ride out a
# long outage: there one attempt takes minutes, apt waiting for each mirror
# of the runner's list to time out (about 4 min for the Python 3.11 pytest
# job on 2026-11-19, when security.ubuntu.com answered 503 and
# azure.archive.ubuntu.com could not be reached), so the step fails after
# one or two attempts (an attempt that ends after 210 s is the last) rather
# than spending more runner minutes in the same outage.
# Against such an outage what helps is needing nothing from the mirrors,
# the first rule.
set -uo pipefail

budget=${APT_INSTALL_BUDGET-240}
case "$budget" in
  '' | *[!0-9]*)
    echo "apt-install: APT_INSTALL_BUDGET must be a number of seconds, not '$budget'" >&2
    exit 2 ;;
esac

if [ "$#" -eq 0 ]; then
  echo "usage: $0 PACKAGE..." >&2
  exit 2
fi

missing=()
for pkg in "$@"; do
  # "ii " is installed and configured; anything else (not installed, removed
  # with its configuration kept, half-installed) is installed again.
  status=$(dpkg-query -W -f='${db:Status-Abbrev}' "$pkg" 2>/dev/null || true)
  if [ "$status" != "ii " ]; then
    missing+=("$pkg")
  fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  echo "apt-install: the image has $*; nothing to install"
  dpkg-query -W "$@"
  exit 0
fi

echo "apt-install: installing ${missing[*]}"
pauses=(30 60)
attempt=1
while :; do
  if sudo apt-get update && sudo apt-get install -y --no-install-recommends "${missing[@]}"; then
    dpkg-query -W "$@"
    exit 0
  fi
  pause=${pauses[$((attempt - 1))]:-}
  if [ -z "$pause" ]; then
    echo "::error::apt-install: ${missing[*]} not installed; attempt $attempt, the last, failed at $SECONDS s"
    exit 1
  fi
  if [ $((SECONDS + pause)) -gt "$budget" ]; then
    echo "::error::apt-install: ${missing[*]} not installed; attempt $attempt failed at $SECONDS s, and no attempt starts after $budget s"
    exit 1
  fi
  echo "::warning::apt-install: attempt $attempt failed at $SECONDS s; trying again in $pause s"
  sleep "$pause"
  attempt=$((attempt + 1))
done
