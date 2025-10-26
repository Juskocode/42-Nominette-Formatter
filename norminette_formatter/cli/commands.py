"""
Command-line interface for the 42-Norminette-Formatter.

This module provides CLI commands for scanning, formatting, and managing
norminette errors in C projects.
"""

import os
import sys
import json
import click
import logging
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

from ..core.scanner import NorminetteScanner
from ..core.parser import ErrorParser
from ..core.formatter import AutoFormatter
from ..core.aggregator import FileAggregator, FileStatus
from ..dashboard.app import create_app

# Initialize Rich console for beautiful output
console = Console()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="1.0.0")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def main(verbose):
    """42-Norminette-Formatter - A comprehensive tool for managing norminette errors."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        console.print("[dim]Verbose mode enabled[/dim]")


@main.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, default=True, help='Scan directories recursively')
@click.option('--output', '-o', type=click.Path(), help='Output file for results (JSON format)')
@click.option('--filter-status', type=click.Choice(['OK', 'Error', 'Warning', 'Critical']), 
              help='Filter results by status')
@click.option('--filter-type', help='Filter results by error type')
@click.option('--show-details', is_flag=True, help='Show detailed error information')
def scan(path, recursive, output, filter_status, filter_type, show_details):
    """Scan a file or directory for norminette errors."""
    console.print(f"[bold blue]Scanning:[/bold blue] {path}")
    
    scanner = NorminetteScanner()
    parser = ErrorParser()
    aggregator = FileAggregator()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scanning files...", total=None)
        
        try:
            if os.path.isfile(path):
                # Scan single file
                result = scanner.scan_file(path)
                results = [result]
            else:
                # Scan directory
                results = scanner.scan_directory(path, recursive=recursive)
            
            progress.update(task, description="Analyzing errors...")
            
            # Process results
            for result in results:
                analyses = []
                if result.errors:
                    analyses = parser.analyze_file_errors(result.errors)
                aggregator.add_scan_result(result, analyses)
            
            progress.update(task, description="Generating report...")
            
        except Exception as e:
            console.print(f"[red]Error during scan: {e}[/red]")
            sys.exit(1)
    
    # Generate summary
    summary = aggregator.generate_project_summary()
    
    # Display results
    display_scan_results(aggregator, summary, filter_status, filter_type, show_details)
    
    # Save to file if requested
    if output:
        save_results_to_file(aggregator, output)
        console.print(f"[green]Results saved to {output}[/green]")


@main.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, default=True, help='Process directories recursively')
@click.option('--auto-fixable-only', is_flag=True, help='Only fix auto-fixable errors')
@click.option('--backup/--no-backup', default=True, help='Create backups before formatting')
@click.option('--dry-run', is_flag=True, help='Show what would be fixed without making changes')
@click.option('--filter-type', help='Only fix specific error types')
def format(path, recursive, auto_fixable_only, backup, dry_run, filter_type):
    """Format files to fix norminette errors."""
    console.print(f"[bold yellow]Formatting:[/bold yellow] {path}")
    
    if dry_run:
        console.print("[dim]Running in dry-run mode - no changes will be made[/dim]")
    
    scanner = NorminetteScanner()
    parser = ErrorParser()
    formatter = AutoFormatter(backup_enabled=backup)
    
    # First, scan to identify files with errors
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        scan_task = progress.add_task("Scanning for errors...", total=None)
        
        try:
            if os.path.isfile(path):
                results = [scanner.scan_file(path)]
            else:
                results = scanner.scan_directory(path, recursive=recursive)
            
            progress.update(scan_task, description="Analyzing errors...")
            
            # Process and filter results
            files_to_format = []
            for result in results:
                if result.status == "OK":
                    continue
                
                analyses = parser.analyze_file_errors(result.errors) if result.errors else []
                
                # Apply filters
                if auto_fixable_only:
                    analyses = [a for a in analyses if a.auto_fixable]
                
                if filter_type:
                    analyses = [a for a in analyses if a.error_type == filter_type]
                
                if analyses:
                    files_to_format.append((result.filepath, analyses))
            
            if not files_to_format:
                console.print("[yellow]No files found that match the formatting criteria[/yellow]")
                return
            
            progress.update(scan_task, description=f"Found {len(files_to_format)} files to format...")
            
        except Exception as e:
            console.print(f"[red]Error during scan: {e}[/red]")
            sys.exit(1)
    
    # Format files
    if dry_run:
        display_dry_run_results(files_to_format)
    else:
        format_files(formatter, files_to_format)


@main.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8080, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def dashboard(host, port, debug):
    """Launch the web dashboard."""
    console.print(f"[bold green]Starting dashboard at http://{host}:{port}[/bold green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    try:
        app = create_app()
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to start dashboard: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file for report')
@click.option('--format', 'report_format', type=click.Choice(['json', 'html', 'text']), 
              default='text', help='Report format')
@click.option('--include-recommendations', is_flag=True, help='Include recommendations in report')
def report(path, output, report_format, include_recommendations):
    """Generate a comprehensive report of norminette errors."""
    console.print(f"[bold cyan]Generating report for:[/bold cyan] {path}")
    
    scanner = NorminetteScanner()
    parser = ErrorParser()
    aggregator = FileAggregator()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Analyzing project...", total=None)
        
        try:
            if os.path.isfile(path):
                results = [scanner.scan_file(path)]
            else:
                results = scanner.scan_directory(path, recursive=True)
            
            for result in results:
                analyses = []
                if result.errors:
                    analyses = parser.analyze_file_errors(result.errors)
                aggregator.add_scan_result(result, analyses)
            
        except Exception as e:
            console.print(f"[red]Error generating report: {e}[/red]")
            sys.exit(1)
    
    # Generate report
    report_data = aggregator.export_report(report_format)
    
    if output:
        save_report_to_file(report_data, output, report_format)
        console.print(f"[green]Report saved to {output}[/green]")
    else:
        display_text_report(aggregator, include_recommendations)


@main.command()
@click.argument('filepath', type=click.Path(exists=True))
def preview(filepath):
    """Preview what fixes would be applied to a file."""
    console.print(f"[bold magenta]Preview fixes for:[/bold magenta] {filepath}")
    
    scanner = NorminetteScanner()
    parser = ErrorParser()
    formatter = AutoFormatter(backup_enabled=False)
    
    try:
        # Scan file
        result = scanner.scan_file(filepath)
        
        if result.status == "OK":
            console.print("[green]File has no norminette errors![/green]")
            return
        
        # Analyze errors
        analyses = parser.analyze_file_errors(result.errors) if result.errors else []
        auto_fixable = [a for a in analyses if a.auto_fixable]
        
        if not auto_fixable:
            console.print("[yellow]No auto-fixable errors found[/yellow]")
            return
        
        # Generate preview
        preview_content = formatter.get_format_preview(filepath, auto_fixable)
        
        if preview_content:
            console.print("\n[bold]Preview of formatted content:[/bold]")
            console.print(Panel(preview_content, title="Formatted Code", border_style="green"))
            console.print(f"\n[green]Would fix {len(auto_fixable)} auto-fixable errors[/green]")
        else:
            console.print("[red]Failed to generate preview[/red]")
            
    except Exception as e:
        console.print(f"[red]Error generating preview: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument('filepath', type=click.Path(exists=True))
def restore(filepath):
    """Restore a file from backup."""
    console.print(f"[bold orange1]Restoring:[/bold orange1] {filepath}")
    
    formatter = AutoFormatter()
    
    try:
        success = formatter.restore_from_backup(filepath)
        
        if success:
            console.print(f"[green]Successfully restored {filepath} from backup[/green]")
        else:
            console.print(f"[red]Failed to restore {filepath} - no backup found or restore failed[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error restoring file: {e}[/red]")
        sys.exit(1)


def display_scan_results(aggregator, summary, filter_status, filter_type, show_details):
    """Display scan results in a formatted table."""
    # Summary panel
    summary_text = f"""
Total Files: {summary.total_files}
OK Files: {summary.ok_files}
Error Files: {summary.error_files}
Success Rate: {summary.success_rate:.1f}%
Total Errors: {summary.total_errors}
Auto-fixable: {summary.auto_fixable_errors}
    """.strip()
    
    console.print(Panel(summary_text, title="Scan Summary", border_style="blue"))
    
    # Files table
    files = aggregator.files
    
    # Apply filters
    if filter_status:
        status_enum = FileStatus(filter_status)
        files = [f for f in files if f.status == status_enum]
    
    if filter_type:
        files = [f for f in files if filter_type in f.error_types]
    
    if not files:
        console.print("[yellow]No files match the specified filters[/yellow]")
        return
    
    table = Table(title="Files")
    table.add_column("File", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Errors", justify="center")
    table.add_column("Auto-fixable", justify="center")
    
    if show_details:
        table.add_column("Error Types", style="dim")
    
    for file_info in files:
        status_style = {
            FileStatus.OK: "green",
            FileStatus.WARNING: "yellow",
            FileStatus.ERROR: "red",
            FileStatus.CRITICAL: "bold red"
        }.get(file_info.status, "white")
        
        row = [
            file_info.filename,
            f"[{status_style}]{file_info.status.value}[/{status_style}]",
            str(file_info.error_count),
            str(file_info.auto_fixable_count)
        ]
        
        if show_details:
            error_types = ", ".join(file_info.error_types) if file_info.error_types else "None"
            row.append(error_types)
        
        table.add_row(*row)
    
    console.print(table)


def display_dry_run_results(files_to_format):
    """Display what would be formatted in dry-run mode."""
    console.print(f"\n[bold]Dry run - would format {len(files_to_format)} files:[/bold]")
    
    table = Table(title="Files to Format")
    table.add_column("File", style="cyan")
    table.add_column("Auto-fixable Errors", justify="center")
    table.add_column("Error Types", style="dim")
    
    for filepath, analyses in files_to_format:
        filename = Path(filepath).name
        error_count = len(analyses)
        error_types = ", ".join(set(a.error_type for a in analyses))
        
        table.add_row(filename, str(error_count), error_types)
    
    console.print(table)


def format_files(formatter, files_to_format):
    """Format the specified files."""
    total_changes = 0
    successful_files = 0
    
    with Progress(console=console) as progress:
        task = progress.add_task("Formatting files...", total=len(files_to_format))
        
        for filepath, analyses in files_to_format:
            filename = Path(filepath).name
            progress.update(task, description=f"Formatting {filename}...")
            
            try:
                result = formatter.format_file(filepath, analyses)
                
                if result.success:
                    total_changes += result.changes_made
                    successful_files += 1
                    console.print(f"[green]✓[/green] {filename}: {result.changes_made} changes")
                else:
                    console.print(f"[red]✗[/red] {filename}: {result.message}")
                    
            except Exception as e:
                console.print(f"[red]✗[/red] {filename}: Error - {e}")
            
            progress.advance(task)
    
    # Summary
    console.print(f"\n[bold]Formatting complete![/bold]")
    console.print(f"Successfully formatted: {successful_files}/{len(files_to_format)} files")
    console.print(f"Total changes made: {total_changes}")


def save_results_to_file(aggregator, output_path):
    """Save scan results to a file."""
    report_data = aggregator.export_report('json')
    
    with open(output_path, 'w') as f:
        json.dump(report_data, f, indent=2)


def save_report_to_file(report_data, output_path, report_format):
    """Save report to file in specified format."""
    if report_format == 'json':
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
    elif report_format == 'html':
        # Generate HTML report (simplified)
        html_content = generate_html_report(report_data)
        with open(output_path, 'w') as f:
            f.write(html_content)
    else:  # text format
        text_content = generate_text_report(report_data)
        with open(output_path, 'w') as f:
            f.write(text_content)


def display_text_report(aggregator, include_recommendations):
    """Display a text report to console."""
    summary = aggregator.generate_project_summary()
    
    # Project overview
    console.print(Panel.fit(
        f"[bold]Project Analysis Report[/bold]\n\n"
        f"Total Files: {summary.total_files}\n"
        f"OK Files: {summary.ok_files}\n"
        f"Files with Errors: {summary.error_files}\n"
        f"Success Rate: {summary.success_rate:.1f}%\n"
        f"Total Errors: {summary.total_errors}\n"
        f"Auto-fixable Errors: {summary.auto_fixable_errors}",
        title="Summary",
        border_style="green"
    ))
    
    # Most common errors
    if summary.most_common_errors:
        console.print("\n[bold]Most Common Errors:[/bold]")
        for error_type, count in summary.most_common_errors[:5]:
            console.print(f"  • {error_type}: {count} occurrences")
    
    # Recommendations
    if include_recommendations:
        recommendations = aggregator.get_recommendations()
        if recommendations:
            console.print("\n[bold]Recommendations:[/bold]")
            for rec in recommendations:
                console.print(f"  {rec}")


def generate_html_report(report_data):
    """Generate HTML report content."""
    # Simplified HTML report generation
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Norminette Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
            .error {{ color: red; }}
            .success {{ color: green; }}
        </style>
    </head>
    <body>
        <h1>Norminette Analysis Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <p>Total Files: {report_data['summary']['total_files']}</p>
            <p>OK Files: {report_data['summary']['ok_files']}</p>
            <p>Error Files: {report_data['summary']['error_files']}</p>
            <p>Success Rate: {report_data['summary']['success_rate']:.1f}%</p>
        </div>
        <h2>Recommendations</h2>
        <ul>
    """
    
    for rec in report_data.get('recommendations', []):
        html += f"<li>{rec}</li>"
    
    html += """
        </ul>
    </body>
    </html>
    """
    
    return html


def generate_text_report(report_data):
    """Generate text report content."""
    lines = [
        "NORMINETTE ANALYSIS REPORT",
        "=" * 50,
        "",
        "SUMMARY:",
        f"Total Files: {report_data['summary']['total_files']}",
        f"OK Files: {report_data['summary']['ok_files']}",
        f"Error Files: {report_data['summary']['error_files']}",
        f"Success Rate: {report_data['summary']['success_rate']:.1f}%",
        f"Total Errors: {report_data['summary']['total_errors']}",
        f"Auto-fixable Errors: {report_data['summary']['auto_fixable_errors']}",
        "",
        "RECOMMENDATIONS:",
    ]
    
    for rec in report_data.get('recommendations', []):
        lines.append(f"- {rec}")
    
    return "\n".join(lines)


if __name__ == '__main__':
    main()