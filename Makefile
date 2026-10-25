.PHONY: up down ping test status backup

# Build the cluster and everything on it, then call /ping.
up:
	sh scripts/up.sh

# Call GET /ping through the gateway; fails unless the body is exactly "pong".
ping:
	sh scripts/ping.sh

# Check the README's claims: re-run is a no-op, GET only, TLS, NetworkPolicies.
test:
	sh scripts/test.sh

# Show pods, the API status and the certificate.
status:
	kubectl --context k3d-gravitee get pods --namespace gravitee
	kubectl --context k3d-gravitee get pods --namespace pong
	kubectl --context k3d-gravitee get apiv4definition,certificate --namespace gravitee

# Dump MongoDB to backups/ before an upgrade.
backup:
	sh scripts/backup.sh

# Delete the cluster and local files.
down:
	k3d cluster delete gravitee
	rm -rf .certs .helm
