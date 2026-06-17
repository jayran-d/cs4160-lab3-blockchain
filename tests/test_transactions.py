from chain.transaction import Transaction
from config import HASH_SIZE


def test_tx_hash_is_deterministic(fake_tx: Transaction):
    # Hashing the same transaction multiple times should always return the same result.
    assert fake_tx.tx_hash() == fake_tx.tx_hash()


def test_tx_hash_changes_when_data_changes(fake_tx: Transaction):
    # Changing any transaction field should produce a different transaction hash.
    changed_tx = Transaction(
        sender_key=fake_tx.sender_key,
        data=b"different",
        timestamp=fake_tx.timestamp,
        signature=fake_tx.signature,
    )

    assert fake_tx.tx_hash() != changed_tx.tx_hash()


def test_tx_hash_is_32_bytes(fake_tx: Transaction):
    # Transaction hashes should always be 32 bytes because SHA-256 outputs 32 bytes.
    assert len(fake_tx.tx_hash()) == HASH_SIZE

def test_tx_hash_changes_when_timestamp_changes(fake_tx: Transaction):
    # Changing the timestamp should also change the transaction hash.
    changed_tx = Transaction(
        sender_key=fake_tx.sender_key,
        data=fake_tx.data,
        timestamp=fake_tx.timestamp + 1,
        signature=fake_tx.signature,
    )

    assert fake_tx.tx_hash() != changed_tx.tx_hash()


def test_tx_hash_changes_when_signature_changes(fake_tx: Transaction):
    # Changing the signature should also change the transaction hash.
    changed_tx = Transaction(
        sender_key=fake_tx.sender_key,
        data=fake_tx.data,
        timestamp=fake_tx.timestamp,
        signature=b"different-signature",
    )

    assert fake_tx.tx_hash() != changed_tx.tx_hash()