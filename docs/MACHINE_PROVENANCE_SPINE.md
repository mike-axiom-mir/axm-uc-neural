# AXM machine provenance spine

Status: experimental, additive, no authority.

This is the machine-readable form of the AXM visual-log idea:

```text
SOURCE
  -> INTERPRETATION
  -> EXECUTION
  -> OUTCOME
  -> LEARNING INTAKE
```

The purpose is not control. It is to preserve enough causal context that a human,
WALMI, ChatGPT, a local model, a scheduler, or a later AXM frontend can answer:

- What caused this machine activity?
- Who or what declared the request?
- Which UC path executed it?
- What outcome was observed?
- Did that same experience reach the neural-learning intake?
- Which later handoff descended from which earlier source event?

## Existing AXM roots

UC already contains provenance atoms and organs for activity references, agent
references, usage assertions, observations, audit events and audit logging. This
experiment does not replace those. It gives the current UC/OpenWALDO runtime an
executable causal spine that can later converge with the broader provenance
fabric.

## Caller contract

Any frontend may attach an optional `axm_source` object to a normal UC machine
request. The source packet is metadata beside the request; deterministic
capability input contracts do not need to change.

Example — human request:

```json
{
  "prompt": "create a small local tool",
  "axm_source": {
    "schema": "axm.source-context/v1",
    "kind": "human_prompt",
    "actor": "mike",
    "interface": "local-cockpit",
    "source_event_id": "prompt-000184",
    "session_id": "weekend-uc-01"
  }
}
```

Example — WALMI:

```json
{
  "kind": "creative-flow",
  "inputs": {},
  "axm_source": {
    "schema": "axm.source-context/v1",
    "kind": "model_request",
    "actor": "walmi",
    "interface": "axm-machine",
    "source_event_id": "walmi-cycle-0042",
    "parent_trace_id": "<trace that caused this handoff>"
  }
}
```

Example — ChatGPT/front-end brain:

```json
{
  "kind": "software-project",
  "inputs": {},
  "axm_source": {
    "kind": "model_request",
    "actor": "chatgpt",
    "interface": "frontend-brain",
    "source_event_id": "handoff-983",
    "parent_trace_id": "<upstream trace>"
  }
}
```

Example — autonomous creative event:

```json
{
  "kind": "creative-flow",
  "inputs": {},
  "axm_source": {
    "kind": "autonomous_creative",
    "actor": "uc-creative-loop",
    "session_id": "creative-session-17",
    "source_event_id": "tick-0091"
  }
}
```

Example — scheduler:

```json
{
  "kind": "verify-project",
  "inputs": {},
  "axm_source": {
    "kind": "scheduled_event",
    "actor": "local-scheduler",
    "source_event_id": "schedule-2026-09-25T20:00"
  }
}
```

Supported source kinds in v1:

- `human_prompt`
- `model_request`
- `autonomous_creative`
- `scheduled_event`
- `machine_event`
- `replay`
- `imported`
- `unattributed`

## No guessing

If caller attribution is absent, UC records:

```json
{"kind":"unattributed","attribution_status":"UNATTRIBUTED"}
```

It does not infer that a prompt was human, AI, WALMI, Mike, ChatGPT, or anything
else from its wording.

Malformed source metadata also does not delete the underlying experience. The
experience is retained with a fail-closed attribution state instead.

## Nested deterministic calls

The machine establishes a request-scoped source context before invoking a
capability. That scope carries the declared caller plus SHA-256 identities for
the originating request and any prompt/direction/purpose text. Nested aliases,
composites and other deterministic capability calls inherit that context without
inserting extra provenance fields into their input schemas.

This is important for long-term specialist networks: source identity follows the
handoff while the specialist tool contract stays clean.

Direct low-level calls made outside a machine/source scope remain unattributed.
A frontend that cares about ancestry must enter through the source contract or
an equivalent future adapter.

## Files

The experiment writes three related evidence surfaces:

- `state/neural-experiment/uc-wiring-events.jsonl` — operational coverage.
- `state/neural-experiment/openwaldo-intake.jsonl` — learning input.
- `state/neural-experiment/provenance-trace.jsonl` — source -> interpretation -> execution -> outcome -> learning linkage.

The same `trace_id` is carried into the UC event and OpenWALDO intake metadata,
so later observers can join them without parsing natural language.

## Prompt retention boundary

The provenance trace does **not** duplicate raw prompt text.

When the ordinary UC request contains a prompt, the trace records:

- that a prompt was present;
- a SHA-256 digest of that prompt;
- a digest of the complete request.

The actual request remains in the ordinary UC experience payload where current
learning already sees it. Nested capability traces inherit the originating
request/prompt digests, so many internal actions can still be grouped back to
one initiating prompt without copying the prompt into every event. This avoids
creating another unbounded raw-prompt memory merely for observability.

## Handoffs between brains

`parent_trace_id` is the minimal bridge for future neural-to-neural handoffs.

A frontend brain can receive a human request, create a trace, and hand a bounded
task to a coding/visual/simulation brain while retaining ancestry:

```text
human prompt
  trace A
    -> frontend interpretation
       -> specialist handoff (parent=A)
          trace B
            -> deterministic UC execution
               -> outcome
                  -> learning intake
```

Later the network can add richer handoff packets (intent, evidence, uncertainty,
return contract, stop conditions) without replacing this causal identity.

## Truth and authority boundaries

A provenance trace proves only what the local recorder observed and what the
caller declared.

It does not prove:

- that a caller's self-declared identity is externally authenticated;
- that an interpretation was semantically correct;
- that an outcome is good;
- that neural state change is useful learning;
- that source identity grants permission or authority.

**Source != authority. Visibility != control. Observation != approval.**

That separation is intentional.
