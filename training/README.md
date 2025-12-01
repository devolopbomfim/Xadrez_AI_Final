# Minimal AlphaZero-style training pipeline

- `training/` contains minimal implementations for model, encoder, MCTS, self-play, replay buffer and trainer.
- `models/AgentA` and `models/AgentB` hold checkpoints and metadata.

## Quick commands:

Install deps (CPU / ROCm as available):

```bash
pip install numpy
# for PyTorch on AMD/ROCm adjust per your system; example placeholder:
pip install torch torchvision
```

Run integrity checks (perft + encoder mapping):

```bash
python3 -m training.checks
```

Run a smoke self-play (requires `torch`):

```bash
python3 training/run_smoke.py
```

Run full training iteration (selfplay → train → evaluate → promote):

```bash
python3 training/run_iteration.py models/AgentA --iteration 0 --num-selfplay 5 --trainer-iters 100 --eval-games 20
```

Run arena between two checkpoints (requires `torch`):

```bash
python3 training/evaluate_and_promote.py models/AgentA --games 20 --threshold 0.55
```

Run trainer loop with gradient accumulation & checkpointing (optimized):

```bash
python3 training/train.py --agent-dir models/AgentA --device cpu --batch-size 32 --grad-accum-steps 4 --epochs 10 --iters-per-epoch 100
```

Or with AMP (ROCm/CUDA):

```bash
python3 training/train.py --agent-dir models/AgentA --device cuda --batch-size 128 --use-amp --epochs 20
```

Run trainer loop manually (legacy, simple):

```bash
python3 - <<'PYEOF'
from training.model import make_model
from training.replay_buffer import ReplayBuffer
from training.trainer import train_loop
model = make_model(device='cpu')
buf = ReplayBuffer('models/AgentA/checkpoints/replay.pt')
cfg = {'ckpt_dir':'models/AgentA/checkpoints','batch_size':32,'lr':1e-3,'iters':1}
train_loop(model, buf, cfg)
PYEOF
```

## Configuration (RX580 8GB):

Edit `training/config_rx580.json`:
- `mcts_sims`: 50–80 (lower if slow; higher for better moves)
- `batch_size`: 32–128 (reduce if VRAM OOM)
- `model.channels`: 32–128 (reduce for smaller VRAM)
- `model.blocks`: 2–10 (reduce for faster training)
- `replay_capacity`: 50k–200k (depends on available disk/RAM)

## Troubleshooting:

**VRAM OOM during selfplay:**
- Reduce `mcts_sims` (e.g., 30 instead of 50)
- Reduce model `channels` (e.g., 32 instead of 64)
- Reduce model `blocks` (e.g., 4 instead of 6)

**Training too slow:**
- Reduce `trainer_iters` per run (e.g., 50 instead of 100)
- Use gradient accumulation (not yet implemented; future enhancement)
- Use distributed training (future enhancement)

**Arena winrate not improving:**
- Increase `eval_games` for statistical significance (currently 20)
- Lower `eval_threshold` to 0.50–0.52 for earlier promotions
- Verify `mcts_sims` and net depth are enough (increase both)

**Checkpoints not being promoted:**
- Check `models/AgentA/experiments/last_arena.json` for winrate
- Ensure challenger's winrate > threshold (default 0.55)
- For first run, set `--eval-games 1` to force quick promotion

## Structure:

```
training/
  config.py             # TrainConfig dataclass with RX580 defaults
  train.py              # Main CLI entry for optimized training
  train_optimized.py    # Training loop with grad accumulation + AMP + checkpointing
  batch_sampler.py      # Dynamic batch sizing for VRAM constraints
  model.py              # Small PyTorch net (policy+value)
  encoder.py            # Board→tensor, action↔index mapping
  mcts.py               # Simple MCTS with NN priors
  selfplay.py           # Self-play worker to generate games
  replay_buffer.py      # Persistent circular buffer (FIFO)
  trainer.py            # Legacy training loop (basic, no grad accum)
  eval_arena.py         # Arena runner between two agents
  arena_runner.py       # Model-vs-model matches
  eval_loop.py          # Promotion logic (latest vs best)
  evaluate_and_promote.py  # CLI for evaluation
  run_iteration.py      # Full iteration: selfplay→train→eval→promote
  run_smoke.py          # Quick smoke test with prechecks
  prechecks.py          # Pre-training integrity checks
  checks.py             # Perft + mapping validation
  metadata_utils.py     # Update metadata.json
  config_rx580.json     # Legacy hyperparams file

models/
  AgentA/
    checkpoints/
      latest.pt         # Current model
      best.pt           # Best model (promoted)
      replay.pt         # Replay buffer (pickle)
      ckpt_000100.pt    # Numbered checkpoints (keep last N)
    experiments/
      prechecks.json    # Last precheck result
      last_arena.json   # Last arena stats
      arena.csv         # Arena history
      train.json        # Training logs (step, loss, epoch)
    metadata.json       # Agent metadata
  AgentB/
    checkpoints/
    experiments/
    metadata.json
```

## Workflow (per agent):

1. Run `python3 training/run_smoke.py` — validates setup, runs 1 quick game
2. Run `python3 training/run_iteration.py models/AgentA --iteration 0 --num-selfplay 10` — full cycle
3. Inspect `models/AgentA/experiments/arena.csv` for promotion history
4. Repeat step 2 with `--iteration 1`, `--iteration 2`, etc.

## Notes:

- Prechecks (perft, encoder round-trip) run automatically before training/smoke
- Replay buffer is FIFO circular (older data discarded when full)
- Promotion requires challenger winrate > 55% (configurable)
- All logs, checkpoints, and arena stats are persisted per agent
- Compatible with Python 3.8+ (uses `Optional[...]` instead of `X | None`)


