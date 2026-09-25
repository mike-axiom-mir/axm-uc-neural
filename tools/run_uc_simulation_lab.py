#!/usr/bin/env python3
"""Explicit local UC/AXM simulation experiment; separate from WALDO training."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'axm-neural-brain':'a463363ac84543f1a4289830793e9f1a0993e6fe',
    'axm-neural-network':'0dc91d6b0324fc2dec2173c73b9e3310e945a254',
}


def _git(*args):
    return subprocess.check_output(['git',*map(str,args)],text=True,stderr=subprocess.STDOUT).strip()


def prepare_dependencies(base):
    """Install exact new checkouts; never reset an existing or modified checkout."""
    base.mkdir(parents=True,exist_ok=True)
    for repo,revision in PINS.items():
        destination = base/repo
        if not destination.exists():
            _git('clone','--no-checkout',f'https://github.com/mike-axiom-mir/{repo}.git',destination)
            _git('-C',destination,'checkout','--detach',revision)
        if _git('-C',destination,'rev-parse','HEAD')!=revision or _git('-C',destination,'status','--porcelain'):
            raise ValueError(f'{destination} differs from the pinned clean dependency; it was preserved')


def load_dependencies(brain_root,network_root):
    required = [(brain_root/'neural/axm_brain/simulation_session.py'),
                (network_root/'src/axm_neural_network/simulation_contract.py')]
    if any(not path.is_file() for path in required):
        raise ValueError('Simulation dependencies missing. Run this command with --prepare, or supply --brain-root and --network-root.')
    sys.path[:0] = [str(ROOT/'src'),str(brain_root),str(network_root/'src')]


def providers():
    from axm_uc.neural_simulation import CanvasFitSimulation
    return {name:CanvasFitSimulation(name) for name in CanvasFitSimulation.FAMILIES}


def fresh_session(*,brain_seed=41,policy='fixed',max_transitions=10_000):
    from neural.axm_brain import AXMBrain,BrainConfig
    from neural.axm_brain.simulation_session import SimulationSession
    brain = AXMBrain(BrainConfig(5,16,4,seed=brain_seed,learning_rate=.04,replay_capacity=32))
    session = SimulationSession(brain,providers(),range(64),range(1000,1064),
                                policy=policy,scheduler_seed=20260925,max_transitions=max_transitions)
    return session


def source_identity(path):
    result = {'path':str(path)}
    try:
        result.update(commit=_git('-C',path,'rev-parse','HEAD'),
                      working_tree_modified=bool(_git('-C',path,'status','--porcelain')))
    except (OSError,subprocess.CalledProcessError):
        result['commit'] = None
    files = {}
    for relative in ('neural/axm_brain','src/axm_neural_network'):
        for file in sorted((path/relative).glob('*.py')):
            files[str(file.relative_to(path))] = hashlib.sha256(file.read_bytes()).hexdigest()
    if path==ROOT:
        for relative in ('src/axm_uc/neural_simulation.py','src/axm_uc/simulation.py','tools/run_uc_simulation_lab.py'):
            files[relative] = hashlib.sha256((path/relative).read_bytes()).hexdigest()
    result['source_sha256'] = files
    return result


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                         prefix=path.name+'.',suffix='.tmp',delete=False) as stream:
            name = stream.name
            json.dump(data,stream,sort_keys=True,indent=2,allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if name and os.path.exists(name): os.unlink(name)


@contextmanager
def checkpoint_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    lock = path.with_name(path.name+'.lock')
    try:
        fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise ValueError(f'Checkpoint is in use: {lock}. If its previous process crashed, confirm it has stopped before removing this lock.') from exc
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream: stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    dependencies = ROOT/'state/neural-experiment/simulation/dependencies'
    parser.add_argument('--prepare',action='store_true',help='Download exact pinned source dependencies using Git')
    parser.add_argument('--brain-root',type=Path,default=dependencies/'axm-neural-brain')
    parser.add_argument('--network-root',type=Path,default=dependencies/'axm-neural-network')
    parser.add_argument('--checkpoint',type=Path,default=ROOT/'state/neural-experiment/simulation/session.json')
    parser.add_argument('--resume',action='store_true',help='Continue the exact saved learner and curriculum')
    parser.add_argument('--episodes',type=int,default=768,help='Additional one-transition UC episodes, at most 10000')
    parser.add_argument('--policy',choices=('fixed','random','error_guided'))
    parser.add_argument('--brain-seed',type=int)
    parser.add_argument('--max-transitions',type=int,default=None)
    args = parser.parse_args(argv)
    if not 1<=args.episodes<=10_000: parser.error('--episodes must be in [1, 10000]')
    if args.resume and any(value is not None for value in (args.policy,args.brain_seed,args.max_transitions)):
        parser.error('resume uses saved policy, brain seed and budget; omit their creation options')
    if args.prepare:
        prepare_dependencies(dependencies)
    brain_root,network_root = args.brain_root.resolve(),args.network_root.resolve()
    load_dependencies(brain_root,network_root)
    with checkpoint_lock(args.checkpoint):
        return run_checkpoint(args,brain_root,network_root)


def run_checkpoint(args,brain_root,network_root):
    from neural.axm_brain.simulation_session import SimulationSession
    from neural.axm_brain.state import snapshot_payload,verify_snapshot
    if args.resume:
        saved = verify_snapshot(json.loads(args.checkpoint.read_text(encoding='utf-8')))
        if saved.get('schema')!='axm.uc-simulation-lab/v1': raise ValueError('unsupported lab checkpoint')
        session = SimulationSession.from_snapshot(saved['session'],providers())
        history = saved['runs']
    else:
        if args.checkpoint.exists():
            raise ValueError('A checkpoint already exists. Use --resume or choose a new --checkpoint; the existing learner was preserved.')
        session = fresh_session(brain_seed=41 if args.brain_seed is None else args.brain_seed,
                                policy=args.policy or 'fixed',
                                max_transitions=10_000 if args.max_transitions is None else args.max_transitions)
        history = []
    before = session.evaluate()
    previous = session.to_snapshot()['sha256']
    start,cpu = time.perf_counter(),time.process_time()
    session.advance(args.episodes)
    elapsed,cpu = time.perf_counter()-start,time.process_time()-cpu
    after = session.evaluate()
    checkpoint = session.to_snapshot()
    restored = SimulationSession.from_snapshot(json.loads(json.dumps(checkpoint)),providers())
    retained = restored.evaluate()
    if after!=retained or restored.to_snapshot()!=checkpoint:
        raise ValueError('restart verification failed; checkpoint was not written')
    record = {'episodes_added':args.episodes,'training_transitions_added':args.episodes,
              'checkpoint_before':previous,'checkpoint_after':checkpoint['sha256'],
              'held_out_before':before,'held_out_after':after,'held_out_after_restore':retained,
              'restore_exact':True,'family_counts':session.counts,
              'training_wall_seconds':elapsed,'training_cpu_seconds':cpu,
              'training_transitions_per_second':args.episodes/elapsed,
              'evaluation_transitions':before['transitions']+after['transitions']+retained['transitions']}
    output = snapshot_payload({'schema':'axm.uc-simulation-lab/v1','session':checkpoint,
                'runs':history+[record],'runtime':{'python':platform.python_version(),'platform':platform.platform()},
                'sources':[source_identity(path) for path in (ROOT,brain_root,network_root)],
                'limits':['This learns numeric predictions of one existing UC canvas-fitting rule.',
                          'Simulated examples are not external user-task success or autonomous creation.',
                          'error_guided is a measured-error scheduling heuristic, not a trained meta-network.',
                          'No WALDO training, no neural-link change, no automatic UC adoption.',
                          'Timing includes direct learning, replay verification and episode receipts; no RAM/GPU measurement.']})
    atomic_write(args.checkpoint,output)
    # Read the actual durable bytes and restore them before reporting success.
    durable = verify_snapshot(json.loads(args.checkpoint.read_text(encoding='utf-8')))
    loaded = SimulationSession.from_snapshot(durable['session'],providers())
    if loaded.to_snapshot()!=checkpoint: raise ValueError('written checkpoint differs from the tested learner')
    print(json.dumps({'status':'SAVED','checkpoint':str(args.checkpoint),'bytes':args.checkpoint.stat().st_size,
                      'total_training_transitions':session.transitions,'policy':session.policy,**record},indent=2))
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print(f'HOLD: {exc}',file=sys.stderr)
        raise SystemExit(2)
