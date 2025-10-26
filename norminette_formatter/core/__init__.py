"""
Core modules for norminette error detection, parsing, and correction.
"""

from .scanner import NorminetteScanner
from .parser import ErrorParser
from .formatter import AutoFormatter
from .aggregator import FileAggregator

__all__ = [
    'NorminetteScanner',
    'ErrorParser',
    'AutoFormatter', 
    'FileAggregator'
]