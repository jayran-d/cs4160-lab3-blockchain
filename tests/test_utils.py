import unittest

from chain.block import BlockHeader, compute_txs_hash
from chain.pow import count_leading_zero_bits, mine_block, valid_pow
from chain.transaction import Transaction
from chain.utils import sha256


class UtilsTests(unittest.TestCase):
    def test_tx_hash_is_32_bytes(self) -> None:
        # Transaction hashes must be SHA-256 digests, which are always 32 bytes.
        tx = Transaction(
            sender_key=b"a",
            data=b"hello",
            timestamp=123,
            signature=b"sig",
        )

        self.assertEqual(len(tx.tx_hash()), 32)

    def test_empty_commitment(self) -> None:
        # Empty blocks commit to SHA256(b""), not 32 zero bytes.
        self.assertEqual(compute_txs_hash([]), sha256(b""))

    def test_header_is_84_bytes(self) -> None:
        # The server validates the exact binary block header size from the README.
        header = BlockHeader(
            prev_hash=b"\x00" * 32,
            txs_hash=b"\x11" * 32,
            timestamp=1,
            difficulty=8,
            nonce=0,
        )

        self.assertEqual(len(header.pack()), 84)

    def test_leading_zero_bits(self) -> None:
        # Proof-of-work difficulty is measured in leading zero bits.
        self.assertEqual(count_leading_zero_bits(b"\x00"), 8)
        self.assertEqual(count_leading_zero_bits(b"\x00\x00"), 16)
        self.assertEqual(count_leading_zero_bits(b"\x0f"), 4)

    def test_mining(self) -> None:
        # Mined blocks must satisfy their declared proof-of-work difficulty.
        block = mine_block(
            prev_hash=b"\x00" * 32,
            transactions=[],
            timestamp=1,
            difficulty=12,
        )

        self.assertTrue(valid_pow(block.block_hash(), 12))


if __name__ == "__main__":
    unittest.main()
