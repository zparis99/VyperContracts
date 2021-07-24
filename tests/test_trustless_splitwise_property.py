import pytest

from brownie import accounts
from brownie.test import given, strategy
from hypothesis.strategies import composite

CONTRACT_DURATION = 100

@pytest.fixture(scope="module", autouse=True)
def trustless_splitwise_contract(TrustlessSplitwise):
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
  
def assert_transact_event(event, sender, receiver, amount):
  assert event['sender'] == sender
  assert event['receiver'] == receiver
  assert event['amount'] == amount
  
@composite
def deposit_and_lesser(draw, max_deposit=10000):
  # Generates 2 numbers. A deposit_amt and another of lesser value. Useful for
  # withdrawal/transaction tests
  deposit_amt = draw(strategy('uint256', max_value=max_deposit))
  lesser_amt = draw(strategy('uint256', max_value=deposit_amt))
  
  return (deposit_amt, lesser_amt)
  
@given(deposit_amt=strategy('uint256', max_value=10000))
def test_deposit_amount(trustless_splitwise_contract, deposit_amt):
  initial_balance = accounts[0].balance()
  
  tx = trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt})
  
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt
  
  assert accounts[0].balance() == initial_balance - deposit_amt
  
  # Check to make sure the correct deposit event was logged
  assert tx.events[0]['account'] == accounts[0]
  assert tx.events[0]['amount'] == deposit_amt
  
@given(deposit_and_lesser=deposit_and_lesser())
def test_withdraw_amount(trustless_splitwise_contract, deposit_and_lesser):
  (deposit_amt, withdraw_amt) = deposit_and_lesser
  initial_balance = accounts[0].balance()
  
  trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt})
  
  assert accounts[0].balance() == initial_balance - deposit_amt
  
  tx = trustless_splitwise_contract.withdraw(withdraw_amt, {'from': accounts[0]})
  
  assert accounts[0].balance() == initial_balance - deposit_amt + withdraw_amt
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt - withdraw_amt
  assert_withdrawal_event(tx.events[0], accounts[0], withdraw_amt)

@given(
  deposit_and_lesser_0=deposit_and_lesser(),
  deposit_and_lesser_1=deposit_and_lesser()
)
def test_transact_amount(trustless_splitwise_contract, deposit_and_lesser_0, deposit_and_lesser_1):
  trustless_splitwise_contract.addMember(accounts[1])
  
  initial_balance_0 = accounts[0].balance()
  initial_balance_1 = accounts[1].balance()
  
  (deposit_amt_0, transact_amt_0) = deposit_and_lesser_0
  (deposit_amt_1, transact_amt_1) = deposit_and_lesser_1
  
  trustless_splitwise_contract.deposit({'from': accounts[0], 'amount': deposit_amt_0})
  trustless_splitwise_contract.deposit({'from': accounts[1], 'amount': deposit_amt_1})
  
  assert accounts[0].balance() == initial_balance_0 - deposit_amt_0
  assert accounts[1].balance() == initial_balance_1 - deposit_amt_1
  
  tx0 = trustless_splitwise_contract.transact(accounts[1], transact_amt_0, {'from': accounts[0]})
  
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt_0 - transact_amt_0
  assert trustless_splitwise_contract.balances(accounts[1]) == deposit_amt_1 + transact_amt_0
  assert_transact_event(tx0.events[0], accounts[0], accounts[1], transact_amt_0)
  
  tx1 = trustless_splitwise_contract.transact(accounts[0], transact_amt_1, {'from': accounts[1]})
  assert trustless_splitwise_contract.balances(accounts[0]) == deposit_amt_0 - transact_amt_0 + transact_amt_1
  assert trustless_splitwise_contract.balances(accounts[1]) == deposit_amt_1 + transact_amt_0 - transact_amt_1
  assert_transact_event(tx1.events[0], accounts[1], accounts[0], transact_amt_1)
