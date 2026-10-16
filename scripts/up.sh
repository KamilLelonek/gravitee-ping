#!/bin/sh
# Builds the whole stack. Safe to re-run: every step converges to the same state.
set -eu
cd "$(dirname "$0")/.."

CONTEXT=k3d-gravitee
CERT_MANAGER_VERSION=v1.21.2
MONGODB_CHART_VERSION=0.20.0
GKO_VERSION=4.12.22

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

log "Installing cert-manager and the local certificate authority"
cluster_helm upgrade --install cert-manager cert-manager --repo https://charts.jetstack.io \
  --version "$CERT_MANAGER_VERSION" --namespace cert-manager --create-namespace \
  --values values/cert-manager.yaml --wait --timeout 5m
cluster_kubectl apply -f manifests/cluster-issuer.yaml
cluster_kubectl wait --for=condition=Ready clusterissuer/local-ca --timeout=120s

log "Creating MongoDB credentials (generated on the first run only)"
cluster_kubectl create namespace gravitee --dry-run=client -o yaml | cluster_kubectl apply -f -
if ! cluster_kubectl -n gravitee get secret mongodb-credentials >/dev/null 2>&1; then
  # Hex keeps the password URI-safe. Piped through stdin, it never appears in a process list.
  openssl rand -hex 24 | tr -d '\n' \
    | cluster_kubectl -n gravitee create secret generic mongodb-credentials --from-file=password=/dev/stdin
fi
password=$(cluster_kubectl -n gravitee get secret mongodb-credentials -o jsonpath='{.data.password}' | openssl base64 -d -A)
printf 'mongodb://admin:%s@mongodb.gravitee.svc:27017/gravitee?authSource=admin' "$password" \
  | cluster_kubectl -n gravitee create secret generic mongodb-uri --from-file=uri=/dev/stdin --dry-run=client -o yaml \
  | cluster_kubectl apply -f -
unset password

log "Installing MongoDB"
cluster_helm upgrade --install mongodb oci://registry-1.docker.io/cloudpirates/mongodb \
  --version "$MONGODB_CHART_VERSION" --namespace gravitee \
  --values values/mongodb.yaml --wait --timeout 5m

log "Installing the Gravitee Kubernetes Operator"
cluster_helm upgrade --install gko gko --repo https://helm.gravitee.io \
  --version "$GKO_VERSION" --namespace gravitee --wait --timeout 5m
# The operator creates its CRDs when it starts, so they may not exist yet.
cluster_kubectl wait --for=create --for=condition=established --timeout=120s \
  crd/managementcontexts.gravitee.io crd/apiv4definitions.gravitee.io

