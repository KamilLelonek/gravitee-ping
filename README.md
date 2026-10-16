# Gravitee APIM ping stack

`make up` creates a local Kubernetes cluster, installs Gravitee API Management (Community Edition) and a small backend, and exposes `GET /ping` on the Gravitee gateway. The response body is `pong`. `make down` removes everything.

## Prerequisites

| Tool | Tested version | Notes |
|---|---|---|
| Docker | 29.8 (Docker Desktop, macOS) | Give Docker at least 4 CPUs and 6 GB of memory. |
| k3d | 5.9.0 | Runs Kubernetes (k3s) inside Docker. |
| kubectl | 1.37 | 1.31 or newer is required. |
| Helm | 4.3 | |
| make, curl, openssl | system versions | Present on macOS; on Linux install `make` if missing. |

Port 443 on 127.0.0.1 must be free. The first run pulls about 2 GB of images. Measured on an Apple Silicon Mac: the stack requests 1.6 CPU and 2.5 GB, and uses about 3.9 GB of memory when idle.

## Run and test

```sh
make up       # about 4 to 5 minutes the first time, under 30 seconds after that
make ping     # fails unless GET /ping returns exactly "pong"
make status   # pods, API status, certificate status
make down     # deletes the cluster
```

The same call by hand. The certificate is signed by a local CA that `make up` exports:

```sh
curl --cacert .certs/ca.crt https://localhost/ping                # pong
curl --cacert .certs/ca.crt -X POST https://localhost/ping -i     # 404: only GET is exposed
```

The Gravitee Console runs at https://localhost/console (user `admin`, password `admin`). The browser warns about the certificate until you trust `.certs/ca.crt` or accept the warning.

Gateway metrics, in Prometheus format:

```sh
kubectl --context k3d-gravitee -n gravitee port-forward svc/apim-gateway 18082:18082
curl -u admin:adminadmin http://localhost:18082/_node/metrics/prometheus
```

## Architecture

```
host (macOS / Linux)       curl --cacert .certs/ca.crt https://localhost/ping   ->  pong
   |  127.0.0.1:443, mapped by k3d to the cluster's load balancer
+-- k3d cluster "gravitee" (1 node, k3s) ------------------------------------------+
|  ns kube-system     traefik             TLS termination, routes by path           |
|  ns cert-manager    cert-manager        local CA -> ClusterIssuer "local-ca"      |
|  ns gravitee        mongodb             API definitions and gateway state         |
|                     apim-api            Management API                            |
|                     apim-ui             Console, served under /console            |
|                     apim-gateway x2     serves /                                  |
|                     gko                 Gravitee Kubernetes Operator              |
|  ns pong            nginx x2            GET /ping -> "pong"                       |
|                     NetworkPolicy       accepts traffic from the gateway only     |
+-----------------------------------------------------------------------------------+
```

A request goes `curl -> Traefik (TLS) -> gateway -> API "/ping" -> pong`.

The API itself is a Kubernetes resource, `manifests/ping-api.yaml`. Its configuration takes this path: the operator reads the `ApiV4Definition` and pushes it to the Management API, the Management API stores it in MongoDB, and every gateway replica picks it up from MongoDB on its sync cycle. The gateway never calls the Management API to serve traffic. If the Management API stops, the gateway keeps serving the APIs it has loaded.

`make up` runs `scripts/up.sh`, which installs in this order: cluster, cert-manager and the local CA, MongoDB, the operator, APIM, the backend, the API. Every step waits for the previous one, and running it again changes nothing.

## Choices and alternatives

| Choice | Alternatives considered | Why this one |
|---|---|---|
| Full APIM with the Gravitee Kubernetes Operator | DB-less gateway; creating the API with a REST script | Matches "deploy APIM" literally and keeps the API as code. DB-less has no Management API or Console. A REST script is imperative and has to handle "already exists" on re-runs. |
| k3d | kind, minikube | Light, starts fast, maps a host port in one line, and ships Traefik, a load balancer and a NetworkPolicy controller. minikube needs `minikube tunnel` in a second terminal. |
| Traefik (bundled with k3s) | ingress-nginx, Gravitee gateway terminating TLS itself | Already in the cluster and maintained. ingress-nginx is archived. Terminating TLS on the gateway would leave the Console reachable only through port-forward. |
| Paths on `localhost` | Host names such as `console.localhost` | `*.localhost` does not resolve in Safari or for the macOS system resolver. |
| cert-manager with a local CA | Static certificate in the repo, mkcert | Issues and renews certificates automatically. The leaf certificate lives 24 hours and is renewed 8 hours before expiry, so renewal happens daily. In production only the issuer changes, to ACME. |
| Makefile calling a POSIX shell script | helmfile, Flux | No extra tool to install. The operator creates its CRDs at startup, so the script has to wait for them between steps, which a plain script does clearly. |
| MongoDB 8.0 standalone | PostgreSQL through JDBC, MongoDB replica set | MongoDB is Gravitee's default repository. 8.0 is the newest version Gravitee tests. A replica set is listed below. |
| nginx-unprivileged with a config map | A custom app image | No image to build or push. The body is exactly `pong`, without a trailing newline. |

## Assumptions

- Everything is reached on `localhost`. There is no DNS name.
- The Community Edition defaults are acceptable for a local demo: admin user `admin/admin` and technical API user `admin/adminadmin`.
- Analytics are not needed, so Elasticsearch is not installed. The Console's analytics pages stay empty.
- The Developer Portal is not needed and is disabled.
- `GET /ping` means only GET. Other methods get 404 from the gateway.
- Docker runs as root (Docker Desktop or the standard Linux daemon). Rootless Docker cannot bind port 443.
- Built and tested on macOS. Linux is covered by using POSIX `sh`, `openssl` for base64 and no GNU-only flags, but it was not run on a Linux machine.

## Monitoring: what I would watch

The gateway exposes Prometheus metrics on its technical port, 18082, behind basic auth. A Prometheus Operator `ServiceMonitor` with `basicAuth` would scrape it. The metrics are per gateway instance, labelled by status code, method and listening port. I would watch:

- Error ratio: `http_server_requests_total` with `code=~"5.."` against all requests, on port 8082.
- Latency: `http_server_response_time_seconds` gives a sum, a count and a max. Average and max are available as is; percentiles would need histogram buckets enabled.
- Load: `http_server_active_connections` and `http_server_active_requests`.
- JVM: `jvm_memory_used_bytes` against the 512 MB heap, and `jvm_gc_pause_seconds`.
- Pod restarts and readiness, from Kubernetes itself.
- Certificate expiry, from cert-manager's own metrics.

Per-API numbers and errors such as a lost MongoDB connection are not in these metrics. They come from the analytics reporter and the gateway logs, which this setup does not ship anywhere.

## Before production

1. Replace both default admin credentials and keep secrets in an external manager, for example External Secrets with Vault.
2. Put the Console and the Management API behind SSO and on an internal entrypoint, separate from public API traffic.
3. Run MongoDB as a replica set with backups and a dedicated application user, or use a managed service.
4. Use several nodes with pod anti-affinity, and scale the gateway with a HorizontalPodAutoscaler.
5. Add an analytics reporter (Elasticsearch or OpenSearch), Redis for rate limiting, and a Prometheus and Grafana stack with alerts.
6. Add CI that runs `helm template` and `kubeconform`, pin images by digest, and write the upgrade and rollback procedure.
7. Use a real DNS name with an ACME issuer.

## Left out within the time box

- Elasticsearch and analytics: the heaviest component, and optional in the brief.
- Developer Portal: not needed to serve `/ping`.
- Changing the default admin passwords: needs a bcrypt hash and secret wiring. It is item 1 above.
