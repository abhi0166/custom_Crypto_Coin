# src/simple_crypto/network.py

from flask import Flask, request, jsonify
from uuid import uuid4
import requests

# Import Blockchain and Wallet (assuming they are instantiated in node_runner.py)
# We'll pass instances to the setup function

def setup_network_routes(app, blockchain_instance, wallet_instance):
    """ Configures Flask routes for the blockchain node. """

    node_identifier = wallet_instance.public_key_string # Use wallet's public key

    @app.route('/mine', methods=)
    def mine():
        """ Mines a new block and adds it to the chain. """
        # --- Check for transactions ---
        if not blockchain_instance.unconfirmed_transactions:
             # Optional: Mine empty blocks if desired, or return message
             # return jsonify({'message': "No transactions to mine"}), 200
             print("Mining an empty block (no transactions in pool).")


        # --- Adjust Difficulty ---
        # Difficulty is adjusted *before* PoW for the *next* block
        # based on the time taken for the *previous* interval.
        # The check and adjustment happen inside blockchain.new_block
        # but we need the PoW to use the *current* target.

        # --- Proof-of-Work ---
        last_block_dict = blockchain_instance.last_block
        proof = blockchain_instance.proof_of_work(last_block_dict)

        # --- Mining Reward ---
        # Sender "0" signifies a new coin mined.
        # Recipient is this node's identifier (public key).
        # Mining rewards don't need user signatures in this simple model.
        reward_transaction = {
            'sender_public_key': "0", # Special sender for reward
            'recipient': node_identifier,
            'amount': 1.0, # Example reward amount
            'timestamp': time(),
            'signature': "mining_reward" # Placeholder
        }
        # Add reward directly to the list for the new block
        current_block_transactions = blockchain_instance.unconfirmed_transactions + [reward_transaction]


        # --- Create New Block ---
        previous_hash = blockchain_instance.hash(last_block_dict)
        current_target = blockchain_instance.current_target # Get target used for PoW

        # Create the block instance (using Block class)
        new_block = Block(index=last_block_dict['index'] + 1,
                          transactions=current_block_transactions,
                          timestamp=time(),
                          previous_hash=previous_hash,
                          proof=proof,
                          target=current_target) # Store the target used

        # --- Add Block to Local Chain & Clear Pool ---
        block_added = blockchain_instance.add_block(new_block.to_dict())

        if not block_added:
             return jsonify({'message': "Error adding mined block locally"}), 500

        blockchain_instance.unconfirmed_transactions = # Clear pool after successful mining & adding

        # --- Broadcast New Block ---
        broadcast_block(new_block.to_dict(), blockchain_instance.nodes)

        response = {
            'message': "New Block Forged",
            **new_block.to_dict() # Include all block details
        }
        return jsonify(response), 200

    @app.route('/transactions/new', methods=)
    def new_transaction_api():
        """ Receives a new transaction from a client/user. """
        values = request.get_json()
        if not values:
            return 'Missing transaction data', 400

        required = ['sender_public_key', 'recipient', 'amount', 'timestamp', 'signature']
        if not all(k in values for k in required):
            return 'Missing values in transaction data', 400

        # Add transaction to the blockchain's pool (includes signature verification)
        success = blockchain_instance.add_new_transaction(values)

        if success:
            # Broadcast the valid transaction to peers
            broadcast_transaction(values, blockchain_instance.nodes)
            response = {'message': f'Transaction added to pool and broadcasted.'}
            return jsonify(response), 201
        else:
            response = {'message': 'Transaction failed verification and was rejected.'}
            return jsonify(response), 400 # Or 422 Unprocessable Entity

    @app.route('/transactions/receive', methods=)
    def receive_transaction():
        """ Receives a broadcasted transaction from a peer node. """
        values = request.get_json()
        if not values:
            return 'Missing received transaction data', 400

        required = ['sender_public_key', 'recipient', 'amount', 'timestamp', 'signature']
        if not all(k in values for k in required):
            return 'Missing values in received transaction data', 400

        # Add received transaction to the pool (includes signature verification)
        # We call add_new_transaction, but it won't re-broadcast
        # because this endpoint is only called by peers.
        success = blockchain_instance.add_new_transaction(values)

        if success:
            response = {'message': 'Transaction received and added to pool.'}
            return jsonify(response), 201
        else:
            # Don't broadcast rejection, just log or ignore
            print(f"Received invalid transaction from peer: {values.get('signature')[:10]}...")
            response = {'message': 'Received transaction failed verification.'}
            # Return 200 OK to peer, even if invalid, to avoid unnecessary retries? Or 400?
            # Let's return 400 to indicate failure to the sender peer.
            return jsonify(response), 400


    @app.route('/chain', methods=)
    def full_chain():
        """ Returns the node's full blockchain. """
        response = {
            'chain': blockchain_instance.chain,
            'length': len(blockchain_instance.chain),
        }
        return jsonify(response), 200

    @app.route('/nodes/register', methods=)
    def register_nodes():
        """ Registers new peer nodes with this node. """
        values = request.get_json()
        nodes_list = values.get('nodes')
        if nodes_list is None:
            return "Error: Please supply a valid list of nodes", 400

        added_nodes =
        failed_nodes =
        for node_address in nodes_list:
            try:
                blockchain_instance.add_node(node_address)
                added_nodes.append(node_address)
            except ValueError:
                 failed_nodes.append(node_address)


        response = {
            'message': 'New nodes have been added',
            'nodes_added': added_nodes,
            'nodes_failed': failed_nodes,
            'total_nodes': list(blockchain_instance.nodes),
        }
        return jsonify(response), 201

    @app.route('/nodes/resolve', methods=)
    def consensus():
        """ Runs the consensus algorithm to resolve conflicts. """
        replaced = blockchain_instance.resolve_conflicts()

        if replaced:
            response = {
                'message': 'Our chain was replaced by a longer valid chain.',
                'new_chain': blockchain_instance.chain
            }
        else:
            response = {
                'message': 'Our chain is authoritative.',
                'chain': blockchain_instance.chain
            }
        return jsonify(response), 200

    @app.route('/blocks/receive', methods=)
    def receive_block():
        """ Receives a broadcasted block from a peer node. """
        block_dict = request.get_json()
        if not block_dict:
            return 'Missing block data', 400

        print(f"Received block #{block_dict.get('index')} from peer.")

        # --- Basic Validation ---
        last_local_block = blockchain_instance.last_block

        # 1. Check if it's the next block
        if block_dict.get('index')!= last_local_block['index'] + 1:
            print("Received block has incorrect index.")
            # Potential fork or out-of-sync issue. Trigger consensus?
            # For now, just reject if not the immediate next block.
            # A more robust system might store orphaned blocks temporarily.
            return 'Received block has incorrect index', 400

        # 2. Check if previous hash matches our last block's hash
        if block_dict.get('previous_hash')!= blockchain_instance.hash(last_local_block):
            print("Received block does not chain to local chain head (previous hash mismatch).")
            return 'Received block does not chain to local chain head', 400

        # --- Full Validation (Proof and Transactions) ---
        # 3. Check if the block's proof is valid for its target
        if not blockchain_instance.is_valid_block_proof(block_dict):
             print("Received block proof validation failed.")
             return 'Received block proof is invalid', 400

        # 4. Verify all transactions within the received block
        for tx in block_dict.get('transactions',):
            # Skip mining reward transaction
            if tx.get('sender_public_key') == '0':
                continue

            required = ['sender_public_key', 'recipient', 'amount', 'timestamp', 'signature']
            if not all(k in tx for k in required):
                print(f"Received block contains transaction missing fields.")
                return 'Received block contains invalid transaction (missing fields)', 400

            tx_data_to_verify = create_signable_transaction_data(
                tx['sender_public_key'], tx['recipient'], tx['amount'], tx['timestamp']
            )
            if not verify_signature(tx['sender_public_key'], tx['signature'], tx_data_to_verify):
                print(f"Received block contains invalid transaction signature.")
                return 'Received block contains invalid transaction signature', 400

        # --- Add Valid Block ---
        # If all checks pass, add the block to our chain
        # We use add_block which does basic checks again, but that's ok.
        added = blockchain_instance.add_block(block_dict)

        if added:
            # Remove transactions included in the received block from our pool
            confirmed_tx_signatures = {tx.get('signature') for tx in block_dict.get('transactions',) if tx.get('signature')}
            blockchain_instance.unconfirmed_transactions = [
                tx for tx in blockchain_instance.unconfirmed_transactions
                if tx.get('signature') not in confirmed_tx_signatures
            ]
            print(f"Block #{block_dict['index']} received, validated, and added. Cleared confirmed transactions from pool.")
            response = {'message': 'Block received and added'}
            return jsonify(response), 201
        else:
            # Should not happen if validation above passed, but handle defensively
            print(f"Failed to add received block #{block_dict['index']} after validation.")
            return 'Error adding received block locally after validation', 500

# --- Helper Functions for Broadcasting ---

def broadcast_transaction(transaction, nodes):
    """ Sends a transaction to all registered peer nodes. """
    print(f"Broadcasting transaction {transaction.get('signature')[:10]}... to {len(nodes)} nodes.")
    for node in nodes:
        try:
            requests.post(f'http://{node}/transactions/receive', json=transaction, timeout=1)
        except requests.exceptions.RequestException as e:
            print(f"Error broadcasting transaction to {node}: {e}")

def broadcast_block(block_dict, nodes):
    """ Sends a newly mined block to all registered peer nodes. """
    print(f"Broadcasting block #{block_dict.get('index')} to {len(nodes)} nodes.")
    for node in nodes:
        try:
            requests.post(f'http://{node}/blocks/receive', json=block_dict, timeout=2) # Longer timeout for blocks
        except requests.exceptions.RequestException as e:
            print(f"Error broadcasting block to {node}: {e}")