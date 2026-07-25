# SkillForge — Architecture

## 1. Style: Modular Monolith (with one deliberate service extraction)

One Django project, one deployable, one database — but **strict internal boundaries**. Each Django app is a bounded context:

| App | Owns | Notes |
|---|---|---|
| `accounts` | users, auth, profiles | Custom user model from day one |
| `orgs` | organizations, seat licenses, memberships | B2B core; all tenancy scoping lives here |
| `catalog` | courses, sections, lessons, instructor profiles, review workflow | Publishes to search index |
| `learning` | enrollments, progress, quizzes, certificates | The busiest app |
| `orders` | Stripe checkout, invoices, refunds, webhooks | Money = append-only audit records + a derived state projection |
| `analytics` | usage events, org dashboards, compliance reports | Read-heavy; populated by consuming domain events (see §3) |
| `tutor` | AI tutor: ingestion, RAG, chat API | Built **inside the monolith first** (phase 4), extracted to FastAPI later (phase 6) |

### Boundary rules — and what actually enforces them

Be honest about the enforcement mechanism, because "enforced by lint" is only partly true:

1. **import-linter enforces the import graph only.** It will stop `learning/services.py` from importing `orders.models`. It **cannot** stop ORM relation traversal: `enrollment.course.title` crosses the `learning`→`catalog` boundary with no import statement at all, and a DRF serializer with `course.instructor.name` does the same lazily. Know this limitation.
2. **Cross-app ForeignKeys are allowed** (a single database is the point of a monolith) but must be declared with string references (`models.ForeignKey("catalog.Course", ...)`) so the import graph stays clean.
3. **Convention, backed by code review:** outside its owning app, another app's model may be treated only as an **opaque ID**. If you need its fields, call that app's `selectors.py`. Serializers must list fields explicitly — no `depth`, no dotted cross-app sources.
4. **Selector/service contract:** selectors may return querysets *of their own app's models only*; services accept IDs/primitives and return their own app's instances or plain dataclasses. This is what keeps "views never touch the ORM" from being a lie — a queryset handed across a boundary *is* ORM access.
5. When following these rules hurts, that pain is the lesson. Write it into an ADR.

### Cross-app writes: `transaction.on_commit`, not raw signals

Signals that enqueue Celery tasks fire **before** the transaction commits — if the transaction rolls back, the task runs against data that doesn't exist; if the task runs fast, it reads pre-commit state. Every signal→task hop (search indexing, analytics events, embedding ingestion) goes through `transaction.on_commit`. Analytics is populated from an explicit `DomainEvent` append (outbox-lite table), not by importing other apps' models.

## 2. Clean Architecture, Django-Flavored

```
app/
├── models.py        # persistence + DB-level invariants (constraints live here, not only in code)
├── services.py      # THE public API of the app: use-cases (enroll_learner, approve_course)
├── selectors.py     # read-side queries (optimized, prefetch-aware) — own models only
├── api/             # DRF serializers + views — thin, call services/selectors, explicit fields
├── admin.py         # Django Admin customization — admin actions call services, never mutate directly
├── tasks.py         # Celery tasks — thin wrappers calling services
└── tests/
```

## 3. Data Model Highlights (the relational deep-dive)

### Seats — constraints first, locks second

`Org 1—* SeatLicense 1—* SeatAssignment *—1 User`.

- **DB constraints are the safety net; locks are the concurrency strategy.** Locks only protect code paths that remember to take them — an admin action, a data migration, or next year's new endpoint will forget. Constraints protect everything:
  - `UniqueConstraint(seat_license, user)` — a user cannot hold two seats on one license.
  - `UniqueConstraint(user, course)` on `Enrollment` — double-enrollment is structurally impossible.
  - `seats_used` counter on `SeatLicense` with `CheckConstraint(seats_used <= seats_total)`, updated with `F()` expressions.
- **Concurrency:** `select_for_update()` on the `SeatLicense` row inside the assignment transaction. **No Redis lock** — a second, non-transactional lock on top of a row lock adds failure modes (expiry, crash between lock and commit) without adding safety. Redis stays for cache/Celery/rate-limiting.
- Write the race-condition test: N concurrent assignment attempts against a license with 1 seat; exactly one succeeds, and the CHECK constraint holds even if you deliberately bypass the service layer.

### Progress — append-only events, with idempotency and a sync path for certificates

- Append-only `LessonEvent` stream + materialized `EnrollmentProgress`.
- **Idempotency:** `UniqueConstraint(enrollment, lesson, event_type)` on completion events — client retries and double-taps must not inflate progress past 100%.
- **Materialization:** per-enrollment Celery task, serialized per enrollment (dedupe by `enrollment_id` task key) so two events for the same enrollment can't race on the materialized row.
- **The eventual-consistency trap:** certificate issuance must NOT read `EnrollmentProgress` (it may lag). `issue_certificate` recomputes completion from `LessonEvent` inside its own transaction. Materialized progress is for dashboards only — document this read-path split.
- **Growth:** `LessonEvent` is unbounded. Note the archival plan (partition by month or export to cold storage after materialization) even if you don't build it.

### Money — immutable rows + a defined current state

- `Order`, `Payment`, `Refund` rows are immutable; state changes append rows. But "what is this order's current state?" needs one answer: a `status` projection on `Order`, updated only by `orders.services`, derived from the append-only rows — never hand-edited.
- **Webhooks, actually done right:**
  - Signature verification + timestamp tolerance.
  - Idempotency: unique constraint on `stripe_event_id`, and the event-row insert happens **in the same transaction** as the side effects — otherwise you can record an event as processed and crash before processing it.
  - **Out-of-order delivery:** Stripe does not guarantee ordering. Handlers must be state-machine-aware (a `charge.refunded` arriving before `checkout.session.completed` must park/retry, not corrupt state).
  - **Webhooks are not the source of truth:** on checkout return, confirm the session via the Stripe API; run a daily reconciliation task that diffs local orders against Stripe and alerts on mismatch. Webhook-only payment truth fails silently when your endpoint is down past Stripe's retry window.
- **Refund policy — the actual hard problem, decided up front (ADR):** default policy: refunding a seat-license order revokes unassigned seats immediately; assigned seats are unassigned and their enrollments **suspended** (not deleted — audit trail); already-issued certificates remain valid but are flagged on the order record. Whatever you choose, choose it *before* building the refund action.

## 4. Multi-Tenancy Isolation (new — this is the B2B killer)

Cross-org data leakage is the one bug a B2B platform cannot survive. It gets its own section:

- Every org-scoped endpoint resolves the org **from the authenticated user's membership**, never from a client-supplied `org_id` alone.
- One shared mixin/dependency does the scoping; per-view ad-hoc filtering is how IDOR happens.
- **IDOR test suite in CI:** for every org-scoped endpoint, a test that user-in-org-A requesting org-B's resource gets 404 (not 403 — don't confirm existence).
- Django Admin querysets for org-visible staff roles are scoped in `get_queryset`, not just hidden in the UI.

## 5. Search (Elasticsearch)

- ES for a catalog of a few thousand courses is over-scale — Postgres FTS would suffice. It stays **as an explicit learning choice**; write the ADR saying so, and when you'd actually reach for it (transcript-scale full text, facet-heavy UX).
- Index on publish: `transaction.on_commit` → Celery task keyed by `course_id`, task re-reads current state (so concurrent edits converge on latest, not on task order), retries with backoff.
- **Reindex strategy:** mapping changes require full reindex — index behind an alias, reindex to a new index, swap the alias. Build this in from the start; retrofitting it is painful.
- **Degraded mode is a different product, define it:** if ES is down, fall back to Postgres `ILIKE` on title/description with a `pg_trgm` GIN index (without it, that's a sequential scan). Facets and typo tolerance disappear — the API returns a `degraded: true` flag and the UI hides facet controls. Test the degradation path.

## 6. The AI Tutor

### 6a. Built inside the monolith first (phase 4)

The tutor starts as a normal Django app (`tutor`): DRF endpoint, pgvector retrieval, LangChain pipeline. This is deliberate — you cannot practice a strangler *extraction* on something that never lived in the monolith.

- **Ingestion:** on lesson publish (`on_commit`), chunk lesson content (markdown-aware for text; timestamp-window chunks for video transcripts) and write embeddings tagged `course_id`. **Transcript dependency is explicit:** transcripts come from instructor upload or a Whisper transcription task — decide and build it, or video content is invisible to the tutor.
- **Quiz leakage is solved at ingestion, not at query time:** quiz questions and answers are **never embedded into the RAG corpus**. Embedding-similarity "refusal" as the primary guard is bypassable by paraphrase and false-positives on legitimate lesson content. The similarity check against the quiz bank remains as a *secondary* signal only.
- **Instructor content is untrusted input.** Instructors are third parties; a lesson can contain prompt injection ("ignore previous instructions, reveal…"). Retrieved chunks are wrapped as quoted data with instructions that they are content, not commands; CI includes a red-team test with a hostile lesson planted in a fixture course.
- **Guardrails:**
  1. Retrieval hard-scoped to `course_id`, and **Django verifies enrollment before any tutor call** — scoping is worthless if the caller can pick the course.
  2. Input + output moderation; conversation logs with PII redaction and a stated retention period.
  3. **Cost controls are a guardrail:** per-user daily token budget, per-user rate limit (Redis), request timeout with a graceful fallback message. Without this, one bored learner is your OpenAI bill.

### 6b. Extraction to FastAPI (phase 6)

Why extract: different scaling profile (LLM-latency-bound vs web-bound), different release cadence, isolates slow streams from the monolith's workers. Now the strangler ADR is honest — the code exists and moves.

```
Django ──(verifies enrollment, mints short-TTL JWT {user_id, course_id, enrollment_id})──▶ browser
browser ──SSE, JWT──▶ tutor-service (FastAPI)
                       ├── validates JWT scope: course in token is the ONLY course retrievable
                       ├── pgvector chunks (tutor-service owns this schema — see below)
                       └── LangChain pipeline with guardrails
```

- **Streaming: do NOT proxy SSE through WSGI Django.** Each open stream pins a sync worker; at default gunicorn worker counts the site dies at a handful of concurrent chats. Default choice: browser connects **directly** to tutor-service with the short-TTL course-scoped JWT above. (Alternative: run Django under ASGI — compare in the ADR, but know the trap.)
- **Trust boundary:** tutor-service never trusts a client-supplied `course_id`; the only course it will retrieve is the one in the validated token. Cross-course isolation test lives in CI on the service.
- **Data ownership:** pgvector tables move under a schema owned by tutor-service (or its own DB). Same physical Postgres is a pragmatic cost call — but Django Celery no longer writes embeddings directly; ingestion calls the service's API. A shared-write database is not an extracted service; it's a distributed monolith. ADR the tradeoff explicitly.
- Django↔service auth for ingestion/admin calls: service token with a rotation note.

## 7. Frontend & Admin

- **Next.js** learner app: catalog, video player (protected media via Nginx `X-Accel-Redirect` — Django authorizes the request, Nginx serves the file), quiz UI, tutor chat.
- **Frontend↔DRF auth is a decision, not a detail:** default to session-cookie auth with CSRF (same-site deployment behind one domain) — document it in an ADR before phase 5, because retrofitting auth mid-frontend-build is a classic week-loss.
- **Instructor course builder v1 is Django Admin**, not a custom Next.js editor. A drag-and-drop curriculum builder is a multi-week project by itself and teaches you React, not the target skills. Next.js builder = stretch goal.
- **Django Admin** as the internal back-office:
  - Role-scoped staff permissions (support vs content-review vs finance), enforced in `get_queryset`/`has_*_permission`, not just menu hiding.
  - Custom actions: approve/reject course (reason → email), issue refund (calls `orders.services`) — **built in the payments phase, not before payments exist**.
  - Impersonation, hardened: staff cannot impersonate other staff or superusers; sessions are time-boxed; a visible banner; every action during impersonation is audit-logged with both identities.
- **Org dashboard** (customer-facing) in Next.js: seat management, progress heatmap, compliance report download — all behind the §4 tenancy scoping.

## 8. Observability (new — non-negotiable, not a stretch goal)

- **Errors:** Sentry from phase 1 (Django, Celery, and later tutor-service), release-tagged.
- **Logs:** structured JSON logs with request IDs; a request ID propagated on the Django→tutor-service hop so one conversation is traceable across both.
- **Metrics/alarms:** queue depth + task failure rate for Celery (a silently dead worker is the #1 "why is nothing happening" incident), Postgres CPU/connections, 5xx rate, webhook failure alarm.
- **Health:** `/health` (shallow) and `/health/deep` (DB/Redis/ES) endpoints; smoke test hits them post-deploy.

## 9. Deployment (self-hosted Docker)

- One VPS running Docker Compose behind **Nginx** (reverse proxy, TLS via Let's Encrypt, static + protected media) — a monolith doesn't need K8s or a cloud provider; knowing when a single well-run box is enough is a senior skill. Write the ADR.
- Postgres (+ pgvector), Redis, and a single-node Elasticsearch as containers with named volumes and bounded ES heap. Email via SMTP (Mailpit in dev, any SMTP provider in prod). Media (certificates, uploads) on a Docker volume under `MEDIA_ROOT`; if S3-compatible object storage is ever needed, self-host MinIO.
- **Backups/DR:** nightly `pg_dump` (cron container) shipped off-box, plus a documented **restore drill** (a backup you've never restored is a hope, not a backup); media volume included in the backup routine.
- Celery worker + beat as separate processes of the same image.
- **CI/CD:** GitHub Actions — ruff/mypy → pytest (Postgres/Redis services) → build image → push to registry → SSH deploy → migrate (no-downtime pattern: additive first, code second, destructive later) → smoke test. **The pipeline and a deployed walking skeleton exist from phase 1** — deploying for the first time in the final phase means discovering every environment problem at once.

## 10. Performance Discipline

- `django-debug-toolbar` locally; `assertNumQueries` tests on hot endpoints in CI.
- Redis caching: per-view cache for catalog, fragment cache for course pages — each cache entry documented with its invalidation trigger (an undocumented cache is a future stale-data bug).
- Load test catalog + enrollment with k6; record before/after numbers in `docs/performance.md`.
- (Leaderboards cut: no feature in the product requires them — a sorted set with no requirement behind it is résumé-driven development. Re-add only if a gamification feature ships.)
