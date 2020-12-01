# pypck - Asynchronous LCN-PCK library written in Python

![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/alengwenus/pypck?color=success)
![GitHub Workflow Status (branch)](https://img.shields.io/github/workflow/status/alengwenus/pypck/CI/dev)
![Codecov branch](https://img.shields.io/codecov/c/github/alengwenus/pypck/dev)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pypck)](https://pypi.org/project/pypck/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

## Overview

**pypck** is an open source library written in Python which allows the connection to the [LCN (local control network) system](https://www.lcn.eu). It uses the vendor protocol LCN-PCK.
To get started an unused license of the coupling software LCN-PCHK and a hardware coupler is necessary.

**pypck** is used by the LCN integration of the [Home Assistant](https://home-assistant.io/) project.

## Example

```python
"""Example for switching an output port of module 10 on and off."""
import asyncio

from pypck.connection import PchkConnectionManager
from pypck.lcn_addr import LcnAddr

async def main():
    """Connect to PCK host, get module object and switch output port on and off."""
    async with PchkConnectionManager(
        "192.168.2.41",
        4114,
        username="lcn",
        password="lcn",
        settings={"SK_NUM_TRIES": 0},
    ) as pck_client:
        module = pck_client.get_address_conn(LcnAddr(0, 10, False))

        await module.dim_output(0, 100, 0)
        await asyncio.sleep(1)
        await module.dim_output(0, 0, 0)

asyncio.run(main())
```

## pypck REPL in ipython

**pypck** relies heavily on asyncio for talking to the LCN-PCHK software. This
makes it unusable with the standard python interactive interpreter.
Fortunately, ipython provides some support for asyncio in its interactive
interpreter, see
[ipython autoawait](https://ipython.readthedocs.io/en/stable/interactive/autoawait.html#).

### Requirements

- **ipython** at least version 7.0 (autoawait support)
- **pypck**

### Example session

```
Python 3.8.3 (default, Jun  9 2020, 17:39:39)
Type 'copyright', 'credits' or 'license' for more information
IPython 7.19.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: from pypck.connection import PchkConnectionManager
   ...: from pypck.lcn_addr import LcnAddr
   ...: import asyncio

In [2]: connection = PchkConnectionManager(host='localhost', port=4114, username='lcn', password='lcn')

In [3]: await connection.async_connect()

In [4]: module = connection.get_address_conn(LcnAddr(seg_id=0, addr_id=10, is_group=False), request_serials=False)

In [5]: await module.request_serials()
Out[5]:
{'hardware_serial': 127977263668,
 'manu': 1,
 'software_serial': 1771023,
 'hardware_type': <HardwareType.UPU: 26>}

In [6]: await module.dim_output(0, 100, 0)
   ...: await asyncio.sleep(1)
   ...: await module.dim_output(0, 0, 0)
Out[6]: True
```

### Caveats

ipython starts and stops the asyncio event loop for each toplevel command
sequence. Also it only starts the loop if the toplevel commands includes async
code (like await or a call to an async function). This can lead to unexpected
behavior. For example, background tasks run only while ipython is executing
toplevel commands that started the event loop. Functions that use the event
loop only internally may fail, e.g. the following would fail:

```
In [4]: module = connection.get_address_conn(LcnAddr(seg_id=0, addr_id=10, is_group=False), request_serials=True)
---------------------------------------------------------------------------
RuntimeError                              Traceback (most recent call last)
<ipython-input-7-cd663974bde2> in <module>
----> 1 module = connection.get_address_conn(modaddr)

/pypck/connection.py in get_address_conn(self, addr, request_serials)
    457                 address_conn = ModuleConnection(self, addr)
    458                 if request_serials:
--> 459                     self.request_serials_task = asyncio.create_task(
    460                         address_conn.request_serials()
    461                     )

/usr/local/lib/python3.8/asyncio/tasks.py in create_task(coro, name)
    379     Return a Task object.
    380     """
--> 381     loop = events.get_running_loop()
    382     task = loop.create_task(coro)
    383     _set_task_name(task, name)

RuntimeError: no running event loop
```

See
[ipython autoawait internals](https://ipython.readthedocs.io/en/stable/interactive/autoawait.html#internals)
for details.
