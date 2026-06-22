import unittest
from unittest.mock import Mock

from chain.blockchain import Blockchain
from chain.mempool import Mempool
from chain.miner import Miner
from chain.pow import mine_block
from chain.transaction import Transaction
from config import (
    BLOCK_DIFFICULTY,
    DIFFICULTY_ADJUSTMENT_WINDOW_SIZE,
    MIN_BLOCK_DIFFICULTY,
)


def make_tx(data: bytes = b"data") -> Transaction:
    return Transaction(
        sender_key=b"sender",
        data=data,
        timestamp=1,
        signature=b"signature",
    )


def add_timed_blocks(
    blockchain: Blockchain,
    timestamps: list[int],
    difficulty: int = MIN_BLOCK_DIFFICULTY,
) -> None:
    for timestamp in timestamps:
        block = mine_block(
            prev_hash=blockchain.tip_hash(),
            transactions=[],
            timestamp=timestamp,
            difficulty=difficulty,
        )
        assert blockchain.add_block(block)


class MinerTests(unittest.TestCase):
    def test_mine_once_uses_initial_adaptive_difficulty_on_early_chain(self) -> None:
        # With no history, the adaptive path should fall back to the initial difficulty.
        blockchain = Blockchain()
        miner = Miner(blockchain=blockchain)

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.header.difficulty, BLOCK_DIFFICULTY)
        self.assertEqual(blockchain.tip(), block)

    def test_mine_once_adds_block_on_current_blockchain_tip(self) -> None:
        # The miner should mine on top of the current canonical blockchain tip.
        blockchain = Blockchain()
        previous_tip_hash = blockchain.tip_hash()
        miner = Miner(
            blockchain=blockchain,
            difficulty=4,
        )

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.header.prev_hash, previous_tip_hash)
        self.assertEqual(blockchain.tip(), block)
        self.assertEqual(blockchain.height(), 1)

    def test_mine_once_includes_and_removes_mempool_transactions(self) -> None:
        # Transactions included in an accepted block should leave the mempool.
        blockchain = Blockchain()
        included_tx = make_tx(b"included")
        blockchain.mempool.add(included_tx)
        miner = Miner(
            blockchain=blockchain,
            difficulty=4,
        )

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.transactions, [included_tx])
        self.assertEqual(len(blockchain.mempool), 0)

    def test_mine_once_broadcasts_accepted_block_when_community_exists(self) -> None:
        # After local acceptance, the mined block should be sent to teammates.
        blockchain = Blockchain()
        broadcast_block = Mock()
        miner = Miner(
            blockchain=blockchain,
            difficulty=4,
            broadcast_block=broadcast_block,
        )

        block = miner.mine_once()

        broadcast_block.assert_called_once_with(block)

    def test_mine_once_does_not_cleanup_or_broadcast_rejected_block(self) -> None:
        # If the blockchain rejects a block, the miner must not lose transactions.
        blockchain = Mock()
        blockchain.tip_hash.return_value = b"\x00" * 32
        blockchain.add_block.return_value = False
        blockchain.mempool = Mempool()
        broadcast_block = Mock()
        tx = make_tx()
        blockchain.mempool.add(tx)
        miner = Miner(
            blockchain=blockchain,
            difficulty=4,
            broadcast_block=broadcast_block,
        )

        block = miner.mine_once()

        self.assertIsNone(block)
        self.assertEqual(len(blockchain.mempool), 1)
        broadcast_block.assert_not_called()
        blockchain.add_block.assert_called_once()

    def test_mine_once_respects_max_transactions_per_block(self) -> None:
        # The optional transaction limit lets us cap block size later if needed.
        blockchain = Blockchain()
        tx1 = make_tx(b"one")
        tx2 = make_tx(b"two")
        blockchain.mempool.add(tx1)
        blockchain.mempool.add(tx2)
        miner = Miner(
            blockchain=blockchain,
            difficulty=4,
            max_transactions_per_block=1,
        )

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.transactions, [tx1])
        self.assertEqual(len(blockchain.mempool), 1)
        self.assertTrue(blockchain.mempool.contains(tx2.tx_hash()))

    def test_mine_once_uses_expected_adaptive_difficulty_after_fast_blocks(self) -> None:
        # Fast recent blocks should raise the computed difficulty used by the miner.
        blockchain = Blockchain()
        timestamps = [
            3 * height
            for height in range(1, DIFFICULTY_ADJUSTMENT_WINDOW_SIZE + 1)
        ]
        add_timed_blocks(blockchain, timestamps)
        expected_difficulty = blockchain.next_difficulty()
        miner = Miner(blockchain=blockchain)

        block = miner.mine_once()

        self.assertIsNotNone(block)
        self.assertEqual(block.header.difficulty, expected_difficulty)
        self.assertEqual(blockchain.tip(), block)


if __name__ == "__main__":
    unittest.main()
