import asyncio
import time

from chain.block import Block
from chain.mempool import Mempool
from chain.pow import mine_block
from config import BLOCK_DIFFICULTY, MINE_BLOCK_PER_SECONDS


class Miner:
    """
    Coordinates single-node mining against the local Blockchain state.
    """

    def __init__(
        self,
        blockchain,
        mempool: Mempool,
        interval_seconds: int = MINE_BLOCK_PER_SECONDS,
        difficulty: int = BLOCK_DIFFICULTY,
        max_transactions_per_block: int | None = None,
        community=None,
    ):
        self.blockchain = blockchain
        self.mempool = mempool
        self.interval_seconds = interval_seconds
        self.difficulty = difficulty
        self.max_transactions_per_block = max_transactions_per_block
        self.community = community
        self.is_running = False

    async def run_forever(self) -> None:
        """
        Mine one block every interval until stop() is called.
        """
        self.is_running = True

        while self.is_running:
            await asyncio.sleep(self.interval_seconds)
            self.mine_once()

    def stop(self) -> None:
        """
        Stop the mining loop after the current iteration finishes.
        """
        self.is_running = False

    def mine_once(self) -> Block | None:
        """
        Mine a single block from current mempool transactions.

        Returns the mined block when it was accepted by the blockchain.
        Returns None when the mined block was rejected.
        """
        transactions = self.mempool.transactions_for_block(
            self.max_transactions_per_block
        )
        prev_hash = self.blockchain.tip_hash()

        block = mine_block(
            prev_hash=prev_hash,
            transactions=transactions,
            timestamp=int(time.time()),
            difficulty=self.difficulty,
        )

        accepted = self.blockchain.add_block(block)
        if not accepted:
            return None

        self.mempool.remove_transactions(block.transactions)

        if self.community is not None:
            self.community.broadcast_block_to_teammates(block)

        return block
