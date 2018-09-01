'''
A patcher for curio that forcibly enables contextvar support.
'''
from functools import partial

try:
    import contextvars

    _should_patch = False
except ImportError:
    _should_patch = True


def _hotpatch_curio():
    try:
        import curio
    except ImportError:
        return

    original_init = curio.Task.__init__

    def Task_init(self: curio.Task, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.context = contextvars.copy_context()

        self._original_send = self._send
        self._original_throw = self._throw

        self._send = partial(Task_send_with_context, self)
        self._throw = partial(Task_throw_with_context, self)

    def Task_send_with_context(self: curio.Task, *args, **kwargs):
        return self.context.run(self._original_send, *args)

    def Task_throw_with_context(self: curio.Task, *args, **kwargs):
        return self.context.run(self._original_throw, *args)

    curio.Task.__init__ = Task_init
