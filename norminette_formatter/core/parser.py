"""
Error Parser Module

This module provides advanced parsing and analysis of norminette errors,
including pattern detection, severity classification, and fix suggestions.
"""

import re
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FixComplexity(Enum):
    """Fix complexity levels."""
    TRIVIAL = "trivial"      # Automatic fix available
    SIMPLE = "simple"        # Simple manual fix
    MODERATE = "moderate"    # Requires some refactoring
    COMPLEX = "complex"      # Significant code changes needed


@dataclass
class ErrorAnalysis:
    """Detailed analysis of a norminette error."""
    rule: str
    line: int
    column: int
    description: str
    error_type: str
    severity: ErrorSeverity
    fix_complexity: FixComplexity
    fix_suggestion: str
    auto_fixable: bool
    related_errors: List[str]
    context: Dict[str, any]


class ErrorParser:
    """
    Advanced parser for norminette errors with pattern detection and fix suggestions.

    This class provides:
    - Detailed error analysis and classification
    - Pattern detection across multiple errors
    - Fix suggestions and complexity assessment
    - Error grouping and prioritization
    """

    def __init__(self):
        """Initialize the error parser."""
        self.error_patterns = self._load_error_patterns()
        self.fix_templates = self._load_fix_templates()

    def _load_error_patterns(self) -> Dict[str, Dict]:
        """Load error pattern definitions."""
        return {
            'TOO_LONG_LINE': {
                'severity': ErrorSeverity.MEDIUM,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': True,
                'pattern': r'line too long \((\d+)/80\)',
                'description': 'Line exceeds 80 character limit'
            },
            'TOO_MANY_LINES': {
                'severity': ErrorSeverity.HIGH,
                'fix_complexity': FixComplexity.MODERATE,
                'auto_fixable': False,
                'pattern': r'too many lines in function \((\d+)/25\)',
                'description': 'Function exceeds 25 line limit'
            },
            'TOO_MANY_FUNCS': {
                'severity': ErrorSeverity.HIGH,
                'fix_complexity': FixComplexity.COMPLEX,
                'auto_fixable': False,
                'pattern': r'too many functions in file \((\d+)/5\)',
                'description': 'File contains too many functions'
            },
            'TOO_MANY_PARAMS': {
                'severity': ErrorSeverity.MEDIUM,
                'fix_complexity': FixComplexity.MODERATE,
                'auto_fixable': False,
                'pattern': r'too many parameters \((\d+)/4\)',
                'description': 'Function has too many parameters'
            },
            'SPACE_BEFORE_FUNC': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'space before function name',
                'description': 'Unexpected space before function name'
            },
            'SPACE_AFTER_KW': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'missing space after keyword',
                'description': 'Missing space after keyword'
            },
            'SPACE_REPLACE_TAB': {
                'severity': ErrorSeverity.MEDIUM,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'space used instead of tab',
                'description': 'Spaces used for indentation instead of tabs'
            },
            'TAB_REPLACE_SPACE': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'tab used instead of space',
                'description': 'Tab used where space is required'
            },
            'INDENT_BRANCH': {
                'severity': ErrorSeverity.MEDIUM,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': True,
                'pattern': r'wrong indentation level',
                'description': 'Incorrect indentation'
            },
            'INDENT_MULT_BRANCH': {
                'severity': ErrorSeverity.MEDIUM,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': True,
                'pattern': r'wrong indentation in multiple branch',
                'description': 'Incorrect indentation in multiple branch structure'
            },
            'BRACE_NEWLINE': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'missing newline after opening brace',
                'description': 'Missing newline after opening brace'
            },
            'BRACE_SHOULD_EOL': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'brace should be at end of line',
                'description': 'Brace should be at end of line'
            },
            'BRACE_SHOULD_NEWLINE': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'brace should be followed by newline',
                'description': 'Opening brace should be followed by newline'
            },
            'VAR_DECL_START_FUNC': {
                'severity': ErrorSeverity.MEDIUM,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': False,
                'pattern': r'variable declaration not at start of function',
                'description': 'Variable declarations must be at function start'
            },
            'DECL_ASSIGN_LINE': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': False,
                'pattern': r'declaration and assignment on same line',
                'description': 'Variable declaration and assignment on same line'
            },
            'HEADER_MISSING': {
                'severity': ErrorSeverity.CRITICAL,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': True,
                'pattern': r'missing or invalid header',
                'description': 'File missing required 42 header'
            },
            'INVALID_HEADER': {
                'severity': ErrorSeverity.HIGH,
                'fix_complexity': FixComplexity.SIMPLE,
                'auto_fixable': True,
                'pattern': r'invalid header format',
                'description': 'Header format does not match 42 standard'
            },
            'WRONG_SCOPE_COMMENT': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'wrong scope comment',
                'description': 'Incorrect scope comment format'
            },
            'EMPTY_LINE_FUNCTION': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'empty line in function',
                'description': 'Empty line found inside function'
            },
            'EMPTY_LINE_EOF': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'empty line at end of file',
                'description': 'Empty line at end of file'
            },
            'NEWLINE_PRECEDES_FUNC': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'newline should precede function',
                'description': 'Function should be preceded by newline'
            },
            'CONSECUTIVE_NEWLINES': {
                'severity': ErrorSeverity.LOW,
                'fix_complexity': FixComplexity.TRIVIAL,
                'auto_fixable': True,
                'pattern': r'consecutive newlines',
                'description': 'Multiple consecutive newlines found'
            }
        }

    def _load_fix_templates(self) -> Dict[str, str]:
        """Load fix suggestion templates."""
        return {
            'TOO_LONG_LINE': 'Break line at logical points (operators, commas, function calls)',
            'TOO_MANY_LINES': 'Split function into smaller, more focused functions',
            'TOO_MANY_FUNCS': 'Move some functions to separate files or combine related functions',
            'TOO_MANY_PARAMS': 'Use structures to group related parameters or split function',
            'SPACE_BEFORE_FUNC': 'Remove space before function name',
            'SPACE_AFTER_KW': 'Add space after keyword (if, while, for, etc.)',
            'SPACE_REPLACE_TAB': 'Replace spaces with tabs for indentation',
            'TAB_REPLACE_SPACE': 'Replace tab with space where appropriate',
            'INDENT_BRANCH': 'Use tabs for indentation, align with proper scope level',
            'INDENT_MULT_BRANCH': 'Fix indentation in multiple branch structures',
            'BRACE_NEWLINE': 'Add newline after opening brace',
            'BRACE_SHOULD_EOL': 'Move opening brace to end of line',
            'BRACE_SHOULD_NEWLINE': 'Add newline after opening brace',
            'VAR_DECL_START_FUNC': 'Move all variable declarations to the beginning of function',
            'DECL_ASSIGN_LINE': 'Separate variable declaration and assignment',
            'HEADER_MISSING': 'Add standard 42 header at the beginning of file',
            'INVALID_HEADER': 'Fix header format to match 42 standard',
            'WRONG_SCOPE_COMMENT': 'Use /* */ for multi-line comments, // for single line',
            'EMPTY_LINE_FUNCTION': 'Remove empty lines inside functions',
            'EMPTY_LINE_EOF': 'Remove empty line at end of file',
            'NEWLINE_PRECEDES_FUNC': 'Add newline before function definition',
            'CONSECUTIVE_NEWLINES': 'Remove consecutive empty lines'
        }

    def analyze_error(self, error: Dict) -> ErrorAnalysis:
        """
        Perform detailed analysis of a single error.

        Args:
            error: Error dictionary from scanner

        Returns:
            ErrorAnalysis object with detailed information
        """
        rule = error.get('rule', 'UNKNOWN')
        line = error.get('line', 0)
        column = error.get('column', 0)
        description = error.get('description', '')
        error_type = error.get('type', 'unknown')

        # Get pattern information
        pattern_info = self.error_patterns.get(rule, {
            'severity': ErrorSeverity.MEDIUM,
            'fix_complexity': FixComplexity.SIMPLE,
            'auto_fixable': False,
            'description': description
        })

        # Extract additional context from description
        context = self._extract_context(rule, description)

        # Generate fix suggestion
        fix_suggestion = self._generate_fix_suggestion(rule, context)

        # Determine related errors
        related_errors = self._find_related_errors(rule)

        return ErrorAnalysis(
            rule=rule,
            line=line,
            column=column,
            description=description,
            error_type=error_type,
            severity=pattern_info['severity'],
            fix_complexity=pattern_info['fix_complexity'],
            fix_suggestion=fix_suggestion,
            auto_fixable=pattern_info['auto_fixable'],
            related_errors=related_errors,
            context=context
        )

    def _extract_context(self, rule: str, description: str) -> Dict[str, any]:
        """Extract additional context from error description."""
        context = {}

        # Extract numeric values (line counts, character counts, etc.)
        numbers = re.findall(r'\d+', description)
        if numbers:
            context['values'] = [int(n) for n in numbers]

        # Rule-specific context extraction
        if rule == 'TOO_LONG_LINE':
            match = re.search(r'(\d+)/80', description)
            if match:
                context['current_length'] = int(match.group(1))
                context['excess_chars'] = int(match.group(1)) - 80

        elif rule == 'TOO_MANY_LINES':
            match = re.search(r'(\d+)/25', description)
            if match:
                context['current_lines'] = int(match.group(1))
                context['excess_lines'] = int(match.group(1)) - 25

        elif rule == 'TOO_MANY_PARAMS':
            match = re.search(r'(\d+)/4', description)
            if match:
                context['current_params'] = int(match.group(1))
                context['excess_params'] = int(match.group(1)) - 4

        return context

    def _generate_fix_suggestion(self, rule: str, context: Dict) -> str:
        """Generate specific fix suggestion based on rule and context."""
        base_suggestion = self.fix_templates.get(rule, 'Manual fix required')

        # Add context-specific details
        if rule == 'TOO_LONG_LINE' and 'excess_chars' in context:
            excess = context['excess_chars']
            base_suggestion += f" (reduce by {excess} characters)"

        elif rule == 'TOO_MANY_LINES' and 'excess_lines' in context:
            excess = context['excess_lines']
            base_suggestion += f" (reduce by {excess} lines)"

        elif rule == 'TOO_MANY_PARAMS' and 'excess_params' in context:
            excess = context['excess_params']
            base_suggestion += f" (reduce by {excess} parameters)"

        return base_suggestion

    def _find_related_errors(self, rule: str) -> List[str]:
        """Find errors that are commonly related to the given rule."""
        related_map = {
            'TOO_LONG_LINE': ['SPACE_BEFORE_FUNC', 'SPACE_AFTER_KW'],
            'TOO_MANY_LINES': ['TOO_MANY_FUNCS', 'VAR_DECL_START_FUNC'],
            'INDENT_BRANCH': ['BRACE_NEWLINE', 'BRACE_SHOULD_EOL'],
            'SPACE_BEFORE_FUNC': ['TOO_LONG_LINE', 'SPACE_AFTER_KW'],
            'BRACE_NEWLINE': ['BRACE_SHOULD_EOL', 'INDENT_BRANCH'],
            'VAR_DECL_START_FUNC': ['TOO_MANY_LINES']
        }

        return related_map.get(rule, [])

    def analyze_file_errors(self, errors: List[Dict]) -> List[ErrorAnalysis]:
        """
        Analyze all errors in a file.

        Args:
            errors: List of error dictionaries

        Returns:
            List of ErrorAnalysis objects
        """
        analyses = []

        for error in errors:
            analysis = self.analyze_error(error)
            analyses.append(analysis)

        return analyses

    def group_errors_by_type(self, analyses: List[ErrorAnalysis]) -> Dict[str, List[ErrorAnalysis]]:
        """Group error analyses by error type."""
        groups = {}

        for analysis in analyses:
            error_type = analysis.error_type
            if error_type not in groups:
                groups[error_type] = []
            groups[error_type].append(analysis)

        return groups

    def group_errors_by_severity(self, analyses: List[ErrorAnalysis]) -> Dict[ErrorSeverity, List[ErrorAnalysis]]:
        """Group error analyses by severity."""
        groups = {severity: [] for severity in ErrorSeverity}

        for analysis in analyses:
            groups[analysis.severity].append(analysis)

        return groups

    def get_auto_fixable_errors(self, analyses: List[ErrorAnalysis]) -> List[ErrorAnalysis]:
        """Get list of errors that can be automatically fixed."""
        return [analysis for analysis in analyses if analysis.auto_fixable]

    def prioritize_errors(self, analyses: List[ErrorAnalysis]) -> List[ErrorAnalysis]:
        """
        Prioritize errors for fixing based on severity and fix complexity.

        Returns:
            Sorted list with highest priority errors first
        """
        severity_order = {
            ErrorSeverity.CRITICAL: 4,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.LOW: 1
        }

        complexity_order = {
            FixComplexity.TRIVIAL: 4,
            FixComplexity.SIMPLE: 3,
            FixComplexity.MODERATE: 2,
            FixComplexity.COMPLEX: 1
        }

        def priority_key(analysis):
            severity_score = severity_order[analysis.severity]
            complexity_score = complexity_order[analysis.fix_complexity]
            auto_fix_bonus = 1 if analysis.auto_fixable else 0

            # Higher severity and easier fixes get higher priority
            return (severity_score, complexity_score, auto_fix_bonus)

        return sorted(analyses, key=priority_key, reverse=True)

    def detect_error_patterns(self, analyses: List[ErrorAnalysis]) -> Dict[str, List[ErrorAnalysis]]:
        """
        Detect common error patterns across multiple errors.

        Returns:
            Dictionary mapping pattern names to lists of related errors
        """
        patterns = {}

        # Pattern: Multiple spacing issues
        spacing_errors = [a for a in analyses if a.error_type == 'spacing']
        if len(spacing_errors) > 2:
            patterns['multiple_spacing_issues'] = spacing_errors

        # Pattern: Consistent indentation problems
        indent_errors = [a for a in analyses if a.error_type == 'indentation']
        if len(indent_errors) > 3:
            patterns['consistent_indentation_issues'] = indent_errors

        # Pattern: Function complexity issues
        func_errors = [a for a in analyses if a.rule in ['TOO_MANY_LINES', 'TOO_MANY_PARAMS', 'TOO_MANY_FUNCS']]
        if len(func_errors) > 1:
            patterns['function_complexity_issues'] = func_errors

        # Pattern: Line length issues throughout file
        line_length_errors = [a for a in analyses if a.rule == 'TOO_LONG_LINE']
        if len(line_length_errors) > 5:
            patterns['widespread_line_length_issues'] = line_length_errors

        return patterns

    def generate_summary_report(self, analyses: List[ErrorAnalysis]) -> Dict:
        """Generate a comprehensive summary report of all errors."""
        if not analyses:
            return {'total_errors': 0}

        # Basic counts
        total_errors = len(analyses)
        auto_fixable = len(self.get_auto_fixable_errors(analyses))

        # Severity breakdown
        severity_groups = self.group_errors_by_severity(analyses)
        severity_counts = {sev.value: len(errors) for sev, errors in severity_groups.items()}

        # Type breakdown
        type_groups = self.group_errors_by_type(analyses)
        type_counts = {error_type: len(errors) for error_type, errors in type_groups.items()}

        # Complexity breakdown
        complexity_counts = {}
        for analysis in analyses:
            complexity = analysis.fix_complexity.value
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1

        # Pattern detection
        patterns = self.detect_error_patterns(analyses)

        # Priority analysis
        prioritized = self.prioritize_errors(analyses)
        top_priority = prioritized[:5] if len(prioritized) >= 5 else prioritized

        return {
            'total_errors': total_errors,
            'auto_fixable_count': auto_fixable,
            'auto_fixable_percentage': (auto_fixable / total_errors * 100) if total_errors > 0 else 0,
            'severity_breakdown': severity_counts,
            'type_breakdown': type_counts,
            'complexity_breakdown': complexity_counts,
            'detected_patterns': list(patterns.keys()),
            'pattern_details': {name: len(errors) for name, errors in patterns.items()},
            'top_priority_errors': [
                {
                    'rule': analysis.rule,
                    'line': analysis.line,
                    'severity': analysis.severity.value,
                    'auto_fixable': analysis.auto_fixable
                }
                for analysis in top_priority
            ]
        }
