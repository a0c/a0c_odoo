.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=====================================================
Audit Log Decorator - Track arbitrary user operations
=====================================================

This module allows the administrator to log arbitrary user operations
performed on data models.

Usage
=====

Annotate methods to be logged with decorator ``@audit``, optionally providing
helper methods ``<method>_audit()`` to generate complex log messages.
``<method>_audit()`` receives all the same parameters as the original
``<method>()`` and should return a tuple ``(log_prefix, message)``:
``message`` is logged to audit database, while ``log_prefix`` joined with
``message`` via newline is logged to standard logger. The purpose of
``log_prefix`` is to give a short summary of the ``<method>``-s action,
including the user name, method/action, record name, etc -- all those data
that log record in audit database inherently contains.

True ``no_audit`` in context disables audit logging.
