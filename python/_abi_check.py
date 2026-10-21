"""Refuse a lib<mod>api.so whose state-struct layout differs from the wrapper's.

Every module's C ABI fills one fixed-layout struct (``tr_state_t``, ...),
and the only rule for changing it is "append, bump the version, rebuild in
the same commit". Nothing used to check that at run time, so a library
and a wrapper from different commits failed silently (#246): a library
with a longer struct wrote past the wrapper's allocation, a library with a
shorter one left the appended fields as plausible zeros.

Since #246 each library exports two functions, callable before init::

    int    <mod>_state_abi_version(void);   /* <MOD>_STATE_ABI_VERSION */
    size_t <mod>_state_size(void);          /* sizeof(<mod>_state_t)   */

:func:`check_state_layout` compares both with the wrapper's ctypes struct
and its copy of the version constant, and raises :class:`AbiMismatchError`
on any difference, including the two symbols being absent (a library
built before #246). Each wrapper's ``_ffi.load_library`` calls it right
after ``ctypes.CDLL``, before ``_apply_prototypes`` and before any struct
is passed, and re-raises as its own error class so ``except <Mod>libError``
keeps working.
"""
from __future__ import annotations

import ctypes
from typing import Any


class AbiMismatchError(RuntimeError):
    """The library's state-struct layout is not the one this wrapper has.

    Attributes carry what was compared so a caller can report precisely:
    ``library_version`` / ``library_size`` are ``None`` when the library
    does not export the query at all.
    """

    def __init__(self, message: str, *, prefix: str, lib_name: str,
                 wrapper_version: int, wrapper_size: int,
                 library_version: int | None, library_size: int | None):
        super().__init__(message)
        self.prefix = prefix
        self.lib_name = lib_name
        self.wrapper_version = wrapper_version
        self.wrapper_size = wrapper_size
        self.library_version = library_version
        self.library_size = library_size


def check_state_layout(lib: Any, *, prefix: str, struct: type,
                       expected_version: int, lib_name: str) -> None:
    """Raise :class:`AbiMismatchError` unless ``lib`` fills ``struct``'s layout.

    ``lib`` is a loaded ``ctypes.CDLL`` (or anything with the same
    attribute access, for tests). ``prefix`` is the C symbol prefix
    (``"tr"``, ``"fp"``, ...), ``struct`` the wrapper's ``ctypes.Structure``
    subclass, ``expected_version`` the wrapper's copy of
    ``<MOD>_STATE_ABI_VERSION``, and ``lib_name`` the file name used in the
    message (``"libtrapi.so"``).

    On success the two query symbols are left with their prototypes
    attached, so a caller may call them again (``lib.tr_state_size()``).
    """
    wrapper_size = ctypes.sizeof(struct)
    # The rebuild hint: the mono image is built under tot, everything
    # else under its own module directory. The Makefiles have no .dll
    # target, so for a Windows library (any case: an explicit path keeps
    # its own) the hint names the sources, as the wrappers' not-found
    # hint does, and no make command.
    if lib_name.lower().endswith(".dll"):
        rebuild_now = f"Build {lib_name} from the Fortran sources."
        rebuild_or = f"build {lib_name} again from the Fortran sources"
    else:
        if lib_name.startswith("libtotapi_mono"):
            target = f"`make -C tot {lib_name}`"
        else:
            target = f"`make -C {prefix} {lib_name}`"
        rebuild_now = f"Rebuild it: {target}."
        rebuild_or = f"rebuild the library ({target})"
    try:
        fn_version = getattr(lib, f"{prefix}_state_abi_version")
        fn_size = getattr(lib, f"{prefix}_state_size")
    except AttributeError as exc:
        raise AbiMismatchError(
            f"{lib_name} does not export {prefix}_state_abi_version / "
            f"{prefix}_state_size: it was built before the layout check "
            f"(#246) and may not match this wrapper's {struct.__name__} "
            f"(v{expected_version}, {wrapper_size} bytes). {rebuild_now}",
            prefix=prefix, lib_name=lib_name,
            wrapper_version=expected_version, wrapper_size=wrapper_size,
            library_version=None, library_size=None,
        ) from exc
    fn_version.restype = ctypes.c_int
    fn_version.argtypes = []
    fn_size.restype = ctypes.c_size_t
    fn_size.argtypes = []
    library_version = int(fn_version())
    library_size = int(fn_size())
    if library_version != expected_version or library_size != wrapper_size:
        raise AbiMismatchError(
            f"{lib_name} state layout is v{library_version} / "
            f"{library_size} bytes; this wrapper's {struct.__name__} is "
            f"v{expected_version} / {wrapper_size} bytes. The library and "
            f"the wrapper come from different commits: {rebuild_or} or "
            f"update python/{prefix}lib/_ffi.py.",
            prefix=prefix, lib_name=lib_name,
            wrapper_version=expected_version, wrapper_size=wrapper_size,
            library_version=library_version, library_size=library_size,
        )
