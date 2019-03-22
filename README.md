# multio

multio is a convenience wrapper for curio and trio, that unifies their
apis such that they can be used willy-nilly.

# Hey! Use anyio instead!
[anyio](https://github.com/agronholm/anyio)

multio was written as an ad hoc layer between curio and trio, for [asks](https://github.com/theelous3/asks).
asks is now driven by anyio which is a much more together version of multio, and even supports asyncio. Go support anyio!

### example

```python
# First creates a curio socket, and then a trio socket.
import curio
import trio

import multio
from multio import asynclib

def make_socket():
    s = asynclib.open_connection('example.org', 80)

multio.init('curio')
curio.run(make_socket)

multio.init('trio')
trio.run(make_socket)
```
