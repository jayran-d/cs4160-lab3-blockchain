import asyncio
import threading
import time
from collections.abc import Callable

from chain.block import Block
from chain.blockchain import Blockchain
from chain.pow import mine_block
from config import MINE_BLOCK_PER_SECONDS


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
        difficulty: int | None = None,
        max_transactions_per_block: int | None = None,
        broadcast_block: Callable[[Block], None] | None = None,
    ):
        self.blockchain = blockchain
        self.interval_seconds = interval_seconds
        self.difficulty = difficulty
        self.max_transactions_per_block = max_transactions_per_block
        self.broadcast_block = broadcast_block
        self.is_running = False
        self._current_stop_event: threading.Event | None = None
        self._stop_event_lock = threading.Lock()

    async def run_forever(self) -> None:
        self.is_running = True

        while self.is_running:
            await asyncio.sleep(self.interval_seconds)
            await asyncio.to_thread(self.mine_once)

    def stop(self) -> None:
        self.is_running = False
        self.interrupt_current_mining()

    def interrupt_current_mining(self) -> None:
        with self._stop_event_lock:
            if self._current_stop_event is not None:
                self._current_stop_event.set()

    def _new_stop_event(self) -> threading.Event:
        stop_event = threading.Event()

        with self._stop_event_lock:
            self._current_stop_event = stop_event

        return stop_event

    def _clear_stop_event(self, stop_event: threading.Event) -> None:
        with self._stop_event_lock:
            if self._current_stop_event is stop_event:
                self._current_stop_event = None

    def mine_once(self) -> Block | None:
        """
        Mine a single block from current mempool transactions.

        Returns the mined block when it was accepted by the blockchain.
        Returns None when the mined block was rejected.
        """
        prev_hash = self.blockchain.tip_hash()
        difficulty = (
            self.difficulty
            if self.difficulty is not None
            else self.blockchain.next_difficulty(prev_hash)
        )
        difficulty_source = "fixed" if self.difficulty is not None else "adaptive"
        transactions = self.blockchain.mempool.transactions_for_block(
            self.max_transactions_per_block
        )
        print(
            "Mining next block: "
            f"parent_height={self.blockchain.height()}, "
            f"parent_hash={prev_hash.hex()}, "
            f"tx_count={len(transactions)}, "
            f"difficulty={difficulty}, "
            f"difficulty_source={difficulty_source}"
        )
        stop_event = self._new_stop_event()

        try:
            block = mine_block(
                prev_hash=prev_hash,
                transactions=transactions,
                timestamp=int(time.time()),
                difficulty=difficulty,
                should_stop=stop_event.is_set,
            )
        finally:
            self._clear_stop_event(stop_event)

        if block is None:
            print("Mining stopped before a valid block was found")
            return None

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
