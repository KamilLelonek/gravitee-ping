# Gravitee APIM ping stack

`make up` creates a local Kubernetes cluster, installs Gravitee API Management (Community Edition) and a small backend, and exposes `GET /ping` on the Gravitee gateway. The response body is `pong`. `make down` removes everything.

Diagrams, design reasoning and the production plan: https://kamillelonek.github.io/gravitee-ping-guide/

## Prerequisites

| Tool | Tested version | Notes |
|---|---|---|
| Docker | 29.8 (Docker Desktop, macOS) | At least 4 CPUs and 6 GB of memory. |
| k3d | 5.9.0 | |
| kubectl | 1.37 | 1.31 or newer. |
| Helm | 4.3 | |
| make, curl, openssl | system versions | |

Port 443 on 127.0.0.1 must be free. The first run pulls about 2 GB of images.

## Run and test

```sh
make up       # 3 to 5 minutes the first time, under 30 seconds after that
make ping     # fails unless GET /ping returns exactly "pong"
make test     # about 35 s: re-run is a no-op, GET only, TLS ready, NetworkPolicies hold
make status   # pods, API status, certificate status
make backup   # MongoDB dump to backups/
make down     # deletes the cluster
```

By hand, trusting the local CA that `make up` exports:

```sh
curl --cacert .certs/ca.crt https://localhost/ping                # pong
curl --cacert .certs/ca.crt -X POST https://localhost/ping -i     # 404: only GET is exposed
```

Console: https://localhost/console (`admin` / `admin`).

Gateway metrics:

```sh
kubectl --context k3d-gravitee -n gravitee port-forward svc/apim-gateway 18082:18082
curl -u admin:adminadmin http://localhost:18082/_node/metrics/prometheus
```

## Choices

- Full APIM with the Gravitee Kubernetes Operator, so the API is a Kubernetes resource in git.
- k3d, because it ships Traefik and a NetworkPolicy controller.
- Traefik for TLS and routing by path; ingress-nginx is archived.
- cert-manager with a local CA, so certificates renew by themselves.
- A Makefile and a POSIX shell script, no extra tools.

## Assumptions

- Everything is on `localhost`, with no DNS name.
- Two default logins stay: Console `admin/admin`, gateway technical API `admin/adminadmin`.
- No Elasticsearch, so the Console's analytics pages stay empty. No Developer Portal.
- `GET /ping` means only GET.
- Docker runs as root; rootless Docker cannot bind port 443.
- Tested on macOS and in an Ubuntu 24.04 container on the same Docker engine.

## What to watch

- 5xx ratio of `http_server_requests_total`, and `http_server_response_time_seconds`.
- `jvm_memory_used_bytes` against the 512 MB heap.
- Pod restarts and certificate expiry.

## Before production

- Replace the default logins, put the Console behind SSO, keep secrets in a vault.
- MongoDB replica set with scheduled backups.
- Several nodes and an autoscaler for the gateway.
- Analytics, rate limiting, alerts and central logs.
- CI checks, images pinned by digest, GitOps.
