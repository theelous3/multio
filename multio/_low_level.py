'''
Low-level unifying functions.
'''


async def wait_read_curio(fd):
    from curio.traps import _read_wait
    from curio.io import _Fd

    # eff dee eff dee eff dee eff dee
    if not isinstance(fd, _Fd):
        fd = _Fd(fd)

    await _read_wait(_Fd(fd))


async def wait_write_curio(fd):
    from curio.traps import _write_wait
    from curio.io import _Fd

    if not isinstance(fd, _Fd):
        fd = _Fd(fd)

    await _write_wait(_Fd(fd))


async def wait_read_trio(fd):
    raise NotImplementedError


async def wait_write_trio(fd):
    raise NotImplementedError
