import pytest
import brownie

# These tests could probably be improved by either:
# Property Based Testing: https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-property.html#hypothesis
# Stateful Testing: https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-stateful.html
# But I need to read more first to see how these work. Ill try these on the next contract I write which
# will just be typical splitwise where people don't need to store any money in the contract and can settle
# up in the end.

# Questions still to solve:
# 1. How do I access private variables in the contract? i.e. if I made balances private can I still
# track its value in tests?

# fixtures are cool, 
@pytest.fixture(scope="module", autouse=True)
def trustless_splitwise_contract(TrustlessSplitwise, accounts):
  yield TrustlessSplitwise.deploy(1, {'from': accounts[0]})
  
# fn_isolation makes it so that the state of the chain is reset
# between each test
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
  pass

def test_initial_state(trustless_splitwise_contract, accounts):
  assert trustless_splitwise_contract.numMembers() == 1
  # When using a getter function you need to pass the argument to index into
  # the object i.e. if a list pass a number, key of hashmap, etc
  # if you don't you get:
  # ValueError: memberList Sequence has incorrect length, expected 1 but got 0
  assert trustless_splitwise_contract.memberList(0) == accounts[0]
  assert trustless_splitwise_contract.members(accounts[0])
  assert trustless_splitwise_contract.creator() == accounts[0]
  
def test_add_member(trustless_splitwise_contract, accounts):
  trustless_splitwise_contract.addMember(accounts[1])
  assert trustless_splitwise_contract.numMembers() == 2
  assert trustless_splitwise_contract.memberList(1) == accounts[1]
  assert trustless_splitwise_contract.members(accounts[1])
  
def test_deposit_valid(trustless_splitwise_contract, accounts):
  initial_balance = accounts[0].balance()
  # Deposit 1 wei, store the transaction event in tx so that we can check on events later
  tx = trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': 1})
  assert trustless_splitwise_contract.balances(accounts[0]) == 1
  
  assert accounts[0].balance() == initial_balance - 1
  
  # Check to make sure the correct deposit event was logged
  assert tx.events[0]['account'] == accounts[0]
  assert tx.events[0]['amount'] == 1
  
def test_deposit_illegal(trustless_splitwise_contract, accounts):
  # Try to write from an account that is not an added member
  with brownie.reverts('depositor is not a member in the group'):
    trustless_splitwise_contract.deposit({'from': accounts[1], 'amount': 1})
    
def test_withdraw_valid(trustless_splitwise_contract, accounts):
  initial_balance = accounts[0].balance()
  # Deposit 100 wei then withdraw 50 wei
  trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': 100})
  
  assert accounts[0].balance() == initial_balance - 100
  
  tx = trustless_splitwise_contract.withdraw(50, {'from': accounts[0]})
  
  assert accounts[0].balance() == initial_balance - 50
  assert trustless_splitwise_contract.balances(accounts[0]) == 50
  assert tx.events[0]['account'] == accounts[0]
  assert tx.events[0]['amount'] == 50
  