import asyncio
import time
from collections.abc import Callable

from chain.block import Block
from chain.blockchain import Blockchain
from chain.pow import mine_block
from config import BLOCK_DIFFICULTY, MINE_BLOCK_PER_SECONDS


class Miner:
    """
    Handles local mining.

    The miner decides:
    - when to mine
    - which transactions to include
    - how to append the mined block
    - when to broadcast accepted blocks

    Networking is injected as a callback.
    """

    def __init__(
        self,
        blockchain: Blockchain,
        interval_seconds: int = MINE_BLOCK_PER_SECONDS,
        difficulty: int = BLOCK_DIFFICULTY,
        max_transactions_per_block: int | None = None,
        broadcast_block: Callable[[Block], None] | None = None,
    ):
        self.blockchain = blockchain
        self.interval_seconds = interval_seconds
        self.difficulty = difficulty
        self.max_transactions_per_block = max_transactions_per_block
        self.broadcast_block = broadcast_block
        self.is_running = False

    async def run_forever(self) -> None:
        self.is_running = True

        while self.is_running:
            await asyncio.sleep(self.interval_seconds)
            self.mine_once()

    def stop(self) -> None:
        self.is_running = False

    def mine_once(self) -> Block | None:
        """
        Mine a single block from current mempool transactions.

        Returns the mined block when it was accepted by the blockchain.
        Returns None when the mined block was rejected.
        """
        transactions = self.blockchain.mempool.transactions_for_block(
            self.max_transactions_per_block
        )
        print(
            "Mining next block: "
            f"parent_height={self.blockchain.height()}, "
            f"parent_hash={self.blockchain.tip_hash().hex()}, "
            f"tx_count={len(transactions)}"
        )

        prev_hash = self.blockchain.tip_hash()
        block = mine_block(
            prev_hash=prev_hash,
            transactions=transactions,
            timestamp=int(time.time()),
            difficulty=self.difficulty,
        )

        block_added = self.blockchain.add_block(block)
        if not block_added:
            print(f"Mined block was rejected: block_hash={block.block_hash().hex()}")
            return None

        print(
            "Mined and accepted block: "
            f"height={self.blockchain.height()}, "
            f"block_hash={block.block_hash().hex()}, "
            f"tx_count={len(block.tx_hashes())}"
        )

        if self.broadcast_block is not None:
            self.broadcast_block(block)
            print("Broadcasted mined block to teammates")

        return block
