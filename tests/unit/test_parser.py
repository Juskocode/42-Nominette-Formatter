"""
Unit tests for the norminette parser module.

These tests cover:
- Error analysis and classification
- Fix suggestion generation
- Error prioritization and grouping
- Pattern detection
"""

import pytest
from unittest.mock import Mock, patch
from norminette_formatter.core.parser import (
    ErrorParser, ErrorAnalysis, ErrorSeverity, FixComplexity
)


class TestErrorParser:
    """Test the ErrorParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ErrorParser()
    
    def test_init(self):
        """Test parser initialization."""
        assert self.parser.error_patterns is not None
        assert self.parser.fix_templates is not None
        assert len(self.parser.error_patterns) > 0
        assert len(self.parser.fix_templates) > 0
    
    def test_analyze_error_basic(self):
        """Test basic error analysis."""
        error = {
            'rule': 'TOO_LONG_LINE',
            'line': 10,
            'column': 85,
            'description': 'Line is too long (85/80)',
            'type': 'line_length'
        }
        
        analysis = self.parser.analyze_error(error)
        
        assert isinstance(analysis, ErrorAnalysis)
        assert analysis.rule == 'TOO_LONG_LINE'
        assert analysis.line == 10
        assert analysis.column == 85
        assert analysis.severity == ErrorSeverity.MEDIUM
        assert analysis.auto_fixable is True
        assert 'reduce by 5 characters' in analysis.fix_suggestion
    
    def test_analyze_error_unknown_rule(self):
        """Test analysis of unknown error rule."""
        error = {
            'rule': 'UNKNOWN_RULE',
            'line': 5,
            'column': 10,
            'description': 'Unknown error',
            'type': 'unknown'
        }
        
        analysis = self.parser.analyze_error(error)
        
        assert analysis.rule == 'UNKNOWN_RULE'
        assert analysis.severity == ErrorSeverity.MEDIUM
        assert analysis.fix_complexity == FixComplexity.SIMPLE
        assert analysis.auto_fixable is False
    
    def test_extract_context_line_length(self):
        """Test context extraction for line length errors."""
        context = self.parser._extract_context('TOO_LONG_LINE', 'Line is too long (95/80)')
        
        assert 'current_length' in context
        assert 'excess_chars' in context
        assert context['current_length'] == 95
        assert context['excess_chars'] == 15
    
    def test_extract_context_function_lines(self):
        """Test context extraction for function line count errors."""
        context = self.parser._extract_context('TOO_MANY_LINES', 'Function has too many lines (30/25)')
        
        assert 'current_lines' in context
        assert 'excess_lines' in context
        assert context['current_lines'] == 30
        assert context['excess_lines'] == 5
    
    def test_extract_context_function_params(self):
        """Test context extraction for function parameter errors."""
        context = self.parser._extract_context('TOO_MANY_PARAMS', 'Function has too many parameters (6/4)')
        
        assert 'current_params' in context
        assert 'excess_params' in context
        assert context['current_params'] == 6
        assert context['excess_params'] == 2
    
    def test_generate_fix_suggestion_with_context(self):
        """Test fix suggestion generation with context."""
        context = {'excess_chars': 10}
        suggestion = self.parser._generate_fix_suggestion('TOO_LONG_LINE', context)
        
        assert 'reduce by 10 characters' in suggestion
        assert 'Break line at logical points' in suggestion
    
    def test_find_related_errors(self):
        """Test finding related errors."""
        related = self.parser._find_related_errors('TOO_LONG_LINE')
        
        assert 'SPACE_BEFORE_FUNC' in related
        assert 'SPACE_AFTER_KW' in related
        
        related_indent = self.parser._find_related_errors('INDENT_BRANCH')
        assert 'BRACE_NEWLINE' in related_indent
        assert 'BRACE_SHOULD_EOL' in related_indent
    
    def test_analyze_file_errors(self):
        """Test analyzing multiple errors in a file."""
        errors = [
            {
                'rule': 'TOO_LONG_LINE',
                'line': 10,
                'column': 85,
                'description': 'Line too long',
                'type': 'line_length'
            },
            {
                'rule': 'SPACE_BEFORE_FUNC',
                'line': 15,
                'column': 5,
                'description': 'Space before function',
                'type': 'spacing'
            }
        ]
        
        analyses = self.parser.analyze_file_errors(errors)
        
        assert len(analyses) == 2
        assert all(isinstance(a, ErrorAnalysis) for a in analyses)
        assert analyses[0].rule == 'TOO_LONG_LINE'
        assert analyses[1].rule == 'SPACE_BEFORE_FUNC'
    
    def test_group_errors_by_type(self):
        """Test grouping errors by type."""
        analyses = [
            Mock(error_type='line_length'),
            Mock(error_type='spacing'),
            Mock(error_type='line_length'),
            Mock(error_type='indentation')
        ]
        
        groups = self.parser.group_errors_by_type(analyses)
        
        assert len(groups['line_length']) == 2
        assert len(groups['spacing']) == 1
        assert len(groups['indentation']) == 1
    
    def test_group_errors_by_severity(self):
        """Test grouping errors by severity."""
        analyses = [
            Mock(severity=ErrorSeverity.CRITICAL),
            Mock(severity=ErrorSeverity.HIGH),
            Mock(severity=ErrorSeverity.CRITICAL),
            Mock(severity=ErrorSeverity.LOW)
        ]
        
        groups = self.parser.group_errors_by_severity(analyses)
        
        assert len(groups[ErrorSeverity.CRITICAL]) == 2
        assert len(groups[ErrorSeverity.HIGH]) == 1
        assert len(groups[ErrorSeverity.MEDIUM]) == 0
        assert len(groups[ErrorSeverity.LOW]) == 1
    
    def test_get_auto_fixable_errors(self):
        """Test filtering auto-fixable errors."""
        analyses = [
            Mock(auto_fixable=True),
            Mock(auto_fixable=False),
            Mock(auto_fixable=True),
            Mock(auto_fixable=False)
        ]
        
        auto_fixable = self.parser.get_auto_fixable_errors(analyses)
        
        assert len(auto_fixable) == 2
        assert all(a.auto_fixable for a in auto_fixable)
    
    def test_prioritize_errors(self):
        """Test error prioritization."""
        analyses = [
            Mock(severity=ErrorSeverity.LOW, fix_complexity=FixComplexity.COMPLEX, auto_fixable=False),
            Mock(severity=ErrorSeverity.CRITICAL, fix_complexity=FixComplexity.TRIVIAL, auto_fixable=True),
            Mock(severity=ErrorSeverity.MEDIUM, fix_complexity=FixComplexity.SIMPLE, auto_fixable=True),
            Mock(severity=ErrorSeverity.HIGH, fix_complexity=FixComplexity.MODERATE, auto_fixable=False)
        ]
        
        prioritized = self.parser.prioritize_errors(analyses)
        
        # Critical + trivial + auto-fixable should be first
        assert prioritized[0].severity == ErrorSeverity.CRITICAL
        assert prioritized[0].fix_complexity == FixComplexity.TRIVIAL
        assert prioritized[0].auto_fixable is True
        
        # Low + complex + not auto-fixable should be last
        assert prioritized[-1].severity == ErrorSeverity.LOW
        assert prioritized[-1].fix_complexity == FixComplexity.COMPLEX
        assert prioritized[-1].auto_fixable is False
    
    def test_detect_error_patterns_spacing(self):
        """Test detection of spacing error patterns."""
        analyses = [
            Mock(error_type='spacing', rule='SPACE_BEFORE_FUNC'),
            Mock(error_type='spacing', rule='SPACE_AFTER_KW'),
            Mock(error_type='spacing', rule='TAB_REPLACE_SPACE'),
            Mock(error_type='line_length', rule='TOO_LONG_LINE')
        ]
        
        patterns = self.parser.detect_error_patterns(analyses)
        
        assert 'multiple_spacing_issues' in patterns
        assert len(patterns['multiple_spacing_issues']) == 3
    
    def test_detect_error_patterns_indentation(self):
        """Test detection of indentation error patterns."""
        analyses = [
            Mock(error_type='indentation', rule='INDENT_BRANCH'),
            Mock(error_type='indentation', rule='INDENT_MULT_BRANCH'),
            Mock(error_type='indentation', rule='SPACE_REPLACE_TAB'),
            Mock(error_type='indentation', rule='TAB_REPLACE_SPACE')
        ]
        
        patterns = self.parser.detect_error_patterns(analyses)
        
        assert 'consistent_indentation_issues' in patterns
        assert len(patterns['consistent_indentation_issues']) == 4
    
    def test_detect_error_patterns_function_complexity(self):
        """Test detection of function complexity patterns."""
        analyses = [
            Mock(rule='TOO_MANY_LINES'),
            Mock(rule='TOO_MANY_PARAMS'),
            Mock(rule='TOO_MANY_FUNCS')
        ]
        
        patterns = self.parser.detect_error_patterns(analyses)
        
        assert 'function_complexity_issues' in patterns
        assert len(patterns['function_complexity_issues']) == 3
    
    def test_detect_error_patterns_line_length(self):
        """Test detection of widespread line length issues."""
        analyses = [Mock(rule='TOO_LONG_LINE') for _ in range(6)]
        
        patterns = self.parser.detect_error_patterns(analyses)
        
        assert 'widespread_line_length_issues' in patterns
        assert len(patterns['widespread_line_length_issues']) == 6
    
    def test_generate_summary_report_empty(self):
        """Test summary report generation with no errors."""
        summary = self.parser.generate_summary_report([])
        
        assert summary['total_errors'] == 0
    
    def test_generate_summary_report_with_errors(self):
        """Test summary report generation with errors."""
        analyses = [
            Mock(
                severity=ErrorSeverity.CRITICAL,
                error_type='header',
                fix_complexity=FixComplexity.SIMPLE,
                auto_fixable=True,
                rule='HEADER_MISSING',
                line=1
            ),
            Mock(
                severity=ErrorSeverity.LOW,
                error_type='spacing',
                fix_complexity=FixComplexity.TRIVIAL,
                auto_fixable=True,
                rule='SPACE_BEFORE_FUNC',
                line=10
            ),
            Mock(
                severity=ErrorSeverity.HIGH,
                error_type='function_count',
                fix_complexity=FixComplexity.COMPLEX,
                auto_fixable=False,
                rule='TOO_MANY_FUNCS',
                line=50
            )
        ]
        
        summary = self.parser.generate_summary_report(analyses)
        
        assert summary['total_errors'] == 3
        assert summary['auto_fixable_count'] == 2
        assert summary['auto_fixable_percentage'] == pytest.approx(66.67, rel=1e-2)
        assert summary['severity_breakdown']['critical'] == 1
        assert summary['severity_breakdown']['high'] == 1
        assert summary['severity_breakdown']['low'] == 1
        assert summary['type_breakdown']['header'] == 1
        assert summary['type_breakdown']['spacing'] == 1
        assert summary['type_breakdown']['function_count'] == 1
        assert len(summary['top_priority_errors']) <= 5


if __name__ == '__main__':
    pytest.main([__file__])