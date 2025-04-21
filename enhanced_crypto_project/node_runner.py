# node_runner.py

from flask import Flask, jsonify, request
from argparse import ArgumentParser

# Import local modules
from src.simple_crypto.wallet import Wallet
from src.simple_crypto.blockchain import Blockchain
from src.simple_crypto.network import setup_network_routes

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-i', '--id', default=None, type=str, help='unique id for this node (used for wallet file naming)')
    args = parser.parse_args()
    port = args.port
    node_id_suffix = args.id

    # --- Initialize Wallet ---
    # Uses node_id_suffix for potentially unique wallet files per node instance
    wallet = Wallet(node_id=node_id_suffix)
    # Try loading keys first, generate if they don't exist
    if not wallet.load_keys():
        wallet.generate_keys()
        wallet.save_keys() # Save the newly generated keys (insecurely)

    if not wallet.public_key_string:
        print("CRITICAL ERROR: Wallet could not be initialized.")
        exit()

    # --- Initialize Blockchain ---
    # Pass the wallet's public key to identify the node
    blockchain = Blockchain(wallet.public_key_string)

    # --- Initialize Flask App ---
    app = Flask(__name__)

    # --- Setup API Routes ---
    # Pass the app, blockchain instance, and wallet instance to the setup function
    setup_network_routes(app, blockchain, wallet)

    # --- Add a simple root endpoint for basic check ---
    @app.route('/', methods=)
    def get_node_ui():
        # In a real app, this might serve a simple HTML interface
        return f"Node Active. Wallet Public Key: {wallet.public_key_string}<br>Known Peers: {list(blockchain.nodes)}"

    # --- Add endpoint to view wallet balance ---
    @app.route('/wallet/balance', methods=)
    def get_wallet_balance():
         balance = wallet.get_balance(blockchain)
         return jsonify({'public_key': wallet.public_key_string, 'balance': balance}), 200

    # --- Run the Flask Server ---
    print(f"Starting node on port {port}...")
    # Use host='0.0.0.0' to make it accessible on the network
    app.run(host='0.0.0.0', port=port, debug=True) # debug=True is helpful for development