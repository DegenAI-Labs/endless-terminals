# Probes and `claim_log.jsonl`

How optional **verification probes** integrate with **`generate_solutions.py`** / **`run_n_solutions`**, and how **`scripts/eval_probe_claims.py`** scores them.

## When this runs

Probes run **only if** `probes.json` exists **next to** `task.json` in the task directory. Execution order inside `run_n_solutions`:

1. Interactive agent loop (commands in the Apptainer PTY until done or `max_actions`).
2. **`_run_probes_after_episode`** (this document): for each probe × each rollout, call the **same** vLLM (`chat_completion_batch`) with a short QA prompt; append lines to **`claim_log.jsonl`**.
3. **`run_final_tests`** (`pytest` on `test_final_state.py`) per rollout.

So probe answers reflect **whatever is on disk inside each rollout’s container** at the end of the episode (file excerpts come from `cat` via `env.exec`).

## Flow (Mermaid)

```mermaid
flowchart TB
  subgraph inputs [Task directory]
    task_json["task.json"]
    probes_json["probes.json"]
  end

  probes_json --> load["load_probes()"]

  subgraph ref_w ["reference_w in probes.json"]
    default_paths["default_paths: list of absolute paths"]
  end

  subgraph after_episode ["After agent episode completes"]
    envs["envs[0 … N−1]\none InteractiveContainerEnvironment\nper rollout"]
  end

  default_paths --> ctx["_probe_file_context(env, paths)\nfor each rollout: cat paths in container"]
  envs --> ctx

  ctx --> batch["Build batch: for each probe,\nN messages =\n  system: PROBE_SYSTEM_MESSAGE\n  user: excerpts + Question"]

  batch --> vllm["chat_completion_batch\n(same model as agent, tunable max_tokens)"]
  vllm --> claims["For each response:\nappend_claim_event(...)"]

  subgraph log [Append-only log]
    claim_log["claim_log.jsonl\none JSON object per line"]
  end

  claims --> claim_log

  subgraph record [Each JSONL line]
    fields["ts, task_id, run_id, step,\nprobe_id, claim_raw,\nextra.rollout_index"]
  end

  claim_log --> record

  subgraph eval [Offline evaluation]
    eval_script["scripts/eval_probe_claims.py\n--probes --log [--rollout-index]"]
    probes_json --> eval_script
    claim_log --> eval_script
    score["summarize_run_against_probes()\ncompare claim_raw to\nprobe.ground_truth"]
  end

  eval_script --> score
```

## Simplified sequence

```mermaid
sequenceDiagram
  participant R as run_n_solutions
  participant E as envs[i] PTY
  participant V as vLLM
  participant L as claim_log.jsonl

  R->>R: Agent loop finishes (N rollouts)
  loop Each probe in probes.json
    loop i = 0 .. N−1
      R->>E: cat default_paths in envs[i]
      E-->>R: file excerpts (or missing)
      R->>V: probe system + user(question + excerpts)
      V-->>R: claim text
      R->>L: append JSONL line (probe_id, rollout_index i, claim_raw, …)
    end
  end
  R->>R: run_final_tests() per env
```

## Ground truth matching

`generator/probe_claims.py` scores each probe with `score_probe_answer()`:

- **`answer_type: "integer"`** — first integer in `claim_raw` vs `ground_truth`.
- **`answer_type: "exact_string"`** — full string vs `ground_truth` (`match.strip_eq` or `casefold_eq`).

If the probe model emits long `<redacted_thinking>` blocks, automated scoring often fails until you strip reasoning or tighten the probe model.

## Commands

```bash
# After a solution run produced claim_log.jsonl
python scripts/eval_probe_claims.py \
  --probes tasks2/task_000000_540a5f77/probes.json \
  --log tasks2/task_000000_540a5f77/claim_log.jsonl \
  --rollout-index 0

python scripts/eval_probe_claims.py ... --json
```
