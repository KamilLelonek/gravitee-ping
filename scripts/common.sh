# Shared by up.sh and test.sh. Every cluster call names the context, so the
# user's current context (possibly a real cluster) is never touched.
CONTEXT=k3d-gravitee
log() { printf '\n==> %s\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }
cluster_kubectl() { kubectl --context "$CONTEXT" "$@"; }
cluster_helm() { helm --kube-context "$CONTEXT" "$@"; }
