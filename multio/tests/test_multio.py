import pytest

import curio
import trio

from .. import init


@pytest.mark.parametrize("lib", ["trio", "curio", trio, curio])
def test_initialize(lib):
    init(lib)

        init(lib)
