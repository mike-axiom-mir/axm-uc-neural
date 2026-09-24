# Neural layer

`waldo/` is a pinned, clean WALDO code substrate placed below AXM Universal Creation for the UC/neural experiment.

Clean means **code and declared source contracts only**. This bootstrap intentionally imports no learned weights, checkpoints, model cache, generated run state, or prior experience.

The full WALDO source snapshot is retained rather than cherry-picking a few model files so its training lifecycle, verification, provenance, export, and dependency boundaries remain inspectable.

The first integration bridge is intentionally not invented here. A later change can define how UC emits experience, what the neural side is allowed to learn from it, how outputs return upward, and which state is authoritative.
