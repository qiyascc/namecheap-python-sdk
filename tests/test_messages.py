from __future__ import annotations

import pytest

from namecheap_sdk import messages
from namecheap_sdk.resources import relative_name


def test_override_and_reset():
    messages.use({"value": {"empty_name": "Record adı boş ola bilməz"}})
    with pytest.raises(ValueError, match="Record adı boş"):
        relative_name("", "example.com")
    messages.reset()
    with pytest.raises(ValueError, match="must not be empty"):
        relative_name("", "example.com")


def test_unknown_key():
    with pytest.raises(KeyError):
        messages.use({"value.nope": "x"})
    messages.reset()
