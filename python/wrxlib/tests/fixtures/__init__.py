"""Namelist-mirror fixtures for wrxlib Layer 1 / Layer 4 tests.

Each fixture module exposes ``SCALARS`` / ``ARRAYS`` /
``UNREGISTERED_KEYS`` / ``BASELINE_NAME`` / ``SOURCE_INPUT`` /
``NRAY_REQUEST`` plus an :func:`apply` helper that forwards the
*registered* subset of a wrx namelist into a :class:`wrxlib.Wrxlib`
handle. Mirrors ``python/trlib/tests/fixtures``.
"""
