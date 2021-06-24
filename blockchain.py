import hashlib
import json 

from flask import Flask, jsonify, request

from time import time
from uuid import uuid4

# TODO: GET/POST work... but new transaction POST doesn't update chain. Why? 

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # Genesis block
        self.new_block(previous_hash=1, proof=100)

    def proof_of_work(self, last_proof):
        '''
        Simple PoW algorithm:
            - Find new proof number where the hash contains 4 leading zeroes
            last_proof: (int)
            returns (int) 
        '''

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        
        return proof
    
    @staticmethod
    def valid_proof(last_proof, proof):
        '''
        Validates proof: Does (last, proof) contain 4 leading zeroes?
        last_proof: (int)
        proof: (int) current
        returns (bool) True or False
        '''

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'
    
    def new_block(self, proof, previous_hash=None):
        '''
        Creates new block in blockchain
        proof: (int) -> proof given by Proof of Work algorithm
        previous_hash (Optional): (str) -> hash of previous block
        returns (dict) new block
        '''
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset current list of transactions
        self.current_transactions = []
        self.chain.append(block)

        return block

    def new_transaction(self, sender, recipient, amount):
        '''
        Creates new transaction to go into next mined block
        sender: (str) -> address of sender
        recipient: (str) -> address of recipient
        amount: (int) -> amount
        returns (int) index of block that will hold transaction
        '''
    
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
    
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        '''
        Creates SHA-256 hash of block
        block: (dict) block 
        returns (str)
        '''
        
        # Make sure dictionary is ordered, else inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

# Create node
app = Flask(__name__)

# Generate unique address for node
node_identifier = str(uuid4()).replace('-', '') 

# Create blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # Run PoW algorithm to get next proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # User has to receive reward for solving proof
    # Sender = 0, signifying node has mined new coin
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )

    # Forge new block and add to chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'New block forged!',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check required fields are in POST data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    # Create new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to block {index}'}
    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
