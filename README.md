# CS4160 Lab 3 - Decentralized Proof-of-Work Blockchain

## Overview

This project implements a decentralized Proof-of-Work blockchain using IPv8. The system allows peers to discover each other through a registration server, exchange signed transactions, mine blocks, propagate newly mined blocks, and maintain a consistent blockchain using a longest-chain consensus rule.

The implementation was developed as part of the Blockchain Engineering (CS4160) course.

## Features

### Networking

* Peer registration through the provided registration server
* Peer discovery using IPv8 overlays
* Transaction gossip between teammates
* Block gossip between teammates

### Blockchain

* Signed transactions
* Transaction validation
* Mempool management
* Proof-of-Work mining
* Block validation
* Longest-chain fork resolution
* Chain synchronization

### Server Integration

* Transaction submission support
* Chain height queries
* Block retrieval queries
* Confirmation handling

## Repository Structure

```text
.
├── chain/
│   ├── block.py
│   ├── blockchain.py
│   ├── block_header.py
│   ├── mempool.py
│   ├── miner.py
│   ├── transaction.py
│   └── utils.py
│
├── registration/
│   ├── community.py
│   └── payloads.py
│
├── bot_tools/
├── tests/
│
├── client.py
├── community.py
├── payloads.py
├── config.py
└── requirements.txt
```

### Important Components

| Component     | Description                                  |
| ------------- | -------------------------------------------- |
| chain/        | Core blockchain implementation               |
| registration/ | Registration protocol and server interaction |
| community.py  | Main blockchain overlay                      |
| payloads.py   | Blockchain network messages                  |
| client.py     | Application entry point                      |
| tests/        | Unit and integration tests                   |

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

## Running the Project

### Register a Node

One node should be started with registration enabled:

```bash
python3 client.py -r
```

This registers the group with the server so that the server can join the blockchain community and submit transactions.

### Start Additional Nodes

All remaining nodes can be started normally:

```bash
python3 client.py
```

After startup, nodes automatically:

* Discover teammates
* Listen for incoming messages
* Exchange transactions
* Mine blocks
* Propagate blocks
* Synchronize chains

No additional manual interaction is required.

## Blockchain Workflow

1. A transaction is created or received.
2. The transaction is validated and added to the mempool.
3. The transaction is gossiped to teammates.
4. The miner periodically creates a candidate block from mempool transactions.
5. A valid Proof-of-Work solution is found.
6. The block is appended to the local chain.
7. The block is broadcast to teammates.
8. Peers validate and apply the block.
9. In case of competing chains, the longest valid chain is selected.

## Design Decisions

### Separate Registration Overlay

The registration protocol was isolated into a dedicated IPv8 overlay. This separates server interaction from blockchain functionality and simplifies the blockchain community implementation.

### Longest-Chain Consensus

Forks are resolved using the longest valid chain rule. When a longer valid chain is received, the node switches to that chain.

### Periodic Mining

Mining runs continuously in a background task and periodically attempts to create new blocks using transactions currently present in the mempool.

### In-Memory Transaction Index

Nodes maintain a collection of known transactions to support transaction lookup and block reconstruction when processing received blocks.

## Validation and Testing

The following functionality was tested during development:

* Peer registration
* Peer discovery
* Transaction propagation
* Mempool behavior
* Block mining
* Block propagation
* Chain synchronization
* Fork resolution
* Server interaction
* End-to-end blockchain operation across multiple nodes

Additional automated tests are provided in the `tests/` directory.

## Known Limitations

* Blockchain state is not persisted to disk.
* Restarting a node resets local blockchain state.
* The transaction cache is not garbage collected and may continue growing during very long executions.
* Mining difficulty is fixed and does not adjust dynamically.

## Additional Documentation

See:

* `docs/CONTRIBUTIONS.md`
* `docs/DEVELOPMENT_PROCESS.md`
