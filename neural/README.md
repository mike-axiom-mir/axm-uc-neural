# Neural layer

This experiment keeps two neural substrates visible and separate beneath AXM Universal Creation.

## `waldo/`

`waldo/` is a pinned, clean WALDO code substrate. Clean means **code and declared source contracts only**: no learned weights, checkpoints, model cache, generated run state, or prior experience are imported.

The full WALDO source snapshot is retained rather than cherry-picking model files so its training lifecycle, verification, provenance, export, and dependency boundaries remain inspectable.

## `axm_brain/`

`axm_brain/` is an AXM-native direct-learning substrate written for this repository. It is not a WALDO fork and does not import WALDO weights or learned state.

Its first milestone provides recurrent state, online learning, reward-modulated eligibility, bounded replay, explicit wake/sleep consolidation, inspectable snapshots, and named software I/O contracts.

## Shared experiment boundary

Neither neural substrate owns UC. UC-to-neural experience bridges must remain explicit, inspectable, testable, and replaceable. The host software owns permissions and decides which observations and outcomes are exposed to a brain.

WALDO remains the weekend baseline/fallback. The AXM brain is a sibling candidate that can later be tested against the same software problem without pretending equivalence or superiority before evidence exists.
