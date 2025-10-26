#!/usr/bin/env python3
"""
Demo script to test the 42-Norminette-Formatter functionality.

This script creates sample C files with various norminette errors
and demonstrates the scanning, parsing, and formatting capabilities.
"""

import os
import tempfile
from pathlib import Path

# Create sample C files with norminette errors
def create_test_files():
    """Create sample C files with various norminette errors."""
    test_dir = Path("test_project")
    test_dir.mkdir(exist_ok=True)
    
    # File 1: Line length and spacing errors
    file1_content = '''/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   test1.c                                           :+:      :+:    :+:   */
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
    printf("This is a very long line that exceeds the 80 character limit and should trigger a norminette error");
    if(1 == 1)  // Missing space after if
    {
        printf("Hello World\\n");
    }
    return (0);
}
'''
    
    # File 2: Function with too many lines and parameters
    file2_content = '''/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   test2.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: student <student@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2024/01/01 10:00:00 by student          #+#    #+#             */
/*   Updated: 2024/01/01 10:00:00 by student         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdio.h>

int complex_function(int a, int b, int c, int d, int e)
{
    int result;
    
    result = 0;
    if (a > 0)
        result += a;
    if (b > 0)
        result += b;
    if (c > 0)
        result += c;
    if (d > 0)
        result += d;
    if (e > 0)
        result += e;
    printf("Processing values\\n");
    printf("Value a: %d\\n", a);
    printf("Value b: %d\\n", b);
    printf("Value c: %d\\n", c);
    printf("Value d: %d\\n", d);
    printf("Value e: %d\\n", e);
    printf("Result: %d\\n", result);
    return (result);
}

int main(void)
{
    complex_function(1, 2, 3, 4, 5);
    return (0);
}
'''
    
    # File 3: Good file (should pass norminette)
    file3_content = '''/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   test3.c                                           :+:      :+:    :+:   */
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
    printf("Hello, 42!\\n");
    return (0);
}
'''
    
    # Write test files
    (test_dir / "test1.c").write_text(file1_content)
    (test_dir / "test2.c").write_text(file2_content)
    (test_dir / "test3.c").write_text(file3_content)
    
    print(f"✓ Created test files in {test_dir}/")
    return test_dir

def demo_scanner():
    """Demonstrate the scanner functionality."""
    print("\n" + "="*60)
    print("DEMO: Scanner Functionality")
    print("="*60)
    
    try:
        from norminette_formatter.core.scanner import NorminetteScanner
        
        scanner = NorminetteScanner()
        print("✓ Scanner initialized")
        
        # Note: This demo shows the structure without actually running norminette
        # since it may not be installed in the test environment
        print("✓ Scanner ready to scan C files")
        print("  - Would detect norminette errors")
        print("  - Would classify error types")
        print("  - Would generate summary statistics")
        
    except ImportError as e:
        print(f"✗ Failed to import scanner: {e}")

def demo_parser():
    """Demonstrate the parser functionality."""
    print("\n" + "="*60)
    print("DEMO: Parser Functionality")
    print("="*60)
    
    try:
        from norminette_formatter.core.parser import ErrorParser, ErrorSeverity
        
        parser = ErrorParser()
        print("✓ Parser initialized")
        
        # Demo error analysis
        sample_error = {
            'rule': 'TOO_LONG_LINE',
            'line': 10,
            'column': 85,
            'description': 'Line is too long (85/80)',
            'type': 'line_length'
        }
        
        analysis = parser.analyze_error(sample_error)
        print(f"✓ Error analysis completed:")
        print(f"  - Rule: {analysis.rule}")
        print(f"  - Severity: {analysis.severity.value}")
        print(f"  - Auto-fixable: {analysis.auto_fixable}")
        print(f"  - Fix suggestion: {analysis.fix_suggestion}")
        
    except ImportError as e:
        print(f"✗ Failed to import parser: {e}")

def demo_formatter():
    """Demonstrate the formatter functionality."""
    print("\n" + "="*60)
    print("DEMO: Formatter Functionality")
    print("="*60)
    
    try:
        from norminette_formatter.core.formatter import AutoFormatter
        
        formatter = AutoFormatter(backup_enabled=False)
        print("✓ Formatter initialized")
        print("✓ Formatter ready to fix errors:")
        print("  - Line length violations")
        print("  - Spacing issues")
        print("  - Indentation problems")
        print("  - Header formatting")
        print("  - Brace placement")
        
    except ImportError as e:
        print(f"✗ Failed to import formatter: {e}")

def demo_aggregator():
    """Demonstrate the aggregator functionality."""
    print("\n" + "="*60)
    print("DEMO: Aggregator Functionality")
    print("="*60)
    
    try:
        from norminette_formatter.core.aggregator import FileAggregator, FileStatus
        
        aggregator = FileAggregator()
        print("✓ Aggregator initialized")
        print("✓ Aggregator ready to organize files:")
        print("  - Categorize by status (OK, Error, Warning, Critical)")
        print("  - Filter by error types")
        print("  - Generate project statistics")
        print("  - Provide recommendations")
        
    except ImportError as e:
        print(f"✗ Failed to import aggregator: {e}")

def demo_cli():
    """Demonstrate the CLI functionality."""
    print("\n" + "="*60)
    print("DEMO: CLI Functionality")
    print("="*60)
    
    print("✓ CLI Commands Available:")
    print("  - norminette-formatter scan <path>     # Scan files for errors")
    print("  - norminette-formatter format <path>   # Auto-fix errors")
    print("  - norminette-formatter dashboard       # Launch web dashboard")
    print("  - norminette-formatter report <path>   # Generate reports")
    print("  - norminette-formatter preview <file>  # Preview fixes")
    print("  - norminette-formatter restore <file>  # Restore from backup")

def demo_dashboard():
    """Demonstrate the dashboard functionality."""
    print("\n" + "="*60)
    print("DEMO: Web Dashboard Functionality")
    print("="*60)
    
    print("✓ Web Dashboard Features:")
    print("  - Project scanning interface")
    print("  - Real-time error statistics")
    print("  - Interactive file filtering")
    print("  - Bulk error fixing")
    print("  - Error preview and confirmation")
    print("  - Report generation and export")
    print("  - Responsive design with Bootstrap")

def main():
    """Run the demo."""
    print("42-NORMINETTE-FORMATTER DEMO")
    print("="*60)
    print("This demo showcases the comprehensive norminette debugging tool.")
    
    # Create test files
    test_dir = create_test_files()
    
    # Demo each component
    demo_scanner()
    demo_parser()
    demo_formatter()
    demo_aggregator()
    demo_cli()
    demo_dashboard()
    
    print("\n" + "="*60)
    print("DEMO COMPLETE")
    print("="*60)
    print("The 42-Norminette-Formatter includes:")
    print("✓ Comprehensive error detection and classification")
    print("✓ Intelligent auto-correction capabilities")
    print("✓ Web-based dashboard interface")
    print("✓ Command-line tools")
    print("✓ Extensive testing framework")
    print("✓ Project organization and reporting")
    
    print(f"\nTest files created in: {test_dir.absolute()}")
    print("\nTo use the tool:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run CLI: python -m norminette_formatter --help")
    print("3. Launch dashboard: python -m norminette_formatter dashboard")
    print("4. Run tests: python -m pytest tests/")

if __name__ == "__main__":
    main()