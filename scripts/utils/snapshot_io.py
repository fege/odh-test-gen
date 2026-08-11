"""Symlink-safe file I/O primitives for strategy snapshots.

These are the generic, containment-policy-free building blocks extracted from
parse_strat.py.  Each caller combines them with its *own* containment policy:

- parse_strat.py gates reads through ``_permitted_strat_path`` (restricts to
  ``artifacts/strat-tasks/``).
- build_citation_inputs.py gates reads through ``require_feature_snapshot``
  (restricts to the caller-supplied ``feature_dir``).
- resolve_strategy.py uses ``write_snapshot_nofollow`` for the write side only.
- resolve_additional_docs.py gates reads through ``require_within_feature_dir``
  (generic containment — any file inside ``feature_dir``).
"""

import os
from pathlib import Path


def read_file_nofollow(path: os.PathLike | str) -> str:
    """Read *path* as UTF-8 without following symlinks.

    ``O_NOFOLLOW`` closes the TOCTOU gap between a prior containment check and
    this open: if the final path component was swapped for a symlink between the
    check and the open, the kernel rejects the open (``ELOOP``) instead of
    silently following the symlink wherever it points.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, encoding="utf-8") as f:
        return f.read()


def write_snapshot_nofollow(path: os.PathLike | str, content: str) -> None:
    """Write *content* (UTF-8) to *path* without following symlinks.

    A pre-existing symlink at *path* (planted before this call, or substituted
    after an earlier check) could redirect the write to overwrite an arbitrary
    file the process has access to.  ``O_NOFOLLOW`` makes the kernel reject the
    open instead of silently writing through it.  Overwriting a real pre-existing
    file (a normal re-run) is still allowed via ``O_TRUNC``.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)


def require_within_feature_dir(feature_dir: os.PathLike | str, path: os.PathLike | str) -> Path:
    """Validate that *path* is a regular file inside *feature_dir* (no symlinks).

    Generic ``<feature_dir>`` containment — usable for any file, unlike
    ``require_feature_snapshot`` which additionally constrains the filename.

    Three ordered checks:

    1. **Containment** — ``resolve()`` dereferences any symlink and returns the
       target's canonical path.  If that target sits outside *feature_dir* the
       path is rejected.
    2. **Symlink** — ``is_symlink()`` (which does NOT follow the link) rejects a
       symlink entry outright, even when its target happens to be inside the
       tree.  ``read_file_nofollow``'s ``O_NOFOLLOW`` remains the TOCTOU
       backstop at open time.
    3. **Regular file** — a FIFO, device, or directory is rejected.
       ``O_NOFOLLOW`` does not reject a FIFO, and a blocking read on one would
       hang the caller.

    The returned path is built from ``parent.resolve() / name`` (resolves
    directory traversals without following a symlink at the final component).

    Raises:
        ValueError: with a stable reason code (``outside_feature_dir``,
            ``symlink``, or ``not_regular_file``) — never leaks the resolved
            absolute path in the message.
    """
    p = Path(path)

    resolved_dir = Path(feature_dir).resolve()
    resolved_target = p.resolve()

    if not resolved_target.is_relative_to(resolved_dir):
        raise ValueError("outside_feature_dir")

    if p.is_symlink():
        raise ValueError("symlink")

    if p.exists() and not p.is_file():
        raise ValueError("not_regular_file")

    resolved_path = p.parent.resolve() / p.name
    return resolved_path


def require_feature_snapshot(feature_dir: os.PathLike | str, path: os.PathLike | str) -> Path:
    """Validate that *path* is a ``.source-strategy.md`` file inside *feature_dir*.

    This is the ``<feature_dir>`` containment policy, distinct from
    ``parse_strat._permitted_strat_path`` (which restricts to
    ``artifacts/strat-tasks/``).  The two policies exist because the same
    snapshot content lives at different locations in different workflows:
    ``parse_strat`` reads from the repo-internal cache, while
    ``build_citation_inputs`` reads from the caller-supplied feature directory
    that ``resolve_strategy`` wrote the snapshot into.

    Both *feature_dir* and *path* are caller-supplied CLI arguments — neither is
    hardcoded to a specific absolute location.

    Three ordered checks:

    1. **Filename** — the supplied path's leaf must be ``.source-strategy.md``.
    2. **Containment** — delegated to ``require_within_feature_dir``.
    3. **Symlink** — delegated to ``require_within_feature_dir``.

    The returned path is built from ``parent.resolve() / name`` (resolves
    directory traversals without following a symlink at the final component).

    Raises:
        ValueError: if *path* has the wrong filename, resolves outside
            *feature_dir*, or is a symlink.
    """
    p = Path(path)

    if p.name != ".source-strategy.md":
        raise ValueError(f"snapshot filename must be .source-strategy.md, got {p.name!r}")

    # Delegate containment + symlink checks to the shared implementation.
    # Re-raise with richer, path-including messages for snapshot-specific
    # callers/tests (require_within_feature_dir uses stable no-leak codes).
    try:
        return require_within_feature_dir(feature_dir, path)
    except ValueError as exc:
        reason = str(exc)
        if reason == "outside_feature_dir":
            resolved_dir = Path(feature_dir).resolve()
            resolved_target = p.resolve()
            raise ValueError(f"snapshot path {resolved_target} is not inside feature_dir {resolved_dir}") from None
        if reason == "symlink":
            raise ValueError(f"snapshot path is a symlink (rejected for safety): {p}") from None
        if reason == "not_regular_file":
            raise ValueError(f"snapshot path is not a regular file: {p}") from None
        raise
