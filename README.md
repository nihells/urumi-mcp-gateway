<div align="center">

# Urumi MCP Gateway

### One gateway. Multiple MCP servers. Team-wide AI tools.

A Kubernetes-hosted WooCommerce platform with a custom **Model Context Protocol (MCP)** server, a unified gateway, team access controls, audit logging, and an AI chat interface.

**Urumi AI FDE Internship — Round 1 Assignment**

![Kubernetes](https://img.shields.io/badge/Kubernetes-Kind%20%7C%20k3s-326CE5?logo=kubernetes&logoColor=white)
![Helm](https://img.shields.io/badge/Deployments-Helm-0F1689?logo=helm&logoColor=white)
![Python](https://img.shields.io/badge/Backend-Python%20%7C%20FastAPI-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react&logoColor=black)
![MCP](https://img.shields.io/badge/Protocol-MCP%20Streamable%20HTTP-6B46C1)

</div>

---

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
- [WooCommerce MCP Tools](#woocommerce-mcp-tools)
- [External MCP Client](#external-mcp-client)
- [Security and Access Control](#security-and-access-control)
- [API Overview](#api-overview)
- [Deployment Configuration](#deployment-configuration)
- [Testing and Validation](#testing-and-validation)
- [System Design](#system-design)
- [Threat Model](#threat-model)
- [Limitations and Future Improvements](#limitations-and-future-improvements)

## Overview

**Urumi MCP Gateway** provides a unified access point for multiple Model Context Protocol (MCP) servers. Instead of configuring each upstream server independently, clients can discover and invoke available tools through one gateway.

WooCommerce is the primary business integration. A custom MCP server exposes product and order operations, while additional demo MCP servers demonstrate multi-server aggregation. A React dashboard provides user access and an AI chat experience backed by a FastAPI service.

### Project goals

- Integrate WooCommerce product and order operations through MCP.
- Aggregate tools from multiple upstream MCP servers behind one gateway.
- Provide administrator and member access with individual gateway API keys.
- Record tool-call activity for traceability.
- Deploy application components using Kubernetes and provide Helm configuration for local and production-like environments.

## Architecture

```mermaid
flowchart TB
    Admin[Administrator]
    Member[Team Member]
    Client[External MCP Client]
    UI[React Dashboard]
    Chat[AI Chat]
    API[FastAPI Backend and MCP Gateway]
    Audit[(Audit Log and Application Database)]

    subgraph Cluster[Kubernetes namespace: urumi]
        WP[WordPress and WooCommerce]
        DB[(MariaDB with Persistent Storage)]
        WooMCP[WooCommerce MCP Server]
        Utility[Utility MCP Server]
        Text[TextTools MCP Server]
    end

    Admin --> UI
    Member --> UI
    UI --> API
    Chat --> API
    Client -->|Gateway endpoint and user API key| API
    API <--> WooMCP
    API <--> Utility
    API <--> Text
    WooMCP <-->|WooCommerce REST API| WP
    WP --> DB
    API --> Audit
```

### Request lifecycle

1. A dashboard user or external MCP client authenticates with the gateway.
2. The gateway discovers tools exposed by enabled upstream servers.
3. Each tool is identified with a server namespace, for example `woocommerce__list_products`.
4. The backend applies authorization checks and routes the request.
5. The upstream tool executes the operation and returns a result.
6. The gateway records relevant details, including user, server, tool, duration, and outcome.

## Features

### Gateway and integrations

- A unified MCP endpoint for connecting to multiple upstream MCP servers.
- A custom WooCommerce MCP server using Streamable HTTP.
- Product and order operations through the WooCommerce REST API.
- Namespaced tool names to distinguish tools from different servers.
- Additional demo MCP servers for aggregation and routing.

### Dashboard and access

- React dashboard with a FastAPI backend.
- Administrator and member accounts.
- Individual gateway API-key creation, listing, and revocation.
- AI chat interface for asking questions and invoking available tools.
- Audit records for gateway tool calls.

### Infrastructure

- Kubernetes manifests for application components.
- Helm chart for WordPress and MariaDB.
- Separate local and production-like Helm values.
- Persistent storage configuration and health checks where configured.

## Repository Structure

```text
urumi-mcp-gateway/
├── backend/                 # FastAPI backend, auth, gateway, chat, audit
├── frontend/                # React dashboard
├── woo-mcp-server/          # Custom WooCommerce MCP server
├── demo-mcp-servers/        # Additional MCP server implementations
├── helm/
│   ├── woo-platform/        # WooCommerce Helm chart and templates
│   └── values/
│       ├── values-local.yaml
│       └── values-prod.yaml
├── k8s/                     # Kubernetes manifests
├── docs/                    # Supporting design and security documents
├── tests/                   # Automated tests
├── kind-config.yaml         # Local Kind configuration
├── backend-openapi.json     # Exported backend OpenAPI specification
├── test_woo_auth.py         # WooCommerce authentication test
├── .gitignore
└── README.md
```

## Technology Stack

| Area | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, Vite |
| MCP | Streamable HTTP |
| Store platform | WordPress, WooCommerce |
| Database | MariaDB for WooCommerce; SQLite for local gateway persistence |
| Containers | Docker |
| Orchestration | Kubernetes, Kind |
| Deployment templates | Helm |
| Integration | WooCommerce REST API |

## Getting Started

These instructions describe the local development workflow. Verify that resource names, image tags, Secret keys, and values match the checked-in configuration before running commands.

### Prerequisites

- Docker Desktop
- `kubectl`
- Kind
- Helm
- Python versions compatible with each service's declared dependencies
- Node.js and npm
- Git

The commands below use Windows Command Prompt (CMD), unless stated otherwise.

### 1. Create or reuse the Kind cluster

From the repository root:

```cmd
kind create cluster --name urumi-local --config kind-config.yaml
```

If the cluster already exists, reuse it:

```cmd
kubectl cluster-info --context kind-urumi-local
```

Create the application namespace if it does not already exist:

```cmd
kubectl create namespace urumi
```

If the namespace already exists, continue.

### 2. Configure Kubernetes Secrets

The WooCommerce MCP server uses a Kubernetes Secret named `woo-api-credentials` with keys `consumer-key` and `consumer-secret`.

Create it using your own WooCommerce API credentials. Replace the placeholders locally; never commit real credentials:

```cmd
kubectl create secret generic woo-api-credentials -n urumi --from-literal=consumer-key=YOUR_WOOCOMMERCE_CONSUMER_KEY --from-literal=consumer-secret=YOUR_WOOCOMMERCE_CONSUMER_SECRET
```

The WooCommerce chart also uses `woo-platform-secrets` for database credentials. Inspect `helm/woo-platform/templates/mariadb.yaml` and `helm/woo-platform/templates/wordpress.yaml` to confirm the exact keys required by your configuration before creating or updating that Secret.

### 3. Deploy WooCommerce

Inspect the chart and values files:

```cmd
dir helm
dir helm\woo-platform
dir helm\values
```

Install or upgrade the chart:

```cmd
helm upgrade --install urumi .\helm\woo-platform -n urumi -f .\helm\values\values-local.yaml
```

Check the resources:

```cmd
kubectl get pods -n urumi
kubectl get services -n urumi
kubectl get ingress -n urumi
kubectl get pvc -n urumi
```

Wait for the WordPress and MariaDB pods to become ready before continuing.

### 4. Build and load application images

Build and load the WooCommerce MCP server image:

```cmd
docker build -t urumi-woo-mcp:0.1.0 .\woo-mcp-server
kind load docker-image urumi-woo-mcp:0.1.0 --name urumi-local
```

Build and load the backend image:

```cmd
docker build -t urumi-backend:0.1.0 .\backend
kind load docker-image urumi-backend:0.1.0 --name urumi-local
```

Apply or upgrade the backend and MCP server Kubernetes resources using the manifests in `k8s/`. Check the manifests and confirm the required Secrets exist before applying them.

Verify rollout status:

```cmd
kubectl get deployments -n urumi
kubectl rollout status deployment/woo-mcp-server -n urumi
kubectl rollout status deployment/urumi-backend -n urumi
```

### 5. Verify backend health

Start port-forwarding and keep that terminal open:

```cmd
kubectl port-forward -n urumi svc/urumi-backend 8010:8001
```

In a second terminal, run:

```cmd
curl.exe http://127.0.0.1:8010/health
```

The local MCP endpoint is available at `http://127.0.0.1:8010/mcp` while the port-forward is active.

### 6. Run the frontend

Open another terminal:

```cmd
cd frontend
npm install
npm.cmd run dev
```

Open the local URL printed by Vite. Confirm that the frontend API base URL matches the backend address used for local testing.

The frontend development server is a local development workflow. Verify any Kubernetes dashboard deployment and Ingress configuration separately.

## WooCommerce MCP Tools

The custom WooCommerce MCP server exposes these operations:

| Tool | Description |
|---|---|
| `list_products` | List WooCommerce products |
| `create_product` | Create a product |
| `list_orders` | List orders, with optional date filters |
| `get_order` | Retrieve an order by ID |
| `update_order_status` | Update an order's status |

The gateway uses namespaced tool names such as `woocommerce__list_products` to identify the upstream server.

Privileged operations should be protected by backend authorization, not only by hiding controls in the frontend. Verify the role policy in the running deployment.

## External MCP Client

A compatible MCP client, such as MCP Inspector, can connect to the gateway using Streamable HTTP.

| Setting | Value |
|---|---|
| Transport | Streamable HTTP |
| Local gateway endpoint | `http://127.0.0.1:8010/mcp` |
| Authorization | `Bearer YOUR_GATEWAY_API_KEY` |

Use the API key created for the intended gateway user. Do not use WooCommerce consumer credentials as the gateway key.

After connecting, verify that tools from enabled upstream servers can be discovered and called. Confirm that calls are attributed to the correct user in the audit log.

## Security and Access Control

The following controls are part of the project's security design and should be validated against the running deployment.

- **Individual gateway keys:** users have separate keys, with hashed storage and revocation support.
- **Role-based authorization:** privileged tool calls are checked in the backend.
- **Server-side credentials:** WooCommerce credentials are supplied to the MCP server through Kubernetes Secrets.
- **Audit logging:** tool calls record relevant identity, server, tool, timing, and outcome details.
- **Internal service communication:** the WooCommerce MCP server should be reachable by the gateway internally rather than exposed directly to the public Internet.
- **Secret hygiene:** passwords, tokens, API keys, populated Secret manifests, and local database files must not be committed to Git.

For production, also consider TLS, restrictive Kubernetes RBAC, encryption at rest, network policies, egress controls, credential rotation, rate limiting, backups, and monitoring.

## API Overview

The backend provides routes for authentication, API-key management, server administration, gateway tool discovery and calls, AI chat, and audit logs. The route definitions in the source and the running OpenAPI document are authoritative.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Backend health check |
| `POST /auth/login` | Authenticate a dashboard user |
| `GET /gateway/tools` | Discover aggregated tools through the dashboard API |
| `POST /gateway/tools/call` | Call an aggregated tool through the dashboard API |
| `GET /audit` | Retrieve audit logs, subject to authorization |
| `/mcp` | MCP endpoint for external clients using a gateway API key |

Dashboard JWTs and gateway API keys serve different purposes. Use the credential type required by each endpoint.

## Deployment Configuration

The WooCommerce Helm chart provides separate values files:

- `helm/values/values-local.yaml`
- `helm/values/values-prod.yaml`

Validate the chart and render both configurations:

```cmd
helm lint .\helm\woo-platform
helm template urumi .\helm\woo-platform -n urumi -f .\helm\values\values-local.yaml
helm template urumi .\helm\woo-platform -n urumi -f .\helm\values\values-prod.yaml
```

Before using production-like values on a VPS or k3s cluster, verify DNS, Ingress and TLS, storage, resources, probes, image distribution, and Secret management. A production-like values file alone does not establish that a production deployment has been completed.

## Testing and Validation

The following checks are recommended before release:

- [ ] WordPress and MariaDB are ready in Kubernetes.
- [ ] Store data persists after pod restarts.
- [ ] All five WooCommerce MCP tools work.
- [ ] The gateway aggregates WooCommerce and at least two additional MCP servers.
- [ ] Tool-name collisions are handled through namespacing.
- [ ] An unavailable upstream does not break healthy upstreams.
- [ ] An administrator can manage upstream server configuration.
- [ ] A member is denied restricted administrative tool calls, including direct calls.
- [ ] Revoking an API key rejects subsequent requests using that key.
- [ ] Chat tool calls execute under the signed-in user's identity.
- [ ] User A creates a product and queries the resulting order through chat.
- [ ] User B queries orders through an external MCP client.
- [ ] Successful and failed calls appear in audit logs.
- [ ] Storefront and dashboard access match the intended deployment.
- [ ] Local and production-like Helm values render successfully.
- [ ] Git contains no credentials, local databases, or generated dependency folders.

## System Design

### Unified gateway

A single endpoint simplifies client configuration and centralizes upstream discovery, authorization, routing, and auditing.

### Namespaced tools

A name such as `woocommerce__list_products` makes the source server explicit and avoids ambiguous routing when upstream servers expose similarly named tools.

### Server-side credentials

Users authenticate to the gateway with their own credentials. They do not need access to upstream WooCommerce consumer keys or secrets.

### Local and production-like environments

Helm values allow a shared chart to be configured for different environments. Production deployment still requires environment-specific review of networking, storage, security, observability, and operations.

### Trade-offs

- SQLite is convenient for local gateway development; production concurrency and availability may require a shared database.
- Port-forwarding is intended for local testing, not public production access.
- Kubernetes Secrets require suitable RBAC and additional production hardening.
- User-configurable upstream URLs require SSRF protection and network egress restrictions.
- Multiple gateway replicas require shared persistence and reliable audit-write behavior.

## Threat Model

| Threat | Potential impact | Mitigation |
|---|---|---|
| Shared upstream credentials | Users may invoke powerful operations indirectly | Server-side secrets, least privilege, backend authorization, audit logging |
| Leaked gateway key | Unauthorized calls under the key owner's identity | Hashed storage, individual revocation, secure delivery |
| Malicious tool output | Content could attempt to manipulate the AI agent | Treat tool output as untrusted; enforce permissions outside the LLM |
| Malicious upstream URL | SSRF into internal services or metadata endpoints | URL validation, destination checks, egress restrictions |
| Cross-user access | A member accesses another user's keys or administrative features | Ownership checks, role checks, audit attribution |
| Secret exposure | Credentials leak through Git, logs, or permissive access | Secret scanning, least-privilege RBAC, rotation, encryption at rest |

## Limitations and Future Improvements

Potential improvements include:

- Add automated integration and security tests for key revocation, role enforcement, and upstream failure isolation.
- Strengthen SSRF defenses for configurable upstream URLs.
- Add rate limiting, metrics, structured logging, and operational dashboards.
- Configure TLS, network policies, backup and recovery, and production secret management.
- Validate production deployment and upgrade/rollback procedures.
- Evaluate a shared database for multi-replica gateway deployments.

Optional multi-store provisioning is outside the core implementation unless implemented and demonstrated separately.

---

<div align="center">

**Urumi MCP Gateway**
*Unified MCP access for team workflows.*

</div>
