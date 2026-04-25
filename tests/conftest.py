"""
Pytest configuration for UniShare test suite.

Adds the project root to sys.path so test modules can
`from validators import ...` without any installation setup.
"""

import sys
import os

# Add the project root directory to the Python path
# This allows tests to import modules like `validators` directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))