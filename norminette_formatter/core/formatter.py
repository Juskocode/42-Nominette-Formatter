"""
Auto Formatter Module

This module provides automatic correction capabilities for norminette errors.
It includes specific formatters for different error types and intelligent
code transformation functions.
"""

import re
import os
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
import logging
from .parser import ErrorAnalysis, FixComplexity

logger = logging.getLogger(__name__)


class FormatResult:
    """Result of a formatting operation."""

    def __init__(self, success: bool, message: str, changes_made: int = 0, original_content: str = "", formatted_content: str = ""):
        self.success = success
        self.message = message
        self.changes_made = changes_made
        self.original_content = original_content
        self.formatted_content = formatted_content

    def __repr__(self):
        return f"FormatResult(success={self.success}, changes={self.changes_made}, message='{self.message}')"


class AutoFormatter:
    """
    Automatic formatter for norminette errors.

    This class provides:
    - Automatic fixing of trivial errors (spacing, indentation, etc.)
    - Intelligent line breaking for long lines
    - Header insertion and formatting
    - Brace and comment formatting
    - Safe backup and restore functionality
    """

    def __init__(self, backup_enabled: bool = True):
        """
        Initialize the auto formatter.

        Args:
            backup_enabled: Whether to create backups before formatting
        """
        self.backup_enabled = backup_enabled
        self.backup_dir = ".norminette_backups"
        self.header_template = self._get_42_header_template()

    def _get_42_header_template(self) -> str:
        """Get the standard 42 header template."""
        return """/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   {filename:<51} :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: {author} <{email}>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: {created} by {author}          #+#    #+#             */
/*   Updated: {updated} by {author}         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

"""

    def _create_backup(self, filepath: str) -> bool:
        """Create a backup of the file before formatting."""
        if not self.backup_enabled:
            return True

        try:
            # Create backup directory if it doesn't exist
            backup_path = Path(self.backup_dir)
            backup_path.mkdir(exist_ok=True)

            # Create backup filename with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = Path(filepath).name
            backup_filename = f"{filename}.{timestamp}.backup"
            backup_filepath = backup_path / backup_filename

            # Copy original file to backup
            import shutil
            shutil.copy2(filepath, backup_filepath)

            logger.info(f"Created backup: {backup_filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup for {filepath}: {e}")
            return False

    def _read_file(self, filepath: str) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
            return None

    def _write_file(self, filepath: str, content: str) -> bool:
        """Write file content safely."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to write file {filepath}: {e}")
            return False

    def _fix_line_length(self, content: str) -> Tuple[str, int]:
        """
        Fix lines that are too long by breaking them at logical points.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        lines = content.split('\n')
        changes = 0

        for i, line in enumerate(lines):
            if len(line) > 80:
                # Try to break at logical points
                new_line = self._break_long_line(line)
                if new_line != line:
                    lines[i] = new_line
                    changes += 1

        return '\n'.join(lines), changes

    def _break_long_line(self, line: str) -> str:
        """Break a long line at logical points."""
        if len(line) <= 80:
            return line

        # Get indentation
        indent = len(line) - len(line.lstrip())
        indent_str = line[:indent]

        # Try different breaking strategies

        # 1. Break at function parameters
        if '(' in line and ')' in line:
            return self._break_at_function_params(line, indent_str)

        # 2. Break at operators
        operators = [' && ', ' || ', ' + ', ' - ', ' * ', ' / ', ' = ', ' == ', ' != ', ' < ', ' > ']
        for op in operators:
            if op in line and line.find(op) < 70:
                pos = line.rfind(op, 0, 70)
                if pos > indent + 10:  # Ensure meaningful break
                    return line[:pos + len(op)] + '\n' + indent_str + '\t' + line[pos + len(op):].lstrip()

        # 3. Break at commas
        if ',' in line:
            pos = line.rfind(',', 0, 70)
            if pos > indent + 10:
                return line[:pos + 1] + '\n' + indent_str + '\t' + line[pos + 1:].lstrip()

        # 4. Break at string concatenation
        if ' + "' in line or '" + ' in line:
            for pattern in [' + "', '" + ']:
                pos = line.rfind(pattern, 0, 70)
                if pos > indent + 10:
                    return line[:pos] + '\n' + indent_str + '\t' + line[pos:].lstrip()

        return line  # Return original if no good break point found

    def _break_at_function_params(self, line: str, indent_str: str) -> str:
        """Break long function calls at parameter boundaries."""
        # Find function call pattern
        match = re.search(r'(\w+\s*\()', line)
        if not match:
            return line

        func_start = match.end()
        paren_count = 1
        params = []
        current_param = ""

        i = func_start
        while i < len(line) and paren_count > 0:
            char = line[i]
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
                if paren_count == 0:
                    if current_param.strip():
                        params.append(current_param.strip())
                    break
            elif char == ',' and paren_count == 1:
                params.append(current_param.strip())
                current_param = ""
                i += 1
                continue

            current_param += char
            i += 1

        if len(params) > 1:
            # Reconstruct with line breaks
            func_name = line[:func_start]
            result = func_name
            for j, param in enumerate(params):
                if j == 0:
                    result += param
                else:
                    result += ',\n' + indent_str + '\t' + param
            result += line[i:]
            return result

        return line

    def _fix_spacing(self, content: str) -> Tuple[str, int]:
        """
        Fix spacing issues in the code.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        changes = 0
        original_content = content

        # Fix space after keywords
        keywords = ['if', 'while', 'for', 'switch', 'return']
        for keyword in keywords:
            pattern = rf'\b{keyword}\('
            replacement = f'{keyword} ('
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes += content.count(keyword + '(') - new_content.count(keyword + '(')
                content = new_content

        # Fix space before function names (remove extra spaces)
        content = re.sub(r'\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', r' \1(', content)

        # Fix space around operators
        operators = ['=', '==', '!=', '<=', '>=', '<', '>', '+', '-', '*', '/', '%']
        for op in operators:
            # Add spaces around operators if missing
            pattern = rf'(\w){re.escape(op)}(\w)'
            replacement = rf'\1 {op} \2'
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes += 1
                content = new_content

        # Fix space after commas
        content = re.sub(r',(\S)', r', \1', content)

        # Fix space after semicolons in for loops
        content = re.sub(r';(\S)', r'; \1', content)

        if content != original_content:
            changes = max(changes, 1)

        return content, changes

    def _fix_indentation(self, content: str) -> Tuple[str, int]:
        """
        Fix indentation issues using tabs.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        lines = content.split('\n')
        changes = 0
        indent_level = 0

        for i, line in enumerate(lines):
            if not line.strip():  # Skip empty lines
                continue

            # Calculate expected indent level
            stripped = line.lstrip()

            # Adjust indent level based on braces
            if '}' in stripped:
                indent_level = max(0, indent_level - stripped.count('}'))

            # Apply correct indentation
            expected_indent = '\t' * indent_level
            if not line.startswith(expected_indent) and line.strip():
                lines[i] = expected_indent + stripped
                changes += 1

            # Update indent level for next line
            if '{' in stripped:
                indent_level += stripped.count('{')

        return '\n'.join(lines), changes

    def _fix_braces(self, content: str) -> Tuple[str, int]:
        """
        Fix brace placement and formatting.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        changes = 0

        # Fix opening braces - should be at end of line
        # Pattern: keyword/condition followed by newline and brace
        pattern = r'(if|while|for|else)\s*\([^)]*\)\s*\n\s*{'
        def replace_brace(match):
            return match.group(0).replace('\n', ' ').replace('  {', ' {')

        new_content = re.sub(pattern, replace_brace, content, flags=re.MULTILINE)
        if new_content != content:
            changes += 1
            content = new_content

        # Fix closing braces - should be on their own line
        content = re.sub(r';\s*}', ';\n}', content)

        # Ensure newline after opening brace
        content = re.sub(r'{\s*([^\n}])', r'{\n\t\1', content)

        return content, changes

    def _add_header(self, content: str, filepath: str) -> Tuple[str, int]:
        """
        Add 42 header to file if missing.

        Args:
            content: File content
            filepath: Path to the file

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        # Check if header already exists
        if content.startswith('/*') and '42' in content[:500]:
            return content, 0

        # Get file info
        filename = Path(filepath).name

        # Use placeholder values - in real implementation, these would come from config
        author = "student"
        email = "student@student.42.fr"

        import datetime
        now = datetime.datetime.now()
        created = now.strftime("%Y/%m/%d %H:%M:%S")
        updated = created

        # Format header
        header = self.header_template.format(
            filename=filename,
            author=author,
            email=email,
            created=created,
            updated=updated
        )

        return header + content, 1

    def _fix_comments(self, content: str) -> Tuple[str, int]:
        """
        Fix comment formatting issues.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        changes = 0

        # Fix single-line comments to use /* */ format
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '//' in line and not line.strip().startswith('//'):
                # Convert inline // comments to /* */ format
                comment_pos = line.find('//')
                before_comment = line[:comment_pos].rstrip()
                comment_text = line[comment_pos + 2:].strip()
                if comment_text:
                    lines[i] = before_comment + ' /* ' + comment_text + ' */'
                    changes += 1

        return '\n'.join(lines), changes

    def _fix_empty_lines(self, content: str) -> Tuple[str, int]:
        """
        Fix empty line issues in the code.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        changes = 0
        lines = content.split('\n')
        result_lines = []
        in_function = False
        brace_count = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track function boundaries
            if '{' in stripped:
                brace_count += stripped.count('{')
                if brace_count > 0:
                    in_function = True

            if '}' in stripped:
                brace_count -= stripped.count('}')
                if brace_count <= 0:
                    in_function = False
                    brace_count = 0

            # Remove empty lines inside functions
            if in_function and not stripped and brace_count > 0:
                changes += 1
                continue

            # Handle consecutive newlines (keep only one)
            if not stripped and result_lines and not result_lines[-1].strip():
                changes += 1
                continue

            result_lines.append(line)

        # Remove empty line at end of file
        while result_lines and not result_lines[-1].strip():
            result_lines.pop()
            changes += 1

        return '\n'.join(result_lines), changes

    def _fix_function_spacing(self, content: str) -> Tuple[str, int]:
        """
        Fix spacing around function definitions.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        changes = 0
        lines = content.split('\n')
        result_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if this line contains a function definition
            if (stripped and 
                ('(' in stripped and ')' in stripped) and
                (stripped.endswith('{') or (i + 1 < len(lines) and lines[i + 1].strip() == '{')) and
                not stripped.startswith('if') and not stripped.startswith('while') and 
                not stripped.startswith('for') and not stripped.startswith('switch')):

                # Ensure newline before function (except for first function)
                if (result_lines and result_lines[-1].strip() and 
                    not result_lines[-1].strip().startswith('/*') and
                    not result_lines[-1].strip().startswith('*') and
                    not result_lines[-1].strip().startswith('#')):
                    result_lines.append('')
                    changes += 1

            result_lines.append(line)

        return '\n'.join(result_lines), changes

    def _fix_tab_space_issues(self, content: str) -> Tuple[str, int]:
        """
        Fix tab/space mixing issues.

        Args:
            content: File content

        Returns:
            Tuple of (formatted_content, changes_made)
        """
        changes = 0
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if not line.strip():  # Skip empty lines
                continue

            # Get leading whitespace
            leading_whitespace = len(line) - len(line.lstrip())
            if leading_whitespace == 0:
                continue

            whitespace = line[:leading_whitespace]

            # Check for mixed tabs and spaces in indentation
            if '\t' in whitespace and ' ' in whitespace:
                # Convert spaces to tabs for indentation
                # Assume 4 spaces = 1 tab for conversion
                spaces_count = whitespace.count(' ')
                tabs_count = whitespace.count('\t')
                total_tabs = tabs_count + (spaces_count // 4)

                new_whitespace = '\t' * total_tabs
                lines[i] = new_whitespace + line.lstrip()
                changes += 1

            # Replace leading spaces with tabs (if more than 3 spaces)
            elif ' ' in whitespace and '\t' not in whitespace and leading_whitespace >= 4:
                tab_count = leading_whitespace // 4
                remaining_spaces = leading_whitespace % 4
                new_whitespace = '\t' * tab_count + ' ' * remaining_spaces
                lines[i] = new_whitespace + line.lstrip()
                changes += 1

        return '\n'.join(lines), changes

    def format_file(self, filepath: str, error_analyses: List[ErrorAnalysis]) -> FormatResult:
        """
        Format a file to fix norminette errors.

        Args:
            filepath: Path to the file to format
            error_analyses: List of error analyses for the file

        Returns:
            FormatResult object
        """
        if not os.path.exists(filepath):
            return FormatResult(False, f"File not found: {filepath}")

        # Read original content
        original_content = self._read_file(filepath)
        if original_content is None:
            return FormatResult(False, f"Failed to read file: {filepath}")

        # Create backup
        if not self._create_backup(filepath):
            return FormatResult(False, f"Failed to create backup for: {filepath}")

        # Apply fixes based on error analyses
        content = original_content
        total_changes = 0

        # Get auto-fixable errors
        auto_fixable = [analysis for analysis in error_analyses if analysis.auto_fixable]

        if not auto_fixable:
            return FormatResult(True, "No auto-fixable errors found", 0, original_content, content)

        # Apply fixes in order of complexity (trivial first)
        error_types = set(analysis.rule for analysis in auto_fixable)

        # Fix header issues
        if any(rule in ['HEADER_MISSING'] for rule in error_types):
            content, changes = self._add_header(content, filepath)
            total_changes += changes

        # Fix spacing issues
        if any(rule in ['SPACE_BEFORE_FUNC', 'SPACE_AFTER_KW'] for rule in error_types):
            content, changes = self._fix_spacing(content)
            total_changes += changes

        # Fix indentation issues
        if any(rule in ['INDENT_BRANCH', 'INDENT_MULT_BRANCH'] for rule in error_types):
            content, changes = self._fix_indentation(content)
            total_changes += changes

        # Fix brace issues
        if any(rule in ['BRACE_NEWLINE', 'BRACE_SHOULD_EOL'] for rule in error_types):
            content, changes = self._fix_braces(content)
            total_changes += changes

        # Fix tab/space issues
        if any(rule in ['SPACE_REPLACE_TAB', 'TAB_REPLACE_SPACE'] for rule in error_types):
            content, changes = self._fix_tab_space_issues(content)
            total_changes += changes

        # Fix comment issues
        if any(rule in ['WRONG_SCOPE_COMMENT'] for rule in error_types):
            content, changes = self._fix_comments(content)
            total_changes += changes

        # Fix empty line issues
        if any(rule in ['EMPTY_LINE_FUNCTION', 'EMPTY_LINE_EOF', 'CONSECUTIVE_NEWLINES'] for rule in error_types):
            content, changes = self._fix_empty_lines(content)
            total_changes += changes

        # Fix function spacing
        if any(rule in ['NEWLINE_PRECEDES_FUNC'] for rule in error_types):
            content, changes = self._fix_function_spacing(content)
            total_changes += changes

        # Fix line length issues (do this last as it might affect other fixes)
        if any(rule in ['TOO_LONG_LINE'] for rule in error_types):
            content, changes = self._fix_line_length(content)
            total_changes += changes

        # Write formatted content
        if total_changes > 0:
            if self._write_file(filepath, content):
                return FormatResult(True, f"Successfully formatted file with {total_changes} changes", 
                                  total_changes, original_content, content)
            else:
                return FormatResult(False, f"Failed to write formatted content to: {filepath}")
        else:
            return FormatResult(True, "No changes needed", 0, original_content, content)

    def format_multiple_files(self, file_analyses: Dict[str, List[ErrorAnalysis]]) -> Dict[str, FormatResult]:
        """
        Format multiple files.

        Args:
            file_analyses: Dictionary mapping filepaths to their error analyses

        Returns:
            Dictionary mapping filepaths to their FormatResult objects
        """
        results = {}

        for filepath, analyses in file_analyses.items():
            logger.info(f"Formatting file: {filepath}")
            result = self.format_file(filepath, analyses)
            results[filepath] = result

            if result.success:
                logger.info(f"Successfully formatted {filepath}: {result.message}")
            else:
                logger.error(f"Failed to format {filepath}: {result.message}")

        return results

    def get_format_preview(self, filepath: str, error_analyses: List[ErrorAnalysis]) -> Optional[str]:
        """
        Get a preview of what the formatted file would look like without actually changing it.

        Args:
            filepath: Path to the file
            error_analyses: List of error analyses

        Returns:
            Preview of formatted content or None if failed
        """
        # Temporarily disable backup for preview
        original_backup_setting = self.backup_enabled
        self.backup_enabled = False

        try:
            # Read original content
            original_content = self._read_file(filepath)
            if original_content is None:
                return None

            # Apply formatting logic without writing to file
            content = original_content
            auto_fixable = [analysis for analysis in error_analyses if analysis.auto_fixable]

            if not auto_fixable:
                return content

            error_types = set(analysis.rule for analysis in auto_fixable)

            # Apply same fixes as format_file but don't write
            if any(rule in ['HEADER_MISSING'] for rule in error_types):
                content, _ = self._add_header(content, filepath)

            if any(rule in ['SPACE_BEFORE_FUNC', 'SPACE_AFTER_KW'] for rule in error_types):
                content, _ = self._fix_spacing(content)

            if any(rule in ['INDENT_BRANCH', 'INDENT_MULT_BRANCH'] for rule in error_types):
                content, _ = self._fix_indentation(content)

            if any(rule in ['BRACE_NEWLINE', 'BRACE_SHOULD_EOL'] for rule in error_types):
                content, _ = self._fix_braces(content)

            if any(rule in ['SPACE_REPLACE_TAB', 'TAB_REPLACE_SPACE'] for rule in error_types):
                content, _ = self._fix_tab_space_issues(content)

            if any(rule in ['WRONG_SCOPE_COMMENT'] for rule in error_types):
                content, _ = self._fix_comments(content)

            if any(rule in ['EMPTY_LINE_FUNCTION', 'EMPTY_LINE_EOF', 'CONSECUTIVE_NEWLINES'] for rule in error_types):
                content, _ = self._fix_empty_lines(content)

            if any(rule in ['NEWLINE_PRECEDES_FUNC'] for rule in error_types):
                content, _ = self._fix_function_spacing(content)

            if any(rule in ['TOO_LONG_LINE'] for rule in error_types):
                content, _ = self._fix_line_length(content)

            return content

        finally:
            # Restore backup setting
            self.backup_enabled = original_backup_setting

    def restore_from_backup(self, filepath: str) -> bool:
        """
        Restore a file from its most recent backup.

        Args:
            filepath: Path to the file to restore

        Returns:
            True if restoration was successful
        """
        try:
            backup_path = Path(self.backup_dir)
            if not backup_path.exists():
                logger.error("No backup directory found")
                return False

            filename = Path(filepath).name

            # Find most recent backup
            backup_files = list(backup_path.glob(f"{filename}.*.backup"))
            if not backup_files:
                logger.error(f"No backup found for {filepath}")
                return False

            # Sort by modification time, get most recent
            most_recent = max(backup_files, key=lambda p: p.stat().st_mtime)

            # Restore file
            import shutil
            shutil.copy2(most_recent, filepath)

            logger.info(f"Restored {filepath} from backup {most_recent}")
            return True

        except Exception as e:
            logger.error(f"Failed to restore {filepath} from backup: {e}")
            return False
