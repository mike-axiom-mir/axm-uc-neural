"""UC's existing canvas-fit rule exposed as pure, source-labeled experience.

No neural imports, rendering, filesystem writes or operational WALDO intake.
This adapter learns a prediction of a rule; deterministic UC still executes it.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import random

from . import simulation


def _packet(body):
    body = deepcopy(body)
    data = json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    return {'body':body,'sha256':hashlib.sha256(data).hexdigest()}


def _number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('finite numeric value required')
    return float(value)


@dataclass(frozen=True)
class CanvasState:
    x: float
    y: float
    width: float
    height: float
    seed: int
    step: int
    family: str


class CanvasFitSimulation:
    simulator_id = 'axm.uc.canvas-fit'
    version = '1'
    backend = 'python'
    experience_source = 'deterministic_simulation'
    FAMILIES = ('inside','overflow','mixed')

    def __init__(self, family='mixed'):
        if family not in self.FAMILIES:
            raise ValueError('unknown canvas-fit family')
        self.family = family
        # Pin the actual existing UC implementation, not a duplicated equation.
        self.capability_sha256 = hashlib.sha256(Path(simulation.__file__).read_bytes()).hexdigest()

    def describe_space(self):
        return {'schema':'axm.simulation-space/v1','simulator_id':self.simulator_id,
                'version':self.version,'backend':self.backend,
                'experience_source':self.experience_source,'observation_size':5,'target_size':4,
                'horizon':1,'action_bounds':[-1.0,1.0],
                'parameters':{'family':self.family,'canvas':[1,1],'action_scale':.25},
                'capability':'axm_uc.simulation._fit_shape',
                'capability_source_sha256':self.capability_sha256}

    def reset(self, seed):
        if type(seed) is not int: raise ValueError('integer seed required')
        rng = random.Random(seed)
        if self.family=='inside':
            width,height = rng.uniform(.05,.45),rng.uniform(.05,.45)
            x,y = rng.uniform(0,1-width),rng.uniform(0,1-height)
        elif self.family=='overflow':
            width,height = rng.uniform(.7,1.4),rng.uniform(.7,1.4)
            x,y = rng.uniform(-.5,1.5),rng.uniform(-.5,1.5)
        else:
            width,height = rng.uniform(.05,1.4),rng.uniform(.05,1.4)
            x,y = rng.uniform(-.5,1.5),rng.uniform(-.5,1.5)
        return CanvasState(x,y,width,height,seed,0,self.family)

    def _validate(self, state):
        if not isinstance(state,CanvasState) or state.family!=self.family or type(state.seed) is not int or type(state.step) is not int or state.step not in (0,1):
            raise ValueError('invalid canvas simulation state')
        for key in ('x','y','width','height'):
            value = _number(getattr(state,key))
            low,high = (-.5,1.5) if key in ('x','y') else (0,1.4)
            if not low<=value<=high: raise ValueError('canvas state outside bounds')

    def snapshot(self,state):
        self._validate(state)
        return _packet({'schema':'axm.uc.canvas-state/v1','space':self.describe_space(),'state':asdict(state)})

    def restore(self,snapshot):
        if not isinstance(snapshot,dict) or _packet(snapshot['body'])!=snapshot:
            raise ValueError('canvas snapshot integrity mismatch')
        body = snapshot['body']
        if body.get('schema')!='axm.uc.canvas-state/v1' or body.get('space')!=self.describe_space():
            raise ValueError('canvas provider identity mismatch')
        state = CanvasState(**body['state'])
        self._validate(state)
        return state

    def step(self,state,action):
        self._validate(state)
        action = _number(action)
        if state.step!=0 or not -1<=action<=1:
            raise ValueError('terminal state or action outside bounds')
        shape = {'kind':'rect','x':state.x+.25*action,'y':state.y-.25*action,
                 'width':state.width,'height':state.height}
        proposed = dict(shape)
        changed = simulation._fit_shape(shape,1.0,1.0)
        after = CanvasState(shape['x'],shape['y'],shape['width'],shape['height'],state.seed,1,self.family)
        observation = [state.x/2,state.y/2,state.width/2,state.height/2,action]
        target = [shape[key]/2 for key in ('x','y','width','height')]
        body = {'schema':'axm.micro-experience/v1','experience_source':self.experience_source,
                'simulator_id':self.simulator_id,'simulator_version':self.version,'backend':self.backend,
                'parameters':self.describe_space(),'seed':state.seed,'before':asdict(state),
                'action':action,'after':asdict(after),'observation':observation,'target':target,'terminal':True,
                'raw_human_prompt':None,'interpreted_intent':'Predict the bounded canvas-fit result.',
                'selected_capabilities':['fit-known-shapes-inside-canvas'],
                'proposed_shape':proposed,'result_shape':shape,'changed':changed,
                'verification':{'within_canvas':all(0<=shape[k]<=1 for k in ('x','y','width','height'))
                                and shape['x']+shape['width']<=1 and shape['y']+shape['height']<=1}}
        return {'state':after,'experience':_packet(body)}

    def step_many(self,states,actions):
        if not isinstance(states,(list,tuple)) or not states or len(states)!=len(actions):
            raise ValueError('aligned nonempty batch required')
        return [self.step(state,action) for state,action in zip(states,actions)]

    def verify_transition(self,packet):
        if not isinstance(packet,dict) or _packet(packet['body'])!=packet:
            raise ValueError('canvas experience integrity mismatch')
        body = packet['body']
        expected = self.step(CanvasState(**body['before']),body['action'])['experience']
        if expected!=packet:
            raise ValueError('canvas experience does not reproduce from UC capability')
        return deepcopy(body)
