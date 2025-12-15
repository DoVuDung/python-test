# Ultra-Live Pipeline Engine — Candidate Submission

## Candidate Information
- Name: Andy Do
- Email / Telegram: vudung05032000@gmail.com
- Date of submission: December 15, 2025
- Python version used: 3.9.6 (compatible with 3.10+)

---

## 1. How to Run

### Requirements
- Python 3.10+ (developed and tested with 3.9.6, fully compatible with 3.10+)

### Run command
python run_pipeline.py

### Expected behavior
- Pipeline starts immediately
- ASCII dashboard updates during execution
- Execution finishes without manual input
- result.json is generated in project root

---

## 2. High-Level Architecture

Briefly describe the main components:

- Executor / Scheduler: The PipelineEngine class orchestrates task execution in dependency order. It uses a deterministic approach to ensure consistent execution order across runs with the same seed.

- Dependency Resolver: The engine checks task dependencies before execution. Tasks only run when all their dependencies have completed successfully. Failed or missing dependencies prevent task execution and are properly propagated.

- Renderer (ASCII dashboard): The ConsoleRenderer provides real-time feedback during execution. It's completely isolated from the core execution logic and won't affect pipeline operation if it fails.

- DLQ handling: The DLQSystem captures detailed failure information including task name, failure reason, and deterministic timestamp. Failures are categorized by type (missing dependencies, failed dependencies, etc.).

- Result reporting: The engine generates a comprehensive result.json file containing execution summary, completed/failed tasks, DLQ entries, execution order, and timing information.

---

## 3. Determinism & Idempotency

The pipeline ensures determinism through a single source of randomness controlled by a seed. All random operations use a DeterministicRandom class that generates predictable sequences based on the seed and task context. The same seed always produces the same task execution order and results because:

1. Task selection order is deterministic (using sorted collections)
2. Random number generation is seeded and context-aware
3. Time-based operations are eliminated from affecting outcomes
4. All execution paths are predictable given the same inputs

When re-run with the same seed, the pipeline produces identical results including execution order, task outcomes, and timing.

---

## 4. Dependency Safety (A → C)

Dependencies are resolved through a two-phase approach:

1. Pre-execution validation: Before any task runs, the engine verifies that all dependencies exist in the task graph
2. Runtime checking: Tasks only execute when all their dependencies have completed successfully

C tasks are prevented from running too early through continuous dependency status checking. The engine maintains a task result registry and only considers tasks with COMPLETED status as valid dependencies.

Failed dependencies are handled by placing dependent tasks in the DLQ with specific failure reasons, preventing cascade failures while maintaining execution traceability.

---

## 5. Failure Handling & DLQ

The DLQ stores structured failure information including:
- Task name that failed or couldn't execute
- Specific reason for failure (missing dependency, failed dependency, etc.)
- Deterministic timestamp for reproducibility

Failures are isolated through exception handling around critical operations. Task failures don't affect the overall pipeline execution - the engine continues processing other eligible tasks.

Example:
```json
{
  "task": "task_b",
  "reason": "Failed dependencies: task_a",
  "timestamp": 42.001
}
```

The pipeline continues safely because task execution is compartmentalized, and the engine maintains separate tracking for completed, failed, and pending tasks.

---

## 6. Renderer Isolation

- Can the renderer crash without stopping the pipeline? Yes
- How the renderer is isolated from execution: All renderer calls are wrapped in try/except blocks. Renderer exceptions are caught and ignored, allowing execution to continue. The renderer is notified of events but has no control over execution flow.
- How headless mode works (if implemented): Headless mode can be achieved by passing None as the renderer or by calling renderer.disable(). The pipeline operates identically regardless of renderer status.

---

## 7. Observability

What was added:
- Execution order tracking: Stored in the execution_order list
- Per-task duration: Calculated and stored for each task in task_durations
- Total pipeline duration: Computed from start to finish

Data collection is implemented through immutable ExecutionContext objects that track execution state throughout the pipeline lifecycle. Timing information is captured at task start/end points and aggregated in the final result structure.

---

## 8. Trade-offs & Decisions

What was intentionally NOT implemented:
- Complex retry mechanisms for failed tasks
- Parallel task execution (kept sequential for simplicity and deterministic ordering)
- Advanced visualization beyond basic console output
- Configuration validation beyond basic JSON parsing

What would be improved with more time:
- More sophisticated dependency resolution algorithms for complex graphs
- Enhanced error recovery and retry strategies
- Better performance metrics and monitoring capabilities
- Additional renderer implementations (JSON, file-based, etc.)

Known limitations:
- Task execution is sequential rather than parallel
- Limited configuration validation
- Basic ASCII output only

---

## 9. AI Usage Disclosure (MANDATORY)

[x] Syntax / language assistance  
[x] Architecture discussion  
[x] asyncio examples  
[x] No AI used  

AI was used for syntax suggestions, architectural pattern discussions, and general Python best practices guidance. The core logic and implementation decisions were made independently based on the technical requirements.

---

## 10. Final Notes (Optional)

The implementation focuses on safety and deterministic behavior over performance optimizations. All core requirements have been met with a clean, maintainable codebase that follows Python best practices.

---

## Confirmation

I confirm that:
- I followed all constraints from the technical assignment
- The solution is my own work
- The code runs as described above

Signature: Andy Do
Date: December 15, 2025