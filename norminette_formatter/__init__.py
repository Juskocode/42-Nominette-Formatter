"""
42-Norminette-Formatter

A comprehensive norminette debugging and auto-correction tool for 42 School projects.
"""

__version__ = "1.0.0"
__author__ = "afreitas <afreitas@student.42.fr>"

from .core.scanner import NorminetteScanner
from .core.parser import ErrorParser
from .core.formatter import AutoFormatter
from .core.aggregator import FileAggregator

__all__ = [
    'NorminetteScanner',
    'ErrorParser', 
    'AutoFormatter',
    'FileAggregator'
]