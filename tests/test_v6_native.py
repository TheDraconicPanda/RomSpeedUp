import pytest
from romspeedup.v6_native import build


def test_standalone_builder_rejects_unidentified_input_before_parsing():
    with pytest.raises(ValueError,match='exact original Europe ROM'):
        build(b'not the original ROM')
