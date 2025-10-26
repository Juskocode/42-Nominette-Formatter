"""
Property-based tests for the norminette parser using Hypothesis.

These tests generate various error inputs and verify that the parser
behaves correctly and consistently across all possible inputs.
"""

import pytest
from hypothesis import given, strategies as st, assume, example
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from unittest.mock import Mock

from norminette_formatter.core.parser import (
    ErrorParser, ErrorAnalysis, ErrorSeverity, FixComplexity
)


# Strategies for generating test data
error_rules = st.sampled_from([
    'TOO_LONG_LINE', 'TOO_MANY_LINES', 'TOO_MANY_FUNCS', 'TOO_MANY_PARAMS',
    'SPACE_BEFORE_FUNC', 'SPACE_AFTER_KW', 'INDENT_BRANCH', 'BRACE_NEWLINE',
    'HEADER_MISSING', 'WRONG_SCOPE_COMMENT', 'UNKNOWN_RULE'
])

error_types = st.sampled_from([
    'line_length', 'function_count', 'function_params', 'spacing',
    'indentation', 'braces', 'header', 'comments', 'unknown'
])

severities = st.sampled_from(list(ErrorSeverity))
complexities = st.sampled_from(list(FixComplexity))

# Strategy for generating error dictionaries
@st.composite
def error_dict(draw):
    """Generate a valid error dictionary."""
    return {
        'rule': draw(error_rules),
        'line': draw(st.integers(min_value=1, max_value=1000)),
        'column': draw(st.integers(min_value=1, max_value=200)),
        'description': draw(st.text(min_size=1, max_size=200)),
        'type': draw(error_types)
    }

# Strategy for generating line length descriptions
@st.composite
def line_length_description(draw):
    """Generate line length error descriptions."""
    current = draw(st.integers(min_value=81, max_value=200))
    return f"Line is too long ({current}/80)"

# Strategy for generating function line descriptions
@st.composite
def function_lines_description(draw):
    """Generate function line count error descriptions."""
    current = draw(st.integers(min_value=26, max_value=100))
    return f"Function has too many lines ({current}/25)"

# Strategy for generating parameter count descriptions
@st.composite
def param_count_description(draw):
    """Generate parameter count error descriptions."""
    current = draw(st.integers(min_value=5, max_value=20))
    return f"Function has too many parameters ({current}/4)"


class TestParserProperties:
    """Property-based tests for the ErrorParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ErrorParser()
    
    @given(error_dict())
    def test_analyze_error_always_returns_analysis(self, error):
        """Property: analyze_error should always return an ErrorAnalysis object."""
        analysis = self.parser.analyze_error(error)
        
        assert isinstance(analysis, ErrorAnalysis)
        assert analysis.rule == error['rule']
        assert analysis.line == error['line']
        assert analysis.column == error['column']
        assert analysis.description == error['description']
        assert analysis.error_type == error['type']
        assert isinstance(analysis.severity, ErrorSeverity)
        assert isinstance(analysis.fix_complexity, FixComplexity)
        assert isinstance(analysis.auto_fixable, bool)
        assert isinstance(analysis.fix_suggestion, str)
        assert isinstance(analysis.related_errors, list)
        assert isinstance(analysis.context, dict)
    
    @given(st.lists(error_dict(), min_size=0, max_size=50))
    def test_analyze_file_errors_preserves_count(self, errors):
        """Property: analyze_file_errors should return same number of analyses as input errors."""
        analyses = self.parser.analyze_file_errors(errors)
        
        assert len(analyses) == len(errors)
        assert all(isinstance(a, ErrorAnalysis) for a in analyses)
    
    @given(st.lists(error_dict(), min_size=1, max_size=20))
    def test_group_errors_by_type_complete_partition(self, errors):
        """Property: grouping by type should partition all errors without loss."""
        analyses = self.parser.analyze_file_errors(errors)
        groups = self.parser.group_errors_by_type(analyses)
        
        # All analyses should be in exactly one group
        total_in_groups = sum(len(group) for group in groups.values())
        assert total_in_groups == len(analyses)
        
        # Each analysis should be in the correct group
        for error_type, group in groups.items():
            assert all(a.error_type == error_type for a in group)
    
    @given(st.lists(error_dict(), min_size=1, max_size=20))
    def test_group_errors_by_severity_complete_partition(self, errors):
        """Property: grouping by severity should partition all errors without loss."""
        analyses = self.parser.analyze_file_errors(errors)
        groups = self.parser.group_errors_by_severity(analyses)
        
        # All analyses should be in exactly one group
        total_in_groups = sum(len(group) for group in groups.values())
        assert total_in_groups == len(analyses)
        
        # Each analysis should be in the correct group
        for severity, group in groups.items():
            assert all(a.severity == severity for a in group)
    
    @given(st.lists(error_dict(), min_size=1, max_size=20))
    def test_get_auto_fixable_errors_subset(self, errors):
        """Property: auto-fixable errors should be a subset of all errors."""
        analyses = self.parser.analyze_file_errors(errors)
        auto_fixable = self.parser.get_auto_fixable_errors(analyses)
        
        # Auto-fixable should be subset
        assert len(auto_fixable) <= len(analyses)
        assert all(a.auto_fixable for a in auto_fixable)
        assert all(a in analyses for a in auto_fixable)
    
    @given(st.lists(error_dict(), min_size=1, max_size=20))
    def test_prioritize_errors_preserves_count(self, errors):
        """Property: prioritizing errors should preserve the total count."""
        analyses = self.parser.analyze_file_errors(errors)
        prioritized = self.parser.prioritize_errors(analyses)
        
        assert len(prioritized) == len(analyses)
        assert set(prioritized) == set(analyses)  # Same elements, possibly different order
    
    @given(st.lists(error_dict(), min_size=2, max_size=20))
    def test_prioritize_errors_ordering(self, errors):
        """Property: prioritized errors should be in descending priority order."""
        analyses = self.parser.analyze_file_errors(errors)
        prioritized = self.parser.prioritize_errors(analyses)
        
        if len(prioritized) >= 2:
            # Check that critical errors come before non-critical
            critical_indices = [i for i, a in enumerate(prioritized) if a.severity == ErrorSeverity.CRITICAL]
            non_critical_indices = [i for i, a in enumerate(prioritized) if a.severity != ErrorSeverity.CRITICAL]
            
            if critical_indices and non_critical_indices:
                assert max(critical_indices) < min(non_critical_indices)
    
    @given(line_length_description())
    def test_extract_context_line_length_properties(self, description):
        """Property: line length context extraction should be consistent."""
        context = self.parser._extract_context('TOO_LONG_LINE', description)
        
        if 'current_length' in context:
            assert context['current_length'] > 80
            assert context['excess_chars'] == context['current_length'] - 80
            assert context['excess_chars'] > 0
    
    @given(function_lines_description())
    def test_extract_context_function_lines_properties(self, description):
        """Property: function lines context extraction should be consistent."""
        context = self.parser._extract_context('TOO_MANY_LINES', description)
        
        if 'current_lines' in context:
            assert context['current_lines'] > 25
            assert context['excess_lines'] == context['current_lines'] - 25
            assert context['excess_lines'] > 0
    
    @given(param_count_description())
    def test_extract_context_params_properties(self, description):
        """Property: parameter count context extraction should be consistent."""
        context = self.parser._extract_context('TOO_MANY_PARAMS', description)
        
        if 'current_params' in context:
            assert context['current_params'] > 4
            assert context['excess_params'] == context['current_params'] - 4
            assert context['excess_params'] > 0
    
    @given(st.lists(error_dict(), min_size=0, max_size=50))
    def test_generate_summary_report_properties(self, errors):
        """Property: summary report should have consistent statistics."""
        analyses = self.parser.analyze_file_errors(errors)
        summary = self.parser.generate_summary_report(analyses)
        
        if not analyses:
            assert summary['total_errors'] == 0
        else:
            assert summary['total_errors'] == len(analyses)
            assert 0 <= summary['auto_fixable_count'] <= len(analyses)
            assert 0 <= summary['auto_fixable_percentage'] <= 100
            
            # Severity breakdown should sum to total
            severity_total = sum(summary['severity_breakdown'].values())
            assert severity_total == len(analyses)
            
            # Type breakdown should sum to total
            type_total = sum(summary['type_breakdown'].values())
            assert type_total == len(analyses)
    
    @given(st.lists(error_dict(), min_size=1, max_size=30))
    def test_detect_error_patterns_properties(self, errors):
        """Property: pattern detection should be consistent."""
        analyses = self.parser.analyze_file_errors(errors)
        patterns = self.parser.detect_error_patterns(analyses)
        
        # All detected patterns should contain actual analyses
        for pattern_name, pattern_errors in patterns.items():
            assert len(pattern_errors) > 0
            assert all(isinstance(e, ErrorAnalysis) for e in pattern_errors)
            assert all(e in analyses for e in pattern_errors)
    
    @given(st.text(min_size=0, max_size=1000))
    def test_generate_fix_suggestion_never_empty(self, rule):
        """Property: fix suggestions should never be empty strings."""
        suggestion = self.parser._generate_fix_suggestion(rule, {})
        assert isinstance(suggestion, str)
        assert len(suggestion.strip()) > 0
    
    @given(error_rules)
    def test_find_related_errors_returns_list(self, rule):
        """Property: finding related errors should always return a list."""
        related = self.parser._find_related_errors(rule)
        assert isinstance(related, list)
        assert all(isinstance(r, str) for r in related)


class ErrorParserStateMachine(RuleBasedStateMachine):
    """Stateful testing for ErrorParser using Hypothesis."""
    
    def __init__(self):
        super().__init__()
        self.parser = ErrorParser()
        self.all_analyses = []
        self.error_count = 0
    
    @rule(error=error_dict())
    def add_error(self, error):
        """Add an error and analyze it."""
        analysis = self.parser.analyze_error(error)
        self.all_analyses.append(analysis)
        self.error_count += 1
    
    @rule()
    def group_by_type(self):
        """Group current analyses by type."""
        if self.all_analyses:
            groups = self.parser.group_errors_by_type(self.all_analyses)
            total_in_groups = sum(len(group) for group in groups.values())
            assert total_in_groups == len(self.all_analyses)
    
    @rule()
    def group_by_severity(self):
        """Group current analyses by severity."""
        if self.all_analyses:
            groups = self.parser.group_errors_by_severity(self.all_analyses)
            total_in_groups = sum(len(group) for group in groups.values())
            assert total_in_groups == len(self.all_analyses)
    
    @rule()
    def get_auto_fixable(self):
        """Get auto-fixable errors."""
        auto_fixable = self.parser.get_auto_fixable_errors(self.all_analyses)
        assert len(auto_fixable) <= len(self.all_analyses)
        assert all(a.auto_fixable for a in auto_fixable)
    
    @rule()
    def prioritize(self):
        """Prioritize current analyses."""
        if self.all_analyses:
            prioritized = self.parser.prioritize_errors(self.all_analyses)
            assert len(prioritized) == len(self.all_analyses)
            assert set(prioritized) == set(self.all_analyses)
    
    @rule()
    def generate_summary(self):
        """Generate summary report."""
        summary = self.parser.generate_summary_report(self.all_analyses)
        assert summary['total_errors'] == len(self.all_analyses)
        
        if self.all_analyses:
            assert 0 <= summary['auto_fixable_percentage'] <= 100
    
    @invariant()
    def analyses_count_matches(self):
        """Invariant: number of analyses should match error count."""
        assert len(self.all_analyses) == self.error_count
    
    @invariant()
    def all_analyses_valid(self):
        """Invariant: all analyses should be valid ErrorAnalysis objects."""
        for analysis in self.all_analyses:
            assert isinstance(analysis, ErrorAnalysis)
            assert isinstance(analysis.severity, ErrorSeverity)
            assert isinstance(analysis.fix_complexity, FixComplexity)
            assert isinstance(analysis.auto_fixable, bool)


# Test the state machine
TestErrorParserStateMachine = ErrorParserStateMachine.TestCase


if __name__ == '__main__':
    pytest.main([__file__])