"""Compare equal-budget curricula across the current UC simulation providers."""
import argparse
import json
from pathlib import Path
import platform
import time

from run_uc_simulation_lab import ROOT,load_dependencies,fresh_session,providers,atomic_write,source_identity,workflow_route_evaluation


def run(episodes=768,full_dir=None):
    from neural.axm_brain.simulation_session import SimulationSession
    rows = []
    for seed in (17,41,73):
        for policy in SimulationSession.POLICIES:
            session = fresh_session(brain_seed=seed,policy=policy,max_transitions=episodes)
            before = session.evaluate()
            routing_before = workflow_route_evaluation(session)
            parent_sha = session.parent['sha256']
            start,cpu = time.perf_counter(),time.process_time()
            session.advance(episodes)
            elapsed,cpu = time.perf_counter()-start,time.process_time()-cpu
            after = session.evaluate()
            routing_after = workflow_route_evaluation(session)
            snapshot = session.to_snapshot()
            restored = SimulationSession.from_snapshot(json.loads(json.dumps(snapshot)),providers())
            retained = restored.evaluate()
            routing_retained = workflow_route_evaluation(restored)
            assert session.parent['sha256']==parent_sha
            assert after==retained and routing_after==routing_retained and restored.to_snapshot()==snapshot
            if full_dir: atomic_write(full_dir/f'{seed}-{policy}.json',snapshot)
            row = {'brain_seed':seed,'policy':policy,'training_transitions':session.transitions,
                   'before':before,'after':after,'retained':retained,
                   'workflow_routing_before':routing_before,'workflow_routing_after':routing_after,
                   'workflow_routing_retained':routing_retained,'restore_exact':True,
                   'parent_sha256':parent_sha,'learner_sha256':session.learner.to_snapshot()['sha256'],
                   'session_sha256':snapshot['sha256'],'history_tip':session.records[-1]['sha256'],
                   'family_counts':session.counts,'wall_seconds':elapsed,'cpu_seconds':cpu,
                   'training_transitions_per_second':episodes/elapsed}
            rows.append(row)
            print(json.dumps({'seed':seed,'policy':policy,'before':before['mean_family_mse'],
                              'after':after['mean_family_mse'],'routing_before':routing_before['best_pass_accuracy'],
                              'routing_after':routing_after['best_pass_accuracy'],'counts':session.counts}),flush=True)
    means = {policy:sum(row['after']['mean_family_mse'] for row in rows if row['policy']==policy)/3
             for policy in SimulationSession.POLICIES}
    return {'schema':'axm.uc-simulation-comparison/v2','rows':rows,'mean_held_out_mse':means,
            'training_seeds':list(range(64)),'held_out_seeds':list(range(1000,1064)),
            'scheduler_seed':20260925,'episodes_per_run':episodes,
            'brain_config':fresh_session().learner.to_snapshot()['body']['config'],
            'providers':{name:provider.describe_space() for name,provider in providers().items()},
            'python':platform.python_version(),'platform':platform.platform(),
            'limits':['The provider set combines three UC canvas-fit distributions with four grounded workflow-pass simulations.',
                      'Workflow providers learn bounded pass consequences from current product-workflow stage contracts; they do not execute or rewrite pipelines.',
                      'error_guided is a moving-error heuristic, not a learned neural meta-selector.',
                      'No external-task, autonomous-creation, aesthetic-quality, general-intelligence or WALDO-learning claim.',
                      'Equal training transitions; evaluation and timing are separately reported.',
                      'No peak RAM/VRAM or million-simulation measurement.']}


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brain-root',type=Path,default=ROOT.parent/'axm-neural-brain')
    parser.add_argument('--network-root',type=Path,default=ROOT.parent/'axm-neural-network')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--full-dir',type=Path)
    parser.add_argument('--episodes',type=int,default=768)
    args = parser.parse_args()
    if not 1<=args.episodes<=10_000: parser.error('episodes must be in [1, 10000]')
    load_dependencies(args.brain_root.resolve(),args.network_root.resolve())
    result = run(args.episodes,args.full_dir)
    result['sources'] = [source_identity(path.resolve()) for path in (ROOT,args.brain_root,args.network_root)]
    atomic_write(args.output,result)
    print(json.dumps(result['mean_held_out_mse']))
