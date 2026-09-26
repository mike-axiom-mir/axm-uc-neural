# Initial full-build finding

The complete initial local build ran 1,310 tests in 552.211 seconds: one failure,
five skips. The sole failure was the shared-directory assumption in
`tests/test_machine.py:44`. Candidate code correctly removes only its own
workspace; another candidate workspace remained in the shared parent. The
old assertion reproduced separately.

The test now requires that the call adds no debris and preserves every existing
foreign path and file byte. When there was no foreign content, the shared
parent must still disappear. Five related machine/workspace-isolation checks
pass after this repair. Candidate runtime cleanup was not broadened to delete
other owners' work. The initial full log remains in `full-build.log`.

Final complete-build status is provided by the PR's Candidate adoption resume
workflow on the published commit, separately from these initial local results.
