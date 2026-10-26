#!/bin/sh
# Builds the whole stack. Safe to re-run: every step converges to the same state.
set -eu
cd "$(dirname "$0")/.."
# shellcheck source=scripts/common.sh
. scripts/common.sh

CERT_MANAGER_VERSION=v1.21.3
MONGODB_CHART_VERSION=0.20.2
GKO_VERSION=4.12.22
APIM_VERSION=4.12.25

# Keep all Helm state inside the project so the user's Helm setup is neither read nor changed.
export HELM_CACHE_HOME="$PWD/.helm/cache"
export HELM_CONFIG_HOME="$PWD/.helm/config"
export HELM_DATA_HOME="$PWD/.helm/data"

# Creates a random hex Secret in gravitee on the first run only. Piped through stdin, the value
# never appears in a process list; hex keeps it safe inside a URI.
create_random_secret() {
  cluster_kubectl -n gravitee get secret "$1" >/dev/null 2>&1 && return 0
  openssl rand -hex 32 | tr -d '\n' \
    | cluster_kubectl -n gravitee create secret generic "$1" --from-file="$2"=/dev/stdin
}

log "Checking prerequisites"
for tool in docker k3d kubectl helm curl openssl; do
  command -v "$tool" >/dev/null 2>&1 || fail "$tool is not installed (see README)"
done
docker info >/dev/null 2>&1 || fail "the Docker daemon is not running"

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

log "Creating generated credentials (first run only)"
cluster_kubectl create namespace gravitee --dry-run=client -o yaml | cluster_kubectl apply -f -
create_random_secret mongodb-credentials password
create_random_secret apim-jwt-secret secret
password=$(cluster_kubectl -n gravitee get secret mongodb-credentials -o jsonpath='{.data.password}' | openssl base64 -d -A)
printf 'mongodb://admin:%s@mongodb.gravitee.svc:27017/gravitee?authSource=admin' "$password" \
  | cluster_kubectl -n gravitee create secret generic mongodb-uri --from-file=uri=/dev/stdin --dry-run=client -o yaml \
  | cluster_kubectl apply -f -
unset password

log "Installing MongoDB"
cluster_helm upgrade --install mongodb oci://registry-1.docker.io/cloudpirates/mongodb \
  --version "$MONGODB_CHART_VERSION" --namespace gravitee \
  --values values/mongodb.yaml --wait --timeout 5m
cluster_kubectl apply -f manifests/mongodb-network-policy.yaml

log "Installing the Gravitee Kubernetes Operator"
cluster_helm upgrade --install gko gko --repo https://helm.gravitee.io \
  --version "$GKO_VERSION" --namespace gravitee --wait --timeout 5m
# The operator creates its CRDs when it starts, so they may not exist yet.
cluster_kubectl wait --for=create --for=condition=established --timeout=120s \
  crd/managementcontexts.gravitee.io crd/apiv4definitions.gravitee.io

log "Installing Gravitee APIM"
cluster_kubectl apply -f manifests/gravitee-edge.yaml
cluster_helm upgrade --install apim apim --repo https://helm.gravitee.io \
  --version "$APIM_VERSION" --namespace gravitee \
  --values values/apim.yaml --wait --timeout 10m

log "Deploying the pong backend and the ping API"
cluster_kubectl apply -f manifests/pong.yaml
# Right after start, the operator's webhook, or the Management API its dry-run calls, can refuse
# connections for a few seconds. Only those errors are retried; any other error stops the build.
attempt=1
until output=$(cluster_kubectl apply -f manifests/ping-api.yaml 2>&1); do
  case "$output" in
    *"failed calling webhook"* | *"apim-api.gravitee.svc"*"connection refused"*) ;;
    *) printf '%s\n' "$output" >&2; fail "manifests/ping-api.yaml was rejected" ;;
  esac
  [ "$attempt" -lt 10 ] || { printf '%s\n' "$output" >&2; fail "the operator webhook did not answer"; }
  attempt=$((attempt + 1))
  sleep 5
done
printf '%s\n' "$output"
if ! cluster_kubectl -n gravitee wait --for=jsonpath='{.status.processingStatus}'=Completed \
  apiv4definition/ping --timeout=300s; then
  cluster_kubectl -n gravitee get apiv4definition ping \
    -o jsonpath='{.status.conditions[?(@.type=="Accepted")].message}{"\n"}' >&2
  fail "the operator did not publish the ping API"
fi
cluster_kubectl -n gravitee wait --for=condition=Ready certificate/localhost-tls --timeout=120s

log "Exporting the local CA to .certs/ca.crt"
mkdir -p .certs
cluster_kubectl -n cert-manager get secret local-ca -o jsonpath='{.data.ca\.crt}' \
  | openssl base64 -d -A > .certs/ca.crt

log "Calling GET https://localhost/ping"
# The gateway loads a new API on its next sync cycle, a few seconds after the operator reports it.
attempt=1
until sh scripts/ping.sh 2>/dev/null; do
  [ "$attempt" -lt 12 ] || { sh scripts/ping.sh; exit 1; }
  attempt=$((attempt + 1))
  sleep 5
done
