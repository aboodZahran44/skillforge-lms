# SkillForge — Project Handoff

> **Status date:** 2026-07-26 (updated same day) · **Branch:** `master`
> **Position in roadmap:** **Phase 2 complete** — Elasticsearch integration finished, certificate persistence fixed, docs descoped. Next: **Phase 3 — Orders & Payments**.
> **Scope change:** cloud (AWS) deployment has been **removed from project scope entirely**. The target is a local / self-hosted Docker stack. The design docs have been updated accordingly.

---

## 1. Architecture Overview (current, local-only stack)

| Layer | Technology | Where |
|---|---|---|
| Web framework | Django 6.0.7, Python 3.13 | `config/`, four apps |
| Database | PostgreSQL 16 | `db` service in [docker-compose.yml](docker-compose.yml) |
| Async tasks | Celery 5.6.3, Redis 7 broker/result backend | `worker` service, [config/celery.py](config/celery.py) |
| Search | Elasticsearch 8.15.0 (single-node, security off, 512 MB heap) | `elasticsearch` service |
| PDF generation | reportlab (certificates, persisted to `MEDIA_ROOT`) | [learning/tasks.py](learning/tasks.py) |
| Containers | Dockerfile (python:3.13-slim, non-root `appuser`) + Compose: `db`, `redis`, `elasticsearch`, `web`, `worker` | repo root |
| CI | GitHub Actions: ruff → mypy → import-linter → `manage.py test` with a Postgres 16 service | [.github/workflows/ci.yml](.github/workflows/ci.yml) |
| Boundaries | import-linter contracts (orgs↛accounts, learning↛catalog/orgs); cross-app FKs via string refs | [setup.cfg](setup.cfg) |

Django apps as bounded contexts:

- **`accounts`** — custom email-based `User` (`AUTH_USER_MODEL = accounts.User`), no username, `UserManager` with `create_user`/`create_superuser`.
- **`orgs`** — `Organization`, `SeatLicense`, `SeatAssignment` (B2B seat licensing).
- **`catalog`** — `Course` (status workflow: draft → pending_review → published), `Section`, `Lesson`, `Quiz`, `QuizQuestion`, `QuizChoice`. Owns search (`search.py`, `services.py`, `tasks.py`).
- **`learning`** — `Enrollment`, `LessonEvent`, `QuizAttempt`, `QuizAnswer`, `Certificate`, quiz scoring service, certificate Celery task.

---

## 2. Implemented Features

### Phase 1 (complete — commits `c0ed7eb`, `a32577d`)
- Custom user model from day one; superuser/staff flags; email as username field.
- **Seat licensing with race safety:**
  - DB-level invariants: `CheckConstraint(seats_used <= total_seats)` on `SeatLicense`; `UniqueConstraint(seat_license, user)` on `SeatAssignment` ([orgs/models.py](orgs/models.py)).
  - [`assign_seat`](orgs/services.py) uses `transaction.atomic` + `select_for_update()` on the license row.
  - Proven by a real two-thread race test using `TransactionTestCase` + `threading.Barrier` ([orgs/tests/test_services.py](orgs/tests/test_services.py)).
- Docker Compose (db/redis/web/worker), non-root container user.
- Lint/type/boundary tooling wired locally and in CI (ruff 0.16, mypy 2.3 + django-stubs, import-linter 2.13).

### Phase 2 (complete)
- **Catalog:** course/section/lesson hierarchy with per-parent `order` unique constraints; course review-status workflow.
- **Learning:**
  - `Enrollment` — `UniqueConstraint(user, course)` (no double-enrollment), org FK, `Enrollment.objects.for_org(org)` tenancy queryset, verified by [test_tenancy.py](learning/tests/test_tenancy.py).
  - `LessonEvent` — append-only, idempotent via `UniqueConstraint(enrollment, lesson, event_type)`; admin is read-only.
  - `Certificate` — OneToOne to `QuizAttempt`, PDF persisted via `FileField` to local media storage; generation task is idempotent and returns the certificate ID (JSON-serializable). Tested in [test_certificates.py](learning/tests/test_certificates.py).
- **Quizzes & scoring:** [`submit_quiz_attempt`](learning/services.py) validates quiz↔course match, requires an answer per question, scores transactionally, and enqueues certificate generation via `transaction.on_commit` only on pass. Tested in [test_quiz_scoring.py](learning/tests/test_quiz_scoring.py).
- **Search (Elasticsearch), end to end:**
  - Write side: [`catalog/services.approve_course`](catalog/services.py) publishes a course and enqueues [`sync_course_to_index`](catalog/tasks.py) via `transaction.on_commit`; the task re-reads current state and indexes (published) or removes (unpublished/deleted). The admin approve action now calls the service per course instead of `queryset.update()`.
  - Read side: [`search_courses`](catalog/search.py) — fuzzy multi-match on title/description, filtered to published, capped at 20 results — with automatic fallback to a Postgres `icontains` search returning `degraded=True` when ES is unreachable.
  - Endpoint: `GET /api/courses/search?q=…` → `{"results": [...], "degraded": bool}` ([catalog/views.py](catalog/views.py)).
  - Bootstrap: `manage.py ensure_search_index` (degrades with a warning if ES is down); `seed_demo_data` also creates the index and indexes published courses.
  - Verified: 18 tests green (mocked-client unit tests keep CI free of an ES service) plus a live smoke test against the real container — fuzzy match ("smoke tsting" → "Smoke Testing 101") and idempotent delete via `.options(ignore_status=404)` both confirmed.
- **Django Admin:** `CourseAdmin` approve action (service-backed), read-only `LessonEvent` and `Certificate` admins, staff roles via Django Groups (commit `e3ce061`).
- **Seed data:** `python manage.py seed_demo_data`.

---

## 3. Resolved During Phase 2 Close-out (2026-07-26)

All items from the previous handoff's "incomplete or broken" list were fixed:

- [x] 1. `remove_course` migrated to the 8.x client API (`.options(ignore_status=404)`).
- [x] 2. `requirements.txt` re-saved as UTF-8 (was UTF-16 / binary to git).
- [x] 3. `search_courses(query)` added — multi-match, published-only filter.
- [x] 4. Indexing wired: `sync_course_to_index` Celery task triggered via `on_commit` from the new `catalog/services.approve_course`; admin action refactored off `queryset.update()`.
- [x] 5. `ELASTICSEARCH_URL` added to the `worker` service in Compose.
- [x] 6. `ensure_search_index` management command; seeding also builds the index.
- [x] 7. Postgres fallback with `degraded=True` flag.
- [x] 8. `GET /api/courses/search?q=` endpoint (first public URL beyond `/admin/`).
- [x] 9. Tests: 12 new tests (service, task, search+fallback, view, certificates); CI needs no ES service.
- [x] 10. Committed in logical commits.
- [x] 11. Certificate persistence: `Certificate` model + `FileField` on local media (`media/` gitignored); task idempotent, returns cert ID instead of raw bytes.
- [x] 12. Docs descoped from cloud: deployment story is now Docker Compose behind Nginx (TLS via Let's Encrypt) on a self-hosted host; protected media via `X-Accel-Redirect`; SMTP email (Mailpit in dev); `pg_dump` backup + restore drill.

**Known deferred items (intentional):**
- Course approval sends no notification email yet.
- `SECRET_KEY`/`DEBUG` are hardcoded dev values — move to env vars before calling the project done.
- Postgres fallback uses `icontains` without a `pg_trgm` index (fine at seed-data scale; add the index when catalog grows).

---

## 4. Next: Phase 3 — Orders & Payments

Per [docs/learning-roadmap.md](docs/learning-roadmap.md):

- [ ] Stripe test mode: checkout session for seat purchases.
- [ ] Webhooks: signature-verified, idempotent (event row + side effects in one transaction), out-of-order tolerant; API confirmation on checkout return; daily reconciliation task.
- [ ] Immutable `Order`/`Payment`/`Refund` rows + a single derived `Order.status` projection.
- [ ] Refund policy ADR (seats/enrollments/certificates side-effects) **before** the refund admin action.
- [ ] Org invoicing + seat purchase flow (replaces fixture-seeded licenses).

---

## 5. How to Run Locally

```bash
docker compose up -d          # db, redis, elasticsearch, web, worker
docker compose exec web python manage.py migrate
docker compose exec web python manage.py ensure_search_index
docker compose exec web python manage.py seed_demo_data
docker compose exec web python manage.py test
```

Search: `curl "http://localhost:8000/api/courses/search?q=python"` (returns `degraded: true` if ES is down).
ES is at `http://localhost:9200` on the host, `http://elasticsearch:9200` inside Compose. Checks: `ruff check .`, `mypy .`, `lint-imports`.
