from unittest.mock import Mock

from chain.blockchain import Blockchain
from chain.transaction import Transaction
from community import BlockchainCommunity
from payloads import (
    SubmitTransactionPayload,
    SubmitTransactionResponsePayload,
    TransactionGossipPayload,
)


def make_test_community() -> BlockchainCommunity:
    # Build only the state needed by transaction gossip tests, without IPv8 startup.
    community = BlockchainCommunity.__new__(BlockchainCommunity)
    community.blockchain = Blockchain()
    community.mempool = community.blockchain.mempool
    return community


def make_payload(tx: Transaction) -> TransactionGossipPayload:
    return TransactionGossipPayload(
        sender_key=tx.sender_key,
        data=tx.data,
        timestamp=tx.timestamp,
        signature=tx.signature,
    )


def test_broadcast_transaction_uses_transaction_gossip_payload(fake_tx):
    # Internal transaction gossip should not reuse the server SubmitTransaction payload.
    community = make_test_community()
    community.broadcast_to_teammates = Mock()

    community.broadcast_transaction_to_teammates(fake_tx)

    payload = community.broadcast_to_teammates.call_args.args[0]
    assert isinstance(payload, TransactionGossipPayload)
    assert payload.sender_key == fake_tx.sender_key
    assert payload.data == fake_tx.data
    assert payload.timestamp == fake_tx.timestamp
    assert payload.signature == fake_tx.signature


def test_apply_transaction_gossip_accepts_valid_transaction(fake_tx, monkeypatch):
    # A valid gossiped transaction should be added to the local mempool.
    community = make_test_community()
    monkeypatch.setattr(Transaction, "verify_signature", lambda self: True)

    accepted = community.apply_transaction_gossip_payload(make_payload(fake_tx))

    assert accepted
    assert community.mempool.contains(fake_tx.tx_hash())


def test_apply_transaction_gossip_rejects_invalid_transaction(fake_tx, monkeypatch):
    # Invalid gossiped transactions should not enter the mempool.
    community = make_test_community()
    monkeypatch.setattr(Transaction, "verify_signature", lambda self: False)

    accepted = community.apply_transaction_gossip_payload(make_payload(fake_tx))

    assert not accepted
    assert not community.mempool.contains(fake_tx.tx_hash())


def test_apply_transaction_gossip_does_not_rebroadcast(fake_tx, monkeypatch):
    # Gossiped transactions are not re-gossiped, which avoids message loops.
    community = make_test_community()
    community.broadcast_to_teammates = Mock()
    monkeypatch.setattr(Transaction, "verify_signature", lambda self: True)

    accepted = community.apply_transaction_gossip_payload(make_payload(fake_tx))

    assert accepted
    community.broadcast_to_teammates.assert_not_called()


def test_apply_transaction_gossip_ignores_duplicate(fake_tx, monkeypatch):
    # Receiving the same gossip twice should not duplicate work.
    community = make_test_community()
    community.mempool.add(fake_tx)
    monkeypatch.setattr(Transaction, "verify_signature", lambda self: True)

    accepted = community.apply_transaction_gossip_payload(make_payload(fake_tx))

    assert not accepted
    assert len(community.mempool) == 1


def test_submit_transaction_from_server_gossips_once(fake_tx, monkeypatch):
    # Only server-submitted transactions should trigger outgoing transaction gossip.
    community = make_test_community()
    community.is_server_peer = Mock(return_value=True)
    community.ez_send = Mock()
    community.broadcast_transaction_to_teammates = Mock()
    monkeypatch.setattr(Transaction, "verify_signature", lambda self: True)

    payload = SubmitTransactionPayload(
        sender_key=fake_tx.sender_key,
        data=fake_tx.data,
        timestamp=fake_tx.timestamp,
        signature=fake_tx.signature,
    )

    BlockchainCommunity.on_submit_transaction.__wrapped__(community, object(), payload)

    response = community.ez_send.call_args.args[1]
    assert isinstance(response, SubmitTransactionResponsePayload)
    assert response.success
    assert community.mempool.contains(fake_tx.tx_hash())
    community.broadcast_transaction_to_teammates.assert_called_once()
