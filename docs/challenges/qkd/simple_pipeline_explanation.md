# step-by-step narrative of the complete QKD pipeline as implemented in the project.

### Phase 1: Connection and Quantum Exchange
1.  **Secure Handshake:** Before any data is exchanged, Alice and Bob initialize their connection using a pre-shared authentication key. This ensures that every subsequent message they send over the classical network is signed (like a digital wax seal), preventing any attacker from tampering with their messages or impersonating them.
2.  **Quantum Transmission (BB84):** Alice and Bob engage the quantum hardware. Alice generates entangled photon pairs (EPR pairs) or sends qubits to Bob. Both parties measure these qubits randomly in either the "Standard" (Z) or "Diagonal" (X) basis. At this stage, they possess raw data that is roughly 50% correlated.

### Phase 2: Sifting and Estimation
3.  **Basis Sifting:** Alice sends a list of the bases she used for measurement (e.g., "X, Z, Z, X...") to Bob over the authenticated channel. Bob compares this with his own list and replies, identifying which rounds matched. Both parties discard all bits where their measurement bases differed.
4.  **Error Estimation:** To detect eavesdropping, Alice and Bob agree to sacrifice a small, random subset of their matching bits (e.g., 100 bits). They publicly compare these values.
    *   If the percentage of mismatches (the **QBER**) is too high (above ~11%), they assume an eavesdropper is present and **abort** the protocol immediately.
    *   If the error rate is safe, they discard these revealed bits and proceed, keeping the estimated error rate for later calculations.

### Phase 3: Reconciliation (Cascade)
5.  **Interactive Error Correction:** Alice and Bob now have keys that are *mostly* identical but still contain small errors. They start the **Cascade Protocol**:
    *   They divide their keys into blocks.
    *   Alice calculates the "parity" (sum modulo 2) of her blocks and sends them to Bob.
    *   If Bob’s parity matches, they assume the block is correct. If it mismatches, they know an error exists inside.
    *   They perform a **Binary Search**, recursively cutting the block in half and comparing parities until the exact location of the error is found and Bob flips the bit to fix it.
6.  **Backtracking:** Because fixing one error might unmask others in previous passes, the protocol recursively checks earlier blocks. This continues until they are confident no errors remain. During this entire process, they count exactly how many parity bits were revealed, as this information leaks partial knowledge to an eavesdropper.

### Phase 4: Verification
7.  **Polynomial Hashing:** To be absolutely sure their keys are now identical, Alice generates a random "salt" and uses a mathematical formula (Polynomial Hashing) to create a unique fingerprint of her key. She sends the salt and the fingerprint to Bob.
8.  **The Check:** Bob performs the same calculation on his key using the salt. If his fingerprint matches Alice's, verification succeeds. If not, the protocol aborts.

### Phase 5: Privacy Amplification
9.  **Calculating Secrecy:** Alice and Bob calculate how much information an eavesdropper could possibly know. This is the sum of information leaked via the quantum channel (estimated from the QBER) and the classical channel (the parity bits from Reconciliation).
10. **Key Distillation (Toeplitz Hashing):** To erase this partial knowledge, they agree on a compression recipe. Alice sends a random "seed" to Bob. Both parties use this seed to construct a large mathematical grid (a **Toeplitz Matrix**).
11. **Final Output:** They multiply their reconciled keys by this matrix. This mathematical operation mixes the bits thoroughly and shrinks the key length. The result is a shorter, **unconditional secret key** that Eve cannot know, concluding the workflow.