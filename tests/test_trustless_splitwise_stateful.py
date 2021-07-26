import pytest
import brownie
import random
from brownie.test import strategy
from hypothesis.stateful import rule, precondition

CONTRACT_DURATION = 100
MAX_MEMBERS = 20

class TrustlessSplitwiseStateMachine:
  def __init__(self, TrustlessSplitwise, accounts, chain):
    self.members = [accounts[0]]
    self.accounts = accounts
    self.chain = chain
    self.done = False
    self.time = 0
    self.contract = TrustlessSplitwise.deploy(CONTRACT_DURATION, {'from': accounts[0]})
    
  @precondition(lambda self: len(self.members) < MAX_MEMBERS and not self.done)
  def rule_add_member(self):
    # Only try to add accounts that are missing
    excluded_accounts = [x for x in self.accounts if x not in self.members]
    if excluded_accounts == []:
      member = self.accounts.add()
    else:
      member = random.sample(excluded_accounts)
      
    num_members = self.contract.numMembers()
    
    self.members.append(member)
    self.contract.addMember(member, {'from': self.accounts[0]})
    
    assert self.contract.members(member)
    assert self.contract.numMembers() == num_members + 1
    assert self.contract.balances(member) == 0
      
  @precondition(lambda self: not self.done)
  @rule(time=strategy('uint8', max_value=CONTRACT_DURATION // 10))
  def rule_advance_chain(self, time):
    self.chain.sleep(time)
    self.chain.mine()
    self.time += time
    
  @precondition(lambda self: not self.done)
  def rule_deposit(self):
    # randomly get some number to deposit from a member
    member = random.sample(self.members)
    initial_acc_balance = member.balance()
    initial_contract_balance = self.contract.balances(member)
    amount = random.randint(0, member.balance() // 4)
    self.contract.deposit({'from': member, 'amount': amount})
    
    assert self.contract.balances(member) == initial_contract_balance + amount
    assert member.balance() == initial_acc_balance - amount
    
  @precondition(lambda self: not self.done)
  def rule_transfer(self):
    [member_from, member_to] = random.sample(self.members, 2)
    initial_from_balance = self.contract.balances(member_from)
    initial_to_balance = self.contract.balances(member_to)
    amount = random.randint(0, initial_to_balance)
    
    self.contract.transact(member_to, amount, {'from': member_from})
    
    assert self.contract.balances(member_from) == initial_from_balance - amount
    assert self.contract.balances(member_to) == initial_to_balance + amount
    
  @precondition(lambda self: not self.done)
  def rule_withdraw(self):
    member = random.sample(self.members)
    initial_acc_balance = member.balance()
    initial_con_balance = self.contract.balances(member)
    amount = random.randint(0, initial_con_balance)
    
    self.contract.withdraw(amount, {'from': member})
    
    assert member.balance() == initial_acc_balance + amount
    assert self.contract.balance() == initial_con_balance - amount
    
    
  @precondition(lambda self: not self.done and self.time > CONTRACT_DURATION)
  def rule_settle_up(self):
    self.contract.settleUp()
    self.done = self.contract.done()
    
    for member in self.members:
      assert member.balance() == 10000
  
  def invariant(self):
    assert self.contract.numMembers() <= MAX_MEMBERS
    
    for member in self.members:
      assert self.contract.balances(member) >= 0
      
    if self.done:
      assert self.contract.numSettled == len(self.members)
    
def test_state_machine(TrustlessSplitwise, accounts, chain, state_machine):
  state_machine(TrustlessSplitwiseStateMachine, TrustlessSplitwise, accounts, chain)