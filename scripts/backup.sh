#!/bin/sh
# Writes a MongoDB dump to backups/. The password goes through a file inside
# the pod, so it never appears in a process list or in the API audit log.
set -eu
cd "$(dirname "$0")/.."
# shellcheck source=scripts/common.sh
. scripts/common.sh

mkdir -p backups
file="backups/mongodb-$(date +%Y%m%d-%H%M%S).archive"
# shellcheck disable=SC2016 # expands inside the pod
cluster_kubectl -n gravitee exec mongodb-0 -c mongodb -- sh -c '
  umask 077
  printf "password: %s\n" "$MONGO_INITDB_ROOT_PASSWORD" > /tmp/dump.yaml
  mongodump --quiet --config /tmp/dump.yaml --username "$MONGO_INITDB_ROOT_USERNAME" --authenticationDatabase admin --archive
  status=$?
  rm -f /tmp/dump.yaml
  exit $status' > "$file" || { rm -f "$file"; fail "mongodump failed"; }
echo "$file"
