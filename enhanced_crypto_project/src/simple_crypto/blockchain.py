# src/simple_crypto/blockchain.py

import hashlib
import json
from time import time
import requests # For consensus
from urllib.parse import urlparse

# Import Block class and utility functions
from.block import Block
from.util import verify_signature, create_signable_transaction_data

# --- Difficulty Adjustment Parameters ---
TARGET_BLOCK_TIME = 15 # Target seconds between blocks (adjust for testing)
RECALCULATION_INTERVAL = 5 # Adjust difficulty every 5 blocks (adjust for testing)
# Initial target: corresponds to a relatively low difficulty (e.g., requires few leading zeros)
# A higher target value means lower difficulty. Max target means easiest.
INITIAL_TARGET = 0x000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
MAX_TARGET = 0x000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff # Max possible target
BOUND_DIVISOR = 4 # Limits adjustment factor (e.g., 4 means max 4x or 1/4x change)

class Blockchain:
    """
    Manages the blockchain, transactions, nodes, consensus, and dynamic difficulty.
    """
    def __init__(self, hosting_node_public_key):
        self.unconfirmed_transactions = # Transactions waiting to be mined
        self.chain = # The list of blocks
        self.nodes = set() # Set to store network locations (e.g., '127.0.0.1:5001') of peer nodes
        self.node_id = hosting_node_public_key # Use node's public key as its identifier

        # --- Dynamic Difficulty Attributes ---
        self.current_target = INITIAL_TARGET
        self.target_block_time = TARGET_BLOCK_TIME
        self.recalculation_interval = RECALCULATION_INTERVAL

        # Create the genesis block
        self.create_genesis_block()

    def create_genesis_block(self):
        """ Creates the first block (Genesis Block). """
        genesis_block = Block(index=0,
                              transactions=,
                              timestamp=time(),
                              previous_hash="0",
                              proof=1, # Arbitrary proof for genesis
                              target=self.current_target) # Use initial target
        self.chain.append(genesis_block.to_dict()) # Store block as dict
        print("Genesis Block created.")

    @property
    def last_block(self):
        """ Returns the most recent block dictionary in the chain. """
        return self.chain[-1]

    def add_node(self, address):
        """
        Adds a new node to the list of nodes.

        Args:
            address (str): Address of node. Eg. 'http://192.168.0.5:5000'
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
            print(f"Node added: {parsed_url.netloc}")
        elif parsed_url.path:
            # Accepts format like '127.0.0.1:5001'
            self.nodes.add(parsed_url.path)
            print(f"Node added: {parsed_url.path}")
        else:
            raise ValueError('Invalid URL')

    def add_new_transaction(self, transaction):
        """
        Adds a new transaction to the list of unconfirmed transactions after verification.

        Args:
            transaction (dict): The transaction dictionary containing sender_public_key,
                                recipient, amount, timestamp, and signature.

        Returns:
            bool: True if transaction is valid and added, False otherwise.
        """
        required_fields = ['sender_public_key', 'recipient', 'amount', 'timestamp', 'signature']
        if not all(field in transaction for field in required_fields):
            print("Error: Transaction missing required fields.")
            return False

        # Recreate the data that was signed (must match signing structure)
        transaction_data_to_verify = create_signable_transaction_data(
            transaction['sender_public_key'],
            transaction['recipient'],
            transaction['amount'],
            transaction['timestamp']
        )

        # Verify the signature
        if verify_signature(transaction['sender_public_key'], transaction['signature'], transaction_data_to_verify):
            self.unconfirmed_transactions.append(transaction)
            print("Transaction added to pool.")
            return True
        else:
            print("Error: Invalid transaction signature. Transaction rejected.")
            return False

    def add_block(self, block_dict):
        """
        Adds a mined block dictionary to the chain after basic validation.
        Assumes PoW and transaction signatures were validated before calling this.

        Args:
            block_dict (dict): The dictionary representation of the block.

        Returns:
            bool: True if block added, False otherwise.
        """
        previous_hash = self.hash(self.last_block)

        # Check if the previous_hash matches
        if previous_hash!= block_dict['previous_hash']:
            print("Error: Previous hash mismatch.")
            return False

        # Basic check: Is the proof valid according to the block's target?
        # (More robust check would re-run valid_proof)
        if not self.is_valid_block_proof(block_dict):
             print("Error: Block proof does not meet target.")
             return False

        # Optional: Re-verify all transactions within the block here for extra security

        self.chain.append(block_dict)
        print(f"Block #{block_dict['index']} added to the chain.")
        return True

    def adjust_difficulty(self):
        """
        Adjusts the mining target based on the time taken for the last interval.
        Called before mining a new block if the interval is met.
        """
        if len(self.chain) < self.recalculation_interval:
            # Not enough blocks yet for first adjustment, or genesis block edge case
            return

        # Ensure we don't go out of bounds, especially after genesis
        if len(self.chain) == self.recalculation_interval:
             # Use genesis block as the start of the first interval
             first_block_in_interval = self.chain
        elif len(self.chain) > self.recalculation_interval:
             first_block_in_interval_index = len(self.chain) - self.recalculation_interval
             # Check index validity
             if first_block_in_interval_index < 0:
                 print("Warning: Difficulty adjustment index calculation error.")
                 return # Avoid index error
             first_block_in_interval = self.chain[first_block_in_interval_index]
        else:
             # Should not happen if initial check passed, but safety first
             return


        last_block_in_interval = self.last_block # The block just before the one being created now

        actual_time = last_block_in_interval['timestamp'] - first_block_in_interval['timestamp']
        expected_time = self.recalculation_interval * self.target_block_time

        # Prevent division by zero if actual_time is somehow zero
        if expected_time == 0:
            print("Warning: Expected time is zero, skipping difficulty adjustment.")
            return
        if actual_time <= 0: # Ensure actual_time is positive
             print(f"Warning: Non-positive actual_time ({actual_time}), using expected_time for factor.")
             actual_time = expected_time # Avoid extreme adjustments or errors


        # Apply bounds (e.g., limit adjustment to factor of 4)
        adjustment_factor = actual_time / expected_time
        adjustment_factor = max(1 / BOUND_DIVISOR, min(adjustment_factor, BOUND_DIVISOR))

        # Calculate new target: Difficulty is inverse to target.
        # Faster blocks (actual < expected) -> factor < 1 -> lower target -> higher difficulty
        # Slower blocks (actual > expected) -> factor > 1 -> higher target -> lower difficulty
        new_target = int(self.current_target * adjustment_factor)

        # Ensure target doesn't exceed maximum allowed value (minimum difficulty)
        new_target = min(new_target, MAX_TARGET)
        # Ensure target doesn't become zero or negative (maximum difficulty)
        new_target = max(new_target, 1) # Target must be at least 1

        if new_target!= self.current_target:
            print(f"Adjusting difficulty: Actual time={actual_time:.2f}s, Expected={expected_time}s, Factor={adjustment_factor:.4f}")
            print(f"Old Target: {hex(self.current_target)}, New Target: {hex(new_target)}")
            self.current_target = new_target
        else:
            print("Difficulty target remains unchanged.")


    def proof_of_work(self, last_block_dict):
        """
        Simple Proof-of-Work algorithm:
        - Find a number 'proof' such that hash(block_header_data_including_proof) < current_target.
        - Difficulty is controlled by self.current_target.

        Args:
            last_block_dict (dict): The dictionary of the last block.

        Returns:
            int: The valid proof/nonce.
        """
        proof = 0
        start_time = time()
        while True:
            # Create a temporary header structure for hashing attempt
            # This structure must match what compute_hash in Block class expects,
            # but with the candidate proof.
            header_data_for_hash = {
                'index': last_block_dict['index'] + 1,
                'timestamp': time(), # Use current time for attempt
                'previous_hash': self.hash(last_block_dict),
                'proof': proof,
                'target': self.current_target
                # Include transaction hash/root here in a real implementation
            }
            header_string = json.dumps(header_data_for_hash, sort_keys=True).encode('utf-8')
            guess_hash = hashlib.sha256(header_string).hexdigest()

            # Check if hash meets the target
            if int(guess_hash, 16) < self.current_target:
                end_time = time()
                print(f"Proof found: {proof} in {end_time - start_time:.2f}s (Hash: {guess_hash})")
                return proof # Found a valid proof

            proof += 1
            # Optional: Add a print statement for long mining processes
            # if proof % 100000 == 0:
            #     print(f"Mining attempt: {proof}, Hash: {guess_hash}")


    def is_valid_block_proof(self, block_dict):
         """ Checks if the block's hash meets its own stored target. """
         # Recompute hash based on block's stored data (excluding its own hash field)
         header_data_for_hash = {
            'index': block_dict['index'],
            'timestamp': block_dict['timestamp'],
            'previous_hash': block_dict['previous_hash'],
            'proof': block_dict['proof'],
            'target': block_dict['target']
            # Include transaction hash/root here in a real implementation
         }
         header_string = json.dumps(header_data_for_hash, sort_keys=True).encode('utf-8')
         recomputed_hash = hashlib.sha256(header_string).hexdigest()

         # Check if recomputed hash matches stored hash AND meets target
         # Note: Stored hash check is implicit if we trust compute_hash,
         # but explicit check is safer. Here we focus on target.
         return int(recomputed_hash, 16) < block_dict['target']


    @staticmethod
    def hash(block_dict):
        """
        Creates a SHA-256 hash of a Block dictionary (specifically its header components).
        Ensures dictionary is ordered for consistent hashes.

        Args:
            block_dict (dict): Block dictionary.

        Returns:
            str: The hexadecimal hash string.
        """
        # Hash the relevant header fields, not the entire block dict directly
        # to avoid issues if transactions change representation slightly.
        # Match the fields used in Block.compute_hash's header_data.
        header_data = {
            'index': block_dict['index'],
            'timestamp': block_dict['timestamp'],
            'previous_hash': block_dict['previous_hash'],
            'proof': block_dict['proof'],
            'target': block_dict['target']
            # Include transaction hash/root here in a real implementation
        }
        block_string = json.dumps(header_data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(block_string).hexdigest()


    def valid_chain(self, chain_list):
        """
        Determine if a given blockchain list (of dictionaries) is valid.

        Args:
            chain_list (list): A list of block dictionaries.

        Returns:
            bool: True if valid, False if not.
        """
        if not chain_list:
            return False # Empty chain is not valid

        # Validate Genesis Block (basic check)
        genesis_block_dict = chain_list
        if genesis_block_dict.get('index')!= 0 or genesis_block_dict.get('previous_hash')!= "0":
             print("Genesis block validation failed.")
             return False
        # Check if genesis block hash meets its target
        if not self.is_valid_block_proof(genesis_block_dict):
             print("Genesis block proof validation failed.")
             return False


        # Validate the rest of the chain
        last_block_dict = genesis_block_dict
        current_index = 1
        while current_index < len(chain_list):
            block_dict = chain_list[current_index]

            # 1. Check previous hash link
            if block_dict.get('previous_hash')!= self.hash(last_block_dict):
                print(f"Chain validation failed: Previous hash mismatch at index {current_index}.")
                print(f"Expected: {self.hash(last_block_dict)}")
                print(f"Got: {block_dict.get('previous_hash')}")
                return False

            # 2. Check if the block's proof is valid for its target
            if not self.is_valid_block_proof(block_dict):
                print(f"Chain validation failed: Invalid proof/target at index {current_index}.")
                block_hash = self.hash(block_dict) # Calculate actual hash for comparison
                print(f"Block Hash: {block_hash} (int: {int(block_hash, 16)})")
                print(f"Block Target: {hex(block_dict.get('target', 0))} (int: {block_dict.get('target', 0)})")
                return False

            # 3. Optional: Verify all transactions within the block
            for tx in block_dict.get('transactions',):
                 # Skip mining reward transaction (sender '0')
                 if tx.get('sender_public_key') == '0':
                     continue

                 required = ['sender_public_key', 'recipient', 'amount', 'timestamp', 'signature']
                 if not all(k in tx for k in required):
                     print(f"Chain validation failed: Transaction missing fields in block {current_index}.")
                     return False

                 tx_data_to_verify = create_signable_transaction_data(
                     tx['sender_public_key'], tx['recipient'], tx['amount'], tx['timestamp']
                 )
                 if not verify_signature(tx['sender_public_key'], tx['signature'], tx_data_to_verify):
                     print(f"Chain validation failed: Invalid transaction signature in block {current_index}.")
                     return False

            last_block_dict = block_dict
            current_index += 1

        print("Chain validation successful.")
        return True

    def resolve_conflicts(self):
        """
        Consensus Algorithm: Replaces our chain with the longest valid chain
        in the network.

        Returns:
            bool: True if our chain was replaced, False if not.
        """
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain) # Current length of our chain

        print("Resolving conflicts...")
        # Grab and verify the chains from all other nodes in our network
        for node in neighbours:
            print(f"Checking chain from node: {node}")
            try:
                response = requests.get(f'http://{node}/chain', timeout=3) # Add timeout

                if response.status_code == 200:
                    length = response.json()['length']
                    chain_list = response.json()['chain'] # List of block dicts

                    # Check if the length is longer and the chain is valid
                    if length > max_length and self.valid_chain(chain_list):
                        print(f"Found longer valid chain from {node} (Length: {length})")
                        max_length = length
                        new_chain = chain_list
                    elif length <= max_length:
                         print(f"Chain from {node} is not longer (Length: {length}).")
                    else: # length > max_length but chain is invalid
                         print(f"Chain from {node} is longer but invalid.")

                else:
                     print(f"Node {node} returned status {response.status_code}")

            except requests.exceptions.RequestException as e:
                print(f"Could not connect to node {node}: {e}")
                continue # Skip this node if unreachable or error

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            # Crucially, update the current target based on the new chain's last block
            self.current_target = self.chain[-1].get('target', INITIAL_TARGET)
            print(f"Chain replaced with the longer valid chain. New length: {max_length}. Updated target to {hex(self.current_target)}")
            return True # Indicates chain was replaced

        print("Conflict resolution complete. Our chain remains authoritative.")
        return False # Indicates chain was not replaced