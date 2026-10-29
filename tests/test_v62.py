import pytest
from romspeedup.v62 import build


def test_v62_refuses_an_unidentified_rom():
    with pytest.raises(ValueError, match='exact original Europe ROM'):
        build(b'not the original ROM')
