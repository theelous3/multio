# multio

multio is a convenience wrapper for curio and trio, that unifies their
apis such that they can be used willy-nilly.

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
