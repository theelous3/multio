import functools
import inspect
import sys
import threading


async def _maybe_await(coro):
    if inspect.isawaitable(coro):
        return await coro

    return coro


# Wrapper classes
class AsyncWithWrapper:
    '''
    A wrapper that allows using a ``with`` context manager with ``async with``.
    '''

    def __init__(self, manager, *args, **kwargs):
        self.manager = manager(*args, **kwargs)

    def __enter__(self):
        return self.manager.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.manager.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)

    @classmethod
    def wrap(cls, meth):
        '''
        Wraps a function that produces an async context manager.
        '''
        return functools.partial(cls, meth)


class SocketWrapper:
    '''
    A wrapper around a socket that unifies the APIs.
    '''

    def __init__(self, sock):
        self.sock = sock

    async def recv(self, nbytes: int = -1, *args, **kwargs) -> bytes:
        '''
        Receives some data on the socket.
        '''
        return await asynclib.recv(self.sock, nbytes, *args, **kwargs)

    async def sendall(self, data: bytes, *args, **kwargs):
        '''
        Sends some data on the socket.
        '''
        return await asynclib.sendall(self.sock, data, *args, **kwargs)

    async def close(self):
        '''
        Closes the socket.
        '''
        return await asynclib.sock_close(self.sock)

    aclose = close

    @classmethod
    def wrap(cls, meth):
        '''
        Wraps a connection opening method in this class.
        '''
        async def inner(*args, **kwargs):
            sock = await meth(*args, **kwargs)
            return cls(sock)
        return inner


class Lock:
    '''
    Represents a lock.
    '''
    def __init__(self):
        self.lock = asynclib.Lock()

    def __aenter__(self):
        return self.lock.__aenter__()

    def __aexit__(self, *args, **kwargs):
        return self.lock.__aexit__(*args, **kwargs)

    async def acquire(self, *args, **kwargs):
        '''
        Acquires the lock.
        '''
        return await self.lock.acquire()

    async def release(self, *args, **kwargs):
        '''
        Releases the lock.
        '''
        return await _maybe_await(self.lock.release(*args, **kwargs))


class Event:
    '''
    Represents an event.
    '''
    def __init__(self):
        self.event = asynclib.Event()

    def is_set(self) -> bool:
        return self.event.is_set()

    async def set(self, *args, **kwargs):
        '''
        Sets the value of the event.
        '''
        return await _maybe_await(self.event.set(*args, **kwargs))

    async def wait(self):
        '''
        Waits for the event.
        '''
        return await self.event.wait()

    def clear(self):
        '''
        Clears this event.
        '''
        return self.event.clear()

# So, the idea here is that multio, after import, must be told explicitly which
# event loop to use. Upon first import we has _AsyncLib which is an empty
# shell. Upon initialisation the instance of _AsyncLib multio uses is
# populated either with functions and classes directly from the chosen async
# lib, or with wrappers around those functions and classes such that they share
# the same api to the extent that is required.

# This results in a meeting point between the two libraries which can be used
# arbitrarily. (You can even run a trio event loop, and then run the same
# functions with curio!)

# For the sake of simplicity, where possible, the methods of _AsyncLib use the
# curio name. For example, TaskTimeout from curio rather than
# TooSlowError from trio. This is not indicative of any preference to the
# libraries themselves. Both are majestic and beautiful.


class _AsyncLib(threading.local):
    '''
    When asynclib.something is requested, asynclib.__dict__['something']
    is checked before asynclib.__getattr__('something')
    '''
    _init = False

    async def aopen(self, *args, **kwargs):
        '''
        Opens an async file.
        '''

    async def open_connection(self, host: str, port: int, *args, **kwargs) -> SocketWrapper:
        '''
        Opens a connection. Returns a SocketWrapper.
        '''

    async def sleep(self, amount: float):
        '''
        Sleeps for a certain time.
        '''

    def task_manager(self, *args, **kwargs):
        '''
        Gets a task manager instance.
        '''

    async def spawn(self, taskgroup_or_nursery, coro, *args):
        '''
        Spawns a task in a taskgroup or nursery.
        '''

    def timeout_after(self, *args, **kwargs):
        '''
        Timeouts an operation after a certain period.
        '''

    async def sendall(self, sock, *args, **kwargs):
        '''
        Sends all data through a socket.
        '''

    async def recv(self, sock, *args, **kwargs) -> bytes:
        '''
        Receives data from a socket.
        '''

    async def sock_close(self, sock):
        '''
        Closes a socket.
        '''

    def __getattribute__(self, item):
        if super().__getattribute__("_init") is False:
            raise RuntimeError("multio.init() wasn't called")

        return super().__getattribute__(item)


# Singleton instance.
asynclib = _AsyncLib()


def init(lib_name):
    '''
    Must be called at some point after import and before your event loop
    is run.

    Populates the asynclib instance of _AsyncLib with methods relevant to the
    async library you are using.

    Args:
        lib_name (str): Either 'curio' or 'trio'.
    '''
    if lib_name == 'curio':
        import curio
        from ._event_loop_wrappers import (curio_sendall,
                                           curio_recv,
                                           curio_close,
                                           curio_spawn)
        asynclib.aopen = curio.aopen
        asynclib.open_connection = curio.open_connection
        asynclib.sleep = curio.sleep
        asynclib.task_manager = curio.TaskGroup
        asynclib.timeout_after = curio.timeout_after
        asynclib.sendall = curio_sendall
        asynclib.recv = curio_recv
        asynclib.sock_close = curio_close
        asynclib.spawn = curio_spawn

        asynclib.Lock = curio.Lock
        asynclib.Queue = curio.Queue
        asynclib.Event = curio.Event
        asynclib.Cancelled = curio.CancelledError
        asynclib.TaskTimeout = curio.TaskTimeout

    elif lib_name == 'trio':
        import trio
        from ._event_loop_wrappers import (trio_open_connection,
                                           trio_send_all,
                                           trio_receive_some,
                                           trio_close,
                                           trio_spawn)
        asynclib.aopen = trio.open_file
        asynclib.sleep = trio.sleep
        asynclib.task_manager = trio.open_nursery
        asynclib.timeout_after = AsyncWithWrapper.wrap(trio.fail_after)
        asynclib.open_connection = trio_open_connection
        asynclib.sendall = trio_send_all
        asynclib.recv = trio_receive_some
        asynclib.sock_close = trio_close
        asynclib.spawn = trio_spawn

        asynclib.Lock = trio.Lock
        asynclib.Queue = trio.Queue
        asynclib.Cancelled = trio.Cancelled
        asynclib.Event = trio.Event
        asynclib.TaskTimeout = trio.TooSlowError

    else:
        raise RuntimeError('{} is not a supported library.'.format(lib_name))

    asynclib.lib_name = lib_name
    asynclib._init = True


def unwrap_result(task):
    '''
    Unwraps a result from a task.
    '''
    if asynclib.lib_name == "curio":
        return task.result
    elif asynclib.lib_name == "trio":
        return task.result.unwrap()


def run(*args, **kwargs):
    '''
    Runs the appropriate library run function.
    '''
    lib = sys.modules[asynclib.lib_name]
    lib.run(*args, **kwargs)


class _ModWrapper:
    '''
    A wrapper that allows ``multio.<name>`` to proxy through to ``asynclib.<name>``.
    '''
    def __init__(self, mod):
        self.mod = mod

    def __repr__(self):
        return "<Wrapper for {}>".format(repr(self.mod))

    def __getattr__(self, item):
        try:
            return getattr(asynclib, item)
        except AttributeError:
            return getattr(self.mod, item)


sys.modules[__name__] = _ModWrapper(sys.modules[__name__])
