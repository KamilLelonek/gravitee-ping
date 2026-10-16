.PHONY: up down

# Build the cluster and everything on it, then call /ping.
up:
	sh scripts/up.sh

# Delete the cluster and local files.
down:
	k3d cluster delete gravitee
	rm -rf .certs .helm
