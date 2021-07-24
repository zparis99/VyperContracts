# @version ^0.2.0

# A contract to simulate some kind of Splitwise like functionality.
# Users can store money in an account then perform many transactions
# amongst the included group, then cash out when the original creator
# calls settleUp(). Always holds at least the balance required for 
# everyone to cash out so the system is trustless as anyone is guarenteed
# to be able to withdraw their money at any time

# Max number of users in a group
MAX_USERS: constant(int128) = 20
# Max number of people to settle up in one transaction
MAX_SETTLE: constant(int128) = 20

event Transaction:
  sender: address
  receiver: address
  amount: uint256

event Deposit:
  account: address
  amount: uint256

event Withdrawal:
  account: address
  amount: uint256

# Parameters
# address which created the contract. Can settle up the contract after
# the group expires
creator: public(address)
expirationDate: public(uint256)

# State
# Store whether an account is a member of the group
members: public(HashMap[address, bool])
# Store the total number of members. Capped at MAX_USERS
numMembers: public(int128)
# Store the list of members
memberList: public(HashMap[int128, address])
# Store the balance of each member
balances: public(HashMap[address, uint256])
# Tracks the number of people who have settled up so far. Allows for batching
numSettled: public(int128)

# Tracks if contract is done
done: public(bool)

# Create a contract to track group transactions
@external
def __init__(_duration: uint256):
  self.creator = msg.sender
  self.expirationDate = block.timestamp + _duration

  self.members[self.creator] = True
  self.memberList[self.numMembers] = self.creator
  self.numMembers += 1

# Add a member to the group
@external
def addMember(account: address):
  assert not self.done, "contract is terminated"
  assert self.numMembers < MAX_USERS, "too many users"
  assert not self.members[account], "user already added"

  self.members[account] = True
  self.memberList[self.numMembers] = account
  self.numMembers += 1

# Return wealth of an account 
@internal
@view
def _wealth(account: address) -> uint256:
  return self.balances[account]

# External wrapper to check balance of an account
@external
@view
def wealth(account: address) -> uint256:
  assert not self.done, "contract is terminated"
  assert self.members[account], "account is not member in the group"
  return self._wealth(account)

# Deposit some eth in the contract for use in the group
@external
@payable
def deposit():
  assert not self.done, "contract is terminated"
  assert self.members[msg.sender], "depositor is not a member in the group" 
  self.balances[msg.sender] += msg.value
  log Deposit(msg.sender, msg.value)

# Withdraw amount of eth from the contract
@external
def withdraw(amount: uint256):
  assert not self.done, "contract is terminated"
  assert self.members[msg.sender], "withdrawer is not a member in the group"
  assert self._wealth(msg.sender) > amount, "insufficient balance"

  self.balances[msg.sender] -= amount

  send(msg.sender, amount)
  
  log Withdrawal(msg.sender, amount)

# Send amount eth to recipient. Recipient must be a member
@external
def transact(receiver: address, amount: uint256):
  assert not self.done, "contract is terminated"
  assert self.members[receiver], "reciever is not a member in the group"
  assert self.members[msg.sender], "sender is not a member in the group"
  assert self._wealth(msg.sender) >= amount, "insufficient funds"
  
  self.balances[msg.sender] -= amount
  self.balances[receiver] += amount
  log Transaction(msg.sender, receiver, amount)

# settle up accounts after expirationDate has passed. Will send everyone their
# balance and terminate the contract. Can only be executed by the creator.
# May have to be executed several times to complete.
@external
def settleUp():
  assert not self.done, "contract is terminated"
  assert block.timestamp >= self.expirationDate
  assert msg.sender == self.creator

  ind: int128 = self.numSettled
  
  # Send money back to members and empty their info
  for i in range(ind, ind + MAX_SETTLE):
    if i >= self.numMembers:
      self.numSettled = self.numMembers

    account: address = self.memberList[i]
    wealth: uint256 = self._wealth(account)

    self.balances[account] = 0
    self.members[account] = False
    self.memberList[i] = ZERO_ADDRESS

    send(account, wealth)
  
