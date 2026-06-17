from chain.block import BlockHeader
from chain.blockchain import Blockchain
from chain.pow import mine_block
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
