# Redesign pg version detection and executable selection

> Is test_command_uses_correct_exe_version() even applicable anymore?

No—not as written.

It has three problems:

- **Always skipped:** Current CI never sets `PGVERSION`. That variable was set by the old
  2020 CircleCI PostgreSQL-version matrix.
- **Doesn’t test executable selection:** `MockCLIExecutor` only confirms that Worek sets
  `PGCLUSTER`.
- **The feature is currently ineffective:** `pg_wrapper` ignores/removes `PGCLUSTER` when
  Worek also passes `--host`. A local check demonstrated:

```text
PGCLUSTER=16/localhost: pg_dump --version
→ PostgreSQL 16

PGCLUSTER=16/localhost: pg_dump --version --host=localhost
→ PostgreSQL 18
```

Additionally, `pg_wrapper` deliberately always uses the newest installed `psql`, which is
the command this test exercises.

So the test provides false confidence. I’d remove it. Then decide separately whether to:

- remove the documented `--version` feature, or
- redesign executable selection and add an integration test that checks the actual invoked
  binary version.
