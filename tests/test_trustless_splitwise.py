import pytest
import brownie

# These tests could probably be improved by either:
# Property Based Testing: https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-property.html#hypothesis
# Stateful Testing: https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-stateful.html
# But I need to read more first to see how these work. Ill try these on the next contract I write which
# will just be typical splitwise where people don't need to store any money in the contract and can settle
# up in the end.
# These could be further built out to actually cover all the useful test cases but I've been using this as
# a learning tool which I think I have now learned so I'm going to continue on to another part of the project
# although this could be further developed.

# Questions still to solve:
# 1. How do I access private variables in the contract? i.e. if I made balances private can I still
# track its value in tests?

CONTRACT_DURATION = 100

# fixtures are cool, 
@pytest.fixture(scope="module", autouse=True)
def trustless_splitwise_contract(TrustlessSplitwise, accounts):
  yield TrustlessSplitwise.deploy(CONTRACT_DURATION, {'from': accounts[0]})

# fn_isolation makes it so that the state of the chain is reset
# between each test
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
  pass

def fast_forward_chain(chain):
  # Fast forward in time then mine a block so the time for the contract has ended
  chain.sleep(CONTRACT_DURATION + 1)
  chain.mine()
  
def assert_withdrawal_event(event, account, amount):
  # Assert a withdrawal event matches the given account and amount
  assert event['account'] == account
  assert event['amount'] == amount

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
  deposit_amt = 1
  
  initial_balance = accounts[0].balance()
  # Deposit 1 wei, store the transaction event in tx so that we can check on events later
  tx = trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt})
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt
  
  assert accounts[0].balance() == initial_balance - deposit_amt
  
  # Check to make sure the correct deposit event was logged
  assert tx.events[0]['account'] == accounts[0]
  assert tx.events[0]['amount'] == deposit_amt
  
def test_deposit_max(trustless_splitwise_contract, accounts):
  initial_balance = accounts[0].balance()
  deposit_amt = initial_balance
  
  # Deposit 1 wei, store the transaction event in tx so that we can check on events later
  tx = trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt})
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt
  
  assert accounts[0].balance() == initial_balance - deposit_amt
  
  # Check to make sure the correct deposit event was logged
  assert tx.events[0]['account'] == accounts[0]
  assert tx.events[0]['amount'] == deposit_amt
  
def test_deposit_not_member(trustless_splitwise_contract, accounts):
  # Try to write from an account that is not an added member
  with brownie.reverts('depositor is not a member in the group'):
    trustless_splitwise_contract.deposit({'from': accounts[1], 'amount': 1})
    
def test_withdraw_valid(trustless_splitwise_contract, accounts):
  # Deposit 100 wei then withdraw 50 wei
  deposit_amt = 100
  withdraw_amt = 50
  
  initial_balance = accounts[0].balance()
  
  trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt})
  
  assert accounts[0].balance() == initial_balance - deposit_amt
  
  tx = trustless_splitwise_contract.withdraw(withdraw_amt, {'from': accounts[0]})
  
  assert accounts[0].balance() == initial_balance - deposit_amt + withdraw_amt
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt - withdraw_amt
  assert_withdrawal_event(tx.events[0], accounts[0], withdraw_amt)
  
def test_withdraw_illegal(trustless_splitwise_contract, accounts):
  # try to withdraw with no money in the contract
  with brownie.reverts('insufficient balance'):
    trustless_splitwise_contract.withdraw(50, {'from': accounts[0]})
    
def test_transact_valid(trustless_splitwise_contract, accounts):
  deposit_amt = 100
  tx_amt = 50
  
  trustless_splitwise_contract.addMember(accounts[1])
  trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt})
  tx = trustless_splitwise_contract.transact(accounts[1], tx_amt, {'from': accounts[0]})
  
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt - tx_amt
  assert trustless_splitwise_contract.balances(accounts[1]) == tx_amt
  assert tx.events[0]['sender'] == accounts[0]
  assert tx.events[0]['receiver'] == accounts[1]
  assert tx.events[0]['amount'] == tx_amt
  
def test_settle_up_valid(trustless_splitwise_contract, accounts, chain):
  # Add members to the contract and have them deposit, then settle up to ensure
  # everyone receives their full balance at termination
  deposit_amt_0 = 50
  deposit_amt_1 = 100
  
  initial_balance_0 = accounts[0].balance()
  initial_balance_1 = accounts[1].balance()

  trustless_splitwise_contract.addMember(accounts[1])
  trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt_0})
  trustless_splitwise_contract.deposit({'from': accounts[1], 'amount': deposit_amt_1})
  
  assert accounts[0].balance() == initial_balance_0 - deposit_amt_0
  assert accounts[1].balance() == initial_balance_0 - deposit_amt_1
  
  fast_forward_chain(chain)
  
  tx = trustless_splitwise_contract.settleUp()
  
  assert accounts[0].balance() == initial_balance_0
  assert accounts[1].balance() == initial_balance_1
  assert_withdrawal_event(tx.events[0], accounts[0], deposit_amt_0)
  assert_withdrawal_event(tx.events[1], accounts[1], deposit_amt_1)
  
def test_contract_terminates(trustless_splitwise_contract, accounts, chain):
  # Make sure no actions can be run after settling up
  trustless_splitwise_contract.addMember(accounts[1])
  
  fast_forward_chain(chain)
  
  trustless_splitwise_contract.settleUp()
  
  with brownie.reverts('contract is terminated'):
    trustless_splitwise_contract.addMember(accounts[2])
  
  with brownie.reverts('contract is terminated'):
    trustless_splitwise_contract.deposit({'from': accounts[0], 'amount':  10})
    
  with brownie.reverts('contract is terminated'):
    trustless_splitwise_contract.withdraw(5, {'from': accounts[0]})
    
  with brownie.reverts('contract is terminated'):
    trustless_splitwise_contract.transact(accounts[1], 5, {'from': accounts[0]})
