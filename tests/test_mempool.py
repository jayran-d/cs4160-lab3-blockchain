from chain.mempool import Mempool
from config import HASH_SIZE


def test_add_and_contains(fake_tx):
    # A transaction added to the mempool should be stored by its transaction hash.
    mempool = Mempool()

    tx_hash = mempool.add(fake_tx)

    assert mempool.contains(tx_hash)
    assert len(mempool) == 1


def test_remove(fake_tx):
    # Removing a transaction by hash should delete it from the mempool.
    mempool = Mempool()
    tx_hash = mempool.add(fake_tx)

    mempool.remove(tx_hash)

    assert not mempool.contains(tx_hash)
    assert len(mempool) == 0


def test_remove_transactions(fake_tx):
    # Transactions included in a block should be removable from the mempool.
    mempool = Mempool()
    mempool.add(fake_tx)

    mempool.remove_transactions([fake_tx])

    assert len(mempool) == 0


def test_transactions_for_block_limit(fake_tx):
    # transactions_for_block should return at most the requested number of transactions.
    mempool = Mempool()
    mempool.add(fake_tx)

    txs = mempool.transactions_for_block(limit=1)

    assert txs == [fake_tx]


def test_remove_missing_transaction_does_not_crash():
    # Removing an unknown transaction hash should be safely ignored.
    mempool = Mempool()

    mempool.remove(b"\x00" * HASH_SIZE)

    assert len(mempool) == 0


def test_get_transaction(fake_tx):
    # get() should return the transaction for a known hash.
    mempool = Mempool()
    tx_hash = mempool.add(fake_tx)

    assert mempool.get(tx_hash) == fake_tx


def test_get_missing_transaction_returns_none():
    # get() should return None when the transaction hash is unknown.
    mempool = Mempool()

    assert mempool.get(b"\x00" * HASH_SIZE) is None
