'''
Wrappers for certain objects that can change behaviour between libraries.
'''
import inspect

from . import asynclib


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
        await self._internal_factory.__aexit__(exc_type, exc_val, exc_tb)

    async def next_done(self):
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

    async def spawn(self, cofunc, *args, **kwargs):
        '''
        Spawns a new task.
        '''
        # curio-style
        if inspect.iscoroutinefunction(self._internal_instance.spawn):
            t = await self._internal_instance.spawn(cofunc, *args, **kwargs)
        # trio-style
        else:
            t = self._internal_instance.spawn(cofunc, *args, **kwargs)

        return t
