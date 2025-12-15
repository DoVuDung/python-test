"""
Pipeline Engine Implementation - Production Grade
"""
import time
import random
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    task_name: str
    status: TaskStatus
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class Task:
    name: str
    dependencies: List[str]
    execution_time: float
    failure_rate: float = 0.0
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class ExecutionContext:
    """Immutable context for a pipeline execution"""
    seed: int
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    dlq: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_task_completed(self, task_name: str) -> bool:
        """Check if a task is completed successfully"""
        result = self.task_results.get(task_name)
        return result is not None and result.status == TaskStatus.COMPLETED
    
    def is_task_failed(self, task_name: str) -> bool:
        """Check if a task has failed"""
        result = self.task_results.get(task_name)
        return result is not None and result.status == TaskStatus.FAILED
    
    def can_execute_task(self, task: Task) -> bool:
        """Check if all dependencies are met for a task"""
        for dep in task.dependencies:
            # Dependency must exist and be completed successfully
            if dep not in self.task_results or not self.is_task_completed(dep):
                return False
        return True
    
    def clone(self) -> 'ExecutionContext':
        """Create a copy of the context"""
        return ExecutionContext(
            seed=self.seed,
            task_results=self.task_results.copy(),
            execution_order=self.execution_order.copy(),
            dlq=self.dlq.copy()
        )


class DeterministicRandom:
    """Deterministic random number generator"""
    
    def __init__(self, seed: int):
        self.seed = seed
        self.states: Dict[str, random.Random] = {}
    
    def get_rng(self, context: str) -> random.Random:
        """Get a deterministic random generator for a specific context"""
        if context not in self.states:
            # Create a new RNG with a seed derived from the main seed and context
            context_seed = (self.seed + hash(context)) % (2**32)
            self.states[context] = random.Random(context_seed)
        return self.states[context]


class DLQSystem:
    """Dead Letter Queue System"""
    
    def __init__(self, seed: int):
        self.failures: List[Dict[str, Any]] = []
        self.seed = seed
        self.counter = 0
    
    def add_failure(self, task_name: str, reason: str, context: Optional[Dict[str, Any]] = None):
        """Add a failure to the DLQ"""
        # Use deterministic "timestamp" based on seed and counter
        deterministic_timestamp = self.seed + self.counter * 0.001
        self.counter += 1
        
        failure_record = {
            "task": task_name,
            "reason": reason,
            "timestamp": deterministic_timestamp,
        }
        if context:
            failure_record["context"] = context
        self.failures.append(failure_record)
    
    def get_failures(self) -> List[Dict[str, Any]]:
        """Get all failures"""
        return self.failures.copy()


class PipelineEngine:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.dlq_system: Optional[DLQSystem] = None
        self.random_generator: Optional[DeterministicRandom] = None

    def add_task(self, task: Task):
        """Add a task to the pipeline"""
        self.tasks[task.name] = task

    def run(self, config: Dict[str, Any], renderer=None) -> Dict[str, Any]:
        """Run the pipeline with the given configuration"""
        start_time = 0.0  # Use deterministic start time
        
        # Initialize deterministic random generator
        seed = config.get('seed', 42)
        self.random_generator = DeterministicRandom(seed)
        self.dlq_system = DLQSystem(seed)  # Deterministic DLQ
        
        # Parse tasks from config
        self._parse_config(config)
        
        # Create initial execution context
        context = ExecutionContext(seed=seed)
        
        # Execute tasks in dependency order
        final_context = self._execute_tasks(context, renderer)
        
        end_time = len(final_context.execution_order) * 0.1  # Deterministic duration
        
        # Return results
        return self._generate_result(final_context, end_time - start_time)

    def _parse_config(self, config: Dict[str, Any]):
        """Parse tasks from configuration"""
        for task_config in config.get('tasks', []):
            task = Task(
                name=task_config['name'],
                dependencies=task_config.get('dependencies', []),
                execution_time=task_config.get('execution_time', 1.0),
                failure_rate=task_config.get('failure_rate', 0.0)
            )
            self.add_task(task)

    def _execute_tasks(self, context: ExecutionContext, renderer) -> ExecutionContext:
        """Execute tasks respecting dependencies in a deterministic way"""
        # Work with a copy of the context to ensure immutability
        current_context = context.clone()
        
        # Get tasks that haven't been processed yet
        remaining_tasks = set(self.tasks.keys())
        processed_tasks = set()
        
        # Continue until all tasks are processed or we reach a deadlock
        while remaining_tasks:
            # Find tasks that can be executed now (dependencies satisfied)
            executable_tasks = []
            
            for task_name in sorted(remaining_tasks):  # Sort for deterministic order
                task = self.tasks[task_name]
                
                # Check if all dependencies are met
                can_execute = True
                missing_deps = []
                failed_deps = []
                
                for dep in task.dependencies:
                    if dep not in self.tasks:
                        # Missing dependency
                        missing_deps.append(dep)
                        can_execute = False
                    elif not current_context.is_task_completed(dep):
                        if current_context.is_task_failed(dep):
                            failed_deps.append(dep)
                        can_execute = False
                
                # Handle dependency issues
                if missing_deps:
                    self.dlq_system.add_failure(
                        task_name, 
                        f"Missing dependencies: {', '.join(missing_deps)}"
                    )
                    processed_tasks.add(task_name)
                    remaining_tasks.remove(task_name)
                    continue
                    
                if failed_deps:
                    self.dlq_system.add_failure(
                        task_name, 
                        f"Failed dependencies: {', '.join(failed_deps)}"
                    )
                    processed_tasks.add(task_name)
                    remaining_tasks.remove(task_name)
                    continue
                
                if can_execute:
                    executable_tasks.append(task_name)
            
            # If no tasks can be executed, we have a deadlock
            if not executable_tasks:
                # Move all remaining tasks to DLQ
                for task_name in sorted(remaining_tasks):  # Sort for deterministic order
                    self.dlq_system.add_failure(
                        task_name, 
                        "Circular dependency or unresolvable dependencies"
                    )
                    processed_tasks.add(task_name)
                break
            
            # Execute tasks in deterministic order
            for task_name in sorted(executable_tasks):  # Sort for deterministic order
                task = self.tasks[task_name]
                processed_tasks.add(task_name)
                remaining_tasks.remove(task_name)
                
                # Notify renderer (isolated from execution)
                if renderer:
                    try:
                        renderer.task_started(task_name)
                    except Exception:
                        # Renderer failure doesn't affect pipeline
                        pass
                
                # Execute task and get result
                task_result = self._execute_task(task, current_context)
                
                # Update context with task result
                current_context.task_results[task_name] = task_result
                current_context.execution_order.append(task_name)
                
                # Notify renderer (isolated from execution)
                if renderer:
                    try:
                        if task_result.status == TaskStatus.COMPLETED:
                            renderer.task_completed(task_name)
                        else:
                            renderer.task_failed(task_name)
                    except Exception:
                        # Renderer failure doesn't affect pipeline
                        pass
        
        # Add DLQ failures to context
        current_context.dlq = self.dlq_system.get_failures()
        return current_context

    def _execute_task(self, task: Task, context: ExecutionContext) -> TaskResult:
        """Execute a single task and return its result"""
        result = TaskResult(task_name=task.name, status=TaskStatus.RUNNING)
        result.start_time = 0.0  # Deterministic start time
        
        try:
            # Get deterministic random generator for this task
            rng = self.random_generator.get_rng(f"{context.seed}:{task.name}")
            
            # Determine if task succeeds based on failure rate (this is deterministic now)
            success = rng.random() > task.failure_rate
            
            result.end_time = result.start_time + task.execution_time  # Deterministic end time
            result.duration = task.execution_time  # Deterministic duration
            result.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            
            if not success:
                result.error = "Task failed due to configured failure rate"
                
        except Exception as e:
            result.end_time = result.start_time + task.execution_time
            result.duration = task.execution_time
            result.status = TaskStatus.FAILED
            result.error = str(e)
        
        return result

    def _generate_result(self, context: ExecutionContext, total_duration: float) -> Dict[str, Any]:
        """Generate the final result"""
        completed_tasks = [
            name for name, result in context.task_results.items() 
            if result.status == TaskStatus.COMPLETED
        ]
        failed_tasks = [
            name for name, result in context.task_results.items() 
            if result.status == TaskStatus.FAILED
        ]
        
        # Calculate per-task durations
        task_durations = {}
        for name, result in context.task_results.items():
            task_durations[name] = result.duration
        
        return {
            "summary": {
                "total_tasks": len(self.tasks),
                "completed_tasks": len(completed_tasks),
                "failed_tasks": len(failed_tasks),
                "dlq_count": len(context.dlq),
                "total_duration": total_duration
            },
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "dlq": context.dlq,
            "execution_order": context.execution_order,
            "task_durations": task_durations
        }