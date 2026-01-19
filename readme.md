# Worek - A Database Backup Tool
[![nox](https://github.com/level12/worek/actions/workflows/nox.yaml/badge.svg)](https://github.com/level12/worek/actions/workflows/nox.yaml)
[![Codecov](https://codecov.io/gh/level12/worek/branch/main/graph/badge.svg)](https://codecov.io/gh/level12/worek)

Worek is a database backup tool.

* Create full binary backups of a PostgreSQL database
* Restore a text or binary backup of a PostgreSQL database
* Can restore a database over the top of an existing database (clears all data first) meaning you
  don't need a super user to restore a database.


## Usage

Create a backup with the contents going to a file:

```
$ worek backup -d database_name -f ./backup.bin
```


Create a backup with the contents going to STDOUT

```
$ worek backup -d database_name \
    | openssl enc -aes-256-cbc -pass file:password.txt -md sha256 -d -out backup.bak.enc
```


Restore a backup from STDIN. Note you have to use the `-F` property to specify
the type of backup you are handing. This is not required when using `-f` and
specifying the file path.

```
$ openssl enc -aes-256-cbc -pass file:password.txt -md sha256 -d -in backup.bak.enc  \
    |  worek restore -h localhost -d database_name -F c
```


Supports standard [PG environment
variables](https://www.postgresql.org/docs/current/libpq-envars.html)

```
$ PGPORT=5432 worek backup -d database_name -f ./backup.bin
```

## Postgres Client Version

Worek makes use of Postgres client utilities internally to create/restore backups. If multiple
versions of the utilities are present, by default Worek will attempt to match the version of the
utilities to the database server version.

You may also specify a particular version of the client utilities to use via the `--version` or `-v`
option. This feature requires `pg_wrapper` to be installed on the system.

```
$ worek backup -d database_name -f ./backup.bin -v 11
```


## Dev

### Copier Template

Project structure and tooling mostly derives from the [Coppy](https://github.com/level12/coppy),
see its documentation for context and additional instructions.

This project can be updated from the upstream repo, see
[Updating a Project](https://github.com/level12/coppy?tab=readme-ov-file#template-updates).


### Project Setup

From zero to hero (passing tests that is):

1. Ensure [host dependencies](https://github.com/level12/coppy/wiki/Mise) are installed

2. Start docker service dependencies (if applicable):

   `docker compose up -d`

3. Sync [project](https://docs.astral.sh/uv/concepts/projects/) virtualenv w/ lock file:

   `uv sync`

4. Configure pre-commit:

   `pre-commit install`

5. Run tests:

   `nox`


### Versions

Versions are date based.  A `bump` action exists to help manage versions:

```shell

  # Show current version
  mise bump --show

  # Bump version based on date, tag, and push:
  mise bump

  # See other options
  mise bump -- --help
```
