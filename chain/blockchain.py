import threading
from hashlib import sha256

from chain.block import Block, create_genesis_block

from chain.mempool import Mempool
from chain.pow import valid_pow
from chain.transaction import Transaction


class Blockchain:
    """
    Fork-aware blockchain.
    Stores all valid known blocks and exposes the current canonical chain
    using the longest-chain rule.
    """

    def __init__(self):
        genesis = create_genesis_block()
        genesis_hash = genesis.block_hash()

        self.lock = threading.RLock()

        # All valid known blocks by block hash.
        self.blocks_by_hash: dict[bytes, Block] = {
            genesis_hash: genesis,
        }

        # Height of each known block.
        self.height_by_hash: dict[bytes, int] = {
            genesis_hash: 0,
        }

        # Canonical chain: height -> block (only blocks on the best chain).
        self.chain_by_height: dict[int, Block] = {
            0: genesis,
        }

        # Current best chain tip according to longest-chain rule.
        self.best_tip_hash: bytes = genesis_hash
        self.best_tip_height: int = 0

        # Blocks received before their parent: missing_parent_hash -> [blocks]
        self.pending_blocks: dict[bytes, list[Block]] = {}

        self.mempool = Mempool()

    # ------------------------------------------------------------------
    # Core insertion
    # ------------------------------------------------------------------

    def add_block(self, block: Block) -> bool:
        """
        Validate and insert a block. Returns True if the block was accepted.
        Triggers fork resolution and flushes any pending orphans.
        """
        with self.lock:
            block_hash = block.block_hash()

            # Already known.
            if block_hash in self.blocks_by_hash:
                return False

            # Validate block-internal correctness.
            if not block.validate():
                print("Ignoring invalid block / block with bad header or txs_hash")
                return False

            if not valid_pow(block_hash, block.header.difficulty):
                print("Ignoring block with invalid proof of work")
                return False

            parent_hash = block.prev_hash()

            # Orphan: parent not yet known - stash for later.
            if parent_hash not in self.blocks_by_hash:
                self.pending_blocks.setdefault(parent_hash, []).append(block)
                print(
                    "Stored orphan block waiting for parent: "
                    f"block_hash={block_hash.hex()}, parent_hash={parent_hash.hex()}"
                )
                return False

            parent_height = self.height_by_hash[parent_hash]
            height = parent_height + 1

            # Accept the block.
            self.blocks_by_hash[block_hash] = block
            self.height_by_hash[block_hash] = height

            if parent_hash == self.best_tip_hash:
                self._append_to_canonical_chain(block_hash, height)
                self._remove_block_transactions_from_mempool(block)
                print(
                    "Accepted block on canonical chain: "
                    f"height={height}, block_hash={block_hash.hex()}, "
                    f"tx_count={len(block.tx_hashes())}"
                )
            elif height > self.best_tip_height:
                old_canonical_blocks = self._canonical_blocks()
                self._apply_longest_chain_rule(block_hash, height)
                self._sync_mempool_after_canonical_change(old_canonical_blocks)
                print(
                    "Switched to longer chain: "
                    f"height={height}, block_hash={block_hash.hex()}, "
                    f"tx_count={len(block.tx_hashes())}"
                )
            else:
                print(
                    "Stored valid side-fork block: "
                    f"height={height}, block_hash={block_hash.hex()}, "
                    f"tx_count={len(block.tx_hashes())}"
                )

            # Process any orphan blocks that were waiting for this block as their parent.
            self._process_orphans_for_parent(block_hash)

            return True

    # ------------------------------------------------------------------
    # Chain queries
    # ------------------------------------------------------------------

    def get_block_at_height(self, height: int) -> Block | None:
        return self.chain_by_height.get(height)

    def tip(self) -> Block:
        return self.blocks_by_hash[self.best_tip_hash]

    def tip_hash(self) -> bytes:
        return self.best_tip_hash

    def height(self) -> int:
        return self.best_tip_height

    def tx_confirmed(self, tx_hash: bytes, confirmations: int = 3) -> bool:
        """True if tx_hash is buried under at least `confirmations` blocks."""

        with self.lock:
            tx_block_height = self._find_tx_height_in_chain(tx_hash)

            if tx_block_height is None:
                return False

            return self.best_tip_height >= tx_block_height + confirmations

    def tx_in_canonical_chain(self, tx_hash: bytes) -> bool:
        with self.lock:
            return self._find_tx_height_in_chain(tx_hash) is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_to_canonical_chain(
        self,
        block_hash: bytes,
        height: int,
    ) -> None:
        """
        Append a block directly when its parent is the current canonical tip.
        """
        self.chain_by_height[height] = self.blocks_by_hash[block_hash]
        self.best_tip_hash = block_hash
        self.best_tip_height = height

    def _remove_block_transactions_from_mempool(self, block: Block) -> None:
        """
        Remove transactions included in a newly canonical block.
        """
        before_hashes = self._mempool_tx_hashes()

        for tx_hash in block.tx_hashes():
            self.mempool.remove(tx_hash)

        after_hashes = self._mempool_tx_hashes()
        removed_hashes = before_hashes - after_hashes

        if block.tx_hashes():
            print(
                "Mempool update after canonical block: "
                f"before={len(before_hashes)}, after={len(after_hashes)}, "
                f"removed={self._format_hashes(removed_hashes)}, "
                f"block_txs={self._format_hashes(block.tx_hashes())}"
            )

    def _apply_longest_chain_rule(
        self, new_tip_hash: bytes, new_tip_height: int
    ) -> None:
        """
        Make the chain ending at new_tip_hash canonical if it is the longest chain.

        This rebuilds chain_by_height by walking backward from the new tip to genesis.
        """
        new_chain: list[tuple[int, bytes]] = []
        cursor = new_tip_hash

        while cursor in self.blocks_by_hash:
            height = self.height_by_hash[cursor]
            new_chain.append((height, cursor))

            if height == 0:
                break

            cursor = self.blocks_by_hash[cursor].prev_hash()

        for height, block_hash in new_chain:
            self.chain_by_height[height] = self.blocks_by_hash[block_hash]

        self.best_tip_hash = new_tip_hash
        self.best_tip_height = new_tip_height

    def _process_orphans_for_parent(self, parent_hash: bytes) -> None:
        """Process orphan blocks whose missing parent has just been accepted."""

        for block in self.pending_blocks.pop(parent_hash, []):
            self.add_block(block)

    def _canonical_blocks(self) -> list[Block]:
        return [
            self.chain_by_height[height]
            for height in range(self.best_tip_height + 1)
            if height in self.chain_by_height
        ]

    def _sync_mempool_after_canonical_change(
        self,
        old_canonical_blocks: list[Block],
    ) -> None:
        """
        Restore txs from old canonical blocks that fell out of the best chain,
        then remove txs now included in the current canonical chain.
        """
        before_hashes = self._mempool_tx_hashes()
        new_canonical_tx_hashes = self._canonical_tx_hashes()
        old_transactions = self._full_transactions_by_hash(old_canonical_blocks)
        restored_hashes = set()

        for tx_hash, transaction in old_transactions.items():
            if tx_hash not in new_canonical_tx_hashes:
                self.mempool.add(transaction)
                restored_hashes.add(tx_hash)

        for tx_hash in new_canonical_tx_hashes:
            self.mempool.remove(tx_hash)

        after_hashes = self._mempool_tx_hashes()
        removed_hashes = before_hashes - after_hashes

        print(
            "Mempool reorg sync: "
            f"before={len(before_hashes)}, after={len(after_hashes)}, "
            f"restored_from_old_chain={self._format_hashes(restored_hashes)}, "
            f"removed_for_new_chain={self._format_hashes(removed_hashes)}, "
            f"new_chain_txs={self._format_hashes(new_canonical_tx_hashes)}"
        )

    def _canonical_tx_hashes(self) -> set[bytes]:
        tx_hashes = set()

        for block in self._canonical_blocks():
            tx_hashes.update(block.tx_hashes())

        return tx_hashes

    def _full_transactions_by_hash(
        self,
        blocks: list[Block],
    ) -> dict[bytes, Transaction]:
        transactions = {}

        for block in blocks:
            for transaction in block.transactions:
                transactions[transaction.tx_hash()] = transaction

        return transactions

    def _find_tx_height_in_chain(self, tx_hash: bytes) -> int | None:
        """Return the canonical-chain height of the block containing tx_hash."""

        for height in range(self.best_tip_height + 1):
            block = self.chain_by_height.get(height)

            if block and tx_hash in block.tx_hashes():
                return height

        return None

    def _mempool_tx_hashes(self) -> set[bytes]:
        return {transaction.tx_hash() for transaction in self.mempool.get_all()}

    def _format_hashes(self, tx_hashes) -> str:
        hashes = sorted(tx_hash.hex() for tx_hash in tx_hashes)

        if not hashes:
            return "[]"

        return "[" + ", ".join(hashes) + "]"
