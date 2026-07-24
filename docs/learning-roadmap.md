# SkillForge — Learning Roadmap (build in this order)

Tag releases per phase; keep ADRs in `docs/decisions/`. **Honest timeline: ~15–16 weeks part-time.** The original 11-week plan silently assumed you already know Django, DRF, Celery, ES, Stripe, Next.js, FastAPI, LangChain, and AWS — if you did, you wouldn't need the project. Overrunning a fake deadline is how learning projects get abandoned; pad it up front instead.

## Phase 1 — Foundations + Walking Skeleton (weeks 1–3)
- Project scaffold, custom user model, `accounts` + `orgs` apps with services/selectors layering.
- Seat licensing: **DB constraints first** (unique constraints, seat-count CHECK), then `select_for_update` on the license row; concurrent race-condition test proving overselling is impossible *and* that the constraint holds when the service layer is bypassed. (Seed licenses via fixture — purchases don't exist until phase 3.)
- Docker Compose (web, postgres, redis), pytest-django, ruff/mypy, import-linter.
- **Deploy the walking skeleton now:** GitHub Actions → build → migrate → deploy a hello-world Django to Beanstalk/ECS, smoke test. Sentry + structured logging wired. Deploying in the last phase means debugging every environment problem at once, at the end, when motivation is lowest.
- **You learn:** Django properly, clean layering, transactional integrity via constraints (not just locks), CI/CD before there's much to deploy.

## Phase 2 — Catalog, Learning & Admin Panel (weeks 4–6)
- `catalog` + `learning`: courses, lessons, enrollments (unique per user+course), idempotent progress events, quizzes, PDF certificates (Celery; certificate issuance recomputes completion from events, never from the lagging materialized table).
- Django Admin deep dive: role-scoped staff (enforced in querysets), course approval workflow, **hardened impersonation** (no staff-on-staff, time-boxed, audited with both identities). *Refund action moved to phase 3 — you can't build a refund action before payments exist.*
- Elasticsearch search (indexing via `on_commit`, alias-based reindex) + defined degraded Postgres fallback (`pg_trgm`, facets off, `degraded` flag).
- **Tenancy isolation:** org-scoping mixin + the IDOR test suite. This is phase 2, not a hardening afterthought — every later endpoint inherits it.
- **You learn:** rich relational modeling, Django Admin mastery, Celery, Elasticsearch, multi-tenant safety.

## Phase 3 — Orders & Payments (weeks 7–8)
- Stripe test mode: checkout session, webhooks — signature-verified, idempotent (event row + side effects in one transaction), **out-of-order tolerant**, plus API confirmation on checkout return and a daily reconciliation task against Stripe.
- Immutable money rows + a single derived `Order.status` projection.
- **Refund policy ADR before the refund code:** what happens to assigned seats, in-progress enrollments, issued certificates. Then the admin refund action (calls `orders.services`).
- Org invoicing + seat purchase flow (replaces phase-1 fixtures).
- **You learn:** payment integration patterns — including the parts (ordering, reconciliation, refund side-effects) that separate "did the tutorial" from "did it right."

## Phase 4 — AI Tutor *inside the monolith* (weeks 9–10)
- `tutor` as a normal Django app: DRF chat endpoint, pgvector retrieval scoped by `course_id` with enrollment verified server-side, LangChain pipeline.
- Ingestion pipeline: markdown-aware chunking; transcript source decided and built (instructor upload or Whisper task) — video content is invisible to the tutor without it.
- Guardrails, tested in CI: cross-course isolation; **quiz content excluded from the corpus at ingestion** (similarity-refusal is secondary); prompt-injection red-team test with a hostile lesson fixture (instructor content is untrusted); input/output moderation; **per-user token budget + rate limit + timeout fallback**.
- **You learn:** scoped RAG, LLM guardrails and cost control in a product context — and you create the thing phase 6 will extract. (The original plan built the tutor as a service from day one, then called it a "strangler migration" — you can't extract what never lived in the monolith, and an interviewer will catch that.)

## Phase 5 — Frontend & Org Dashboard (weeks 11–12)
- **Auth ADR first** (session-cookie + CSRF vs JWT) — retrofitting frontend auth mid-build is a classic week-loss.
- Next.js learner app: catalog/search UI (handles `degraded` mode), video player (CloudFront signed URLs), quiz flow, tutor chat.
- **Instructor course builder v1 = Django Admin.** The custom drag-and-drop builder is a stretch goal; it's a multi-week React project that teaches none of the target skills.
- Customer-facing org dashboard: seats, progress heatmap, compliance report export (Celery + SES) — all behind the tenancy scoping from phase 2.
- **You learn:** full-stack integration against DRF, S3 presigned uploads, signed content delivery.

## Phase 6 — Tutor Extraction to FastAPI (weeks 13–14)
- Extract the phase-4 tutor app into `tutor-service` (FastAPI): now the strangler ADR is real — why this piece, why now, what stayed.
- **Streaming:** browser → tutor-service **directly** via SSE with a short-TTL JWT minted by Django, scoped to `{user, course, enrollment}` — the service retrieves only the course in the token. Do not proxy SSE through WSGI Django (one pinned worker per open stream).
- **Data ownership:** pgvector schema owned by the service; Django calls the service's ingestion API instead of writing embeddings directly. Shared-write DB = distributed monolith; ADR the same-physical-Postgres cost tradeoff explicitly.
- Cross-service request-ID propagation so one conversation is traceable end to end.
- **You learn:** monolith→microservice migration for real — moving live code, redrawing a trust boundary, and keeping the tests green across the cut.

## Phase 7 — Hardening & Performance (weeks 15–16)
- k6 load tests on catalog + enrollment; N+1 hunt with `assertNumQueries`; `docs/performance.md` with before/after numbers.
- Observability completion: Celery queue-depth + failure alarms, webhook-failure alarm, deep health checks in smoke tests.
- Cost review against the phase-1 budget table; RDS restore drill (a backup you've never restored is a hope).
- **You learn:** monolith ops, safe migrations at steady state, query optimization, and proving the system works rather than assuming it.

## Stretch Goals
- Custom Next.js instructor course builder.
- Feature flags (waffle) + gradual-rollout story.
- i18n (Arabic + English — RTL support is a great differentiator).
- Read replica for analytics; measure replication-lag implications.

## Interview Story This Project Gives You
"I built a B2B learning marketplace as a modular Django monolith — constraint-backed race-safe seat licensing, tenant-isolation tests in CI, idempotent and out-of-order-tolerant Stripe webhooks with reconciliation, Elasticsearch with a defined degradation mode — built the AI tutor inside the monolith with course-scoped RAG, ingestion-time quiz exclusion, and prompt-injection tests, then extracted it to a FastAPI service with the strangler pattern behind a JWT-scoped trust boundary, deployed continuously to AWS from week one."
