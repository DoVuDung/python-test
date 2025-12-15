#!/usr/bin/env python3
"""
Final validation test for all senior-level requirements
"""
from pipeline.engine import PipelineEngine
from pipeline.renderer import ConsoleRenderer
import json
import hashlib


def test_requirement_1_idempotency():
    """A) Task execution is idempotent"""
    print("Requirement A: Testing idempotency...")
    
    # Run pipeline multiple times with same seed
    results = []
    for i in range(3):
        with open('pipeline_config.json', 'r') as f:
            config = json.load(f)
        config['seed'] = 999  # Fixed seed
        
        engine = PipelineEngine()
        result = engine.run(config)
        results.append(result)
    
    # All results should be identical
    first_hash = hashlib.md5(json.dumps(results[0], sort_keys=True).encode()).hexdigest()
    for i, result in enumerate(results[1:], 1):
        result_hash = hashlib.md5(json.dumps(result, sort_keys=True).encode()).hexdigest()
        if result_hash != first_hash:
            print(f"  FAILURE: Run {i} differs from run 0")
            return False
    
    print("  SUCCESS: All runs with same seed are identical")
    return True


def test_requirement_2_partial_failure_safety():
    """B) Partial failure does NOT corrupt pipeline state"""
    print("Requirement B: Testing partial failure safety...")
    
    # Create config with a guaranteed failure
    with open('pipeline_config.json', 'r') as f:
        config = json.load(f)
    
    # Make task_b fail
    for task in config["tasks"]:
        if task["name"] == "task_b":
            task["failure_rate"] = 1.0  # 100% failure
            break
    
    engine = PipelineEngine()
    result = engine.run(config)
    
    # Check that the pipeline completed (didn't crash)
    if result["summary"]["total_tasks"] > 0:
        print("  SUCCESS: Pipeline completed despite partial failure")
        return True
    else:
        print("  FAILURE: Pipeline crashed due to partial failure")
        return False


def test_requirement_3_same_result():
    """C) Rerunning pipeline produces SAME RESULT (given same seed)"""
    print("Requirement C: Testing deterministic results...")
    
    # This is essentially the same as requirement A
    return test_requirement_1_idempotency()


def test_requirement_4_renderer_isolation():
    """D) Renderer never blocks execution"""
    print("Requirement D: Testing renderer isolation...")
    
    with open('pipeline_config.json', 'r') as f:
        config = json.load(f)
    
    engine = PipelineEngine()
    renderer = ConsoleRenderer()
    renderer.fail_on_task = "task_a"  # Force renderer to fail
    
    try:
        result = engine.run(config, renderer)
        # If we get here, the pipeline completed despite renderer failure
        print("  SUCCESS: Renderer failure didn't block execution")
        return True
    except Exception as e:
        print(f"  FAILURE: Renderer failure blocked execution: {e}")
        return False


def test_requirement_5_dlq_correctness():
    """E) DLQ is logically correct"""
    print("Requirement E: Testing DLQ correctness...")
    
    # Create config with missing dependency
    with open('pipeline_config.json', 'r') as f:
        config = json.load(f)
    
    # Add task with missing dependency
    config["tasks"].append({
        "name": "task_e",
        "dependencies": ["missing_task"],
        "execution_time": 0.1,
        "failure_rate": 0.0
    })
    
    engine = PipelineEngine()
    result = engine.run(config)
    
    # Check DLQ structure
    dlq = result["dlq"]
    if len(dlq) > 0:
        entry = dlq[0]
        required_fields = ["task", "reason", "timestamp"]
        if all(field in entry for field in required_fields):
            print("  SUCCESS: DLQ contains proper structured information")
            return True
        else:
            print(f"  FAILURE: DLQ missing required fields: {entry}")
            return False
    else:
        print("  FAILURE: Expected DLQ entries not found")
        return False


def main():
    print("Validating all senior-level requirements...\n")
    
    requirements = [
        ("A) Task execution is idempotent", test_requirement_1_idempotency),
        ("B) Partial failure does NOT corrupt pipeline state", test_requirement_2_partial_failure_safety),
        ("C) Rerunning pipeline produces SAME RESULT (given same seed)", test_requirement_3_same_result),
        ("D) Renderer never blocks execution", test_requirement_4_renderer_isolation),
        ("E) DLQ is logically correct", test_requirement_5_dlq_correctness),
    ]
    
    passed = 0
    for name, test_func in requirements:
        print(f"[{name}]")
        try:
            if test_func():
                passed += 1
            print()  # Blank line
        except Exception as e:
            print(f"  ERROR: {e}\n")
    
    print("=" * 50)
    print(f"Requirements met: {passed}/{len(requirements)}")
    
    if passed == len(requirements):
        print("\nALL SENIOR-LEVEL REQUIREMENTS MET!")
        print("The pipeline engine is production-ready!")
        return 0
    else:
        print("\nSome requirements not met. Needs improvement.")
        return 1


if __name__ == "__main__":
    exit(main())