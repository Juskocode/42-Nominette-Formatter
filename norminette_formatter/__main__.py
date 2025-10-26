"""
Main entry point for the 42-Norminette-Formatter package.

This allows the package to be run as a module:
python -m norminette_formatter
"""

from .cli.commands import main

if __name__ == '__main__':
    main()