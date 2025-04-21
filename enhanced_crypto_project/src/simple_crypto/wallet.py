# src/simple_crypto/wallet.py

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
import json
import time
import binascii # For converting signature bytes to hex

# Import utility function
from.util import create_signable_transaction_data

class Wallet:
    """
    Manages ECDSA key pairs (secp256k1), signs transactions,
    and conceptually stores/loads keys.
    """
    def __init__(self, node_id=None):
        self.private_key = None
        self.public_key = None
        self.public_key_pem = None # Store PEM bytes
        self.node_id = node_id # Optional identifier for file naming

    def generate_keys(self):
        """ Generates a new EC private/public key pair (secp256k1). """
        self.private_key = ec.generate_private_key(ec.SECP256k1())
        self.public_key = self.private_key.public_key()
        self.public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        print("New key pair generated.")

    def sign_transaction_data(self, recipient, amount):
        """
        Creates transaction data, signs it using the private key,
        and returns the full transaction dictionary including the signature.
        """
        if not self.private_key or not self.public_key_pem:
            print("Error: Wallet keys not generated or loaded.")
            return None

        timestamp = time.time()
        # Create the data structure that will be signed
        transaction_data_to_sign = create_signable_transaction_data(
            self.public_key_string, # Use the PEM string representation
            recipient,
            amount,
            timestamp
        )

        # Serialize and hash
        message_bytes = json.dumps(transaction_data_to_sign, sort_keys=True).encode('utf-8')
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(message_bytes)
        digest = hasher.finalize()

        # Sign the hash
        signature_bytes = self.private_key.sign(
            digest,
            ec.ECDSA(utils.Prehashed(hashes.SHA256()))
        )

        # Return the full transaction structure including signature (hex encoded)
        full_transaction = {
            **transaction_data_to_sign, # Unpack the signed data
            'signature': binascii.hexlify(signature_bytes).decode('utf-8') # Store signature as hex string
        }
        return full_transaction

    def save_keys(self):
        """ Saves keys to files (INSECURE - FOR DEMONSTRATION ONLY). """
        if not self.private_key or not self.public_key_pem:
            print("Error: No keys to save.")
            return False
        try:
            id_suffix = f"_{self.node_id}" if self.node_id else ""
            private_key_file = f'wallet{id_suffix}.key'
            public_key_file = f'wallet{id_suffix}.pub'

            # Save private key (unencrypted PEM)
            pem_private = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption() # WARNING: INSECURE
            )
            with open(private_key_file, 'wb') as f:
                f.write(pem_private)

            # Save public key (PEM)
            with open(public_key_file, 'wb') as f:
                f.write(self.public_key_pem)
            print(f"Keys saved to {private_key_file} and {public_key_file} (INSECURELY)")
            return True
        except IOError as e:
            print(f"Error saving keys: {e}")
            return False

    def load_keys(self):
        """ Loads keys from files (INSECURE - FOR DEMONSTRATION ONLY). """
        try:
            id_suffix = f"_{self.node_id}" if self.node_id else ""
            private_key_file = f'wallet{id_suffix}.key'
            public_key_file = f'wallet{id_suffix}.pub'

            with open(private_key_file, 'rb') as f:
                pem_private = f.read()
            self.private_key = serialization.load_pem_private_key(pem_private, password=None)

            with open(public_key_file, 'rb') as f:
                self.public_key_pem = f.read()
            self.public_key = serialization.load_pem_public_key(self.public_key_pem)

            print(f"Keys loaded from {private_key_file} and {public_key_file}")
            return True
        except FileNotFoundError:
            # Don't print error if files just don't exist yet
            # print("Info: Key files not found. Generate new keys if needed.")
            return False
        except Exception as e:
            print(f"Error loading keys: {e}")
            return False

    @property
    def public_key_string(self):
        """ Returns the public key as a PEM string. """
        return self.public_key_pem.decode('utf-8') if self.public_key_pem else None

    def get_balance(self, blockchain_instance):
        """
        Calculates the balance by scanning the blockchain's confirmed blocks
        and optionally the pending transactions.
        """
        if not self.public_key_pem:
            print("Error: Wallet public key not available.")
            return 0.0

        my_public_key_str = self.public_key_string
        balance = 0.0
        tx_sender = None
        tx_recipient = None
        tx_amount = None

        # Iterate through confirmed blocks
        for block_data in blockchain_instance.chain: # Assuming chain stores block dicts
            for tx in block_data.get('transactions',):
                # Ensure transaction has expected structure before accessing keys
                if isinstance(tx, dict):
                    tx_recipient = tx.get('recipient')
                    tx_sender = tx.get('sender_public_key') # Use public key as sender ID
                    tx_amount = tx.get('amount')

                    # Ensure amount is numeric before arithmetic
                    if not isinstance(tx_amount, (int, float)):
                        continue # Skip malformed transaction amount

                    if tx_recipient == my_public_key_str:
                        balance += tx_amount
                    if tx_sender == my_public_key_str:
                        balance -= tx_amount
                        # Note: Transaction fees are not explicitly handled here

        # Optional: Consider unconfirmed transactions in the pool
        for tx in blockchain_instance.unconfirmed_transactions:
             if isinstance(tx, dict):
                tx_recipient = tx.get('recipient')
                tx_sender = tx.get('sender_public_key')
                tx_amount = tx.get('amount')

                if not isinstance(tx_amount, (int, float)):
                    continue

                if tx_recipient == my_public_key_str:
                    balance += tx_amount # Add unconfirmed incoming (potential double count if mined)
                if tx_sender == my_public_key_str:
                    balance -= tx_amount # Subtract unconfirmed outgoing

        return balance