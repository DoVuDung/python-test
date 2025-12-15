"""
Renderer for pipeline visualization
"""
import sys
from typing import Any


class ConsoleRenderer:
    def __init__(self):
        self.enabled = True
        self.fail_on_task = None  # For testing renderer isolation

    def task_started(self, task_name: str):
        """Called when a task starts"""
        if self.fail_on_task == task_name:
            raise Exception("Intentional renderer failure")
            
        if self.enabled:
            try:
                print(f"[STARTED] {task_name}")
                sys.stdout.flush()
            except Exception:
                # If rendering fails, disable renderer but don't crash pipeline
                self.enabled = False

    def task_completed(self, task_name: str):
        """Called when a task completes successfully"""
        if self.fail_on_task == task_name:
            raise Exception("Intentional renderer failure")
            
        if self.enabled:
            try:
                print(f"[COMPLETED] {task_name}")
                sys.stdout.flush()
            except Exception:
                # If rendering fails, disable renderer but don't crash pipeline
                self.enabled = False

    def task_failed(self, task_name: str):
        """Called when a task fails"""
        if self.fail_on_task == task_name:
            raise Exception("Intentional renderer failure")
            
        if self.enabled:
            try:
                print(f"[FAILED] {task_name}")
                sys.stdout.flush()
            except Exception:
                # If rendering fails, disable renderer but don't crash pipeline
                self.enabled = False

    def disable(self):
        """Disable rendering"""
        self.enabled = False