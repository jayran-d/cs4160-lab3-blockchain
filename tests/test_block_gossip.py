from chain.block import BlockHeader
from chain.blockchain import Blockchain
from chain.pow import mine_block
from chain.transaction import Transaction
from community import BlockchainCommunity
from config import BLOCK_DIFFICULTY, HASH_SIZE
from payloads import BlockGossipPayload


def make_test_community() -> BlockchainCommunity:
    # Build only the state needed by apply_block_gossip_payload, without IPv8 startup.
    community = BlockchainCommunity.__new__(BlockchainCommunity)
    community.blockchain = Blockchain()
    community.mempool = community.blockchain.mempool
    return community


def make_payload(block) -> BlockGossipPayload:
    # Block gossip sends the header plus transaction hashes.
    return BlockGossipPayload(
        prev_hash=block.header.prev_hash,
        txs_hash=block.header.txs_hash,
        timestamp=block.header.timestamp,
        difficulty=block.header.difficulty,
        nonce=block.header.nonce,
        block_hash=block.block_hash(),
        tx_hashes=block.tx_hashes_bytes(),
    )


def test_valid_block_gossip_is_added_and_cleans_mempool(fake_tx):
    # A valid gossiped block should be added and remove included tx hashes from our mempool.
    community = make_test_community()
    tx_hash = community.mempool.add(fake_tx)
    block = mine_block(
        prev_hash=community.blockchain.tip_hash(),
        transactions=[fake_tx],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )

    accepted = community.apply_block_gossip_payload(make_payload(block))

    assert accepted
    assert community.blockchain.tip_hash() == block.block_hash()
    assert not community.mempool.contains(tx_hash)


def test_block_gossip_rejects_mismatching_block_hash(fake_tx):
    # The payload hash must match the hash of the provided header fields.
    community = make_test_community()
    community.mempool.add(fake_tx)
    block = mine_block(
        prev_hash=community.blockchain.tip_hash(),
        transactions=[fake_tx],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )
    payload = make_payload(block)
    payload.block_hash = b"\xff" * HASH_SIZE

    accepted = community.apply_block_gossip_payload(payload)

    assert not accepted
    assert community.blockchain.height() == 0
    assert community.mempool.contains(fake_tx.tx_hash())


def test_block_gossip_rejects_bad_body_commitment(fake_tx):
    # txs_hash must match SHA256 over the included transaction hashes.
    community = make_test_community()
    community.mempool.add(fake_tx)
    block = mine_block(
        prev_hash=community.blockchain.tip_hash(),
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
    payload = make_payload(block)
    payload.txs_hash = bad_header.txs_hash
    payload.block_hash = bad_header.block_hash()

    accepted = community.apply_block_gossip_payload(payload)

    assert not accepted
    assert community.blockchain.height() == 0
    assert community.mempool.contains(fake_tx.tx_hash())


def test_block_gossip_rejects_malformed_tx_hashes(fake_tx):
    # tx_hashes must be complete 32-byte chunks.
    community = make_test_community()
    community.mempool.add(fake_tx)
    block = mine_block(
        prev_hash=community.blockchain.tip_hash(),
        transactions=[fake_tx],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )
    payload = make_payload(block)
    payload.tx_hashes = b"\x01" * (HASH_SIZE - 1)

    accepted = community.apply_block_gossip_payload(payload)

    assert not accepted
    assert community.blockchain.height() == 0
    assert community.mempool.contains(fake_tx.tx_hash())


def test_equal_height_fork_is_stored_but_not_canonical(fake_tx):
    # A valid side fork should be remembered, but it should not replace an equal-height tip.
    community = make_test_community()
    current_tip = mine_block(
        prev_hash=community.blockchain.tip_hash(),
        transactions=[],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )
    assert community.blockchain.add_block(current_tip)

    tx_hash = community.mempool.add(fake_tx)
    fork_block = mine_block(
        prev_hash=community.blockchain.get_block_at_height(0).block_hash(),
        transactions=[fake_tx],
        timestamp=2,
        difficulty=BLOCK_DIFFICULTY,
    )

    accepted = community.apply_block_gossip_payload(make_payload(fork_block))

    assert accepted
    assert fork_block.block_hash() in community.blockchain.blocks_by_hash
    assert community.blockchain.tip_hash() == current_tip.block_hash()
    assert community.mempool.contains(tx_hash)


def test_longer_gossiped_fork_becomes_canonical_and_cleans_mempool(fake_tx):
    # Once a fork becomes longer, Blockchain switches the canonical chain to it.
    community = make_test_community()
    genesis_hash = community.blockchain.tip_hash()
    current_tip = mine_block(
        prev_hash=genesis_hash,
        transactions=[],
        timestamp=1,
        difficulty=BLOCK_DIFFICULTY,
    )
    assert community.blockchain.add_block(current_tip)

    second_tx = Transaction(
        sender_key=b"second-sender",
        data=b"second-data",
        timestamp=fake_tx.timestamp + 1,
        signature=b"second-signature",
    )
    fake_tx_hash = community.mempool.add(fake_tx)
    second_tx_hash = community.mempool.add(second_tx)

    fork_block = mine_block(
        prev_hash=genesis_hash,
        transactions=[fake_tx],
        timestamp=2,
        difficulty=BLOCK_DIFFICULTY,
    )
    fork_child = mine_block(
        prev_hash=fork_block.block_hash(),
        transactions=[second_tx],
        timestamp=3,
        difficulty=BLOCK_DIFFICULTY,
    )

    assert community.apply_block_gossip_payload(make_payload(fork_block))
    assert community.blockchain.tip_hash() == current_tip.block_hash()

    assert community.apply_block_gossip_payload(make_payload(fork_child))

    assert community.blockchain.tip_hash() == fork_child.block_hash()
    assert community.blockchain.get_block_at_height(1).block_hash() == fork_block.block_hash()
    assert not community.mempool.contains(fake_tx_hash)
    assert not community.mempool.contains(second_tx_hash)
