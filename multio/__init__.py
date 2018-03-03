import functools
import inspect
import socket
import sys
import threading
import types
import typing
from typing import Callable

from . import _low_level, _event_loop_wrappers

# used for static introspection e.g. pycharm
# in reality, we can't import anything due to module getattr
if typing.TYPE_CHECKING:
    __all__ = [
        "SocketWrapper",
        "Lock",
        "Event",
        "Promise",
        "Semaphore",
        "Queue",
        "Cancelled",
        "TaskTimeout"
        "finalize_agen",

        # export the asynclib
        "asynclib",
        "init",
        "register",

        # asynclib delegates
        "aopen",
        "open_connection",
        "sleep",
        "task_manager",
        "spawn",
        "timeout_after",
        "sendall",
        "recv",
        "sock_close",
        "wait_read",
        "wait_write",
        "cancel_task_group"
    ]


async def _maybe_await(coro):
    if inspect.isawaitable(coro):
        return await coro

    return coro


# Wrapper classes
class AsyncWithWrapper:
    '''
    A wrapper that allows using a ``with`` context manager with ``async with``.
    '''

    def __init__(self, ctxmanager, *args, **kwargs):
        self.manager = ctxmanager(*args, **kwargs)

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

    async def recv(self, nbytes: int = -1, **kwargs) -> bytes:
        '''
        Receives some data on the socket.
        '''
        return await asynclib.recv(self.sock, nbytes, **kwargs)

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

    def locked(self) -> bool:
        '''
        Returns if this lock is locked or not.
        '''
        return self.lock.locked()


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


class Promise(object):
    '''
    Represents a Promise, i.e. an Event with a return value.
    '''

    def __init__(self):
        self.event = Event()

        self._data = None

    async def set(self, data):
        '''
        Sets the promise with some data.
        '''
        self._data = data
        await self.event.set()

    async def wait(self):
        '''
        Waits for the promise to be set.
        '''
        await self.event.wait()
        return self._data

    def clear(self):
        '''
        Clears this promise.
        '''
        return self.event.clear()

    def is_set(self) -> bool:
        '''
        Returns if this Promise is set.
        '''
        return self.event.is_set()


# finalize_agen support for curio; by defualt does not much
def finalize_agen(gen):
    '''
    See curio.meta.finalize_agen.
    '''
    return asynclib.finalize_agen(gen)


class _AgenFinalizer(object):
    def __init__(self, agen):
        self._ = agen

    async def __aenter__(self):
        return self._

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False


# multio core
class _AsyncLibManager:
    '''
    A manager for multio. This allows registering a library and a function that sets the
    attributes of the object for the appropriate library.
    '''

    def __init__(self):
        self._handlers = {}

    def register(self, library: str, cbl: Callable[['_AsyncLib'], None]):
        '''
        Registers a callable to set up a library.
        '''
        self._handlers[library] = cbl

    def init(self, library: str, lib: '_AsyncLib'):
        return self._handlers[library](lib)


class _not_impl_generic:
    def __init__(self):
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __call__(self):
        _raise_not_implemented(self.name)


def _raise_not_implemented(name: str = None):
    # do stack inspection for names
    if name is None:
        frame = inspect.stack()[1]
        name = frame.frame.f_code.co_name

    raise NotImplementedError("The library in use ({}) does not have an implementation for "
                              "'asynclib.{}'"
                              .format(asynclib.lib_name, name))


class _AsyncLib(threading.local):
    #: If multio is initialized yet.
    _init = False

    #: The lib name currently in usage.
    lib_name = ""

    # lib-specific constructs
    Lock = _not_impl_generic()
    Semaphore = _not_impl_generic()
    Queue = _not_impl_generic()
    Cancelled = _not_impl_generic()
    Event = _not_impl_generic()
    TaskTimeout = _not_impl_generic()
    TaskGroupError = _not_impl_generic()

    def finalize_agen(self, agen):
        '''
        Finalizes an async generator. The default implementation of this function suffices if no
        implementation is made by a lib author.
        '''
        return _AgenFinalizer(agen)

    async def cancel_task_group(self, group):
        '''
        Cancels a task group.
        '''
        _raise_not_implemented()

    async def aopen(self, *args, **kwargs):
        '''
        Opens an async file.
        '''
        _raise_not_implemented()

    async def open_connection(self, host: str, port: int, *args, **kwargs):
        '''
        Opens a connection. Returns a SocketWrapper.
        '''
        _raise_not_implemented()

    async def sleep(self, amount: float):
        '''
        Sleeps for a certain time.
        '''
        _raise_not_implemented()

    def task_manager(self, *args, **kwargs):
        '''
        Gets a task manager instance.
        '''
        _raise_not_implemented()

    async def spawn(self, taskgroup_or_nursery, coro, *args):
        '''
        Spawns a task in a taskgroup or nursery.
        '''
        _raise_not_implemented()

    def timeout_after(self, *args, **kwargs):
        '''
        Timeouts an operation after a certain period.
        '''
        _raise_not_implemented()

    async def sendall(self, sock, *args, **kwargs):
        '''
        Sends all data through a socket.
        '''
        _raise_not_implemented()

    async def recv(self, sock, *args, **kwargs) -> bytes:
        '''
        Receives data from a socket.
        '''
        _raise_not_implemented()

    async def sock_close(self, sock):
        '''
        Closes a socket.
        '''
        _raise_not_implemented()

    def unwrap_taskgrouperror(self, error) -> typing.List[Exception]:
        '''
        Unwraps a TaskGroupError or MultiError into its constituent exceptions.
        '''
        _raise_not_implemented()

    def unwrap_result(self, task) -> typing.Any:
        '''
        Unwraps a task's result.
        '''
        _raise_not_implemented()

    # low level
    def wait_read(self, sock: socket.socket):
        '''
        Waits until a socket is ready to read from.
        '''
        _raise_not_implemented()

    def wait_write(self, sock: socket.socket):
        '''
        Waits until a socket is ready to write to.
        '''
        _raise_not_implemented()

    def __getattribute__(self, item):
        if super().__getattribute__("_init") is False:
            raise RuntimeError("multio.init() wasn't called")

        return super().__getattribute__(item)


# Singleton instances.
manager = _AsyncLibManager()
asynclib = _AsyncLib()


def _curio_init(lib: _AsyncLib):
    import curio
    from ._event_loop_wrappers import (curio_sendall,
                                       curio_recv,
                                       curio_close,
                                       curio_spawn)
    lib.aopen = curio.aopen
    lib.open_connection = curio.open_connection
    lib.sleep = curio.sleep
    lib.task_manager = curio.TaskGroup
    lib.timeout_after = curio.timeout_after
    lib.sendall = curio_sendall
    lib.recv = curio_recv
    lib.sock_close = curio_close
    lib.spawn = curio_spawn
    lib.finalize_agen = curio.meta.finalize
    lib.cancel_task_group = _event_loop_wrappers.curio_cancel
    lib.unwrap_taskgrouperror = lambda error: [task.next_exc for task in error.failed]
    lib.unwrap_result = lambda task: task.result

    lib.Lock = curio.Lock
    lib.Semaphore = curio.BoundedSemaphore
    lib.Queue = curio.Queue
    lib.Event = curio.Event
    lib.Cancelled = curio.CancelledError
    lib.TaskTimeout = curio.TaskTimeout
    lib.TaskGroupError = curio.TaskGroupError

    lib.wait_read = _low_level.wait_read_curio
    lib.wait_write = _low_level.wait_write_curio


def _trio_init(lib: _AsyncLib):
    import trio
    from ._event_loop_wrappers import (trio_open_connection,
                                       trio_send_all,
                                       trio_receive_some,
                                       trio_close,
                                       trio_spawn)
    lib.aopen = trio.open_file
    lib.sleep = trio.sleep
    lib.task_manager = trio.open_nursery
    lib.timeout_after = AsyncWithWrapper.wrap(trio.fail_after)
    lib.open_connection = trio_open_connection
    lib.sendall = trio_send_all
    lib.recv = trio_receive_some
    lib.sock_close = trio_close
    lib.spawn = trio_spawn
    lib.cancel_task_group = _event_loop_wrappers.trio_cancel
    lib.unwrap_taskgrouperror = lambda error: error.exceptions
    lib.unwrap_result = lambda task: task.result.unwrap()

    lib.Lock = trio.Lock
    lib.Semaphore = trio.CapacityLimiter
    lib.Queue = trio.Queue
    lib.Cancelled = trio.Cancelled
    lib.Event = trio.Event
    lib.TaskTimeout = trio.TooSlowError
    lib.TaskGroupError = trio.MultiError

    lib.read_wait = _low_level.wait_read_trio
    lib.write_wait = _low_level.wait_write_trio


manager.register("curio", _curio_init)
manager.register("trio", _trio_init)


def register(lib_name: str, cbl: Callable[[_AsyncLib], None]):
    '''
    Registers a new library function with the current manager.
    '''
    return manager.register(lib_name, cbl)


def init(library: typing.Union[str, types.ModuleType]) -> None:
    '''
    Must be called at some point after import and before your event loop
    is run.

    Populates the asynclib instance of _AsyncLib with methods relevant to the
    async library you are using.

    The supported libraries at the moment are:
    - curio
    - trio

    Args:
        library (str or module): Either the module name as a string or the
                                 imported module itself. E.g. ``multio.init(curio)``.
    '''
    if isinstance(library, types.ModuleType):
        library = library.__name__

    if library not in manager._handlers:
        raise ValueError("Possible values are <{}>, not <{}>".format(manager._handlers.keys(),
                                                                     library))

    manager.init(library, asynclib)
    asynclib.lib_name = library
    asynclib._init = True


def run(*args, **kwargs):
    '''
    Runs the appropriate library run function.
    '''
    lib = sys.modules[asynclib.lib_name]
    lib.run(*args, **kwargs)


# Metamagic.
# Python 3.7+ module-level getattr and dir; see PEP 562.
def __getattr__(name: str):
    return getattr(asynclib, name)


def __dir__():
    return asynclib.__dir__()


# Python <=3.6 module-level getattr; this hijacks our sys.module entry to provide getattr access
# to asynclib.
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
            return getattr(self.mod, item)
        except AttributeError:
            return getattr(asynclib, item)

    def __dir__(self):
        return asynclib.__dir__()


if sys.version_info[0:2] <= (3, 6):
    original = sys.modules[__name__]

    # store a copy, in case somebody needs it.
    sys.modules["multio.__original"] = original
    sys.modules[__name__] = _ModWrapper(original)
