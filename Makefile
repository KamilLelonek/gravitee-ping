.PHONY: up down ping status

# Build the cluster and everything on it, then call /ping.
up:
	sh scripts/up.sh

# Call GET /ping through the gateway; fails unless the body is exactly "pong".
ping:
	sh scripts/ping.sh

# Show pods, the API status and the certificate.
status:
	kubectl --context k3d-gravitee get pods --namespace gravitee
	kubectl --context k3d-gravitee get pods --namespace pong
	kubectl --context k3d-gravitee get apiv4definition,certificate --namespace gravitee

# Delete the cluster and local files.
down:
	k3d cluster delete gravitee
	rm -rf .certs .helm
