# SSE Client

A very rudementary SSE client implementation using raw sockets,
this uses only native python library feature and coroutines which
are non blocking.

The coroutine either returns an Event type or it returns None when
called with `next()` or within a for loop
