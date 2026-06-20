from chain.blockchain import Blockchain
from chain.pow import mine_block
from config import ALLOWED_FUTURE_TIMESTAMP_DRIFT_SECONDS, BLOCK_DIFFICULTY


def mine_test_block(prev_hash: bytes, timestamp: int, difficulty: int = BLOCK_DIFFICULTY):
    return mine_block(
        prev_hash=prev_hash,
        transactions=[],
        timestamp=timestamp,
        difficulty=difficulty,
    )


def add_block_at(chain: Blockchain, timestamp: int) -> None:
    block = mine_test_block(chain.tip_hash(), timestamp)
    assert chain.add_block(block)


def test_normal_increasing_timestamps_are_accepted():
    chain = Blockchain()

    add_block_at(chain, 100)
    add_block_at(chain, 115)

    assert chain.height() == 2


def test_backward_timestamp_is_rejected():
    chain = Blockchain()
    add_block_at(chain, 100)
    add_block_at(chain, 115)
    block = mine_test_block(chain.tip_hash(), 110)

    assert not chain.add_block(block)
    assert chain.height() == 2


def test_equal_parent_timestamp_is_rejected():
    chain = Blockchain()
    add_block_at(chain, 100)
    block = mine_test_block(chain.tip_hash(), 100)

    assert not chain.add_block(block)
    assert chain.height() == 1


def test_extreme_future_timestamp_is_rejected(monkeypatch):
    chain = Blockchain()
    now = 1_000
    monkeypatch.setattr("chain.blockchain.time.time", lambda: now)
    block = mine_test_block(
        chain.tip_hash(),
        now + ALLOWED_FUTURE_TIMESTAMP_DRIFT_SECONDS + 1,
    )

    assert not chain.add_block(block)
    assert chain.height() == 0


def test_allowed_future_timestamp_is_accepted(monkeypatch):
    chain = Blockchain()
    now = 1_000
    monkeypatch.setattr("chain.blockchain.time.time", lambda: now)
    block = mine_test_block(
        chain.tip_hash(),
        now + ALLOWED_FUTURE_TIMESTAMP_DRIFT_SECONDS,
    )

    assert chain.add_block(block)
    assert chain.height() == 1


def test_rejected_future_timestamp_does_not_affect_difficulty(monkeypatch):
    chain = Blockchain()
    now = 1_000
    monkeypatch.setattr("chain.blockchain.time.time", lambda: now)
    before = chain.next_difficulty()
    block = mine_test_block(
        chain.tip_hash(),
        now + ALLOWED_FUTURE_TIMESTAMP_DRIFT_SECONDS + 1,
    )

    assert not chain.add_block(block)
    assert chain.next_difficulty() == before
