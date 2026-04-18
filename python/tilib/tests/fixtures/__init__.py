"""Parameter fixtures for Layer 1 (equivalence) and Layer 4 (sweep) tests.

Each ``*_params.py`` module mirrors one of the namelist inputs under
``test_run/inputs/`` as a Python dict plus an :func:`apply` helper that
feeds those values through :py:meth:`tilib.TiLib.set_param`.

Only parameters registered in ``ti/ti_param_registry.f90`` are forwarded;
namelist keys that are not yet in the registry (e.g. ``PM`` -- the
char-valued ``KID_NS``) are listed as ``UNREGISTERED_KEYS`` so future
registry growth can pick them up without re-reading the ``.in`` file.

These fixtures are *hand-maintained* and only need to be updated if the
corresponding ``test_run/inputs/ti_*.in`` changes.
"""
