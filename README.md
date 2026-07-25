# SkillForge — Corporate Learning Marketplace (Django Monolith + AI Tutor)

> **Business idea:** A B2B learning platform where instructors publish courses, companies buy seat licenses for their employees, and every course has an **AI tutor** that answers questions grounded only in that course's content. Companies get progress dashboards and compliance reports; the platform team runs everything from a powerful admin panel.
>
> **Why companies pay for this:** Corporate training is a $350B+ market. Companies need to train employees, *prove* it (compliance), and reduce instructor support load — the per-course AI tutor does exactly that.

## Why a Monolith? (that's the point)

DocuMind and FraudGuard teach you microservices (HTTP-style and event-driven). SkillForge teaches the third pattern that most real companies actually run: a **well-structured modular monolith**. You'll learn why monoliths are often the right call, how to keep one clean, and how to carve out your first service when a real reason appears.

The AI tutor is **built inside the monolith first** (phase 4) and extracted to a FastAPI service later (phase 6) — that ordering is what makes it an honest strangler migration instead of a greenfield service wearing a strangler costume.

## Skills You Will Practice Here

| From your list | How it appears in this project |
|---|---|
| Django | The core: ORM, class-based views / DRF, auth, management commands, tests |
| Admin panels | Django Admin taken seriously: custom ModelAdmins, inlines, actions (approve course, refund order), queryset-enforced staff roles, hardened audited impersonation — plus a customer-facing org dashboard |
| FastAPI | The AI tutor microservice (phase 6) — extracting a real, working Django app into a service |
| LangChain + guardrails | Tutor answers **only from course content** (enrollment-verified, course-scoped RAG); quiz content excluded from the corpus at ingestion; instructor content treated as untrusted (prompt-injection tests); per-user cost budgets |
| pgvector | Course-content embeddings (same Postgres while in the monolith; service-owned schema after extraction) |
| Chunking | Markdown-aware lesson chunks; timestamp-window transcript chunks (with an explicit transcript pipeline) |
| Relational DB | PostgreSQL — deep modeling: orgs, seats, enrollments, progress, orders, certificates — invariants held by **DB constraints**, not just application code |
| Redis | Cache (per-view + fragment), Celery broker, tutor rate limiting |
| Non-relational | Elasticsearch for course search (facets, typo tolerance) — chosen as an explicit learning ADR (Postgres FTS would suffice at this scale) |
| Monolith style | Modular monolith: Django apps as bounded contexts — import-linter for the import graph, plus conventions for the ORM traversal it can't catch |
| Clean architecture | Service layer between views and ORM; selectors return only their own app's data |
| Full stack | Next.js (React) learner frontend consuming DRF API |
| Docker | Compose: web, worker, beat, postgres, redis, elasticsearch, tutor-service |
| CI/CD | GitHub Actions from **phase 1** — a walking skeleton deploys before the features exist |
| Deployment | Self-hosted Docker: Compose behind Nginx (TLS via Let's Encrypt) on a VPS; Postgres, Redis, and Elasticsearch as containers with volumes and a tested backup/restore routine |
| Gateways | Nginx as reverse proxy/static gateway |

**Bonus skills baked in:** Celery + Beat (compliance reports, certificates), Stripe test-mode payments (signature-verified, idempotent, **out-of-order-tolerant** webhooks + reconciliation), multi-tenant isolation with IDOR tests in CI, observability (Sentry, structured logs, queue-depth alarms), feature flags, protected media downloads via Nginx `X-Accel-Redirect`, PDF certificates, i18n, N+1 prevention enforced in CI.

## High-Level Architecture

```
                    Nginx (TLS, static/protected media)
                           │
 Next.js frontend ──▶ Nginx ──▶ Django monolith (DRF + Django Admin)
        │                       │  apps: accounts, orgs, catalog, learning,
        │                       │        orders, analytics, tutor*
        │                       ├── PostgreSQL (+ pgvector)
        │                       ├── Redis (cache, Celery, rate limits)
        │                       ├── Elasticsearch (course search)
        │                       └── (mints short-TTL course-scoped JWT)
        └────SSE + JWT────▶ tutor-service (FastAPI + LangChain)  [phase 6]
                                └── scoped RAG; service-owned pgvector schema

 * tutor lives inside the monolith in phases 4–5, extracted in phase 6
```

See [docs/architecture.md](docs/architecture.md) and [docs/learning-roadmap.md](docs/learning-roadmap.md).

## Getting Started (once you build it)

```bash
docker compose up -d
make migrate seed        # demo org, courses, learners
make test                # pytest-django
```

## Suggested Repository Setup

```bash
git init
git add .
git commit -m "chore: project scaffold and docs"
gh repo create skillforge-lms --public --source=. --push
```

## Definition of Done (each item is testable)

- [ ] Learner can browse (ES search, with tested Postgres degradation mode), enroll via seat license, complete lessons, take quizzes, get a PDF certificate
- [ ] Seat limits held by DB constraints + row locks — concurrent race test passes, and the constraint holds even when the service layer is bypassed
- [ ] Tenancy: IDOR test suite proves no cross-org data access on every org-scoped endpoint
- [ ] Org admin dashboard: seat usage, per-employee progress, compliance report export (Celery task, emailed via SMTP — Mailpit locally)
- [ ] Django Admin: queryset-scoped staff roles, course approval workflow, refund action (with a written refund-side-effects policy) with audit trail, hardened impersonation
- [ ] AI tutor: cross-course isolation test, quiz-corpus-exclusion test, prompt-injection test against hostile lesson content, per-user token budget enforced — all in CI
- [ ] Stripe: signature-verified, idempotent, out-of-order-tolerant webhooks; reconciliation task diffs local state against Stripe
- [ ] Zero N+1 queries on the 5 hottest endpoints (`assertNumQueries` in CI)
- [ ] CI/CD deploys to the self-hosted target **from phase 1**; no-downtime migration pattern documented *and exercised* by at least one real additive→code→destructive migration
- [ ] Observability: Sentry wired across Django/Celery/tutor-service; Celery queue-depth and webhook-failure alarms exist
