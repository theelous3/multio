'''
Low-level unifying functions.
'''
import socket


async def wait_read_curio(sock: socket.socket):
    from curio.traps import _read_wait
    return await _read_wait(sock.fileno())


async def wait_write_curio(sock: socket.socket):
    from curio.traps import _write_wait
    return await _write_wait(sock.fileno())


async def wait_read_trio(sock: socket.socket):
    # only works with sockets
    from trio.hazmat import wait_socket_readable
    return await wait_socket_readable(sock)


async def wait_write_trio(sock: socket.socket):
    # also only works with sockets
    from trio.hazmat import wait_socket_writable
    return await wait_socket_writable(sock)
