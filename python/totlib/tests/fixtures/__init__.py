"""Phase L-6 fixture package for totlib tests.

Each ``tot_*_params.py`` module here exposes the same symbols as the
trlib / eqlib fixtures so the equivalence / sweep drivers stay
schema-uniform. The big difference for tot is that **every** parameter
name MUST carry an ``<ns>:`` namespace prefix because the orchestrator
fans out to per-module registries (eq, tr, fp, ti, wr, wrx).

Symbols expected by the equivalence / sweep drivers:

* ``SCALARS``           -- dict[str, float|int] of namespaced scalar
                           params for ``tot.set_param`` (e.g.
                           ``"eq:RR": 6.5``, ``"tr:DT": 0.001``).
* ``ARRAYS``            -- dict[str, list|dict] of 1-origin (or
                           0-origin for ``eq:PSIB``) array elements.
                           Keys are namespaced (e.g. ``"tr:PN"``).
* ``STRINGS``           -- dict[str, str] for ``tot.set_param_str``
                           (e.g. ``"tr:KNAMEQ": "eqdata.demo2014"``).
* ``UNREGISTERED_KEYS`` -- tuple[str] of namelist keys that exist in
                           the input file but are not yet exposed in
                           any per-module registry; ``apply`` skips
                           them silently.
* ``BASELINE_NAME``     -- str, ``test_run/baselines/<name>/`` subdir.
* ``NTMAX``             -- int, the ``tot.run(ntmax=...)`` argument
                           used by Layer 1.
* ``apply(tot)``        -- callable that applies all of the above to
                           an open :class:`totlib.Tot` handle.

These fixtures are designed so the Layer 1 equivalence test and the
Layer 4 sweep can share the same realistic baseline parameter set;
sweeps then override individual axes (e.g. ``eq:RR`` / ``eq:BB``).
"""
