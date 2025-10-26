"""
Norminette Scanner Module

This module provides functionality to scan C files using the norminette tool
and capture error information for further processing.
"""

import subprocess
import os
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class NorminetteResult:
    """Represents the result of a norminette scan on a single file."""
    
    def __init__(self, filepath: str, status: str, errors: List[Dict] = None):
        self.filepath = filepath
        self.status = status  # 'OK' or 'Error'
        self.errors = errors or []
        self.error_count = len(self.errors)
    
    def __repr__(self):
        return f"NorminetteResult(filepath='{self.filepath}', status='{self.status}', errors={self.error_count})"


class NorminetteScanner:
    """
    Scanner class for running norminette on C files and parsing results.
    
    This class provides methods to:
    - Scan individual files or entire directories
    - Parse norminette output into structured data
    - Filter results by status or error type
    - Generate summary statistics
    """
    
    def __init__(self, norminette_path: str = "norminette"):
        """
        Initialize the scanner.
        
        Args:
            norminette_path: Path to the norminette executable
        """
        self.norminette_path = norminette_path
        self.results: List[NorminetteResult] = []
        
    def _check_norminette_available(self) -> bool:
        """Check if norminette is available in the system."""
        try:
            result = subprocess.run(
                [self.norminette_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _run_norminette(self, filepath: str) -> Tuple[int, str, str]:
        """
        Run norminette on a single file.
        
        Args:
            filepath: Path to the C file to scan
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                [self.norminette_path, filepath],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Norminette timeout for file: {filepath}")
            return -1, "", "Timeout"
        except Exception as e:
            logger.error(f"Error running norminette on {filepath}: {e}")
            return -1, "", str(e)
    
    def _parse_norminette_output(self, filepath: str, stdout: str, stderr: str) -> NorminetteResult:
        """
        Parse norminette output into structured data.
        
        Args:
            filepath: Path to the scanned file
            stdout: Standard output from norminette
            stderr: Standard error from norminette
            
        Returns:
            NorminetteResult object
        """
        if "OK!" in stdout:
            return NorminetteResult(filepath, "OK")
        
        errors = []
        
        # Parse error lines - norminette format: "Error: RULE_NAME (line:col): description"
        error_pattern = r'Error:\s+(\w+)\s+\(line:\s*(\d+),\s*col:\s*(\d+)\):\s*(.*)'
        
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith('Error:'):
                match = re.match(error_pattern, line)
                if match:
                    rule_name, line_num, col_num, description = match.groups()
                    errors.append({
                        'rule': rule_name,
                        'line': int(line_num),
                        'column': int(col_num),
                        'description': description.strip(),
                        'type': self._classify_error_type(rule_name)
                    })
                else:
                    # Fallback parsing for different norminette output formats
                    errors.append({
                        'rule': 'UNKNOWN',
                        'line': 0,
                        'column': 0,
                        'description': line,
                        'type': 'unknown'
                    })
        
        status = "Error" if errors else "OK"
        return NorminetteResult(filepath, status, errors)
    
    def _classify_error_type(self, rule_name: str) -> str:
        """
        Classify error type based on rule name.
        
        Args:
            rule_name: The norminette rule name
            
        Returns:
            Error type category
        """
        type_mapping = {
            'TOO_MANY_LINES': 'line_length',
            'TOO_LONG_LINE': 'line_length',
            'TOO_MANY_FUNCS': 'function_count',
            'TOO_MANY_PARAMS': 'function_params',
            'SPACE_BEFORE_FUNC': 'spacing',
            'SPACE_AFTER_KW': 'spacing',
            'INDENT_BRANCH': 'indentation',
            'INDENT_MULT_BRANCH': 'indentation',
            'WRONG_SCOPE_COMMENT': 'comments',
            'MISSING_IDENTIFIER': 'header',
            'HEADER_MISSING': 'header',
            'BRACE_NEWLINE': 'braces',
            'BRACE_SHOULD_EOL': 'braces',
            'VAR_DECL_START_FUNC': 'variables',
            'DECL_ASSIGN_LINE': 'variables'
        }
        
        return type_mapping.get(rule_name, 'other')
    
    def scan_file(self, filepath: str) -> NorminetteResult:
        """
        Scan a single C file.
        
        Args:
            filepath: Path to the C file
            
        Returns:
            NorminetteResult object
        """
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return NorminetteResult(filepath, "Error", [{'rule': 'FILE_NOT_FOUND', 'description': 'File not found'}])
        
        if not filepath.endswith(('.c', '.h')):
            logger.warning(f"Skipping non-C file: {filepath}")
            return NorminetteResult(filepath, "OK")
        
        if not self._check_norminette_available():
            logger.error("Norminette not available")
            return NorminetteResult(filepath, "Error", [{'rule': 'NORMINETTE_NOT_FOUND', 'description': 'Norminette not available'}])
        
        return_code, stdout, stderr = self._run_norminette(filepath)
        result = self._parse_norminette_output(filepath, stdout, stderr)
        
        return result
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[NorminetteResult]:
        """
        Scan all C files in a directory.
        
        Args:
            directory: Path to the directory
            recursive: Whether to scan subdirectories
            
        Returns:
            List of NorminetteResult objects
        """
        results = []
        path = Path(directory)
        
        if not path.exists():
            logger.error(f"Directory not found: {directory}")
            return results
        
        # Find all C files
        pattern = "**/*.c" if recursive else "*.c"
        c_files = list(path.glob(pattern))
        
        pattern = "**/*.h" if recursive else "*.h"
        h_files = list(path.glob(pattern))
        
        all_files = c_files + h_files
        
        logger.info(f"Found {len(all_files)} C/H files to scan")
        
        for file_path in all_files:
            result = self.scan_file(str(file_path))
            results.append(result)
        
        self.results = results
        return results
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics of scan results.
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}
        
        total_files = len(self.results)
        ok_files = len([r for r in self.results if r.status == "OK"])
        error_files = total_files - ok_files
        total_errors = sum(r.error_count for r in self.results)
        
        # Error type breakdown
        error_types = {}
        for result in self.results:
            for error in result.errors:
                error_type = error.get('type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            'total_files': total_files,
            'ok_files': ok_files,
            'error_files': error_files,
            'total_errors': total_errors,
            'error_types': error_types,
            'success_rate': (ok_files / total_files * 100) if total_files > 0 else 0
        }
    
    def filter_results(self, status: Optional[str] = None, error_type: Optional[str] = None) -> List[NorminetteResult]:
        """
        Filter scan results by status or error type.
        
        Args:
            status: Filter by status ('OK' or 'Error')
            error_type: Filter by error type
            
        Returns:
            Filtered list of NorminetteResult objects
        """
        filtered = self.results
        
        if status:
            filtered = [r for r in filtered if r.status == status]
        
        if error_type:
            filtered = [r for r in filtered if any(e.get('type') == error_type for e in r.errors)]
        
        return filtered