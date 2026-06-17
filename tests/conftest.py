import pytest

from chain.transaction import Transaction


@pytest.fixture
def fake_tx() -> Transaction:
    return Transaction(
        sender_key=b"sender-key",
        data=b"hello",
        timestamp=123,
        signature=b"fake-signature",
    )