#!/usr/bin/env python3
"""
Entry point for the pipeline engine.
"""

from pipeline.engine import PipelineEngine
from pipeline.renderer import ConsoleRenderer
import json


def main():
    # Load pipeline configuration
    try:
        with open('pipeline_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: pipeline_config.json not found")
        return 1
    
    # Create engine and renderer
    engine = PipelineEngine()
    renderer = ConsoleRenderer()
    
    # Run pipeline
    result = engine.run(config, renderer)
    
    # Save result
    with open('result.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("Pipeline completed. Results saved to result.json")
    return 0


if __name__ == "__main__":
    exit(main())