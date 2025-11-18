# pypck - Asynchronous LCN-PCK library written in Python

![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/alengwenus/pypck?color=success)
![GitHub Workflow Status (dev branch)](https://github.com/alengwenus/pypck/actions/workflows/ci.yaml/badge.svg?branch=dev)
![Codecov branch](https://img.shields.io/codecov/c/github/alengwenus/pypck/dev)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/pypck)](https://pypi.org/project/pypck/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

<a href="https://www.buymeacoffee.com/alengwenus" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/white_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>

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
        module = pck_client.get_device_connection(LcnAddr(0, 10, False))

        await module.dim_output(0, 100, 0)
        await asyncio.sleep(1)
        await module.dim_output(0, 0, 0)

asyncio.run(main())
```
