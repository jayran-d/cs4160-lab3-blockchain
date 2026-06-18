import asyncio
from random import random
import time

from ipv8.keyvault.crypto import ECCrypto

from chain import transaction
from chain.transaction import Transaction
from chain.utils import u64_be
from community import BlockchainCommunity
from payloads import SubmitTransactionPayload


class TransactionBot:
    """
    Generates valid signed test transactions and gossips them over the normal
    blockchain community.
    """

    def __init__(
        self,
        community: BlockchainCommunity,
        interval_seconds: float = 1.0,
    ):
        self.community = community
        self.interval_seconds = interval_seconds
        self.crypto = ECCrypto()
        self.private_key = self.crypto.generate_key("curve25519")
        self.counter = 0
        self.task: asyncio.Task | None = None

    def start(self) -> None:
        if self.task is not None and not self.task.done():
            return

        self.task = asyncio.create_task(self.run())
        print(f"Started transaction bot: interval_seconds={self.interval_seconds}")

    def stop(self) -> None:
        if self.task is not None:
            self.task.cancel()

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            self.create_and_send_transaction_to_random_teammate()

    def create_and_send_transaction_to_random_teammate(self) -> Transaction | None:
        timestamp = int(time.time())
        self.counter += 1

        sender_key = self.private_key.pub().key_to_bin()
        data = (
            f"test-tx group={self.community.group_id} "
            f"node={self.community.own_public_key().hex()[:12]} "
            f"counter={self.counter}"
        ).encode()

        signed_data = sender_key + data + u64_be(timestamp)
        signature = self.crypto.create_signature(self.private_key, signed_data)

        tx = Transaction(
            sender_key=sender_key,
            data=data,
            timestamp=timestamp,
            signature=signature,
        )

        tx_hash = tx.tx_hash()

        if not tx.verify_signature():
            print(f"Transaction bot generated invalid transaction: {tx_hash.hex()}")
            return None

        if self.community.mempool.contains(tx_hash):
            print(f"Transaction bot duplicate already in mempool: {tx_hash.hex()}")
            return tx

        if self.community.blockchain.tx_in_canonical_chain(tx_hash):
            print(f"Transaction bot duplicate already in chain: {tx_hash.hex()}")
            return tx

        self.community.mempool.add(tx)

        print(
            "Transaction bot accepted local tx: "
            f"tx_hash={tx_hash.hex()}, mempool_size={len(self.community.mempool)}"
        )

        if not self.community.teammate_peers:
            print("Transaction bot could not gossip tx: no teammate peers known")
            return tx

        peer = random.choice(self.community.teammate_peers)

        payload = SubmitTransactionPayload(
            sender_key=tx.sender_key,
            data=tx.data,
            timestamp=tx.timestamp,
            signature=tx.signature,
        )

        self.community.ez_send(peer, payload)

        print(
            "Transaction bot sent tx to random teammate: "
            f"tx_hash={tx_hash.hex()}, peer={peer}"
        )

        return tx

    # def create_and_broadcast_transaction(self) -> Transaction | None:
    #     timestamp = int(time.time())
    #     self.counter += 1
    #     sender_key = self.private_key.pub().key_to_bin()
    #     data = (
    #         f"test-tx group={self.community.group_id} "
    #         f"node={self.community.own_public_key().hex()[:12]} "
    #         f"counter={self.counter}"
    #     ).encode()
    #     signed_data = sender_key + data + u64_be(timestamp)
    #     signature = self.crypto.create_signature(self.private_key, signed_data)
    #     transaction = Transaction(
    #         sender_key=sender_key,
    #         data=data,
    #         timestamp=timestamp,
    #         signature=signature,
    #     )
    #     tx_hash = transaction.tx_hash()

    #     if not transaction.verify_signature():
    #         print(f"Transaction bot generated invalid transaction: {tx_hash.hex()}")
    #         return None

    #     if self.community.mempool.contains(tx_hash):
    #         print(f"Transaction bot duplicate already in mempool: {tx_hash.hex()}")
    #         return transaction

    #     if self.community.blockchain.tx_in_canonical_chain(tx_hash):
    #         print(f"Transaction bot duplicate already in chain: {tx_hash.hex()}")
    #         return transaction

    #     self.community.mempool.add(transaction)

    #     print(
    #         "Transaction bot accepted local tx: "
    #         f"tx_hash={tx_hash.hex()}, mempool_size={len(self.community.mempool)}"
    #     )

    #     self.community.broadcast_transaction_to_teammates(transaction)
    #     print(f"Transaction bot gossiped tx to teammates: tx_hash={tx_hash.hex()}")

    #     return transaction
