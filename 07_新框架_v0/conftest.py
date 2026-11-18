"""Root conftest – redirect TEMP/TMP to D: to avoid C: disk‑full errors."""
import os, pathlib

_D_TMP = pathlib.Path(r"D:\搭建\tmptest")


def pytest_configure(config):
    """Before collection: ensure TEMP points to D: drive."""
    _D_TMP.mkdir(parents=True, exist_ok=True)
    os.environ["TEMP"] = str(_D_TMP)
    os.environ["TMP"] = str(_D_TMP)
    # Also patch tempfile so already‑imported modules pick it up.
    import tempfile
    tempfile.tempdir = str(_D_TMP)
