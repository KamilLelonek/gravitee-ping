#!/bin/sh
# Builds the whole stack. Safe to re-run: every step converges to the same state.
set -eu
cd "$(dirname "$0")/.."

CONTEXT=k3d-gravitee

# Keep Helm repositories inside the project so the user's Helm setup is neither read nor changed.
export HELM_REPOSITORY_CONFIG="$PWD/.helm/repositories.yaml"
export HELM_REPOSITORY_CACHE="$PWD/.helm/cache"

log() { printf '\n==> %s\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
cluster_kubectl() { kubectl --context "$CONTEXT" "$@"; }
cluster_helm() { helm --kube-context "$CONTEXT" "$@"; }

log "Checking prerequisites"
for tool in docker k3d kubectl helm curl openssl; do
  command -v "$tool" >/dev/null 2>&1 || fail "$tool is not installed (see README)"
done
docker info >/dev/null 2>&1 || fail "the Docker daemon is not running"
kubectl wait --help 2>/dev/null | grep -q -- '--for=create' || fail "kubectl 1.31 or newer is required"

log "Creating the k3d cluster"
if ! k3d cluster list gravitee >/dev/null 2>&1; then
  port_check=0
  curl --silent --output /dev/null --max-time 2 http://127.0.0.1:443 || port_check=$?
  [ "$port_check" -eq 7 ] || fail "port 443 on 127.0.0.1 is already in use"
  k3d cluster create --config k3d.yaml
fi
cluster_kubectl -n kube-system wait --for=create deployment/traefik --timeout=180s
cluster_kubectl -n kube-system rollout status deployment/traefik --timeout=180s

