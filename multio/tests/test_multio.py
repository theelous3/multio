import pytest

import curio
import trio

from .. import init, manager


@pytest.mark.parametrize("lib", ["trio", "curio", trio, curio])
def test_initialize(lib):
    init(lib)


@pytest.mark.parametrize("lib", ["curio", "trio"])
def test_lib_is_registered(lib):
    assert lib in manager._handlers
        init(lib)
