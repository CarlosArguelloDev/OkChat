# OkChat — Enterprise Architecture Blueprint
### FastAPI · Python 3.12+ · Clean Architecture · DDD · Cloud-Native

---

## Table of Contents
1. [Philosophy & Guiding Principles](#1-philosophy)
2. [Folder Structure](#2-folder-structure)
3. [Service Decomposition](#3-service-decomposition)
4. [Inter-Service Communication](#4-inter-service-communication)
5. [Auth & Authorization](#5-auth--authorization)
6. [Event System](#6-event-system)
7. [FastAPI Router Organization](#7-fastapi-router-organization)
8. [WebSockets & Streaming](#8-websockets--streaming)
9. [External Provider Decoupling](#9-external-provider-decoupling)
10. [Domain Layer Design](#10-domain-layer-design)
11. [Configuration by Environment](#11-configuration-by-environment)
12. [Testing Strategy](#12-testing-strategy)
13. [Kubernetes Readiness](#13-kubernetes-readiness)
14. [Observability](#14-observability)
15. [Rate Limiting & Security](#15-rate-limiting--security)
16. [Workers & Async Tasks](#16-workers--async-tasks)
17. [API Versioning](#17-api-versioning)
18. [Avoiding Tight Coupling](#18-avoiding-tight-coupling)
19. [Patterns & Anti-Patterns](#19-patterns--anti-patterns)
20. [Code Examples](#20-code-examples)
21. [Dockerfile & docker-compose](#21-dockerfile--docker-compose)
22. [CI/CD Strategy](#22-cicd-strategy)
23. [Secrets Management](#23-secrets-management)
24. [Deployment Strategy](#24-deployment-strategy)
25. [Naming Conventions](#25-naming-conventions)
26. [Multi-Tenant Strategy](#26-multi-tenant-strategy)
27. [Scaling to Millions of Requests](#27-scaling-to-millions-of-requests)
28. [What NOT to Do](#28-what-not-to-do)
29. [Evolution Roadmap](#29-evolution-roadmap)

---

## 1. Philosophy

### Guiding Principles
- **Async-first, always.** Python 3.12 + asyncio + SQLAlchemy 2.0 async. No blocking I/O anywhere.
- **Ports & Adapters (Hexagonal Architecture).** The domain never imports infrastructure.
- **Dependency Inversion.** Depend on abstractions (Protocols), not implementations.
- **Fail fast, log always.** Structured JSON logs with correlation IDs on every request.
- **Boring technology where possible.** Microservices are a scaling solution, not a starting point.

### When Monolith → When Microservices
| Factor | Stay Monolith | Go Microservices |
|---|---|---|
| Team size | <10 devs | >15 devs per domain |
| Traffic | <10k req/s | >100k req/s per service |
| Deploy frequency | 1x/day | Multiple teams, multiple deploys |
| Domain complexity | Single domain | Multiple bounded contexts |
| SLA differences | Uniform | Per-service SLA |

> **Recommendation:** Start as a **Modular Monolith**. Each module enforces its own boundaries. Extract to microservices only when you have a proven bottleneck.

---

## 2. Folder Structure

```
okchat/
├── pyproject.toml
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── Makefile
│
├── src/
│   └── okchat/
│       ├── __init__.py
│       ├── main.py                    # FastAPI app factory
│       ├── lifespan.py                # Startup/shutdown handlers
│       │
│       ├── core/                      # Cross-cutting concerns
│       │   ├── config.py              # Pydantic Settings
│       │   ├── logging.py             # Structured logging setup
│       │   ├── exceptions.py          # Base domain exceptions
│       │   ├── errors.py              # HTTP error handlers
│       │   ├── security.py            # JWT helpers
│       │   ├── dependencies.py        # Shared FastAPI deps
│       │   └── middleware/
│       │       ├── correlation.py     # X-Request-ID injection
│       │       ├── timing.py          # Response time header
│       │       └── rate_limit.py      # Rate limiting middleware
│       │
│       ├── shared/                    # Shared domain primitives
│       │   ├── base_entity.py
│       │   ├── base_repository.py     # Protocol/Interface
│       │   ├── base_use_case.py
│       │   ├── pagination.py
│       │   ├── result.py              # Result[T, E] monad
│       │   └── events.py              # Base domain event
│       │
│       ├── modules/                   # Feature modules (bounded contexts)
│       │   │
│       │   ├── auth/
│       │   │   ├── domain/
│       │   │   │   ├── entities.py
│       │   │   │   ├── value_objects.py
│       │   │   │   └── repository.py  # Protocol
│       │   │   ├── application/
│       │   │   │   ├── use_cases/
│       │   │   │   │   ├── login.py
│       │   │   │   │   └── refresh_token.py
│       │   │   │   └── schemas.py
│       │   │   ├── infrastructure/
│       │   │   │   ├── repository.py
│       │   │   │   └── models.py
│       │   │   └── api/
│       │   │       ├── router.py
│       │   │       └── dependencies.py
│       │   │
│       │   ├── conversations/
│       │   │   ├── domain/
│       │   │   ├── application/
│       │   │   ├── infrastructure/
│       │   │   └── api/
│       │   │
│       │   ├── channels/
│       │   │   ├── domain/
│       │   │   ├── application/
│       │   │   └── infrastructure/
│       │   │       └── adapters/
│       │   │           ├── whatsapp.py
│       │   │           ├── telegram.py
│       │   │           └── discord.py
│       │   │
│       │   ├── agents/
│       │   │   └── infrastructure/
│       │   │       └── providers/
│       │   │           ├── openai.py
│       │   │           ├── anthropic.py
│       │   │           └── gemini.py
│       │   │
│       │   ├── memory/
│       │   │   └── infrastructure/
│       │   │       ├── redis_memory.py
│       │   │       └── pg_memory.py
│       │   │
│       │   ├── voice/
│       │   │   └── infrastructure/
│       │   │       └── providers/
│       │   │           ├── deepgram.py
│       │   │           └── elevenlabs.py
│       │   │
│       │   ├── webhooks/
│       │   ├── billing/
│       │   ├── analytics/
│       │   └── tenants/
│       │
│       ├── infrastructure/
│       │   ├── database/
│       │   │   ├── session.py
│       │   │   └── base.py
│       │   ├── cache/
│       │   │   └── redis.py
│       │   ├── events/
│       │   │   ├── bus.py
│       │   │   └── broker.py
│       │   ├── websockets/
│       │   │   └── manager.py
│       │   └── workers/
│       │       └── celery.py
│       │
│       └── api/
│           ├── v1/
│           │   └── router.py
│           └── health.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── alembic/
│   └── versions/
│
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── hpa.yaml
│   └── configmap.yaml
│
└── scripts/
    └── seed.py
```

---

## 3. Service Decomposition

### Phase 1 — Modular Monolith (MVP)
All modules in one process. Module boundaries enforced by Python import rules and layer separation.

```
[Client] → [FastAPI Modular Monolith]
                ├── auth module
                ├── conversations module
                ├── agents module
                ├── channels module
                └── voice module
           → [PostgreSQL] + [Redis]
```

### Phase 2 — API Gateway + Services
```
[Client] → [Traefik API Gateway]
                ├── /api/v1/auth        → auth-service
                ├── /api/v1/chat        → conversation-service
                ├── /api/v1/voice       → voice-service
                ├── /ws                 → realtime-service
                └── /webhooks           → webhook-service
```

---

## 4. Inter-Service Communication

### Sync
- **REST** via `httpx.AsyncClient` with connection pooling and timeout configuration.
- **gRPC** for high-throughput internal calls (auth validation, memory lookups).

### Async
- **Redis Streams** — lightweight, low-latency. Start here.
- **RabbitMQ / Kafka** — when you need durability, consumer groups, replay.

### Rule
> Immediate response needed → **sync**.  
> Notification / fire-and-forget → **async event**.

---

## 5. Auth & Authorization

- **JWT (RS256)** — asymmetric. Public key distributed to all services.
- **Short-lived access tokens** (15 min) + **refresh tokens** (7 days in Redis).
- **API Keys** for machine-to-machine (webhooks, integrations).
- **RBAC** via scopes in JWT: `{"sub": "uid", "tid": "tenant_id", "scopes": ["chat:write"]}`.
- Every DB query auto-filters by `tenant_id` via base repository.

---

## 6. Event System

### Naming Convention
```
{domain}.{entity}.{action}.{version}
conversations.message.created.v1
voice.call.ended.v1
billing.usage.recorded.v1
```

### In-Process (Phase 1)
Simple async event bus for decoupling within the monolith.

### Distributed (Phase 2+)
Redis Streams or RabbitMQ with dead letter queues, retry with exponential backoff, and CloudEvents schema.

---

## 7. FastAPI Router Organization

```python
# src/okchat/api/v1/router.py
from fastapi import APIRouter
from okchat.modules.auth.api.router import router as auth_router
from okchat.modules.conversations.api.router import router as conv_router
from okchat.modules.agents.api.router import router as agents_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router,  prefix="/auth",          tags=["Auth"])
v1_router.include_router(conv_router,  prefix="/conversations",  tags=["Conversations"])
v1_router.include_router(agents_router, prefix="/agents",        tags=["Agents"])
```

---

## 8. WebSockets & Streaming

- `ConnectionManager` holds active WS connections per `session_id`.
- Redis Pub/Sub as the backplane for multi-instance scaling.
- **SSE** for simple LLM token streaming over HTTP.
- **Binary WS frames** for PCM/opus audio.
- Deepgram streaming STT via WebSocket.
- ElevenLabs streaming TTS via chunked HTTP.

---

## 9. External Provider Decoupling

### Pattern: Port (Protocol) + Adapter

```
LLMPort (Protocol) ← OpenAIAdapter
                   ← AnthropicAdapter
                   ← GeminiAdapter

STTPort (Protocol) ← DeepgramAdapter
                   ← WhisperAdapter

TTSPort (Protocol) ← ElevenLabsAdapter
                   ← AzureTTSAdapter
```

Providers are injected via FastAPI dependencies. Switching providers = change one env var.

---

## 10. Domain Layer Design

- Entities have identity (`id: UUID`). No ORM imports inside the domain layer.
- Business logic lives in entities and aggregate roots.
- Value objects are immutable (`@dataclass(frozen=True)`).
- Domain events are emitted from aggregate roots, not services.
- Examples: `Email`, `PhoneNumber`, `MessageContent`, `TenantId`.

---

## 11. Configuration by Environment

```
.env              # defaults, no secrets
.env.local        # local overrides (gitignored)
.env.staging      # staging values
.env.production   # secrets via Vault/Secrets Manager
```

`SettingsConfigDict(env_prefix="OKCHAT_", env_nested_delimiter="__")`

Nested config example: `OKCHAT_DB__URL=postgresql+asyncpg://...`

---

## 12. Testing Strategy

```
tests/
├── unit/        # Pure domain logic. No I/O. No fixtures.
├── integration/ # DB + Redis via testcontainers-python.
└── e2e/         # Full HTTP with httpx.AsyncClient + TestClient.
```

- Unit: `pytest` + `pytest-asyncio`. Mock only at port boundaries.
- Integration: Real PostgreSQL + Redis via `testcontainers`.
- E2E: `httpx.AsyncClient` against running app.
- Target: >80% coverage on domain + application layers.

---

## 13. Kubernetes Readiness

| Requirement | Implementation |
|---|---|
| Stateless | No local state; sessions in Redis |
| Health probes | `/health/live` and `/health/ready` |
| Graceful shutdown | `lifespan` closes DB pool, drains WS |
| Config | ConfigMaps (non-secret), Secrets (sensitive) |
| Autoscaling | HPA on CPU + KEDA on queue depth |
| Resource limits | Defined in Deployment spec |
| Non-root user | Dockerfile USER directive |

---

## 14. Observability

| Pillar | Tool | Sink |
|---|---|---|
| Logs | `structlog` → JSON | Fluentd → Loki |
| Metrics | `prometheus-fastapi-instrumentator` | Prometheus → Grafana |
| Traces | `opentelemetry-sdk` + OTLP | Jaeger / Grafana Tempo |

Every request gets `X-Request-ID` propagated to all downstream calls, DB queries, and log entries.

---

## 15. Rate Limiting & Security

- `slowapi` with Redis backend for distributed rate limiting.
- Per endpoint, per user, per tenant limits.
- TLS terminated at ingress/load balancer.
- `SecurityHeaders` middleware: HSTS, CSP, X-Frame-Options.
- Pydantic validates all input automatically.
- `pip-audit` in CI for dependency vulnerability scanning.

---

## 16. Workers & Async Tasks

- **FastAPI BackgroundTasks** — lightweight, within request lifecycle (<200ms).
- **Celery + Redis broker** — long-running tasks, retry logic, scheduling.
- **Celery Beat** — scheduled tasks: analytics aggregation, memory pruning.

> Rule: Task > 1s or needs retry → Celery. Otherwise → BackgroundTasks.

---

## 17. API Versioning

- URL versioning: `/api/v1/`, `/api/v2/`
- Never break a published version. Add v2 instead.
- Deprecation header: `Deprecation: true`, `Sunset: 2027-01-01`
- Maintain N-1 support (current + 1 previous version).

---

## 18. Avoiding Tight Coupling

| Technique | How |
|---|---|
| Dependency Inversion | Depend on `Protocol`, not concrete class |
| Event-driven | Services communicate via events |
| Anti-corruption Layer | Wrap 3rd-party APIs in your own types |
| Separate DB per service | No shared database between bounded contexts |
| Contract testing | Pact for consumer-driven contracts |

---

## 19. Patterns & Anti-Patterns

### ✅ Use
- Repository Pattern, Unit of Work, CQRS, Saga, Circuit Breaker, Outbox Pattern, Retry with backoff

### ❌ Avoid
| Anti-pattern | Why |
|---|---|
| Anemic domain model | Logic leaks into services |
| God service | Impossible to maintain |
| Shared database | Destroys service independence |
| Synchronous everything | Cascading failures |
| Hardcoded config | Violates 12-factor |
| Fat controllers | Logic should be in use cases |
| No correlation ID | Impossible to debug |
| Blocking I/O in async | Starves event loop |

---

## 20. Code Examples

See companion source files generated in the OkChat project:

- `src/okchat/main.py` — App factory
- `src/okchat/lifespan.py` — Startup/shutdown
- `src/okchat/core/config.py` — Settings
- `src/okchat/infrastructure/database/session.py` — Async DB session
- `src/okchat/infrastructure/events/bus.py` — Event bus
- `src/okchat/infrastructure/websockets/manager.py` — WS manager
- `src/okchat/core/middleware/correlation.py` — Middleware
- `src/okchat/shared/base_repository.py` — Base repo
- `src/okchat/modules/conversations/domain/entities.py` — Domain
- `src/okchat/modules/conversations/application/use_cases/send_message.py` — Use case
- `src/okchat/modules/conversations/infrastructure/repository.py` — Infra
- `src/okchat/modules/conversations/api/router.py` — Router

---

## 21. Dockerfile & docker-compose

See `Dockerfile` and `docker-compose.yml` in project root.

Strategy:
- Multi-stage build: `builder` stage → `runtime` stage
- Non-root user in final image
- `python:3.12-slim` runtime
- Layer caching: copy `pyproject.toml` → install deps → copy source

---

## 22. CI/CD Strategy

```
PR Opened:
  ruff lint → mypy typecheck → unit tests → integration tests

Merge to main:
  build image → push to registry → deploy to staging → smoke test

Tag vX.Y.Z:
  deploy to production → health check → rollback on failure
```

- DB migrations run as a pre-deploy Kubernetes Job (always backward-compatible).
- Zero-downtime via rolling updates with `maxUnavailable: 0`.

---

## 23. Secrets Management

| Environment | Strategy |
|---|---|
| Development | `.env.local` (gitignored) |
| Staging/Production | Kubernetes Secrets + HashiCorp Vault / AWS Secrets Manager |
| Rotation | Vault Agent sidecar — no redeploy needed |

Never put secrets in: code, git, Docker layers, logs.

---

## 24. Deployment Strategy

- **Container Registry:** GCR / ECR
- **Orchestration:** GKE / EKS
- **Ingress:** Traefik or Nginx Ingress Controller
- **TLS:** cert-manager + Let's Encrypt
- **DB:** Cloud SQL / RDS (managed, auto-backup)
- **Cache:** Cloud Memorystore / ElastiCache
- **Environments:** `local → staging → production` (separate K8s namespaces)

---

## 25. Naming Conventions

| Type | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `send_message.py` |
| Classes | `PascalCase` | `SendMessageUseCase` |
| Functions | `snake_case` | `send_message` |
| Constants | `UPPER_SNAKE` | `MAX_RETRIES` |
| Env vars | `OKCHAT_MODULE__KEY` | `OKCHAT_DB__URL` |
| DB tables | `snake_case` plural | `conversations` |
| Events | `domain.entity.action.v1` | `chat.message.created.v1` |
| API routes | `kebab-case` | `/api/v1/send-message` |
| Docker images | `okchat-<service>` | `okchat-api` |

---

## 26. Multi-Tenant Strategy

| Level | Strategy | Use Case |
|---|---|---|
| Row-level | `tenant_id` column + base filter | SaaS MVP |
| Schema-level | Separate PostgreSQL schema per tenant | Medium isolation |
| DB-level | Separate DB per tenant | Enterprise / maximum isolation |

**Recommendation:** Start row-level with `TenantBaseRepository` auto-injecting `tenant_id`. Upgrade to schema-level on demand.

---

## 27. Scaling to Millions of Requests

- **Stateless pods** + HPA autoscaling
- **PgBouncer** for DB connection pooling
- **Read replicas** for read-heavy queries
- **Redis Cluster** for HA cache
- **Semantic caching** for LLM responses
- **Kafka + KEDA** for event processing autoscaling
- **Circuit breaker** with fallback to secondary LLM provider
- **CDN** for static assets and cached API responses

---

## 28. What NOT to Do

- ❌ `asyncio.run()` inside async code
- ❌ `time.sleep()` in async context — use `asyncio.sleep()`
- ❌ CPU-heavy work in async endpoints — use `run_in_executor` or Celery
- ❌ Secrets in `.env` committed to git
- ❌ `SELECT *` — always select specific columns
- ❌ Building microservices from day 1
- ❌ `print()` for logging — use `structlog`
- ❌ Global mutable state in FastAPI
- ❌ Domain layer importing infrastructure
- ❌ Skipping correlation IDs

---

## 29. Evolution Roadmap

### Phase 0 — MVP (0-3 months)
Modular monolith, PostgreSQL + Redis, JWT auth, text chat via WebSocket, 1 LLM provider, Docker Compose.

### Phase 1 — Growth (3-9 months)
Extract auth service, Celery workers, multi-channel (WhatsApp/Telegram), Prometheus + Grafana, Kubernetes, voice support.

### Phase 2 — Scale (9-18 months)
Extract conversation service, Redis Streams → Kafka, CQRS for reads, multi-LLM failover, billing, full OpenTelemetry.

### Phase 3 — Enterprise (18+ months)
Full microservices with gRPC, multi-region active-active, Kafka, custom ML serving, ClickHouse analytics, SLA-based routing.
