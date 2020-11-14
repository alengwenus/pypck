# pypck

Open source LCN-PCK library written in Python

## Overview

**pypck** is an open source library written in Python which allows the connection to the [LCN (local control network) system](https://www.lcn.eu). It uses the vendor protocol LCN-PCK.
To get started an unused license of the coupling software LCN-PCHK and a hardware coupler is necessary.

**pypck** is used by the LCN integration of the [Home Assistant](https://home-assistant.io/) project.

## Example

```python
"""Example for switching an output port of moudle 10 on and off."""
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
        module10 = pck_client.get_address_conn(LcnAddr(0, 7, False))

        module10.dim_output(0, 100, 0)
        await asyncio.sleep(1)
        module10.dim_output(0, 0, 0)
        await asyncio.sleep(1)

asyncio.run(main())
```
