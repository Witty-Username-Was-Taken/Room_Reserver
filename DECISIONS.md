# Decision Log — Room Booking System

Format: what was decided, why, and what it cost. Update this before the artifact, not after.

## D1. Time model: bookings as ranges (not materialized slots)
**Decision:** Bookings store `start_time`/`end_time` as `timestamptz`. No slots table.
**Rationale:** One table owns time; no nightly slot-generation job; no slot↔booking reconciliation; Postgres exclusion constraints give database-enforced overlap prevention.
**Cost:** Availability is computed (overlap queries) rather than read from materialized rows.
**Note:** This reversed an earlier fixed-slots decision — consciously, after weighing both.

## D2. 15-minute granularity — RESOLVED: enforced in the database
**Decision:** Start/end must land on :00/:15/:30/:45 with zero seconds. Enforced by CHECK constraints (`EXTRACT(MINUTE ...) % 15 = 0 AND EXTRACT(SECOND ...) = 0`) on both columns.
**Rationale:** Same "binds every writer" logic as D5. App-level validation may be added later purely for friendlier error messages — correctness already lives in the DB.

## D3. Holds are a booking status, not a table
**Decision:** A hold is a `bookings` row with `status='pending'` and `expires_at` set. Confirmation is an UPDATE, not a row move.
**Rationale:** One state machine; no data shuffling on conversion; abandoned holds remain as history (free analytics).
**Cost:** `expires_at` is nullable and only meaningful for pending rows. Accepted tradeoff — NULL is the honest value for a confirmed booking's expiry.

## D4. Booking state machine
`pending → confirmed → completed | cancelled | no_show`, plus `pending → expired`.
Six statuses total, as the `booking_status` Postgres enum. Illegal transitions (e.g., cancelled → confirmed) enforced in the WHERE clause of update queries.
**RESOLVED (confirm-vs-expiry race):** every transition out of `pending` is an atomic compare-and-swap — the WHERE clause is both the check and the act:
```sql
-- confirm (API):
UPDATE bookings SET status='confirmed', expires_at=NULL
WHERE id=$1 AND user_id=$2 AND status='pending' AND expires_at > now()
RETURNING id;
-- expire (sweep):
UPDATE bookings SET status='expired'
WHERE status='pending' AND expires_at <= now();
```
`> now()` / `<= now()` partition time exactly — one predicate true per row per instant. Row locks serialize racers; the loser matches zero rows. API reads RETURNING/rowcount: zero rows = lost the race = 410, never a false 200. Ownership check rides in the same atomic breath.
**Open:** Expiry driver — lazy vs. active Celery sweep. Demoted from architectural fork to operational tuning: the CAS pattern is identical either way.

## D5. Double-booking prevention: invariant in the database, UX in the app
**Decision:** Correctness lives in a Postgres exclusion constraint:
```sql
EXCLUDE USING gist (
  room_id WITH =,
  tstzrange(start_time, end_time, '[)') WITH &&
) WHERE (status IN ('pending', 'confirmed'))
```
Application keeps a pre-check for UX only. Insert either succeeds or raises exclusion violation → 409.
**Rationale:** Check-then-insert is a TOCTOU race. The GiST-backed constraint serializes conflicts atomically and binds every writer (API, Celery, raw psql).
**Supporting facts:**
- Correct overlap predicate: `existing.start < new.end AND existing.end > new.start`.
- Requires `btree_gist` (migration #1) — GiST natively handles ranges/`&&` but not scalar `=`; the extension teaches it, so `room_id` can join the index.
- Partial constraint: cancelled/expired rows physically leave the index — old bookings never block rooms, and the index stays small.

## D6. Auth: deliberately boring
**Decision:** Email + hashed password (bcrypt/argon2), two roles via `role` enum on `users`. No RBAC tables (YAGNI — migration path exists if per-building admins appear). Email is the sole login identifier; no username column. Uniqueness via functional unique index on `lower(email)` (case-insensitive).
**Open:** JWT vs. session cookies.

## D7. Buildings own operating hours
**Decision:** `building_hours(building_id, weekday, start_time, end_time)` with composite PK `(building_id, weekday)` — uniqueness IS the primary key, no surrogate id. `weekday` is a Postgres enum; `start_time`/`end_time` are `time` (time-of-day, not instants).
**Decision (overnight hours):** NO `end > start` CHECK on this table — `end_time < start_time` is legitimate and means hours wrap past midnight (e.g., open until 2am during finals). Availability logic must handle wraparound.
**Open:** Admin changes hours after bookings exist for next week — reconciliation story.

## D8. Room types — RESOLVED: collapsed to a varchar column
**Decision:** No `room_types` table. `rooms.room_type` is varchar — chosen over enum because types are admin-owned vocabulary, not code-owned (adding "podcast studio" shouldn't require a migration; PG enums are also awkward to modify).
**Cost:** DB won't reject "Study Pod" vs "study pod". Mitigation: types come only from seed data; app validates against the known set.
**Re-entry condition:** Resurrect the table (defaults + per-room overrides via COALESCE) when types grow real attributes or an admin UI manages them.

## D9. Settings: global key-value table
**Decision:** `settings(name, value, comment)` for global policy only (hold TTL, booking window, weekly caps). `comment` nullable. Per-room/per-building config lives on those tables. Sort every config item by scope first.

## D10. Type discipline
- Instants → `timestamptz` (`DateTime(timezone=True)` — SQLAlchemy's bare `DateTime` is timestamp WITHOUT tz; the flag is mandatory every time).
- Time-of-day → `time`. Knowing which is which is the point.
- Closed code-owned vocabularies (`status`, `role`, `weekday`) → enums with explicit PG type names; enum names == values, always. Admin-owned vocabularies (`room_type`) → data, not enums.

## D11. The ERD is not the schema; the model is not the migration
Constraints inexpressible in dbdiagram (exclusion, CHECKs, btree_gist) live in the models AND the hand-written migrations. **Alembic migrations are the source of truth.** Migration #1: `CREATE EXTENSION btree_gist`. Migration #2: tables + constraints. Verify emitted DDL with `alembic upgrade head --sql` and diff against D5's spec. Never hand-edit the database.
**Learned in practice:** migrations are an append-only ledger — each revision file is an immutable chain link; manual edits live in their revision forever and never need re-applying. Autogenerate diffs models vs. current DB and emits only deltas. psycopg escaping: autogenerate emits `%%` for literal `%` (pyformat parameter style); after any escaping edits, verify the real constraint text via `\d bookings` — the catalog is the only truth.

## D12. Async SQLAlchemy end to end
**Decision:** Async engine/sessions (SQLAlchemy 2.0 + psycopg v3 async: `postgresql+psycopg://`).
**Rationale:** I/O concurrency under load is the point of the project (milestone 4 publishes p99s).
**Cost:** Every session touch is `await`; and implicit lazy-loading raises under async — so:
**Corollary:** `lazy="raise"` on all relationships; every query declares its loads explicitly (`selectinload`/`joinedload`). Relationships defined only where traversed (Booking↔User, Booking↔Room, Room↔Building) — sparse is a feature.

## D13. Defaults discipline
`server_default` (DB-side, binds every writer) only for bookkeeping columns: `created_at = now()`, `status = 'pending'` (a booking is born pending by definition). Business data (`start_time`, `end_time`, `expires_at`) has NO defaults — missing values must fail loudly, not be papered over with plausible lies.

## D14. Deletion policy
**Decision:** `ondelete="RESTRICT"` on every FK — deleting a user/room/building with dependent rows is an error; deletion is an explicit, handled operation. History is analytics; CASCADE would vaporize it.
**Open:** Soft-delete (`is_active`) for rooms that get decommissioned but whose history matters.

## D15. Range bounds semantics: half-open `[)`
Inclusive start, exclusive end. A 1:00–2:00 and a 2:00–3:00 booking share the boundary instant but do NOT overlap — back-to-back bookings work. `[]` would make adjacent bookings collide. One character encoding a product rule.

## D16. Tooling & environment
- `pyproject.toml` + `uv` (+ `uv.lock`) — no hand-maintained requirements.txt (generate one only if a deploy target demands it: declared truth in one place, artifacts derived).
- uv owns the `.venv`; `uv run` for everything. Environment boundary follows deployment boundary — future React frontend gets a sibling dir with its own world; small monorepo.
- conda stays in ML land (CUDA/binary deps); web land is uv. Different ecosystems on purpose.
- Style: always write `= mapped_column()` even when empty, so every column name is a real, referenceable binding (the unbound-`email` lesson).
- `models/__init__.py` imports all model modules — that's what registers tables on `Base.metadata` for Alembic; a missing import silently drops a table from autogenerate.

## Process notes
- Four times a settled decision evaporated between discussion and artifact (slots→bookings; status/expires_at columns; truncated status enum; missing WHERE on the exclusion constraint). The log exists to close that gap: record when decided, diff artifacts against the log before review.
- Review findings decay in ~a day; interesting fixes land, boring ones don't. Discipline: fix the WHOLE list before the next diff.

## Open items queue
1. Expiry mechanism: lazy vs. sweep (D4 — now operational tuning, not architecture)
2. JWT vs. session cookies (D6)
3. Hours-change reconciliation when future bookings exist (D7)
4. Overnight-hours wraparound in availability logic (D7 — milestone 2)
5. Soft-delete for rooms (D14)

---

# Milestone 1 Closeout — Verification Probes

Schema frozen 2026-07-17. Every probe below was run by hand against the migrated database.
Each proves a specific clause of the D5/D15 design. (Transcripts lightly trimmed; replace
representative output with your actual psql output where it differs.)

## Probe 1 — Exclusion scope: overlap is per-room (`room_id WITH =`)
```sql
INSERT INTO bookings (user_id, room_id, start_time, end_time, status)
VALUES (1, 1, '2026-07-20 14:00+00', '2026-07-20 15:00+00', 'confirmed');
-- INSERT 0 1
INSERT INTO bookings (user_id, room_id, start_time, end_time, status)
VALUES (2, 2, '2026-07-20 14:00+00', '2026-07-20 15:00+00', 'confirmed');
-- INSERT 0 1  ← same time, different room: allowed
```

## Probe 2 — Half-open bounds: back-to-back bookings (`[)`, D15)
```sql
INSERT INTO bookings (user_id, room_id, start_time, end_time, status)
VALUES (2, 1, '2026-07-20 15:00+00', '2026-07-20 16:00+00', 'confirmed');
-- INSERT 0 1  ← shares the 15:00 boundary instant with probe 1; no collision
```

## Probe 3 — Partial constraint: cancelled rows release their range (`WHERE status IN ...`)
```sql
UPDATE bookings SET status = 'cancelled' WHERE room_id = 1 AND start_time = '2026-07-20 14:00+00';
-- UPDATE 1
INSERT INTO bookings (user_id, room_id, start_time, end_time, status)
VALUES (2, 1, '2026-07-20 14:00+00', '2026-07-20 15:00+00', 'confirmed');
-- INSERT 0 1  ← overlaps the cancelled booking exactly; allowed, because
--               cancelled rows physically leave the partial GiST index
```

## Probe 4 — The race: two connections, one referee (TOCTOU immunity)
Two psql sessions. A inserts inside an open transaction and does not commit — a request
frozen mid-flight. B attempts an overlapping insert.

```
-- Terminal A                          -- Terminal B
BEGIN;
INSERT ... 14:00–15:00 ...;
-- INSERT 0 1 (uncommitted)
                                       BEGIN;
                                       INSERT ... 14:30–15:30 ...;
                                       -- (hangs — waiting on A's fate)
COMMIT;
                                       -- ERROR: conflicting key value violates
                                       --   exclusion constraint
                                       --   "no_overlapping_room_bookings"
                                       ROLLBACK;
```

Rerun with A ending in `ROLLBACK` instead: B unfreezes and its insert **succeeds** —
the conflict evaporated with A's transaction, so waiting (not failing early) was correct.

**Why this matters:** the hang is Postgres serializing the conflict inside the GiST index —
the referee no application-level check-then-insert can have. This is the slow-motion version
of the milestone-2 load test (100 concurrent requests, exactly one winner).

## Also verified via `\d bookings`
- CHECK constraints present with correct `% 15` (post-`%%` escaping fix) and second == 0
- `tstzrange(start_time, end_time, '[)')` bounds intact
- Partial WHERE compiled to `status = ANY (ARRAY['pending','confirmed']::booking_status[])` — Postgres's spelling of `IN`, same semantics
- FKs with `ON DELETE RESTRICT` per D14

**Milestone 1: complete.** Next: FastAPI skeleton, async session-per-request, POST /bookings
(pre-check for UX, constraint for correctness), CAS confirm endpoint (409/410), then the
automated concurrency test.
