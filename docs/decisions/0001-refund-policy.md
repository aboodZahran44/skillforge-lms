# ADR 0001: Refund Policy

## Status
Accepted

## Context
SkillForge sells seat licenses to organizations. Employees get seats
assigned from that license, complete lessons, take quizzes, and earn
certificates. At some point an org may request a refund. Before writing
any Stripe or refund code, we need a clear, written answer to: what
happens to seats already assigned, learner progress already made, and
certificates already issued?

Writing this after the code exists is how refund logic ends up decided
ad hoc inside a webhook handler — exactly what we want to avoid.

## Decision

**1. Refund window:** Refunds are only accepted within **14 days** of
the original purchase date. Requests after that window are rejected at
the service layer before any Stripe refund call is made.

**2. Seat revocation:** When an order is refunded, every seat assigned
under that order is **revoked immediately** — the employee loses access
to the course(s) right away. This is a deliberate choice: it keeps the
seat-count invariant (`seats_used <= total_seats`) trivially true at all
times, with no "grace period" state to track.

**3. Progress data is preserved, not deleted:** Revoking a seat removes
*access*, not *history*. `LessonEvent` and `QuizAttempt` rows for that
enrollment are kept as-is. This follows the same principle already used
for money rows and lesson events elsewhere in the system: historical
records are never destroyed, only superseded. If the same employee is
re-enrolled later (new seat, same or different order), their prior
progress remains visible for audit purposes, but does not automatically
restore access or count toward a new attempt.

**4. Certificates already issued are never revoked.** A certificate is
proof that the learner met the pass bar at a point in time. Refunding
the org's payment is a billing event between SkillForge and the org — it
does not retroactively undo something the learner actually achieved.
Once issued, a `Certificate` row is permanent.

**5. Refunds are whole-order only for now.** A single order refund
revokes exactly the seats purchased in that order. Partial (partial-
quantity) refunds are out of scope for this phase — an org that wants to
reduce seat count without refunding an entire order can be handled as a
separate feature later.

## Consequences

- The refund action needs to look up seats by `order`, not just by
  license, so we can revoke only the seats tied to the refunded order.
  This means `SeatAssignment` (or the purchase flow) must record which
  order it came from — a field we don't have yet and will add in this
  phase.
- Because seats can be revoked without deleting learning history, an
  `Enrollment` needs a way to represent "seat revoked" distinct from
  "never had a seat" — to be modeled explicitly when we build the
  purchase/refund flow (not decided here).
- Support cost is a deliberate tradeoff: once a learner earns a
  certificate, that specific seat's value cannot be clawed back even via
  refund. This is considered acceptable — it avoids the much worse
  outcome of silently revoking someone's earned credential.

## Open questions for implementation (not blocking this ADR)
- Exact mechanism for tracking "which order granted which seat
  assignment" — decided when we design the `Order`/`SeatAssignment`
  relationship in this phase.