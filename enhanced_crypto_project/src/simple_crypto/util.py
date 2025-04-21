# src/simple_crypto/util.py

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.exceptions import InvalidSignature
import json
import binascii # For converting hex signature back to bytes

def create_signable_transaction_data(sender_pub_key_pem_str, recipient, amount, timestamp):
    """
    Creates the ordered dictionary representation of transaction data used for signing.
    Crucially, this must match the data structure used during verification.

    Args:
        sender_pub_key_pem_str (str): Sender's public key in PEM format.
        recipient (str): Recipient's address (or public key PEM).
        amount (float): Transaction amount.
        timestamp (float): Transaction timestamp.

    Returns:
        dict: Ordered dictionary of transaction data.
    """
    return {
        'sender_public_key': sender_pub_key_pem_str,
        'recipient': recipient,
        'amount': amount,
        'timestamp': timestamp
    }

def verify_signature(sender_public_key_pem_str, signature_hex, transaction_data_to_verify):
    """
    Verifies an ECDSA signature against the transaction data using the sender's public key.

    Args:
        sender_public_key_pem_str (str): Sender's public key in PEM format.
        signature_hex (str): The signature as a hexadecimal string.
        transaction_data_to_verify (dict): The transaction data dictionary (must match signed data structure).

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    try:
        # Load public key from PEM string
        public_key_pem_bytes = sender_public_key_pem_str.encode('utf-8')
        public_key = serialization.load_pem_public_key(public_key_pem_bytes)

        # Convert hex signature back to bytes
        signature_bytes = binascii.unhexlify(signature_hex)

        # 1. Serialize consistently (must match signing process)
        message_bytes = json.dumps(transaction_data_to_verify, sort_keys=True).encode('utf-8')

        # 2. Hash the message (must match signing process)
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(message_bytes)
        digest = hasher.finalize()

        # 3. Verify the signature against the hash
        public_key.verify(
            signature_bytes,
            digest,
            ec.ECDSA(utils.Prehashed(hashes.SHA256())) # Use Prehashed
        )
        # print("Signature verified successfully.") # Debugging
        return True # Verification successful
    except InvalidSignature:
        print("Signature verification failed: InvalidSignature exception.")
        return False # Verification failed
    except ValueError as e:
        print(f"Signature verification failed: Error decoding hex signature or loading key - {e}")
        return False
    except Exception as e:
        print(f"Signature verification failed: An unexpected error occurred - {e}")
        return False # Other error during verification