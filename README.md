# CS4160 Lab 3 - Decentralized Proof-of-Work Blockchain

## Overview

This project implements a decentralized Proof-of-Work blockchain using IPv8. The
system allows peers to discover each other, exchange signed transactions, mine
blocks, propagate newly mined blocks, and maintain a consistent blockchain using
the longest-chain consensus rule.

The implementation was developed as part of the Blockchain Engineering (CS4160)
course. The full assignment description is kept separately in
`docs/LAB-3-DESCRIPTION.md`; this README focuses on how our implementation works
and how to run it.

## Features

### Networking

- Peer discovery using IPv8 overlays
- Registration with the provided Lab 3 server
- Transaction gossip between teammates
- Block gossip between teammates
- Peer filtering by configured public keys

### Blockchain

- Fixed shared genesis block
- Signed transactions
- Transaction validation
- Mempool management
- Proof-of-Work mining
- Block validation
- Orphan block handling
- Longest-chain fork resolution
- Mempool synchronization after chain reorganizations

### Server Integration

- Transaction submission support
- Chain height queries
- Block retrieval queries
- Confirmation handling
- Server-key validation before accepting server messages

## Repository Structure

```text
.
├── chain/
│   ├── block.py
│   ├── blockchain.py
│   ├── mempool.py
│   ├── miner.py
│   ├── pow.py
│   ├── pretty_print.py
│   ├── transaction.py
│   └── utils.py
│
├── registration/
│   ├── registation_community.py
│   └── registration_payloads.py
│
├── bot_tools/
├── docs/
├── tests/
│
├── client.py
├── community.py
├── payloads.py
├── config.py
├── pytest.ini
└── requirements.txt
```

### Important Components

| Component       | Description                                                                   |
| --------------- | ----------------------------------------------------------------------------- |
| `chain/`        | Core blockchain implementation                                                |
| `registration/` | Registration protocol and server interaction                                  |
| `community.py`  | Main blockchain overlay, peer filtering, transaction gossip, and block gossip |
| `payloads.py`   | Blockchain network message payloads                                           |
| `client.py`     | Application entry point                                                       |
| `config.py`     | Group ID, community IDs, public keys, key path, and mining parameters         |
| `tests/`        | Unit and simulation tests                                                     |
| `docs/`         | Development process and contribution notes                                    |
| `bot_tools/`    | Sandbox overlay and transaction bot for testing.                              |

## Design Decisions

### Separate Registration Overlay

The registration protocol is isolated into a dedicated IPv8 overlay. This keeps
server registration separate from the blockchain overlay and makes the main
blockchain community easier to reason about.

### Fixed Genesis Block

All nodes create the same genesis block locally. This prevents the group from
starting on different chains before any network messages are exchanged.

### Public-Key Filtering

The node only accepts server messages from the configured Lab 3 server public
key. Teammate gossip is also filtered by the configured group member public keys.
This avoids processing messages from unrelated peers discovered through IPv8.

### Longest-Chain Consensus

Forks are resolved using the longest valid chain rule. When a longer valid chain
is received, the node switches to that chain after validating the received
blocks.

### Orphan Block Handling

If a block is received before its parent, it is stored temporarily as an orphan.
When the missing parent arrives, the waiting block can be processed.

### Mempool Reorganization Handling

When the canonical chain changes, transactions from replaced blocks are restored
to the mempool when needed, and transactions included in the new canonical chain
are removed.

The mempool also maintains a global index of all validated transactions that
have been observed by the node. This index is used to reconstruct transaction
objects when processing block gossip messages that contain only transaction
hashes.

### Periodic Mining

Mining runs continuously in a background task. At each interval, the miner builds
a candidate block from the current mempool and searches for a valid
Proof-of-Work nonce.

The nonce search itself runs in a worker thread so that IPv8 message handling can
continue while a block is being mined. This keeps the node responsive to incoming
transactions and block gossip. Mining also checks a stop signal every
`MINING_STOP_CHECK_INTERVAL` nonce attempts, allowing the node to interrupt the
current search when a teammate's block is received.

### Transaction Hash-Based Block Gossip

Blocks are gossiped using transaction hashes rather than transmitting the full
transaction contents. This significantly reduces the size of block gossip
messages, since transaction data is not duplicated when peers have already
received the corresponding transactions through transaction gossip.

To support this design, every validated transaction is stored in a global
transaction index (`all_known_txs`) in addition to being placed in the mempool.
This applies both to transactions received from the server and transactions
received through peer gossip.

When a block gossip message is received, the block contains only the hashes of
its transactions. The receiving node reconstructs the full transaction list by
looking up each transaction hash in `all_known_txs`. This allows blocks to be
validated and applied without requiring transactions to be retransmitted inside
every block message.

This approach reduces network overhead while still allowing peers to reconstruct
and verify received blocks.

### Adaptive Difficulty Parameters

Difficulty tuning values are centralized in `config.py`:

| Parameter                                | Default | Purpose                                                     |
| ---------------------------------------- | ------: | ----------------------------------------------------------- |
| `BLOCK_DIFFICULTY`                       |      16 | Initial difficulty for the first mined block after genesis. |
| `TARGET_BLOCK_TIME_SECONDS`              |      15 | Target time between blocks.                                 |
| `DIFFICULTY_ADJUSTMENT_WINDOW_SIZE`      |       5 | Number of recent blocks used for retargeting.               |
| `MIN_BLOCK_DIFFICULTY`                   |      12 | Lowest accepted lab-chain difficulty.                       |
| `MAX_BLOCK_DIFFICULTY`                   |      24 | Highest accepted lab-chain difficulty.                      |
| `MAX_DIFFICULTY_CHANGE_PER_BLOCK`        |       2 | Largest difficulty step after each adjustment window.       |
| `BLOCK_TIME_TOLERANCE_RATIO`             |    0.20 | Timing error tolerated before retargeting.                  |
| `MIN_OBSERVED_BLOCK_TIME_SECONDS`        |       3 | Smallest interval used by retargeting.                      |
| `MAX_OBSERVED_BLOCK_TIME_SECONDS`        |      60 | Largest interval used by retargeting.                       |
| `ALLOWED_FUTURE_TIMESTAMP_DRIFT_SECONDS` |      30 | Clock skew tolerated for future-dated blocks.               |

The defaults are chosen for a 3-node laptop chain: a
15-second target leaves time for gossip, a 5-block window smooths one lucky block
without reacting too slowly, and a 12 to 24 difficulty range keeps a steady range
for this setup. The next difficulty is computed deterministically from recent
chain history and clamped to avoid sudden jumps. Blocks must also move forward
relative to recent median chain time and cannot be too far in the future.

## Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If you get an error from `ipv8_rust_tunnels` then you may need to use an old version of python (check the error you got). See `Python Version` section below.

Place the node's IPv8 private key at the path configured in `config.py`.

By default this is:

```text
keys/lab_identity_key.pem
```

Before running, check the relevant values in `config.py`:

- `GROUP_ID`
- `BLOCKCHAIN_COMMUNITY_ID_HEX`
- `REGISTER_SERVER_PUBLIC_KEY_HEX`
- `MEMBER_PUBLIC_KEYS_HEX`
- `KEY_FILE`
- `BLOCK_DIFFICULTY`
- `MINE_BLOCK_PER_SECONDS`
- `MINING_STOP_CHECK_INTERVAL`

### Python Version

This project should be run with Python 3.11 or another Python version supported
by the IPv8 dependencies.

Python 3.14 may fail when installing `ipv8_rust_tunnels`, because one of its
native dependencies may not yet support that Python version. If installation
fails with a PyO3 or `ipv8_rust_tunnels` error, recreate the virtual environment
with Python 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Project

Each group member runs one node. Exactly one of the three nodes should be started
with registration enabled, so that the Lab 3 server can join the blockchain
community and submit transactions.

### Start the Registering Node

One group member starts their node with the `-r` flag:

```bash
python3 client.py -r
```

The long option is also supported:

```bash
python3 client.py --register
```

This starts the normal blockchain node and also registers the configured
blockchain community with the Lab 3 server.

### Start the Other Nodes

The remaining group members start their nodes normally:

```bash
python3 client.py
```

After startup, all nodes automatically:

- discover teammates
- listen for incoming messages
- exchange transactions
- mine blocks
- propagate blocks
- synchronize chains

No additional manual interaction is required after the nodes are running.

### Stop a Node

Stop a node with:

```text
Ctrl+C
```

## Expected Runtime Behavior

During a successful run, the terminal should show messages indicating that:

- teammates are discovered
- transactions are received and validated
- transactions are added to the mempool
- blocks are mined
- blocks are gossiped to teammates
- received blocks are validated and added to the chain
- the chain height increases over time
- when a node is stopped with `Ctrl+C`, it prints its canonical chain; after enough time to converge, all nodes should print the same longest chain with enough time to converge.

### Sandbox Testing with the Transaction Bot

`bot_tools/bot_client.py` is a local testing tool that sends signed test
transactions to the running blockchain nodes. Run it with:

```bash
python bot_tools/bot_client.py --interval 1.0
```

`--interval` controls how often test transactions are generated.

Before using the transaction bot, update `config.py` so that the bot public key is
treated as the allowed server key. Around line 65, set:

```python
REGISTER_SERVER_PUBLIC_KEY_HEX = "4c69624e61434c504b3a17646deee961ab394dbff5588ab83b63d112d28f4400cd48924c53be3c5eb87e547b75a13ac43c281c764f4a5135a0d1e87d715d45255f0db4d429447495d910"
```

The original Lab 3 server public key should be commented out while using the bot.
Only one `REGISTER_SERVER_PUBLIC_KEY_HEX` value should be active at a time.

This is necessary because incoming server-style messages are filtered by public
key. If the bot public key is not configured as the allowed server key, bot
transactions will be ignored.

## Blockchain Workflow

1. A transaction is received.
2. The transaction signature is validated.
3. The transaction is added to the mempool.
4. The transaction is gossiped to teammates.
5. The miner periodically creates a candidate block from mempool transactions.
6. A valid Proof-of-Work solution is found.
7. The block is appended to the local chain.
8. The block is broadcast to teammates.
9. Peers validate and apply the block.
10. In case of competing chains, the longest valid chain is selected.

## Running Tests

Run all local tests with:

```bash
pytest
```

The tests cover core blockchain behavior, including:

- block formatting
- transaction validation
- Proof-of-Work
- mempool behavior
- mining
- mining interruption
- transaction gossip
- block gossip
- fork handling
- network simulation behavior

## Known Limitations

- Blockchain state is not persisted to disk.
- Restarting a node resets local blockchain state.
- Mining difficulty is fixed and does not adjust dynamically.
- The `all_known_txs` transaction index is not garbage collected and may grow
  during long-running executions.

## Additional Documentation

See:

- `docs/CONTRIBUTIONS.md`
- `docs/DEVELOPMENT_PROCESS.md`
