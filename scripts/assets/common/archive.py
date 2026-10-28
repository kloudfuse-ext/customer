"""Helpers for reading/writing compressed bundles (.zip, .tar.gz, .tgz).

Used by alert.py and dashboard.py so that a nested folder tree can be moved
between Grafana instances as a single file.
"""
import os
import re
import shutil
import tarfile
import tempfile
import zipfile
from contextlib import contextmanager

from loguru import logger as log

ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tgz")

# Guard against zip bombs / runaway archives.
MAX_MEMBERS = 50000
MAX_TOTAL_BYTES = 2 * 1024 ** 3


def is_archive(path) -> bool:
    return bool(path) and str(path).lower().endswith(ARCHIVE_SUFFIXES)


def safe_name(name: str) -> str:
    """Make a Grafana title usable as a single file name."""
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "unnamed"


def _check_member_path(dest: str, member_name: str):
    target = os.path.realpath(os.path.join(dest, member_name))
    if target != dest and not target.startswith(dest + os.sep):
        raise ValueError(f"Unsafe path in archive: {member_name}")


def extract_archive(archive_path: str, dest: str):
    """Extract archive_path into dest, rejecting traversal, links and oversize content."""
    dest = os.path.realpath(dest)
    if archive_path.lower().endswith(".zip"):
        with zipfile.ZipFile(archive_path) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_MEMBERS or sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
                raise ValueError("Archive is too large")
            for info in infos:
                _check_member_path(dest, info.filename)
                # Unix mode lives in the top 16 bits; 0o120000 is a symlink.
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError(f"Symlink in archive not allowed: {info.filename}")
            zf.extractall(dest)
    else:
        with tarfile.open(archive_path, "r:gz") as tf:
            members = tf.getmembers()
            if len(members) > MAX_MEMBERS or sum(m.size for m in members) > MAX_TOTAL_BYTES:
                raise ValueError("Archive is too large")
            for m in members:
                _check_member_path(dest, m.name)
                if not (m.isfile() or m.isdir()):
                    raise ValueError(f"Only files and directories allowed in archive: {m.name}")
            tf.extractall(dest, members=members)


@contextmanager
def extracted(path: str):
    """Yield a directory with the contents of `path`.

    If `path` is a plain directory it is yielded untouched; if it is an archive
    it is extracted to a temp dir that is removed afterwards.
    """
    if not is_archive(path):
        yield path
        return
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    tmp = tempfile.mkdtemp(prefix="kfuse-assets-")
    try:
        extract_archive(path, tmp)
        log.info("[*] Extracted {}", path)
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def pack_archive(src_dir: str, archive_path: str) -> int:
    """Pack every file under src_dir into archive_path; returns the file count."""
    files = []
    for root, _, names in os.walk(src_dir):
        for n in sorted(names):
            full = os.path.join(root, n)
            files.append((full, os.path.relpath(full, src_dir)))
    os.makedirs(os.path.dirname(os.path.abspath(archive_path)), exist_ok=True)
    if archive_path.lower().endswith(".zip"):
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for full, rel in files:
                zf.write(full, rel)
    else:
        with tarfile.open(archive_path, "w:gz") as tf:
            for full, rel in files:
                tf.add(full, arcname=rel)
    return len(files)


@contextmanager
def output_target(output: str, single_name: str = None):
    """Yield the local path a download should write to.

    For a normal output this is `output` itself. For an archive output, a temp
    dir is yielded (or, when `single_name` is given, a file path inside it) and
    the contents are packed into the archive when the block exits cleanly.
    """
    if not is_archive(output):
        yield output
        return
    tmp = tempfile.mkdtemp(prefix="kfuse-assets-")
    try:
        yield os.path.join(tmp, single_name) if single_name else tmp
        count = pack_archive(tmp, output)
        if count:
            log.info("[+] Wrote {} file(s) to {}", count, output)
        else:
            os.remove(output)
            log.warning("[!] Nothing was downloaded; no archive written")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
