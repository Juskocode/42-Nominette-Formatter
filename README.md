# 42-Norminette-Formatter

A comprehensive norminette debugging and auto-correction tool for 42 School projects.

## Overview

This tool provides a dashboard-style interface for analyzing, filtering, and auto-correcting norminette errors in C projects. It helps developers quickly identify and fix coding standard violations according to the 42 School norm.

## Features

### Core Functionality
- **Error Detection**: Automatically scan C files for norminette violations
- **Error Classification**: Categorize errors by type (indentation, line length, function complexity, etc.)
- **File Aggregation**: Separate files into OK and Error categories
- **Auto-Correction**: Intelligent formatting to fix common norm violations
- **Dashboard Interface**: Web-based UI for filtering and managing errors

### Error Types Supported
- Line length violations (> 80 characters)
- Function length violations (> 25 lines)
- Function parameter count (> 4 parameters)
- Variable declarations
- Indentation errors
- Spacing and formatting issues
- Header formatting
- Comment formatting
- Brace placement
- And more...

### Dashboard Features
- Filter by file status (OK, Error, All)
- Filter by error type
- Bulk operations (fix all, fix selected)
- Real-time error statistics
- File-by-file error breakdown
- Quick fix suggestions

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd 42-norminette-formatter

# Install dependencies
pip install -r requirements.txt

# Install norminette (if not already installed)
pip install norminette
```

## Usage

### Command Line Interface
```bash
# Scan a single file
python -m norminette_formatter scan file.c

# Scan entire project
python -m norminette_formatter scan .

# Launch dashboard
python -m norminette_formatter dashboard

# Auto-fix specific errors
python -m norminette_formatter fix --type=indentation file.c

# Auto-fix all errors in a file
python -m norminette_formatter fix --all file.c
```

### Web Dashboard
1. Launch the dashboard: `python -m norminette_formatter dashboard`
2. Open your browser to `http://localhost:8080`
3. Upload or select your C project directory
4. Use filters to view specific error types
5. Apply fixes individually or in bulk

## Project Structure

```
norminette_formatter/
├── core/
│   ├── scanner.py          # Norminette error detection
│   ├── parser.py           # Error parsing and classification
│   ├── formatter.py        # Auto-correction engine
│   └── aggregator.py       # File status aggregation
├── dashboard/
│   ├── app.py             # Flask web application
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JS, assets
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── property/         # Property-based tests
│   └── mock/            # Mock tests
├── cli/
│   └── commands.py       # Command-line interface
└── utils/
    ├── config.py         # Configuration management
    └── helpers.py        # Utility functions
```

## Development

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test types
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/property/

# Run with coverage
python -m pytest --cov=norminette_formatter tests/
```

### Contributing
This project follows a comprehensive development workflow with:
- 400+ commits planned across multiple features
- 50+ Pull Requests for organized development
- Property-based testing (PBT)
- Mock testing for external dependencies
- White-box and black-box testing strategies

## License

MIT License - see LICENSE file for details.

## Authors

- afreitas <afreitas@student.42.fr>

## Acknowledgments

- 42 School for the norminette standard
- The norminette tool developers
