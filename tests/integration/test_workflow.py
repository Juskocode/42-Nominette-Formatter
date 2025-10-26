"""
Integration tests for the complete norminette formatter workflow.

These tests verify that the scanner, parser, formatter, and aggregator
work together correctly in realistic scenarios.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from norminette_formatter.core.scanner import NorminetteScanner, NorminetteResult
from norminette_formatter.core.parser import ErrorParser
from norminette_formatter.core.formatter import AutoFormatter
from norminette_formatter.core.aggregator import FileAggregator, FileStatus


class TestCompleteWorkflow:
    """Test the complete workflow integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = NorminetteScanner()
        self.parser = ErrorParser()
        self.formatter = AutoFormatter(backup_enabled=False)
        self.aggregator = FileAggregator()
    
    def create_test_file(self, content: str, suffix: str = '.c') -> str:
        """Create a temporary test file with given content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    
    def test_scan_parse_aggregate_workflow(self):
        """Test the scan -> parse -> aggregate workflow."""
        # Create test files with different error types
        good_file_content = '''/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   good.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: student <student@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 10:00:00 by student          #+#    #+#             */
/*   Updated: 2024/01/01 10:00:00 by student         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>

int main(void)
{
    printf("Hello World\\n");
    return (0);
}
'''
        
        bad_file_content = '''#include <stdio.h>

int main(void){
    printf("This is a very long line that exceeds the 80 character limit and should trigger a norminette error");
    if(1 == 1)
    {
        printf("Hello World\\n");
    }
    return (0);
}
'''
        
        good_file = self.create_test_file(good_file_content)
        bad_file = self.create_test_file(bad_file_content)
        
        try:
            # Mock norminette results since we can't rely on actual norminette
            with patch.object(self.scanner, '_run_norminette') as mock_run:
                # Mock good file result
                mock_run.side_effect = [
                    (0, f"{good_file}: OK!", ""),
                    (1, f"{bad_file}:\nError: TOO_LONG_LINE (line: 4, col: 85): Line too long\nError: SPACE_AFTER_KW (line: 5, col: 2): Missing space after keyword", "")
                ]
                
                # Scan files
                good_result = self.scanner.scan_file(good_file)
                bad_result = self.scanner.scan_file(bad_file)
                
                # Verify scan results
                assert good_result.status == "OK"
                assert good_result.error_count == 0
                
                assert bad_result.status == "Error"
                assert bad_result.error_count == 2
                
                # Parse errors
                good_analyses = self.parser.analyze_file_errors(good_result.errors)
                bad_analyses = self.parser.analyze_file_errors(bad_result.errors)
                
                assert len(good_analyses) == 0
                assert len(bad_analyses) == 2
                
                # Verify error analysis
                line_error = next((a for a in bad_analyses if a.rule == 'TOO_LONG_LINE'), None)
                space_error = next((a for a in bad_analyses if a.rule == 'SPACE_AFTER_KW'), None)
                
                assert line_error is not None
                assert line_error.auto_fixable is True
                assert space_error is not None
                assert space_error.auto_fixable is True
                
                # Aggregate results
                self.aggregator.add_scan_result(good_result, good_analyses)
                self.aggregator.add_scan_result(bad_result, bad_analyses)
                
                # Verify aggregation
                summary = self.aggregator.generate_project_summary()
                assert summary.total_files == 2
                assert summary.ok_files == 1
                assert summary.error_files == 1
                assert summary.total_errors == 2
                assert summary.auto_fixable_errors == 2
                assert summary.success_rate == 50.0
                
        finally:
            # Clean up
            os.unlink(good_file)
            os.unlink(bad_file)
    
    def test_format_and_rescan_workflow(self):
        """Test the format -> rescan workflow."""
        # Create a file with auto-fixable errors
        content_with_errors = '''#include <stdio.h>

int main(void)
{
    if(1 == 1)  // Missing space after if
    {
        printf("Hello World\\n");
    }
    return (0);
}
'''
        
        test_file = self.create_test_file(content_with_errors)
        
        try:
            # Mock initial scan with errors
            with patch.object(self.scanner, '_run_norminette') as mock_run:
                mock_run.return_value = (1, f"{test_file}:\nError: SPACE_AFTER_KW (line: 5, col: 2): Missing space after keyword", "")
                
                # Initial scan
                initial_result = self.scanner.scan_file(test_file)
                initial_analyses = self.parser.analyze_file_errors(initial_result.errors)
                
                assert initial_result.error_count == 1
                assert len(initial_analyses) == 1
                assert initial_analyses[0].auto_fixable is True
                
                # Format the file
                format_result = self.formatter.format_file(test_file, initial_analyses)
                
                assert format_result.success is True
                assert format_result.changes_made > 0
                
                # Mock rescan after formatting (should be clean)
                mock_run.return_value = (0, f"{test_file}: OK!", "")
                
                # Rescan after formatting
                final_result = self.scanner.scan_file(test_file)
                final_analyses = self.parser.analyze_file_errors(final_result.errors)
                
                assert final_result.status == "OK"
                assert final_result.error_count == 0
                assert len(final_analyses) == 0
                
        finally:
            # Clean up
            os.unlink(test_file)
    
    def test_directory_scan_workflow(self):
        """Test scanning an entire directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple test files
            files_content = {
                'file1.c': '#include <stdio.h>\nint main(void) { return (0); }',
                'file2.c': '#include <stdio.h>\nint main(void){return (0);}',  # Missing spaces
                'file3.h': '#ifndef FILE3_H\n# define FILE3_H\nint func(void);\n#endif',
                'readme.txt': 'This is not a C file'  # Should be ignored
            }
            
            file_paths = {}
            for filename, content in files_content.items():
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
                file_paths[filename] = filepath
            
            # Mock norminette results
            with patch.object(self.scanner, '_run_norminette') as mock_run:
                def mock_norminette(filepath):
                    if 'file1.c' in filepath:
                        return (0, f"{filepath}: OK!", "")
                    elif 'file2.c' in filepath:
                        return (1, f"{filepath}:\nError: SPACE_AFTER_KW (line: 2, col: 15): Missing space", "")
                    elif 'file3.h' in filepath:
                        return (0, f"{filepath}: OK!", "")
                    else:
                        return (0, f"{filepath}: OK!", "")
                
                mock_run.side_effect = lambda fp: mock_norminette(fp)
                
                # Scan directory
                results = self.scanner.scan_directory(temp_dir, recursive=False)
                
                # Should find 3 C/H files (readme.txt ignored)
                assert len(results) == 3
                
                # Process results
                for result in results:
                    analyses = self.parser.analyze_file_errors(result.errors)
                    self.aggregator.add_scan_result(result, analyses)
                
                # Verify aggregation
                summary = self.aggregator.generate_project_summary()
                assert summary.total_files == 3
                assert summary.ok_files == 2
                assert summary.error_files == 1
                assert summary.total_errors == 1
    
    def test_filter_and_fix_workflow(self):
        """Test filtering files and applying fixes."""
        # Create multiple files with different error types
        files_data = [
            ('spacing_errors.c', 'SPACE_AFTER_KW'),
            ('line_length.c', 'TOO_LONG_LINE'),
            ('good_file.c', None)
        ]
        
        created_files = []
        
        try:
            # Create files and mock scan results
            with patch.object(self.scanner, '_run_norminette') as mock_run:
                def mock_norminette_for_file(filepath):
                    if 'spacing_errors.c' in filepath:
                        return (1, f"{filepath}:\nError: SPACE_AFTER_KW (line: 2, col: 5): Missing space", "")
                    elif 'line_length.c' in filepath:
                        return (1, f"{filepath}:\nError: TOO_LONG_LINE (line: 3, col: 85): Line too long", "")
                    else:
                        return (0, f"{filepath}: OK!", "")
                
                mock_run.side_effect = lambda fp: mock_norminette_for_file(fp)
                
                # Create and scan files
                for filename, error_type in files_data:
                    content = f"#include <stdio.h>\nint main(void) {{ return (0); }}"
                    filepath = self.create_test_file(content)
                    created_files.append(filepath)
                    
                    # Scan file
                    result = self.scanner.scan_file(filepath)
                    analyses = self.parser.analyze_file_errors(result.errors)
                    self.aggregator.add_scan_result(result, analyses)
                
                # Filter files with errors
                error_files = self.aggregator.filter_files(status=FileStatus.ERROR)
                assert len(error_files) == 2
                
                # Filter auto-fixable files
                auto_fixable_files = self.aggregator.filter_files(auto_fixable_only=True)
                assert len(auto_fixable_files) == 2
                
                # Get recommendations
                recommendations = self.aggregator.get_recommendations()
                assert len(recommendations) > 0
                assert any('auto-fix' in rec.lower() for rec in recommendations)
                
        finally:
            # Clean up
            for filepath in created_files:
                if os.path.exists(filepath):
                    os.unlink(filepath)
    
    def test_error_pattern_detection_workflow(self):
        """Test detection of error patterns across multiple files."""
        # Create files with consistent error patterns
        with patch.object(self.scanner, '_run_norminette') as mock_run:
            # Mock multiple spacing errors across files
            mock_run.side_effect = [
                (1, "file1.c:\nError: SPACE_AFTER_KW (line: 2, col: 5): Missing space\nError: SPACE_BEFORE_FUNC (line: 3, col: 1): Space before function", ""),
                (1, "file2.c:\nError: SPACE_AFTER_KW (line: 4, col: 8): Missing space\nError: TAB_REPLACE_SPACE (line: 5, col: 1): Tab instead of space", ""),
                (1, "file3.c:\nError: SPACE_REPLACE_TAB (line: 1, col: 1): Space instead of tab", "")
            ]
            
            created_files = []
            all_analyses = []
            
            try:
                # Create and process multiple files
                for i in range(3):
                    content = f"#include <stdio.h>\nint main{i}(void) {{ return (0); }}"
                    filepath = self.create_test_file(content)
                    created_files.append(filepath)
                    
                    result = self.scanner.scan_file(filepath)
                    analyses = self.parser.analyze_file_errors(result.errors)
                    all_analyses.extend(analyses)
                    self.aggregator.add_scan_result(result, analyses)
                
                # Detect patterns across all analyses
                patterns = self.parser.detect_error_patterns(all_analyses)
                
                # Should detect multiple spacing issues pattern
                assert 'multiple_spacing_issues' in patterns
                assert len(patterns['multiple_spacing_issues']) >= 3
                
                # Verify project-wide statistics
                summary = self.aggregator.generate_project_summary()
                assert summary.total_files == 3
                assert summary.error_files == 3
                assert summary.total_errors == 5  # Total errors across all files
                
            finally:
                # Clean up
                for filepath in created_files:
                    if os.path.exists(filepath):
                        os.unlink(filepath)


class TestComponentInteraction:
    """Test interactions between specific components."""
    
    def test_scanner_parser_integration(self):
        """Test scanner and parser working together."""
        scanner = NorminetteScanner()
        parser = ErrorParser()
        
        # Mock norminette output with complex errors
        mock_output = """test.c:
Error: TOO_LONG_LINE (line: 10, col: 95): Line is too long (95/80)
Error: SPACE_AFTER_KW (line: 15, col: 2): Missing space after keyword
Error: INDENT_BRANCH (line: 20, col: 1): Wrong indentation level
"""
        
        with patch.object(scanner, '_run_norminette') as mock_run:
            mock_run.return_value = (1, mock_output, "")
            
            # Scan file
            result = scanner.scan_file("test.c")
            
            # Parse errors
            analyses = parser.analyze_file_errors(result.errors)
            
            # Verify integration
            assert len(analyses) == 3
            assert all(hasattr(a, 'fix_suggestion') for a in analyses)
            assert all(hasattr(a, 'severity') for a in analyses)
            
            # Verify error types are properly classified
            error_types = {a.error_type for a in analyses}
            assert 'line_length' in error_types
            assert 'spacing' in error_types
            assert 'indentation' in error_types
    
    def test_parser_formatter_integration(self):
        """Test parser and formatter working together."""
        parser = ErrorParser()
        formatter = AutoFormatter(backup_enabled=False)
        
        # Create test file with fixable errors
        content = '''#include <stdio.h>

int main(void)
{
    if(1 == 1)
    {
        printf("Hello\\n");
    }
    return (0);
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(content)
            filepath = f.name
        
        try:
            # Create mock error analyses
            mock_errors = [
                {
                    'rule': 'SPACE_AFTER_KW',
                    'line': 5,
                    'column': 2,
                    'description': 'Missing space after keyword',
                    'type': 'spacing'
                }
            ]
            
            analyses = parser.analyze_file_errors(mock_errors)
            
            # Format file using analyses
            result = formatter.format_file(filepath, analyses)
            
            # Verify formatting worked
            assert result.success is True
            assert result.changes_made > 0
            
            # Verify file was actually modified
            with open(filepath, 'r') as f:
                formatted_content = f.read()
            
            assert 'if (' in formatted_content  # Space should be added
            
        finally:
            os.unlink(filepath)
    
    def test_aggregator_recommendations_integration(self):
        """Test aggregator generating appropriate recommendations."""
        aggregator = FileAggregator()
        parser = ErrorParser()
        
        # Create mock scan results with various error patterns
        mock_results = [
            # File with many auto-fixable errors
            NorminetteResult("easy_fix.c", "Error", [
                {'rule': 'SPACE_AFTER_KW', 'line': 1, 'column': 5, 'description': 'Missing space', 'type': 'spacing'},
                {'rule': 'BRACE_NEWLINE', 'line': 2, 'column': 10, 'description': 'Missing newline', 'type': 'braces'}
            ]),
            # File with complex errors
            NorminetteResult("complex.c", "Error", [
                {'rule': 'TOO_MANY_LINES', 'line': 1, 'column': 1, 'description': 'Too many lines (30/25)', 'type': 'line_length'},
                {'rule': 'TOO_MANY_PARAMS', 'line': 5, 'column': 1, 'description': 'Too many params (6/4)', 'type': 'function_params'}
            ]),
            # Good file
            NorminetteResult("good.c", "OK", [])
        ]
        
        # Process results
        for result in mock_results:
            analyses = parser.analyze_file_errors(result.errors)
            aggregator.add_scan_result(result, analyses)
        
        # Get recommendations
        recommendations = aggregator.get_recommendations()
        
        # Verify appropriate recommendations are generated
        assert len(recommendations) > 0
        
        # Should recommend auto-fixing
        auto_fix_recs = [r for r in recommendations if 'auto-fix' in r.lower()]
        assert len(auto_fix_recs) > 0
        
        # Should identify problematic files
        problematic_recs = [r for r in recommendations if 'problematic' in r.lower()]
        assert len(problematic_recs) > 0


if __name__ == '__main__':
    pytest.main([__file__])