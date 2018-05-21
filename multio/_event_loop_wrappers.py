'''
Here we find wrappers for functions and methods that curio and trio do not
share a close enough api for, or which may require a little wangjangling
to get to function correctly.
'''

__all__ = ['trio_open_connection', 'trio_send_all', 'trio_receive_some', 'trio_close', 'trio_spawn',
           'curio_sendall', 'curio_recv', 'curio_close', 'curio_spawn']


# Wrapper functions.
async def trio_open_connection(host, port, *, ssl=False, **kwargs):
    '''
    Allows connections to be made that may or may not require ssl.
    Somewhat surprisingly trio doesn't have an abstraction for this like
    curio even though it's fairly trivial to write. Down the line hopefully.

    Args:
        host (str): Network location, either by domain or IP.
        port (int): The requested port.
        ssl (bool): Whether or not SSL is required.
        kwargs: A catch all to soak up curio's additional kwargs and
            ignore them.
    '''
    import trio
    if not ssl:
        sock = await trio.open_tcp_stream(host, port)
    else:
        sock = await trio.open_ssl_over_tcp_stream(host, port)
        await sock.do_handshake()

    sock.close = sock.aclose
    return sock


async def trio_send_all(sock, *args, **kwargs):
    await sock.send_all(*args, **kwargs)


async def trio_receive_some(sock, max_bytes):
    return await sock.receive_some(max_bytes)


async def trio_close(sock):
    return await sock.aclose()


async def curio_sendall(sock, *args, **kwargs):
    await sock.sendall(*args, **kwargs)


async def curio_recv(sock, max_bytes):
    return await sock.recv(max_bytes)


async def curio_close(sock):
    return await sock.close()


# custom spawn semantics
async def trio_spawn(nursery, coro, *args):
    return nursery.start_soon(coro, *args)


async def curio_spawn(taskgroup, coro, *args):
    return await taskgroup.spawn(coro, *args)


# cancellation of task groups
async def trio_cancel(nursery):
    return nursery.cancel_scope.cancel()


async def curio_cancel(tg):
    await tg.cancel_remaining()
