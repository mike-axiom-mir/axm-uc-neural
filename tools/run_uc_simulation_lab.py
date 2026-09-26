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
    from axm_uc.workflow_simulation import WorkflowPassSimulation
    result = {name:CanvasFitSimulation(name) for name in CanvasFitSimulation.FAMILIES}
    result.update({f'workflow-{name}':WorkflowPassSimulation(name) for name in WorkflowPassSimulation.FAMILIES})
    return result


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
        for relative in ('src/axm_uc/neural_simulation.py','src/axm_uc/workflow_simulation.py',
                         'src/axm_uc/trajectory_simulation.py','src/axm_uc/product_workflow.py',
                         'src/axm_uc/simulation.py','tools/run_uc_simulation_lab.py',
                         'tools/run_uc_trajectory_learning.py'):
            files[relative] = hashlib.sha256((path/relative).read_bytes()).hexdigest()
    result['source_sha256'] = files
    return result


def workflow_route_evaluation(session):
    """Measure whether learned predictions select the best next workflow pass.

    This is read-only held-out evaluation. It does not execute or adopt a UC
    pipeline and it does not feed its result back into training.
    """
    from axm_uc.workflow_simulation import WorkflowPassSimulation
    from neural.axm_brain import AXMBrain
    from neural.axm_brain.simulation import _reset

    by_family, total, correct, total_regret = {}, 0, 0, 0.0
    for name, provider in session.providers.items():
        if not isinstance(provider, WorkflowPassSimulation):
            continue
        brain = AXMBrain.from_snapshot(session.learner.to_snapshot())
        family_total = family_correct = 0
        family_regret = 0.0
        for seed in session.evaluation_seeds:
            state = provider.reset(seed)
            actual_scores, predicted_scores = [], []
            for action in WorkflowPassSimulation.ACTION_VALUES:
                event = provider.step(state, action)['experience']['body']
                actual_scores.append(provider.debt_score(event['target']))
                _reset(brain)
                prediction = brain.predict(event['observation'], update_state=False)
                predicted_scores.append(sum(prediction))
            actual_best = min(range(len(actual_scores)), key=lambda index: (actual_scores[index], index))
            predicted_best = min(range(len(predicted_scores)), key=lambda index: (predicted_scores[index], index))
            regret = actual_scores[predicted_best] - actual_scores[actual_best]
            family_total += 1
            family_correct += predicted_best == actual_best
            family_regret += regret
        by_family[name] = {
            'best_pass_accuracy': family_correct / family_total,
            'mean_debt_regret': family_regret / family_total,
            'probes': family_total,
        }
        total += family_total
        correct += family_correct
        total_regret += family_regret
    return {
        'families': by_family,
        'best_pass_accuracy': correct / total if total else None,
        'mean_debt_regret': total_regret / total if total else None,
        'probes': total,
        'truth': 'Read-only held-out choice from predicted pass outcomes; not autonomous pipeline execution or aesthetic quality.',
    }


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
    parser.add_argument('--checkpoint',type=Path,default=ROOT/'state/neural-experiment/simulation/session-workflow-v2.json')
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
    routing_before = workflow_route_evaluation(session)
    previous = session.to_snapshot()['sha256']
    start,cpu = time.perf_counter(),time.process_time()
    session.advance(args.episodes)
    elapsed,cpu = time.perf_counter()-start,time.process_time()-cpu
    after = session.evaluate()
    routing_after = workflow_route_evaluation(session)
    checkpoint = session.to_snapshot()
    restored = SimulationSession.from_snapshot(json.loads(json.dumps(checkpoint)),providers())
    retained = restored.evaluate()
    retained_routing = workflow_route_evaluation(restored)
    if after!=retained or routing_after!=retained_routing or restored.to_snapshot()!=checkpoint:
        raise ValueError('restart verification failed; checkpoint was not written')
    record = {'episodes_added':args.episodes,'training_transitions_added':args.episodes,
              'checkpoint_before':previous,'checkpoint_after':checkpoint['sha256'],
              'held_out_before':before,'held_out_after':after,'held_out_after_restore':retained,
              'workflow_routing_before':routing_before,'workflow_routing_after':routing_after,
              'workflow_routing_after_restore':retained_routing,
              'restore_exact':True,'family_counts':session.counts,
              'training_wall_seconds':elapsed,'training_cpu_seconds':cpu,
              'training_transitions_per_second':args.episodes/elapsed,
              'evaluation_transitions':before['transitions']+after['transitions']+retained['transitions']}
    output = snapshot_payload({'schema':'axm.uc-simulation-lab/v1','session':checkpoint,
                'runs':history+[record],'runtime':{'python':platform.python_version(),'platform':platform.platform()},
                'sources':[source_identity(path) for path in (ROOT,brain_root,network_root)],
                'limits':['This learns numeric predictions of existing UC canvas-fit behavior and bounded workflow-pass consequences.',
                          'Workflow routing is grounded in current product-workflow stage contracts but does not execute or rewrite those pipelines.',
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
