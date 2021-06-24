import hashlib
import json 
import requests

from flask import Flask, jsonify, request
from urllib.parse import urlparse

from time import time
from uuid import uuid4


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # Genesis block
        self.new_block(previous_hash=1, proof=100)

    def valid_chain(self, chain):
        '''
        Determine if given blockchain is valid
        chain: (list) blockchain
        returns (bool) True or False
        '''
    
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n----\n')
            
            # Check that hash is correct in block
            if block['previous_hash'] != self.hash(last_block):
                return False
            
            # Check that proof is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            
            last_block = block
            current_index += 1
        
        return True
    
    def resolve_conflicts(self):
        '''
        Consensus algorithm: resolves conflicts by replacing chain w/ longest in network
        returns (bool) True if chain replaced, False otherwise
        '''

        neighbors = self.nodes
        new_chain = None

        # We're looking for chains longer than ours...
        max_length = len(self.chain)

        # Grab/verify the chains from all nodes in network
        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if length is longer and chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        
        # Replace chain if there is discovery of longer, valid chain
        if new_chain:
            self.chain = new_chain
            return True
        
        return False

    def register_node(self, address):
        '''
        Add a new node to list of nodes
        address: (str) -> address of node, e.g. 'http://134.0.0.1:5000'
        returns None
        '''

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

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

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400
    
    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced.',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is up-to-date (authoritative)',
            'chain': blockchain.chain
        }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
