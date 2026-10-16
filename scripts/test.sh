#!/bin/sh
# Checks the README's claims against the running stack. Run after make up.
set -eu
cd "$(dirname "$0")/.."
# shellcheck source=scripts/common.sh
. scripts/common.sh

check() { printf '%-58s' "$1"; }
curl_exit() {
  status=0
  cluster_kubectl -n "$1" exec "$2" -- curl -s -m 3 -o /dev/null "$3" </dev/null 2>/dev/null || status=$?
  echo "$status"
}
restart_counts() {
  cluster_kubectl get pods -A --no-headers \
    -o custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount | grep -v '^probe-' | sort
}
remove_probes() {
  cluster_kubectl -n gravitee delete pod probe-gateway --ignore-not-found --now >/dev/null
  cluster_kubectl -n pong delete pod probe-other --ignore-not-found --now >/dev/null
}

check "a second make up restarts nothing"
before=$(restart_counts)
sh scripts/up.sh >/dev/null 2>&1 || fail "make up failed"
[ "$before" = "$(restart_counts)" ] || fail "pods were restarted or replaced"
echo ok

check "NetworkPolicies let only Gravitee reach pong and MongoDB"
remove_probes
trap remove_probes EXIT
cluster_kubectl -n gravitee run probe-gateway --restart=Never --image=curlimages/curl:8.16.0 \
  --labels=app.kubernetes.io/name=apim,app.kubernetes.io/component=gateway --command -- sleep 300 >/dev/null
cluster_kubectl -n pong run probe-other --restart=Never --image=curlimages/curl:8.16.0 --command -- sleep 300 >/dev/null
cluster_kubectl -n gravitee wait --for=condition=Ready pod/probe-gateway --timeout=60s >/dev/null
cluster_kubectl -n pong wait --for=condition=Ready pod/probe-other --timeout=60s >/dev/null
# k3s applies policies to a new pod a few seconds after it starts.
sleep 15
# curl exit codes: 0 = answered, 28 = connected but no HTTP reply (MongoDB), 7 = refused.
[ "$(curl_exit gravitee probe-gateway http://pong.pong.svc:8080/ping)" = 0 ] || fail "the gateway cannot reach pong"
[ "$(curl_exit pong probe-other http://pong:8080/ping)" = 7 ] || fail "a non-gateway pod reached pong"
[ "$(curl_exit gravitee probe-gateway telnet://mongodb.gravitee.svc:27017)" = 28 ] || fail "Gravitee cannot reach MongoDB"
[ "$(curl_exit pong probe-other telnet://mongodb.gravitee.svc:27017)" = 7 ] || fail "a non-Gravitee pod reached MongoDB"
echo ok

# Runs after the 15 s wait above, so the gateway has synced any API change from make up.
check "GET /ping returns exactly pong"
sh scripts/ping.sh >/dev/null
echo ok

check "POST /ping is refused by the gateway"
code=$(curl -s -o /dev/null -w '%{http_code}' --cacert .certs/ca.crt -X POST https://localhost/ping)
[ "$code" = 404 ] || fail "expected 404, got $code"
echo ok

check "the TLS certificate is Ready"
cluster_kubectl -n gravitee wait --for=condition=Ready certificate/localhost-tls --timeout=10s >/dev/null
echo ok
