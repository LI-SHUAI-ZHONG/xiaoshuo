"""M0 package import smoke test."""


def test_import_nw() -> None:
    import nw

    assert nw.__name__ == "nw"
