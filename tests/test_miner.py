import unittest

from chain.block import Block, create_genesis_block
from chain.mempool import Mempool
from chain.miner import Miner
from chain.transaction import Transaction


def make_tx(data: bytes = b"data") -> Transaction:
    return Transaction(
        sender_key=b"sender",
        data=data,
        timestamp=1,
        signature=b"signature",
    )


class FakeBlockchain:
    def __init__(self, should_accept: bool = True):
        self.blocks = [create_genesis_block()]
        self.should_accept = should_accept

    def tip_hash(self) -> bytes:
        return self.blocks[-1].block_hash()

    def append_block(self, block: Block) -> bool:
        if not self.should_accept:
            return False

        self.blocks.append(block)
        return True


class FakeCommunity:
    def __init__(self):
        self.broadcasted_blocks = []

    def broadcast_block_to_teammates(self, block: Block) -> None:
        self.broadcasted_blocks.append(block)


class MinerTests(unittest.TestCase):
    def test_mine_once_appends_block_on_current_tip(self) -> None:
        blockchain = FakeBlockchain()
        mempool = Mempool()
        previous_tip_hash = blockchain.tip_hash()
        miner = Miner(blockchain=blockchain, mempool=mempool, difficulty=4)

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.header.prev_hash, previous_tip_hash)
        self.assertEqual(blockchain.blocks[-1], block)
        self.assertEqual(len(blockchain.blocks), 2)

    def test_mine_once_includes_and_removes_mempool_transactions(self) -> None:
        blockchain = FakeBlockchain()
        mempool = Mempool()
        included_tx = make_tx(b"included")
        mempool.add(included_tx)
        miner = Miner(blockchain=blockchain, mempool=mempool, difficulty=4)

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.transactions, [included_tx])
        self.assertEqual(len(mempool), 0)

    def test_mine_once_broadcasts_accepted_block_when_community_exists(self) -> None:
        blockchain = FakeBlockchain()
        mempool = Mempool()
        community = FakeCommunity()
        miner = Miner(
            blockchain=blockchain,
            mempool=mempool,
            difficulty=4,
            community=community,
        )

        block = miner.mine_once()

        self.assertEqual(community.broadcasted_blocks, [block])

    def test_mine_once_does_not_cleanup_or_broadcast_rejected_block(self) -> None:
        blockchain = FakeBlockchain(should_accept=False)
        mempool = Mempool()
        community = FakeCommunity()
        tx = make_tx()
        mempool.add(tx)
        miner = Miner(
            blockchain=blockchain,
            mempool=mempool,
            difficulty=4,
            community=community,
        )

        block = miner.mine_once()

        self.assertIsNone(block)
        self.assertEqual(len(mempool), 1)
        self.assertEqual(community.broadcasted_blocks, [])
        self.assertEqual(len(blockchain.blocks), 1)

    def test_mine_once_respects_max_transactions_per_block(self) -> None:
        blockchain = FakeBlockchain()
        mempool = Mempool()
        tx1 = make_tx(b"one")
        tx2 = make_tx(b"two")
        mempool.add(tx1)
        mempool.add(tx2)
        miner = Miner(
            blockchain=blockchain,
            mempool=mempool,
            difficulty=4,
            max_transactions_per_block=1,
        )

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.transactions, [tx1])
        self.assertEqual(len(mempool), 1)
        self.assertTrue(mempool.contains(tx2.tx_hash()))


if __name__ == "__main__":
    unittest.main()
