# CS4160 Lab 3 - Decentralized Proof-of-Work Blockchain

## Overview

This project implements a decentralized Proof-of-Work blockchain using IPv8. The
system allows peers to discover each other, exchange signed transactions, mine
blocks, propagate newly mined blocks, and maintain a consistent blockchain using
the longest-chain consensus rule.

The implementation was developed as part of the Blockchain Engineering (CS4160)
course. The full assignment description is kept separately in
`ASSIGNMENTREADME.md`; this README focuses on how our implementation works and
how to run it.

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

### Periodic Mining

Mining runs continuously in a background task. At each interval, the miner builds
a candidate block from the current mempool and searches for a valid
Proof-of-Work nonce.

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

Place the node's IPv8 private key at the path configured in `config.py`.
By default this is:

```text
keys/lab_identity_key.pem
```

Private keys should not be committed.

Before running, check the relevant values in `config.py`:

- `GROUP_ID`
- `BLOCKCHAIN_COMMUNITY_ID_HEX`
- `REGISTER_SERVER_PUBLIC_KEY_HEX`
- `MEMBER_PUBLIC_KEYS_HEX`
- `KEY_FILE`
- `BLOCK_DIFFICULTY`
- `MINE_BLOCK_PER_SECONDS`

## Running the Project

### Start a Node

Each group member starts one node:

```bash
python3 client.py
```

After startup, nodes automatically:

- discover teammates
- listen for incoming messages
- exchange transactions
- mine blocks
- propagate blocks
- synchronize chains

No additional manual interaction is required after the node is running.

### Register with the Server

When all three nodes are online and have found each other, one group member can
start a node with registration enabled:

```bash
python3 client.py -r
```

The long option is also supported:

```bash
python3 client.py --register
```

This registers the configured blockchain community with the Lab 3 server so that
the server can join the community and submit transactions.

### Stop a Node

Stop a node with:

```text
Ctrl+C
```

# Sandbox testing with the transaction bot

To exercise mempool, mining, and gossip behavior without touching the
production chain used for grading, run the node with `--test`:

```bash
source .venv/bin/activate
python client.py --test
```

This starts a second overlay (`BotBlockchainCommunity`, its own `community_id`
configured in `config.py`) alongside the real one. A `TransactionBot` generates
signed test transactions on an interval (`--test-interval`, default 1 second)
and gossips them to the other teammates' sandbox overlays. All three group
members should pass `--test` for the sandbox chain to converge. On shutdown,
both the production chain and the sandbox chain are printed separately.

You can also run just the sandbox overlay, without the production chain, using
`bot_tools/bot_client.py`:

```bash
source .venv/bin/activate
python bot_tools/bot_client.py
```

On shutdown, the client prints the final local chain for inspection.

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
- transaction gossip
- block gossip
- fork handling
- network simulation behavior

## Known Limitations

- Blockchain state is not persisted to disk.
- Restarting a node resets local blockchain state.
- Mining difficulty is fixed and does not adjust dynamically.

## Additional Documentation

See:

- `docs/CONTRIBUTIONS.md`
- `docs/DEVELOPMENT_PROCESS.md`
