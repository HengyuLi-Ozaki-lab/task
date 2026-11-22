"""eq:MODEFR through tr_set_param takes 0 only (task-web-client #202).

TR's MODELG 3, 5 and 8 load their file through EQ's FROPEN, whose MODEP is EQ's MODEFR: with 1 it
reads the file name from standard input, the stdio MCP servers' channel. The ``eq:`` names reach
EQ's registry, which refuses it.
"""
import pytest

from trlib import Trlib, TrlibParamError

pytestmark = pytest.mark.forked


@pytest.mark.parametrize("value", [1.0, 2.0])
def test_eq_modefr_other_than_0_is_refused(value):
    with Trlib() as t, pytest.raises(TrlibParamError):
        t.set_param("eq:MODEFR", value)


def test_eq_modefr_0_is_taken():
    with Trlib() as t:
        t.set_param("eq:MODEFR", 0.0)
