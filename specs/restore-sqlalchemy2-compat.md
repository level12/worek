# Worek Restore Cleanup Should Tolerate Cascade-Removed Objects

## Status

Implemented

## Context

Worek restore is expected to clean database objects that would conflict with a restore and to
tolerate objects that are already absent.

Cleanup currently fails for a table-owned PostgreSQL sequence. For example, dropping the `role`
table with `CASCADE` also removes `role_id_seq`, but cleanup later attempts to drop that sequence
explicitly and raises `psycopg2.errors.UndefinedTable`. The restore never begins.

This appears to be a transaction-visibility regression from the SQLAlchemy 2 compatibility work:

- `drop_schema()` performs DDL through one connection but does not commit until all cleanup is
  complete.
- Catalog helpers open separate connections, which cannot observe the cleanup connection's
  uncommitted catalog changes.
- A catalog helper can therefore correctly list an object from the last committed catalog state
  even though cascading DDL has already removed it within the cleanup transaction.
- The subsequent `DROP` does not use `IF EXISTS`, and the current exception handling re-raises the
  missing-object error.

## Desired Behavior

- Restore cleanup completes when an object was removed as a consequence of an earlier cleanup
  operation.
- Catalog reads used during cleanup are consistent with cleanup operations already performed.
- Unexpected database failures remain visible; resilience should not broadly suppress errors.
- Existing CLI behavior and restore formats remain unchanged.

## Recommended Direction

Use an internal `_begin()` context manager to establish the cleanup connection and transaction on
`self._conn`. Methods participating in cleanup must assert that `self._conn` is active and use it
for both catalog reads and DDL. Calling those methods outside an `_begin()` context is an explicit
API usage error; they must not silently open independent connections or transactions.

Make schema cleanup explicitly tolerant of already-absent objects by using PostgreSQL's `IF
EXISTS` support wherever available. This complements the consistent transaction boundary by also
handling objects removed through cascades or concurrent activity without suppressing unexpected
database errors.

## Validation

Add a regression test using a table with an owned `SERIAL` or identity sequence. Cleaning its
schema should not raise after the table drop cascades to the sequence, and the restore should be
able to proceed.

Retain coverage for independently owned objects and verify that unexpected SQL errors are not
silently ignored.

## Acceptance Criteria

- The reported table-owned-sequence failure no longer occurs.
- Cleanup remains safe when an object disappears because of an earlier cascading drop.
- The full Worek test suite passes.

## Validation Outcome

- The focused PostgreSQL suite passes with 23 tests passed and 1 skipped.
- The full Worek suite passes with 25 tests passed and 1 skipped.
- Ruff formatting and lint checks pass.

## Non-Goals

- Redesigning the backup or restore workflow.
- Changing the CLI contract.
- Ignoring arbitrary cleanup exceptions.
