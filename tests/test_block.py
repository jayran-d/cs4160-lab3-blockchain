from chain.block import compute_txs_hash, create_genesis_block
from chain.pow import mine_block
from chain.utils import sha256
from chain.transaction import Transaction
from config import HASH_SIZE, BLOCK_DIFFICULTY, HEADER_SIZE
from chain.block import Block, BlockHeader


def test_genesis_block_is_valid():
    # The genesis block should be well-formed and valid.
    genesis = create_genesis_block()

    assert len(genesis.block_hash()) == HASH_SIZE
    assert genesis.validate()
    assert genesis.header.prev_hash == b"\x00" * HASH_SIZE
    assert genesis.transactions == []


def test_block_hash_is_deterministic():
    # Hashing the same block multiple times should always return the same result.
    genesis = create_genesis_block()

    assert genesis.block_hash() == genesis.block_hash()


def test_block_with_wrong_txs_hash_is_invalid(fake_tx: Transaction):
    # A block should be invalid if the header txs_hash does not match its transactions.
    block = mine_block(
        prev_hash=b"\x00" * HASH_SIZE,
        transactions=[fake_tx],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )

    bad_header = BlockHeader(
        prev_hash=block.header.prev_hash,
        txs_hash=b"\xff" * HASH_SIZE,
        timestamp=block.header.timestamp,
        difficulty=block.header.difficulty,
        nonce=block.header.nonce,
    )

    bad_block = Block(
        header=bad_header,
        transactions=block.transactions,
    )

    assert not bad_block.validate()


def test_block_with_invalid_prev_hash_size_is_invalid():
    # A block with a malformed prev_hash should fail validation.
    block = mine_block(
        prev_hash=b"\x00" * HASH_SIZE,
        transactions=[],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )

    block.header.prev_hash = b"\x00" * (HASH_SIZE - 1)

    assert not block.validate()


def test_mined_block_is_valid():
    # A mined block should pass block validation and satisfy the PoW difficulty.
    block = mine_block(
        prev_hash=b"\x00" * HASH_SIZE,
        transactions=[],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )

    assert block.validate()
    assert block.block_hash()[0] == 0


def test_txs_hash_empty():
    # An empty transaction list should hash to SHA256 of empty bytes.
    assert compute_txs_hash([]) == sha256(b"")


def test_txs_hash_nonempty(fake_tx: Transaction):
    # A non-empty transaction list should hash the concatenated transaction hashes.
    tx_hash = fake_tx.tx_hash()
    expected = sha256(tx_hash)

    assert compute_txs_hash([tx_hash]) == expected


def test_header_encoding_is_84_bytes():
    # The packed block header should match the required 84-byte format.
    block = create_genesis_block()
    packed_header = block.header.pack()

    assert len(packed_header) == HEADER_SIZE
