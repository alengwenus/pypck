"""Tests for variable value and unit handling."""

import math

import pytest

from pypck.lcn_defs import VarUnit, VarValue

VARIABLE_TEST_VALUES = (
    0,
    48,
    49,
    50,
    51,
    52,
    100,
    198,
    199,
    200,
    201,
    202,
    205,
    1000,
    1023,
    4095,
    65535,
)

UNITS_LOSSLESS_ROUNDTRIP = (
    VarUnit.NATIVE,
    VarUnit.CELSIUS,
    VarUnit.KELVIN,
    VarUnit.FAHRENHEIT,
    VarUnit.LUX_I,
    VarUnit.METERPERSECOND,
    VarUnit.PERCENT,
    VarUnit.VOLT,
    VarUnit.AMPERE,
    VarUnit.DEGREE,
    VarUnit.PPM,
    # VarUnit.LUX_T,
)

ROUNDTRIP_TEST_VECTORS = (
    *(
        (unit, value, value)
        for value in VARIABLE_TEST_VALUES
        for is_abs in (True, False)
        for unit in UNITS_LOSSLESS_ROUNDTRIP
    ),
)


CALIBRATION_TEST_VECTORS = (
    *(
        (VarUnit.CELSIUS, native, value)
        for native, value in ((0, -100), (1000, 0), (2000, 100))
    ),
    *(
        (VarUnit.KELVIN, native, value)
        for native, value in (
            (0, -100 + 273.15),
            (1000, 0 + 273.15),
            (2000, 100 + 273.15),
        )
    ),
    *(
        (VarUnit.FAHRENHEIT, native, value)
        for native, value in (
            (0, -100 * 1.8 + 32),
            (1000, 0 * 1.8 + 32),
            (2000, 100 * 1.8 + 32),
        )
    ),
    *(
        (VarUnit.LUX_I, native, value)
        for native, value in (
            (0, math.exp(0)),
            (10, math.exp(0.1)),
            (100, math.exp(1)),
            (1000, math.exp(10)),
        )
    ),
    *(
        (VarUnit.METERPERSECOND, native, value)
        for native, value in ((0, 0), (10, 1), (100, 10), (1000, 100))
    ),
    *(
        (VarUnit.PERCENT, native, value)
        for native, value in ((0, 0), (1, 1), (100, 100))
    ),
    *(
        (VarUnit.VOLT, native, value)
        for native, value in ((0, 0), (400, 1), (4000, 10))
    ),
    *(
        (VarUnit.AMPERE, native, value)
        for native, value in ((0, 0), (100, 0.001), (4000, 0.04))
    ),
    *(
        (VarUnit.DEGREE, native, value)
        for native, value in ((0, -100), (1000, 0), (2000, 100), (4000, 300))
    ),
    *(
        (VarUnit.PPM, native, value)
        for native, value in ((0, 0), (1, 1), (100, 100), (1000, 1000))
    ),
    # VarUnit.LUX_T,
)


@pytest.mark.parametrize("unit, native, expected", ROUNDTRIP_TEST_VECTORS)
def test_roundtrip(unit: VarUnit, native: int, expected: VarValue) -> None:
    """Test that variable conversion roundtrips."""
    assert (
        expected
        == VarValue.from_var_unit(
            VarValue.to_var_unit(VarValue.from_native(native), unit), unit, True
        ).to_native()
    )


@pytest.mark.parametrize("unit, native, value", CALIBRATION_TEST_VECTORS)
def test_calibration(unit: VarUnit, native: int, value: int | float) -> None:
    """Test proper calibration of variable conversion."""
    assert value == VarValue.to_var_unit(VarValue.from_native(native), unit)
