# VALO
A slowly improving Python-based crypto-currency.

##Features
- [x] Currently VALO uses **Proof of Stake** with a premine. Proof of work is implemented
and tested as well.
- [ ] A transition to **eigentrust** or similar would move the stake from being money to
trust and reputation.
- [x] The balance system is based on **accounts** instead of UTXO's, allowing for
significantly smaller transaction sizes and therefore chain.
- [ ] Transactions need a **rate limit** of some sort (for example a fee).
- [ ] Transactions could be **compressed** by giving rewards for the usage of 5 byte
usernames instead of 32 byte public keys.
- [x] The **LWMA** difficulty algorithm makes sure that the chain won't be attacked using
hash attacks.
- [ ] The hashing algorithm used is the blake2b implementation from pynacl. Switching to
**blake3**, where possible, will improve hashing speeds a lot. 
- [x] A flexible database backend exists, currently written using **REDIS**.
- [ ] A transition to RocksDB or **QuestDB** would improve the query speeds and scalability
drastically
- [x] The **custom networking** stack is tailor-made for this application. This
allows for higher performance, even though the limitations of python apply.
- [ ] Currently the networking uses jsonpickle for dictionary objects. Writing **custom 
binary encodings** for the two datatypes will further improve the performance.
- [x] Everything is currently written in **Python**, allowing for easy contribution.
- [ ] A **rewrite into V** is targeted to take place once low-level networking and
cryptography libraries exist.
- [ ] The ultimate goal is distributing jobs across a **trustless kubernetes cluster**,
essentially using the kubernetes protocol as a smart contract layer.
- [ ] **Voting** for foreign nodes should be allowed, to enable offline users to use
their stake to secure the network. Both voter and delegate receive rewards for their
actions.
- [ ] **Pruned history** by removing the entire history if full consensus is achieved.
- [ ] **Node tiering** system to split the task itself across groups (similar to "model
parallel" in machine learning)
- [ ] **Sharding** to split the invocations across participants (similar to "data
parallel" in machine learning)


## Contributing
There are two kinds of contributions possible to this project, as donations are not
accepted.\
The first and less technical way is to get creative and submit ideas for future
improvements in the form of an [issue](https://gitlab.com/ClashLuke/valo/-/issues/new)
or an [email](mailto:lucasnestler@web.de). Duplicates will be closed and linked to a main
thread, there is no action required on your part. Anything is possible.\
The second would be to look through current to-do's and start implementing one on a
fork.