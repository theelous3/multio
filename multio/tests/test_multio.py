# -*- coding: utf-8 -*-

import pytest

import trio
import curio

from .. import init


class TestCase(object):

    @pytest.mark.parametrize("lib", ["trio", "curio", trio, curio])
    def test_initialize(self, lib):
        init(lib)

