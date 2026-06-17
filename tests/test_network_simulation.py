from chain.blockchain import Blockchain
from chain.pow import mine_block
from config import BLOCK_DIFFICULTY, HASH_SIZE

def mine_test_block(prev_hash: bytes, transactions=None, timestamp: int = 1):
    # Helper for mining low-difficulty test blocks.
    if transactions is None:
        transactions = []

    return mine_block(
        prev_hash=prev_hash,
        transactions=transactions,
        timestamp=timestamp,
        difficulty=BLOCK_DIFFICULTY,
    )


def broadcast(nodes: list[Blockchain], block, sender_idx: int):
    # Simulate broadcasting one block from one node to all other nodes.
    for i, node in enumerate(nodes):
        if i != sender_idx:
            node.add_block(block)


def test_three_node_convergence():
    # One node mines blocks and broadcasts them to all other nodes.
    nodes = [Blockchain(), Blockchain(), Blockchain()]

    for timestamp in range(1, 6):
        block = mine_test_block(nodes[0].tip_hash(), timestamp=timestamp)

        assert nodes[0].add_block(block)
        broadcast(nodes, block, sender_idx=0)

    assert nodes[0].tip_hash() == nodes[1].tip_hash() == nodes[2].tip_hash()
    assert nodes[0].height() == nodes[1].height() == nodes[2].height() == 5


def test_nodes_converge_after_delayed_block_delivery():
    # Node 0 mines two blocks, but node 2 receives the child before the parent.
    nodes = [Blockchain(), Blockchain(), Blockchain()]

    b1 = mine_test_block(nodes[0].tip_hash(), timestamp=1)
    assert nodes[0].add_block(b1)

    b2 = mine_test_block(b1.block_hash(), timestamp=2)
    assert nodes[0].add_block(b2)

    # Node 1 receives blocks in normal order.
    assert nodes[1].add_block(b1)
    assert nodes[1].add_block(b2)

    # Node 2 receives b2 first, so it stores b2 as an orphan.
    assert not nodes[2].add_block(b2)
    assert nodes[2].height() == 0

    # Once node 2 receives b1, it should process b2 and catch up.
    assert nodes[2].add_block(b1)

    assert nodes[0].tip_hash() == nodes[1].tip_hash() == nodes[2].tip_hash()
    assert nodes[0].height() == nodes[1].height() == nodes[2].height() == 2


def test_nodes_converge_to_longer_fork():
    # Nodes first see different forks, then all converge to the longer fork.
    nodes = [Blockchain(), Blockchain(), Blockchain()]

    genesis_hash = nodes[0].tip_hash()

    # Two competing blocks at height 1.
    b1a = mine_test_block(genesis_hash, timestamp=1)
    b1b = mine_test_block(genesis_hash, timestamp=2)

    # Node 0 follows fork A.
    assert nodes[0].add_block(b1a)

    # Node 1 follows fork B.
    assert nodes[1].add_block(b1b)

    # Node 2 sees fork A first.
    assert nodes[2].add_block(b1a)

    # Fork B becomes longer.
    b2b = mine_test_block(b1b.block_hash(), timestamp=3)

    assert nodes[1].add_block(b2b)

    # Broadcast the longer fork to everyone.
    assert nodes[0].add_block(b1b)
    assert nodes[0].add_block(b2b)

    assert nodes[2].add_block(b1b)
    assert nodes[2].add_block(b2b)

    assert nodes[0].tip_hash() == nodes[1].tip_hash() == nodes[2].tip_hash()
    assert nodes[0].tip_hash() == b2b.block_hash()
    assert nodes[0].height() == nodes[1].height() == nodes[2].height() == 2


def test_nodes_reject_duplicate_broadcasts():
    # A node should ignore the same block if it receives it multiple times.
    nodes = [Blockchain(), Blockchain(), Blockchain()]

    b1 = mine_test_block(nodes[0].tip_hash(), timestamp=1)

    assert nodes[0].add_block(b1)

    assert nodes[1].add_block(b1)
    assert not nodes[1].add_block(b1)

    assert nodes[1].height() == 1
    assert nodes[1].tip_hash() == b1.block_hash()


def test_partition_then_rejoin_converges_to_longer_chain():
    # Simulate a temporary network partition where nodes mine different chains.
    nodes = [Blockchain(), Blockchain(), Blockchain()]

    genesis_hash = nodes[0].tip_hash()

    # Partition A: node 0 mines a shorter chain.
    a1 = mine_test_block(genesis_hash, timestamp=1)
    assert nodes[0].add_block(a1)

    # Partition B: nodes 1 and 2 mine/receive a longer chain.
    b1 = mine_test_block(genesis_hash, timestamp=2)
    b2 = mine_test_block(b1.block_hash(), timestamp=3)

    assert nodes[1].add_block(b1)
    assert nodes[1].add_block(b2)

    assert nodes[2].add_block(b1)
    assert nodes[2].add_block(b2)

    # Network rejoins: node 0 receives the longer chain.
    assert nodes[0].add_block(b1)
    assert nodes[0].add_block(b2)

    assert nodes[0].tip_hash() == nodes[1].tip_hash() == nodes[2].tip_hash()
    assert nodes[0].tip_hash() == b2.block_hash()
    assert nodes[0].height() == nodes[1].height() == nodes[2].height() == 2