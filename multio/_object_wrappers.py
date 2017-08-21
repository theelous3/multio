'''
Wrappers for certain objects that can change behaviour between libraries.
'''
import inspect
import typing

from . import asynclib


class _TaskResult:
    def __init__(self, value: typing.Any = None, exc: Exception = None):
        self.value = value
        self.exc = exc

    def unwrap(self):
        '''
        Unwraps the current result.
        '''
        if self.exc is not None:
            raise self.exc

        return self.value


class Task:
    '''
    Wrapper for a Task that uses curio or trio's Task objects.

    This should never be created directly, only through the usage of a TaskGroup.
    '''

    def __init__(self, internal_task):
        self._internal_task = internal_task

        self.cancelled = False

    async def cancel(self):
        '''
        Attempts to cancel this task.
        '''
        if self.cancelled:
            return

        if asynclib.lib_name == "trio":
            # This is horrible.
            import trio
            with trio.open_cancel_scope() as scope:
                scope._add_task(self._internal_task)
                scope.cancel()
        elif asynclib.lib_name == "curio":
            # capture the error!
            await self._internal_task.cancel()

        self.cancelled = True

    async def wait(self):
        '''
        Waits for this task to complete.
        '''
        # no need to proxy (yet)
        # just pass straight through
        await self._internal_task.wait()

    async def join(self) -> _TaskResult:
        '''
        Joins this task; waits for it to finish.
        '''
        if asynclib.lib_name == "trio":
            await self._internal_task.wait()
            res = self._internal_task.result
        elif asynclib.lib_name == "curio":
            # eat the exception if we need to
            from curio import TaskError
            try:
                c_res = await self._internal_task.join()
            except TaskError as e:
                actual = e.__cause__
                res = _TaskResult(exc=actual)
            else:
                res = _TaskResult(value=c_res)

        return res


class TaskGroup:
    '''
    Wrapper for a TaskGroup that either uses curio's TaskGroup or trio's nursery.
    '''

    def __init__(self, *args, **kwargs):
        self._internal_factory = asynclib.task_manager(*args, **kwargs)
        self._internal_instance = None

        self._trio_batch = []

    async def __aenter__(self):
        # hacky!
        self._internal_instance = await self._internal_factory.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._internal_factory.__aexit__(exc_type, exc_val, exc_tb)

    async def next_done(self) -> Task:
        '''
        Gets the next done task.
        '''
        # implemented in one of two ways:
        # curio - just call next_done
        # trio - get the batch, get the first task
        if asynclib.lib_name == "trio":
            # ensure we use the trio batch if we need to
            if self._trio_batch:
                batch = self._trio_batch
            else:
                batch = await self._internal_instance.monitor.get_batch()

            # update the last batch, so that we can collect it again later
            self._trio_batch = batch[1:]
            # pop off the first task
            next_task = batch[0]
            self._internal_instance.reap(next_task)
        elif asynclib.lib_name == "curio":
            # curio is a lot simpler
            next_task = await self._internal_instance.next_done()

        return next_task

    async def spawn(self, cofunc, *args, **kwargs) -> Task:
        '''
        Spawns a new task.
        '''
        # curio-style
        if inspect.iscoroutinefunction(self._internal_instance.spawn):
            t = await self._internal_instance.spawn(cofunc, *args, **kwargs)
        # trio-style
        else:
            t = self._internal_instance.spawn(cofunc, *args, **kwargs)

        return Task(t)
