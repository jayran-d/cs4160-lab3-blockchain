from community import BlockchainCommunity
from payloads import ChainHeightResponsePayload
from ipv8.lazy_community import lazy_wrapper
from ipv8.peer import Peer


class BotBlockchainCommunity(BlockchainCommunity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)