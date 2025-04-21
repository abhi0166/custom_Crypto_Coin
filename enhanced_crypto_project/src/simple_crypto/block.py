# src/simple_crypto/block.py

import hashlib
import json
from time import time

class Block:
    """
    Represents a single block in the blockchain.

    Attributes:
        index (int): The position of the block in the chain.
        transactions (list): List of transactions included in the block.
        timestamp (float): Time of block creation.
        previous_hash (str): Hash of the preceding block.
        proof (int): The Proof-of-Work nonce/proof value for this block.
        target (int): The target value the block hash must be less than (for dynamic difficulty).
        hash (str): The calculated hash of this block.
    """
    def __init__(self, index, transactions, timestamp, previous_hash, proof, target):
        self.index = index
        self.transactions = transactions # Now contains signed transaction dicts
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.proof = proof # Renamed nonce to proof for clarity
        self.target = target # Store the target used for mining this block
        self.hash = self.compute_hash()

    def compute_hash(self):
        """
        Computes the SHA-256 hash of the block header components.
        Note: Transactions are typically hashed into a Merkle Root,
              but for simplicity, we hash key header info.
              A more robust implementation would include a transaction hash/root.
        """
        # Simplified header string for hashing
        header_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'proof': self.proof,
            'target': self.target
            # In a real chain, include a hash of transactions (Merkle Root) here
        }
        block_string = json.dumps(header_data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(block_string).hexdigest()

    def to_dict(self):
        """ Returns the block data as a dictionary. """
        return {
            'index': self.index,
            'transactions': self.transactions, # Transactions are already dicts
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'proof': self.proof,
            'target': self.target,
            'hash': self.hash
        }