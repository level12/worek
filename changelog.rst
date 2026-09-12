Changelog
=========

2.0.0 released 2026-09-12
-------------------------

- Require Python 3.11+ and support Python 3.11 through 3.14 (78a39d0_)
- Restore SQLAlchemy 2 compatibility and reliable cascading schema cleanup (e787768_)
- Correctly identify PostgreSQL system schemas by the literal ``pg_`` prefix (564b2a2_)
- Modernize packaging and development tooling with Coppy, Hatch, uv, and Nox (dcd86c8_)
- Add automated PyPI publishing with trusted publishing (2e477c5_)

.. _78a39d0: https://github.com/level12/worek/commit/78a39d0
.. _e787768: https://github.com/level12/worek/commit/e787768
.. _564b2a2: https://github.com/level12/worek/commit/564b2a2
.. _dcd86c8: https://github.com/level12/worek/commit/dcd86c8
.. _2e477c5: https://github.com/level12/worek/commit/2e477c5


0.1.1 released 2021-02-01
-------------------------

- Allow PG client executable version to be specified (abff603_)

.. _abff603: https://github.com/level12/worek/commit/abff603


0.1.0 released 2019-04-03
-------------------------

- Cleanup Piping Mechanism (da86b5b_)
- Setup CI for PG9.6 and PG10 (002640b_)
- Cleanup API and add tests (e5371da_)
- Update Readme (0697703_)
- Add init for packages (78e6ec2_)
- Setup a Postgres Backup Tool (be27b46_)

.. _da86b5b: https://github.com/level12/worek/commit/da86b5b
.. _002640b: https://github.com/level12/worek/commit/002640b
.. _e5371da: https://github.com/level12/worek/commit/e5371da
.. _0697703: https://github.com/level12/worek/commit/0697703
.. _78e6ec2: https://github.com/level12/worek/commit/78e6ec2
.. _be27b46: https://github.com/level12/worek/commit/be27b46
