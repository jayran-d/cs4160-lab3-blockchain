import asyncio

from aiohttp import payload
from ipv8.community import Community
from ipv8.lazy_community import lazy_wrapper

from chain import block
from chain.blockchain import Blockchain
from chain.pretty_print import print_block

from chain.transaction import Transaction
from chain.blockchain import Blockchain
from chain.miner import Miner
from chain.transaction import Transaction
from payloads import (
    SubmitTransactionPayload,
    SubmitTransactionResponsePayload,
    GetChainHeightPayload,
    ChainHeightResponsePayload,
    GetBlockPayload,
    BlockResponsePayload,
)

from config import (
    BLOCKCHAIN_COMMUNITY_ID_HEX,
    REGISTER_SERVER_PUBLIC_KEY_HEX,
    MEMBER_PUBLIC_KEYS_HEX,
    GROUP_ID,
)


class BlockchainCommunity(Community):

    community_id = bytes.fromhex(BLOCKCHAIN_COMMUNITY_ID_HEX)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.group_id = GROUP_ID

        # ------------------------------------------------------------------
        # Message handlers
        # ------------------------------------------------------------------

        self.add_message_handler(SubmitTransactionPayload, self.on_submit_transaction)
        self.add_message_handler(GetChainHeightPayload, self.on_get_chain_height)
        self.add_message_handler(GetBlockPayload, self.on_get_block)

        # ------------------------------------------------------------------
        # Known peers
        # ------------------------------------------------------------------
        self.server_peer = None

        # Map teammate name -> peer object once discovered.
        self.teammate_peers = {
            "darian": None,
            "jayran": None,
            "yves": None,
        }

        # Do not include our own peer here yet. We filter dynamically using
        # our own public key in is_teammate_peer().
        self.expected_teammate_keys = {
            name.lower(): bytes.fromhex(public_key_hex)
            for name, public_key_hex in MEMBER_PUBLIC_KEYS_HEX.items()
        }

        # ------------------------------------------------------------------
        # Local blockchain state
        # ------------------------------------------------------------------
        self.blockchain = Blockchain()
        self.mempool = self.blockchain.mempool
        self.miner = Miner(
            blockchain=self.blockchain,
            mempool=self.mempool,
            community=self,
        )
        self.mining_task: asyncio.Task | None = None

    # ----------------------------------------------------------------------
    # Peer and key helper methods
    # ----------------------------------------------------------------------

    def expected_server_public_key(self) -> bytes:
        """
        Return the official Lab 3 registration/server public key as bytes.
        """
        return bytes.fromhex(REGISTER_SERVER_PUBLIC_KEY_HEX)

    def peer_public_key(self, peer) -> bytes:
        """
        Return an IPv8 peer's public key in the byte format used by the lab.
        """
        return peer.public_key.key_to_bin()

    def own_public_key(self) -> bytes:
        """
        Return this node's public key.
        """
        return self.my_peer.public_key.key_to_bin()

    def is_server_peer(self, peer) -> bool:
        """
        Check whether a peer is the official Lab 3 server.
        """
        return self.peer_public_key(peer) == self.expected_server_public_key()

    def is_own_peer_key(self, public_key: bytes) -> bool:
        """
        Check whether a public key belongs to this node.
        """
        return public_key == self.own_public_key()

    def is_teammate_peer(self, peer) -> bool:
        """
        Check whether a peer is one of the known group members, excluding self.
        """
        peer_key = self.peer_public_key(peer)

        if self.is_own_peer_key(peer_key):
            return False

        return peer_key in self.expected_teammate_keys.values()

    def teammate_name_for_peer(self, peer) -> str | None:
        """
        Return the teammate name for a peer, or None if it is unknown.
        """
        peer_key = self.peer_public_key(peer)

        for name, expected_key in self.expected_teammate_keys.items():
            if peer_key == expected_key:
                return name

        return None

    # ----------------------------------------------------------------------
    # Peer discovery helper methods
    # ----------------------------------------------------------------------

    async def find_server_peer(self):
        """
        Keep looking through discovered peers until the Lab 3 server is found.
        """
        while self.server_peer is None:
            peers = self.get_peers()
            print(f"Discovered {len(peers)} peer(s).")

            for peer in peers:
                try:
                    if self.is_server_peer(peer):
                        self.server_peer = peer
                        print("===== Found Lab 3 server =====")
                        return peer
                except Exception as error:
                    print(f"Skipping peer with unreadable public key: {error}")

            print("Server peer not found yet.")
            await asyncio.sleep(0.25)

    async def find_teammate_peers(self):
        """
        Keep looking through discovered peers until all other teammates are found.
        """
        while True:
            peers = self.get_peers()
            print(f"Discovered {len(peers)} peer(s).")

            for peer in peers:
                try:
                    teammate_name = self.teammate_name_for_peer(peer)
                except Exception as error:
                    print(f"Skipping peer with unreadable public key: {error}")
                    continue

                if teammate_name is None:
                    continue

                # # Do not store ourselves as a teammate.
                # if self.is_own_peer_key(self.peer_public_key(peer)):
                #     continue

                if self.teammate_peers[teammate_name] is None:
                    self.teammate_peers[teammate_name] = peer
                    print(f"===== Found teammate: {teammate_name} =====")

            if self.all_teammates_found():
                print("All teammate peers found.")
                return self.teammate_peers

            await asyncio.sleep(0.25)

    def all_teammates_found(self) -> bool:
        """
        Return True once all teammates except this node have been found.
        """
        own_key = self.own_public_key()

        for name, expected_key in self.expected_teammate_keys.items():
            if expected_key == own_key:
                continue

            if self.teammate_peers[name] is None:
                return False

        return True

    # ----------------------------------------------------------------------
    # Broadcast helper methods
    # ----------------------------------------------------------------------

    def broadcast_to_teammates(self, payload) -> None:
        """
        Send a payload to all currently discovered teammates.
        """
        for teammate_peer in self.teammate_peers.values():
            if teammate_peer is None:
                continue

            self.ez_send(teammate_peer, payload)

    # ----------------------------------------------------------------------
    # Miner lifecycle
    # ----------------------------------------------------------------------

    def start_mining(self) -> None:
        """
        Start the background mining loop once.
        """
        if self.mining_task is not None and not self.mining_task.done():
            return

        self.mining_task = asyncio.create_task(self.miner.run_forever())

    def stop_mining(self) -> None:
        """
        Stop the background mining loop.
        """
        self.miner.stop()

        if self.mining_task is not None:
            self.mining_task.cancel()

    # ----------------------------------------------------------------------
    # Lab server query message handlers
    # ----------------------------------------------------------------------
    @lazy_wrapper(SubmitTransactionPayload)
    def on_submit_transaction(self, peer, payload: SubmitTransactionPayload):
        if not self.is_server_peer(peer):
            print("Ignoring SubmitTransaction from non-server peer")
            return

        tx = Transaction(
            sender_key=payload.sender_key,
            data=payload.data,
            timestamp=payload.timestamp,
            signature=payload.signature,
        )

        tx_hash = tx.tx_hash()
        should_broadcast = False

        if not tx.verify_signature():
            success = False
            message = "Invalid transaction signature"

            print(
                f"Rejected transaction: invalid signature, " f"tx_hash={tx_hash.hex()}"
            )

        elif self.blockchain.mempool.contains(tx_hash):
            success = True
            message = "Transaction already in mempool"

            print(f"Duplicate transaction already in mempool: {tx_hash.hex()}")

        elif self.blockchain.tx_in_canonical_chain(tx_hash):
            success = True
            message = "Transaction already included in best chain"

            print(f"Transaction already in best chain: {tx_hash.hex()}")

        else:
            self.blockchain.mempool.add(tx)

            success = True
            message = "Transaction accepted into mempool"
            should_broadcast = True

            print(f"Accepted transaction: {tx_hash.hex()}")
            print(f"Mempool size: {len(self.blockchain.mempool)}")

        response = SubmitTransactionResponsePayload(
            success=success,
            tx_hash=tx_hash,
            message=message,
        )

        self.ez_send(peer, response)

        if should_broadcast:
            # Share transaction with teammates.
            self.broadcast_to_teammates(tx)
            print("Broadcasted submitted transaction to teammates")

    @lazy_wrapper(GetChainHeightPayload)
    def on_get_chain_height(self, peer, payload: GetChainHeightPayload):
        if not self.is_server_peer(peer):
            print("Ignoring GetChainHeight from non-server peer")
            return

        height = self.blockchain.height()
        tip_hash = self.blockchain.tip_hash()

        response = ChainHeightResponsePayload(
            request_id=payload.request_id,
            height=height,
            tip_hash=tip_hash,
        )

        self.ez_send(peer, response)

        print(
            f"Sent chain height to server: request_id={payload.request_id}, height={height}, tip_hash={tip_hash.hex()}"
        )

    @lazy_wrapper(GetBlockPayload)
    def on_get_block(self, peer, payload: GetBlockPayload):
        if not self.is_server_peer(peer):
            print("Ignoring GetBlock from non-server peer")
            return

        block = self.blockchain.get_block_at_height(payload.height)

        if block is None:
            print(f"Requested block not found: height={payload.height}")
            return

        response = BlockResponsePayload(
            height=payload.height,
            prev_hash=block.prev_hash(),
            txs_hash=block.header.txs_hash,
            timestamp=block.header.timestamp,
            difficulty=block.header.difficulty,
            nonce=block.header.nonce,
            block_hash=block.block_hash(),
            tx_hashes=block.tx_hashes_bytes(),
        )

        self.ez_send(peer, response)

        print("Sent block to server:")
        print_block(block, height=payload.height)

    # ----------------------------------------------------------------------
    # Internal teammate message handlers
    # ----------------------------------------------------------------------
