"""Parameter fixtures for Layer 1 (equivalence) and Layer 4 (sweep) tests.

Each ``*_params.py`` module mirrors one of the namelist inputs under
``test_run/inputs/`` as a Python dict plus an :func:`apply` helper that
feeds those values through :py:meth:`trlib.Trlib.set_param`.

Only parameters registered in ``tr/tr_param_registry.f90`` are forwarded;
namelist keys that are not yet in the registry (e.g. ``PROFN2``,
``PNBR0`` on ITER01) are listed as comments so future registry growth
can uncomment them without re-reading the ``.in`` file.

These fixtures are *hand-maintained* and only need to be updated if the
corresponding ``test_run/inputs/tr_*.in`` changes.
"""
