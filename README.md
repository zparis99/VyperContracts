# VyperContracts
Repo to store various contracts while learning how to work with Vyper.

Steps to be completed:
- [x] Write a basic contract to test (TrustlessSplitwise.vy)
- [x] Write a suite of basic tests. (test_trustless_splitwise.vy)
- [x] Write a suite of tests that use [property based testing](https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-property.html). (test_trustless_splitwise_property.vy)
- [x] Write a suite of tests that use [stateful testing](https://eth-brownie.readthedocs.io/en/stable/tests-hypothesis-stateful.html). (test_trustless_splitwise_stateful.vy)

To compile the contract:

```
brownie compile
```

To run the tests;

```
brownie test
```
