'''
Here we find wrappers for functions and methods that curio and trio do not
share a close enough api for, or which may require a little wangjangling
to get to function correctly.
'''

__all__ = ['trio_open_connection', 'trio_send_all', 'trio_receive_some', 'trio_close', 'trio_spawn',
           'curio_sendall', 'curio_recv', 'curio_close', 'curio_spawn', 'TrioQueue']


# Wrapper functions.
async def trio_open_connection(host, port, *, ssl=False, **kwargs):
    '''
    Allows connections to be made that may or may not require ssl.
    Somewhat surprisingly trio doesn't have an abstraction for this like
    curio even though it's fairly trivial to write. Down the line hopefully.

    Args:
        host (str): Network location, either by domain or IP.
        port (int): The requested port.
        ssl (bool or SSLContext): If False or None, SSL is not required. If
            True, the context returned by trio.ssl.create_default_context will
            be used. Otherwise, this may be an SSLContext object.
        kwargs: A catch all to soak up curio's additional kwargs and
            ignore them.
    '''
    import trio
    if not ssl:
        sock = await trio.open_tcp_stream(host, port)
    else:
        if isinstance(ssl, bool):
            ssl_context = None
        else:
            ssl_context = ssl
        sock = await trio.open_ssl_over_tcp_stream(host, port, ssl_context=ssl_context)
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


# synchronization primitives
class TrioQueue:

    __slots__ = '_send_channel', '_receive_channel'

    def __init__(self, max_items: int):
        import trio
        self._send_channel, self._receive_channel = trio.open_memory_channel(max_items)

    def empty(self):
        return self._receive_channel.statistics().current_buffer_used == 0

    def full(self):
        statistics = self._receive_channel.statistics()
        return statistics.current_buffer_used >= statistics.max_buffer_size

    def qsize(self) -> int:
        return self._receive_channel.statistics().current_buffer_used

    async def put(self, item):
        await self._send_channel.send(item)

    async def get(self):
        return await self._receive_channel.receive()
