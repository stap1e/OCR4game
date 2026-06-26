# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Install the project with development dependencies:

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run tests and lint:

```bash
pytest
python -m ruff check src tests
```

Run targeted tests:

```bash
pytest tests/test_workflow_engine.py -q
pytest tests/test_workflow_engine.py::test_retry_retries_step_until_success -q
pytest tests/test_validation.py tests/test_config.py -q
```

Validate the built-in Star Rail task without launching the game:

```bash
ocr4game --validate --game star_rail --task daily
ocr4game --validate --strict --game star_rail --task daily
```

Useful runtime/debug commands:

```bash
ocr4game --list-games
ocr4game --dry-run --game star_rail --task daily
ocr4game --game star_rail --task daily
ocr4game --game star_rail --task daily --var sweep_times=3 --var claim_loop_max=5
ocr4game --log-level DEBUG --game star_rail --task daily
ocr4game-annotate --game star_rail --list-windows --verbose
ocr4game-annotate --game star_rail --name claim_button
ocr4game-threshold --game star_rail --anchor claim_button --sweep
ocr4game-anchor-eval --game star_rail --include-ocr --screenshots tests/fixtures/star_rail/frames --output-dir runs/anchor_eval --html --overlay
ocr4game-recognize --game star_rail --image tests/fixtures/star_rail/frames/daily_panel.png --json
ocr4game-threshold --game star_rail --anchor claim_button --apply
ocr4game-import --game star_rail --from-dir D:\captures\star_rail
ocr4game-report --run runs/star_rail_xxx
ocr4game-replay --run runs/star_rail_xxx
ocr4game-replay --run runs/star_rail_xxx --step-index 12
```

If console scripts are unavailable, use the module entry point for the main CLI:

```bash
python -m ocr4game.app --list-games
```

## Project overview

OCR4game is a Windows-oriented game visual automation framework. It combines OpenCV template matching, RapidOCR text anchors, Win32 window/input handling, and YAML-defined workflows. The included game target is `star_rail` (崩坏：星穹铁道), with recommended windowed client size 1280×720.

The central design is configuration-driven:

- `configs/global.yaml` sets logging, run output, capture/input defaults, and workflow limits.
- `configs/games/<game_id>/profile.yaml` defines window matching, expected resolution, anchors, asset/task paths, recovery, and game-specific extensions.
- `configs/games/<game_id>/tasks/*.yaml` defines workflow steps, conditions, loops/repeats, and actions.
- `configs/games/<game_id>/assets/` contains template images referenced by profile anchors.
- Python code supplies the engine, perception, platform bindings, validation, and plugin extension points.

## Runtime flow

A normal `ocr4game --game star_rail --task daily` run follows this path:

1. `src/ocr4game/app.py` parses CLI args, loads `GlobalConfig` and `GameProfile`, locates the task file, and gets the game plugin.
2. `validation.validate_run()` checks the profile/task/action/anchor references before runtime binding.
3. `runtime/binding.py` finds the configured game window, creates `ScreenCapture`, `InputDriver`, and `Perception`, then stores them in `RunContext`.
4. `GamePlugin.preflight()` performs game-specific runtime checks such as client-size validation.
5. `WorkflowEngine.run_task()` loads the task YAML, merges task `vars` with CLI `--var` overrides, resolves `{var}` substitutions, and executes each step.
6. Actions use `RunContext` to capture frames, evaluate anchors, wait/click/log, and save failure screenshots under `runs/<game_id>_<timestamp>/` for non-optional failures.

## Important modules

- `src/ocr4game/config.py` — Pydantic models and YAML loaders for global config, game profiles, anchors, and task files.
- `src/ocr4game/resources.py` — repository-relative path helpers for configs, game assets/tasks, fixtures, and run outputs.
- `src/ocr4game/validation.py` — offline validation of profiles, tasks, actions, vars, anchors, and template assets.
- `src/ocr4game/platform/` — Windows-specific window discovery, screenshot capture, and DirectInput-backed input.
- `src/ocr4game/perception/` — ROI handling, template matching, OCR, Perception v2 content snapshots, screen state recognition, and `Perception.evaluate_anchor()` as the unified anchor API.
- `src/ocr4game/workflow/engine.py` — workflow execution, step retries, loops/repeats, timeouts, `when`, and action-level `if` branches.
- `src/ocr4game/workflow/actions/` — default action registry and handlers (`log`, `wait`, `assert_window`, `wait_for`, `click_template`, `click_ocr`).
- `src/ocr4game/games/` — plugin abstraction, registry, and the built-in Star Rail plugin.
- `src/ocr4game/tools/` — CLI tools for annotation, threshold tuning, screenshot import, and asset sync.

## Workflow and config semantics

Task YAML files are sequences of `steps`, each with a required `do` list. Steps may define:

- `when`: skip the whole step if the condition is false.
- `retry`: retry the whole step after `StepFailed`; default comes from `global.yaml`.
- `repeat`: run the step body a fixed number of times.
- `loop.max`: run up to N times and stop when an action returns `False`.
- `vars`: task-level values referenced with `{var_name}`; CLI `--var KEY=VALUE` overrides them.

Condition handling lives in `workflow/conditions.py`. Supported conditions include `anchor_visible`, `anchor_missing`, `screen_state`, `ocr_contains`, content comparisons (`content_eq`, `content_gt`, etc.), variable comparisons (`var_eq`, `var_gt`, etc.), `all`, `any`, and `not`.

Actions are parsed by `workflow/semantics.py` and dispatched through `ActionRegistry`. `optional: true` on an action makes failures log and continue instead of aborting the step.

## Plugin and extension model

New games should avoid changing the core engine unless the behavior is truly generic. The expected path is:

1. Copy `configs/games/_template/` to `configs/games/<game_id>/`.
2. Add `profile.yaml`, `tasks/*.yaml`, and assets.
3. Optionally implement `src/ocr4game/games/<game_id>/plugin.py` by subclassing `GamePlugin`.
4. Register the plugin in `pyproject.toml` under `[project.entry-points."ocr4game.plugins"]`.

`games/registry.py` automatically loads entry-point plugins and also provides a built-in fallback for `star_rail` when running directly from `PYTHONPATH=src` without installing the package.

Plugins can override `preflight()`, `normalize_frame()`, `register_actions()`, `validate_profile()`, `validate_task()`, and `on_step_failure()`.

## Testing notes

The tests are designed to run without launching the game. Runtime-facing tests use dummy capture/input/perception objects and static fixtures. Use strict validation and fixture regression tests when changing profile anchors, assets, task YAML, or template matching behavior.

Generated/runtime outputs belong under `runs/` and are not part of normal source changes.
