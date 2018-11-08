Worek - A Database Backup Tool
##############################

.. image:: https://circleci.com/gh/level12/worek.svg?style=shield
    :target: https://circleci.com/gh/level12/worek
.. image:: https://codecov.io/gh/level12/worek/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/level12/worek


Introduction
---------------

A logical database backup tool.

* Create full binary backups of a PostgreSQL database
* Restore a text or binary backup of a PostgreSQL database
* Can restore a database over the top of an existing database (clears all data
  first) meaning you don't need a super user to restore a database.


Usage
--------------

Create a backup with the contents going to a file

.. code::

  $ worek backup -d database_name -f ./backup.bin


Create a backup with the contents going to STDOUT

.. code::

  $ worek backup -d database_name \
      | openssl enc -aes-256-cbc -pass file:password.txt -md sha256 -d -out backup.bak.enc


Restore a backup from STDIN. Note you have to use the `-F` property to specify
the type of backup you are handing. This is not required when using `-f` and
specifying the file path.

.. code::

  $ openssl enc -aes-256-cbc -pass file:password.txt -md sha256 -d -in backup.bak.enc  \
      |  worek restore -h localhost -d database_name -F c


Supports standard `PG environment variables`

.. code::

  $ PGPORT=5432 worek backup -d database_name -f ./backup.bin


.. _PG environment variables: https://www.postgresql.org/docs/current/libpq-envars.html
