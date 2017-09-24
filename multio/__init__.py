'''
Alright, you're probably having a heart attack looking at this right now.
Just breathe, and it will be ok, I promise!
'''

import threading
import sys


class _AsyncLib(threading.local):
    '''
    When asynclib.something is requested, asynclib.__dict__['something']
    is checked before asynclib.__getattr__('something')
    '''

    def __getattr__(self, attr):
        # the __dict__ is empty when a new instance has just been created
        if not self.__dict__:
            raise RuntimeError("multio.init() wasn't called")

        raise AttributeError("object {} has no attribute '{}'".format(type(self).__name__, attr))


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
                                           curio_recv)
        asynclib.aopen = curio.aopen
        asynclib.open_connection = curio.open_connection
        asynclib.sleep = curio.sleep
        asynclib.task_manager = curio.TaskGroup
        asynclib.TaskTimeout = curio.TaskTimeout
        asynclib.timeout_after = curio.timeout_after
        asynclib.sendall = curio_sendall
        asynclib.recv = curio_recv

    elif lib_name == 'trio':
        import trio
        from ._event_loop_wrappers import (trio_open_connection,
                                           trio_send_all,
                                           trio_receive_some)
        asynclib.aopen = trio.open_file
        asynclib.sleep = trio.sleep
        asynclib.task_manager = trio.open_nursery
        asynclib.TaskTimeout = trio.TooSlowError
        asynclib.timeout_after = trio.fail_after
        asynclib.open_connection = trio_open_connection
        asynclib.sendall = trio_send_all
        asynclib.recv = trio_receive_some

    else:
        raise RuntimeError('{} is not a supported library.'.format(lib_name))

    asynclib.lib_name = lib_name


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
