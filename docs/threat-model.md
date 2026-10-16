\# Security Threat Model



\## 1. Scope



This document identifies security risks for the Urumi MCP Gateway,

including authentication, API keys, upstream MCP servers, tool

execution, and deployment configuration.



\## 2. Assets to Protect



\- User accounts and authentication tokens

\- MCP API keys

\- WooCommerce products and customer orders

\- Database contents

\- Upstream MCP server availability

\- Tool execution and audit records



\## 3. Trust Boundaries



1\. Browser to FastAPI backend

2\. MCP client to the unified MCP endpoint

3\. Gateway to upstream MCP servers

4\. WooCommerce MCP server to the WooCommerce REST API

5\. Application containers to persistent database storage



Requests crossing these boundaries must be validated and authorized.



\## 4. Threats and Mitigations



| Threat | Potential Impact | Mitigation |

|---|---|---|

| Missing or invalid authentication | Unauthorized access | Require valid bearer tokens or MCP API keys |

| Stolen API key | Unauthorized tool execution | Hash API keys at rest and support revocation |

| Member invokes administrative tools | Unauthorized product or order changes | Enforce role-based permissions during execution |

| Disabled server receives calls | Access to an unavailable or intentionally disabled integration | Discover and route only to enabled servers |

| Ambiguous server prefix | Tool routed to the wrong server | Reject ambiguous prefixes |

| Slow or unavailable upstream | Delayed or failed requests | Configure upstream timeouts and handle errors |

| Failed tool calls go unnoticed | Reduced accountability | Record call outcomes and duration in audit logs |

| Credentials committed to Git | Credential compromise | Use Kubernetes Secrets, environment configuration, and Git ignore rules |



\## 5. Residual Risks



\- Kubernetes Secrets require appropriate cluster access controls.

\- Local development configuration is not equivalent to production hardening.

\- A compromised administrator account may perform privileged operations.

\- Audit records require suitable retention, access controls, and monitoring.

\- Upstream services and external APIs may have their own vulnerabilities.

\- Public deployment requires additional network, TLS, and operational controls.



\## 6. Security Verification



The current automated tests cover:



\- Health endpoint behavior

\- Missing and invalid REST bearer tokens

\- Missing and invalid MCP API keys

\- The administrator-only tool-name policy



Additional tests should verify runtime role enforcement, API-key revocation,

audit logging, and upstream failure handling.



\## 7. Production Recommendations



\- Rotate credentials exposed during development.

\- Never commit passwords, API keys, JWTs, or private configuration.

\- Use TLS for externally accessible endpoints.

\- Restrict Kubernetes and database access.

\- Apply resource limits and monitor service health.

\- Validate upstream URLs and prevent access to unintended internal services.

\- Test authorization and failure paths before production deployment.
