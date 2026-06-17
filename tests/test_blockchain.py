from chain.blockchain import Blockchain
from chain.pow import mine_block
from chain.transaction import Transaction
from config import BLOCK_DIFFICULTY, HASH_SIZE


def mine_test_block(prev_hash: bytes, transactions=None, timestamp: int = 1):
    # Helper function to mine small test blocks with a low difficulty.
    if transactions is None:
        transactions = []

    return mine_block(
        prev_hash=prev_hash,
        transactions=transactions,
        timestamp=timestamp,
        difficulty=BLOCK_DIFFICULTY,
    )


def test_add_block():
    # A new blockchain should start at height 0 with only the genesis block.
    chain = Blockchain()

    assert chain.height() == 0

    # Mine one valid block on top of the current chain tip.
    b1 = mine_test_block(chain.tip_hash(), timestamp=1)

    # Adding the block should update the chain height and tip.
    assert chain.add_block(b1)
    assert chain.height() == 1
    assert chain.tip_hash() == b1.block_hash()


def test_duplicate_block_rejected():
    # Adding the same block twice should reject the duplicate.
    chain = Blockchain()

    b1 = mine_test_block(chain.tip_hash(), timestamp=1)

    assert chain.add_block(b1)
    assert not chain.add_block(b1)
    assert chain.height() == 1
    assert chain.tip_hash() == b1.block_hash()


def test_block_with_unknown_parent_is_stored_as_orphan():
    # A block whose parent is unknown should be stored as an orphan.
    chain = Blockchain()

    unknown_parent_hash = b"\x11" * HASH_SIZE
    orphan = mine_test_block(unknown_parent_hash, timestamp=1)

    assert not chain.add_block(orphan)
    assert chain.height() == 0
    assert unknown_parent_hash in chain.pending_blocks
    assert chain.pending_blocks[unknown_parent_hash] == [orphan]


def test_get_block_at_height():
    # Blocks on the canonical chain should be retrievable by height.
    chain = Blockchain()

    genesis = chain.get_block_at_height(0)
    b1 = mine_test_block(chain.tip_hash(), timestamp=1)
    b2 = mine_test_block(b1.block_hash(), timestamp=2)

    assert chain.add_block(b1)
    assert chain.add_block(b2)

    assert chain.get_block_at_height(0) == genesis
    assert chain.get_block_at_height(1) == b1
    assert chain.get_block_at_height(2) == b2
    assert chain.get_block_at_height(3) is None


def test_orphan_resolution():
    # This tests receiving a child block before receiving its parent.
    chain = Blockchain()

    b1 = mine_test_block(chain.tip_hash(), timestamp=1)
    b2 = mine_test_block(b1.block_hash(), timestamp=2)

    # b2 depends on b1, but b1 is not known yet, so b2 should be stored as an orphan.
    assert not chain.add_block(b2)
    assert chain.height() == 0

    # Once b1 is added, the chain should automatically process b2 as well.
    assert chain.add_block(b1)
    assert chain.height() == 2
    assert chain.tip_hash() == b2.block_hash()


def test_fork_resolution():
    # This tests the longest-chain rule when two forks exist.
    chain = Blockchain()

    # Mine two different competing blocks on top of genesis.
    b1a = mine_test_block(chain.tip_hash(), timestamp=1)
    b1b = mine_test_block(chain.tip_hash(), timestamp=2)

    # First fork becomes the canonical chain.
    assert chain.add_block(b1a)
    assert chain.tip_hash() == b1a.block_hash()

    # Second fork has the same height, so it should not replace the current tip.
    assert chain.add_block(b1b)
    assert chain.tip_hash() == b1a.block_hash()

    # Extend the second fork, making it longer than the first fork.
    b2b = mine_test_block(b1b.block_hash(), timestamp=3)

    # The blockchain should switch to the longer fork.
    assert chain.add_block(b2b)
    assert chain.tip_hash() == b2b.block_hash()
    assert chain.height() == 2


def test_confirmations(fake_tx: Transaction):
    # This tests whether a transaction is considered confirmed after enough blocks are mined on top.
    chain = Blockchain()

    # Mine a block containing the fake transaction.
    b1 = mine_test_block(
        prev_hash=chain.tip_hash(),
        transactions=[fake_tx],
        timestamp=1,
    )

    # The transaction is included, but not buried under enough blocks yet.
    assert chain.add_block(b1)
    assert not chain.tx_confirmed(fake_tx.tx_hash())

    # Mine three more blocks on top of the transaction block.
    for timestamp in [2, 3, 4]:
        b = mine_test_block(chain.tip_hash(), timestamp=timestamp)
        assert chain.add_block(b)

    # Now the transaction should have 3 confirmations.
    assert chain.tx_confirmed(fake_tx.tx_hash())
