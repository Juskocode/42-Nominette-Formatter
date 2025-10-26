"""
Unit tests for the norminette scanner module.

These tests cover:
- Norminette output parsing
- Error classification
- File scanning functionality
- Edge cases and error handling
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from norminette_formatter.core.scanner import NorminetteScanner, NorminetteResult


class TestNorminetteResult:
    """Test the NorminetteResult class."""
    
    def test_init_with_no_errors(self):
        """Test NorminetteResult initialization with no errors."""
        result = NorminetteResult("test.c", "OK")
        
        assert result.filepath == "test.c"
        assert result.status == "OK"
        assert result.errors == []
        assert result.error_count == 0
    
    def test_init_with_errors(self):
        """Test NorminetteResult initialization with errors."""
        errors = [
            {'rule': 'TOO_LONG_LINE', 'line': 10, 'column': 85, 'description': 'Line too long'},
            {'rule': 'SPACE_BEFORE_FUNC', 'line': 15, 'column': 5, 'description': 'Space before function'}
        ]
        result = NorminetteResult("test.c", "Error", errors)
        
        assert result.filepath == "test.c"
        assert result.status == "Error"
        assert result.errors == errors
        assert result.error_count == 2
    
    def test_repr(self):
        """Test string representation of NorminetteResult."""
        result = NorminetteResult("test.c", "OK")
        repr_str = repr(result)
        
        assert "test.c" in repr_str
        assert "OK" in repr_str
        assert "errors=0" in repr_str


class TestNorminetteScanner:
    """Test the NorminetteScanner class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = NorminetteScanner()
    
    def test_init(self):
        """Test scanner initialization."""
        scanner = NorminetteScanner()
        assert scanner.norminette_path == "norminette"
        assert scanner.results == []
        
        custom_scanner = NorminetteScanner("custom_norminette")
        assert custom_scanner.norminette_path == "custom_norminette"
    
    @patch('subprocess.run')
    def test_check_norminette_available_success(self, mock_run):
        """Test successful norminette availability check."""
        mock_run.return_value.returncode = 0
        
        result = self.scanner._check_norminette_available()
        
        assert result is True
        mock_run.assert_called_once_with(
            ["norminette", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_check_norminette_available_failure(self, mock_run):
        """Test failed norminette availability check."""
        mock_run.return_value.returncode = 1
        
        result = self.scanner._check_norminette_available()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_check_norminette_available_timeout(self, mock_run):
        """Test norminette availability check timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("norminette", 10)
        
        result = self.scanner._check_norminette_available()
        
        assert result is False
    
    @patch('subprocess.run')
    def test_run_norminette_success(self, mock_run):
        """Test successful norminette execution."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "test.c: OK!"
        mock_run.return_value.stderr = ""
        
        returncode, stdout, stderr = self.scanner._run_norminette("test.c")
        
        assert returncode == 0
        assert stdout == "test.c: OK!"
        assert stderr == ""
        mock_run.assert_called_once_with(
            ["norminette", "test.c"],
            capture_output=True,
            text=True,
            timeout=30
        )
    
    @patch('subprocess.run')
    def test_run_norminette_timeout(self, mock_run):
        """Test norminette execution timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("norminette", 30)
        
        returncode, stdout, stderr = self.scanner._run_norminette("test.c")
        
        assert returncode == -1
        assert stdout == ""
        assert stderr == "Timeout"
    
    def test_parse_norminette_output_ok(self):
        """Test parsing OK norminette output."""
        stdout = "test.c: OK!"
        stderr = ""
        
        result = self.scanner._parse_norminette_output("test.c", stdout, stderr)
        
        assert result.filepath == "test.c"
        assert result.status == "OK"
        assert result.errors == []
    
    def test_parse_norminette_output_with_errors(self):
        """Test parsing norminette output with errors."""
        stdout = """test.c:
Error: TOO_LONG_LINE (line: 10, col: 85): Line is too long (85/80)
Error: SPACE_BEFORE_FUNC (line: 15, col: 5): Space before function name"""
        stderr = ""
        
        result = self.scanner._parse_norminette_output("test.c", stdout, stderr)
        
        assert result.filepath == "test.c"
        assert result.status == "Error"
        assert len(result.errors) == 2
        
        error1 = result.errors[0]
        assert error1['rule'] == 'TOO_LONG_LINE'
        assert error1['line'] == 10
        assert error1['column'] == 85
        assert error1['type'] == 'line_length'
        
        error2 = result.errors[1]
        assert error2['rule'] == 'SPACE_BEFORE_FUNC'
        assert error2['line'] == 15
        assert error2['column'] == 5
        assert error2['type'] == 'spacing'
    
    def test_parse_norminette_output_malformed_error(self):
        """Test parsing malformed norminette error output."""
        stdout = """test.c:
Error: Some malformed error message"""
        stderr = ""
        
        result = self.scanner._parse_norminette_output("test.c", stdout, stderr)
        
        assert result.filepath == "test.c"
        assert result.status == "Error"
        assert len(result.errors) == 1
        
        error = result.errors[0]
        assert error['rule'] == 'UNKNOWN'
        assert error['line'] == 0
        assert error['column'] == 0
        assert error['type'] == 'unknown'
    
    def test_classify_error_type(self):
        """Test error type classification."""
        test_cases = [
            ('TOO_LONG_LINE', 'line_length'),
            ('TOO_MANY_LINES', 'line_length'),
            ('TOO_MANY_FUNCS', 'function_count'),
            ('TOO_MANY_PARAMS', 'function_params'),
            ('SPACE_BEFORE_FUNC', 'spacing'),
            ('INDENT_BRANCH', 'indentation'),
            ('HEADER_MISSING', 'header'),
            ('BRACE_NEWLINE', 'braces'),
            ('VAR_DECL_START_FUNC', 'variables'),
            ('UNKNOWN_RULE', 'other')
        ]
        
        for rule_name, expected_type in test_cases:
            result = self.scanner._classify_error_type(rule_name)
            assert result == expected_type, f"Rule {rule_name} should be classified as {expected_type}"
    
    @patch.object(NorminetteScanner, '_check_norminette_available')
    @patch.object(NorminetteScanner, '_run_norminette')
    def test_scan_file_success(self, mock_run, mock_check):
        """Test successful file scanning."""
        mock_check.return_value = True
        mock_run.return_value = (0, "test.c: OK!", "")
        
        with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as tmp:
            tmp.write(b"int main() { return 0; }")
            tmp_path = tmp.name
        
        try:
            result = self.scanner.scan_file(tmp_path)
            
            assert result.filepath == tmp_path
            assert result.status == "OK"
            assert result.errors == []
        finally:
            os.unlink(tmp_path)
    
    def test_scan_file_not_found(self):
        """Test scanning non-existent file."""
        result = self.scanner.scan_file("nonexistent.c")
        
        assert result.filepath == "nonexistent.c"
        assert result.status == "Error"
        assert len(result.errors) == 1
        assert result.errors[0]['rule'] == 'FILE_NOT_FOUND'
    
    def test_scan_file_non_c_file(self):
        """Test scanning non-C file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b"This is not a C file")
            tmp_path = tmp.name
        
        try:
            result = self.scanner.scan_file(tmp_path)
            
            assert result.filepath == tmp_path
            assert result.status == "OK"
            assert result.errors == []
        finally:
            os.unlink(tmp_path)
    
    @patch.object(NorminetteScanner, '_check_norminette_available')
    def test_scan_file_norminette_not_available(self, mock_check):
        """Test scanning when norminette is not available."""
        mock_check.return_value = False
        
        with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as tmp:
            tmp.write(b"int main() { return 0; }")
            tmp_path = tmp.name
        
        try:
            result = self.scanner.scan_file(tmp_path)
            
            assert result.filepath == tmp_path
            assert result.status == "Error"
            assert len(result.errors) == 1
            assert result.errors[0]['rule'] == 'NORMINETTE_NOT_FOUND'
        finally:
            os.unlink(tmp_path)
    
    @patch.object(NorminetteScanner, 'scan_file')
    def test_scan_directory(self, mock_scan_file):
        """Test directory scanning."""
        # Create mock results
        mock_scan_file.side_effect = [
            NorminetteResult("file1.c", "OK"),
            NorminetteResult("file2.c", "Error", [{'rule': 'TEST_ERROR'}]),
            NorminetteResult("file3.h", "OK")
        ]
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            (Path(tmp_dir) / "file1.c").touch()
            (Path(tmp_dir) / "file2.c").touch()
            (Path(tmp_dir) / "file3.h").touch()
            (Path(tmp_dir) / "readme.txt").touch()  # Should be ignored
            
            results = self.scanner.scan_directory(tmp_dir, recursive=False)
            
            assert len(results) == 3
            assert mock_scan_file.call_count == 3
            
            # Check that results are stored
            assert len(self.scanner.results) == 3
    
    def test_scan_directory_not_found(self):
        """Test scanning non-existent directory."""
        results = self.scanner.scan_directory("nonexistent_dir")
        
        assert results == []
    
    def test_get_summary_empty(self):
        """Test getting summary with no results."""
        summary = self.scanner.get_summary()
        
        assert summary == {}
    
    def test_get_summary_with_results(self):
        """Test getting summary with results."""
        # Add mock results
        self.scanner.results = [
            NorminetteResult("file1.c", "OK"),
            NorminetteResult("file2.c", "Error", [
                {'rule': 'TOO_LONG_LINE', 'type': 'line_length'},
                {'rule': 'SPACE_BEFORE_FUNC', 'type': 'spacing'}
            ]),
            NorminetteResult("file3.c", "Error", [
                {'rule': 'TOO_LONG_LINE', 'type': 'line_length'}
            ])
        ]
        
        summary = self.scanner.get_summary()
        
        assert summary['total_files'] == 3
        assert summary['ok_files'] == 1
        assert summary['error_files'] == 2
        assert summary['total_errors'] == 3
        assert summary['success_rate'] == pytest.approx(33.33, rel=1e-2)
        assert summary['error_types']['line_length'] == 2
        assert summary['error_types']['spacing'] == 1
    
    def test_filter_results(self):
        """Test filtering results."""
        # Add mock results
        self.scanner.results = [
            NorminetteResult("file1.c", "OK"),
            NorminetteResult("file2.c", "Error", [
                {'rule': 'TOO_LONG_LINE', 'type': 'line_length'}
            ]),
            NorminetteResult("file3.c", "Error", [
                {'rule': 'SPACE_BEFORE_FUNC', 'type': 'spacing'}
            ])
        ]
        
        # Filter by status
        ok_results = self.scanner.filter_results(status="OK")
        assert len(ok_results) == 1
        assert ok_results[0].status == "OK"
        
        error_results = self.scanner.filter_results(status="Error")
        assert len(error_results) == 2
        
        # Filter by error type
        line_length_results = self.scanner.filter_results(error_type="line_length")
        assert len(line_length_results) == 1
        assert any(e['type'] == 'line_length' for e in line_length_results[0].errors)
        
        # Combined filters
        combined_results = self.scanner.filter_results(status="Error", error_type="spacing")
        assert len(combined_results) == 1
        assert any(e['type'] == 'spacing' for e in combined_results[0].errors)


# Import subprocess for the timeout test
import subprocess

if __name__ == '__main__':
    pytest.main([__file__])