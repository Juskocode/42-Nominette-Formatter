"""
Flask Web Dashboard for Norminette Formatter

This module provides a web-based dashboard for managing norminette errors,
including scanning, filtering, auto-fixing, and project analysis.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

from ..core.scanner import NorminetteScanner, NorminetteResult
from ..core.parser import ErrorParser, ErrorAnalysis
from ..core.formatter import AutoFormatter, FormatResult
from ..core.aggregator import FileAggregator, FileStatus

logger = logging.getLogger(__name__)


class NorminetteDashboard:
    """Main dashboard application class."""
    
    def __init__(self):
        """Initialize the dashboard."""
        self.scanner = NorminetteScanner()
        self.parser = ErrorParser()
        self.formatter = AutoFormatter()
        self.aggregator = FileAggregator()
        self.current_project_path = None
        self.scan_results = {}
        
    def scan_project(self, project_path: str) -> Dict[str, Any]:
        """
        Scan a project directory for norminette errors.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Dictionary with scan results and statistics
        """
        try:
            self.current_project_path = project_path
            
            # Scan all files in the project
            scan_results = self.scanner.scan_directory(project_path, recursive=True)
            
            # Clear previous results
            self.aggregator = FileAggregator()
            
            # Process each scan result
            for result in scan_results:
                # Parse errors for detailed analysis
                analyses = []
                if result.errors:
                    analyses = self.parser.analyze_file_errors(result.errors)
                
                # Add to aggregator
                self.aggregator.add_scan_result(result, analyses)
                
                # Store for later use
                self.scan_results[result.filepath] = {
                    'result': result,
                    'analyses': analyses
                }
            
            # Generate summary
            summary = self.aggregator.generate_project_summary()
            recommendations = self.aggregator.get_recommendations()
            statistics = self.aggregator.get_statistics()
            
            return {
                'success': True,
                'project_path': project_path,
                'scan_time': datetime.now().isoformat(),
                'summary': {
                    'total_files': summary.total_files,
                    'ok_files': summary.ok_files,
                    'error_files': summary.error_files,
                    'warning_files': summary.warning_files,
                    'critical_files': summary.critical_files,
                    'total_errors': summary.total_errors,
                    'auto_fixable_errors': summary.auto_fixable_errors,
                    'success_rate': summary.success_rate
                },
                'recommendations': recommendations,
                'statistics': statistics
            }
            
        except Exception as e:
            logger.error(f"Error scanning project {project_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_file_details(self, filepath: str) -> Dict[str, Any]:
        """Get detailed information about a specific file."""
        if filepath not in self.scan_results:
            return {'success': False, 'error': 'File not found in scan results'}
        
        data = self.scan_results[filepath]
        result = data['result']
        analyses = data['analyses']
        
        # Group errors by type and severity
        error_groups = {}
        if analyses:
            parser_groups = self.parser.group_errors_by_type(analyses)
            for error_type, error_list in parser_groups.items():
                error_groups[error_type] = [
                    {
                        'rule': analysis.rule,
                        'line': analysis.line,
                        'column': analysis.column,
                        'description': analysis.description,
                        'severity': analysis.severity.value,
                        'fix_suggestion': analysis.fix_suggestion,
                        'auto_fixable': analysis.auto_fixable
                    }
                    for analysis in error_list
                ]
        
        return {
            'success': True,
            'filepath': filepath,
            'filename': Path(filepath).name,
            'status': result.status,
            'error_count': result.error_count,
            'errors': result.errors,
            'error_groups': error_groups,
            'auto_fixable_count': len([a for a in analyses if a.auto_fixable]) if analyses else 0
        }
    
    def format_file(self, filepath: str, selected_errors: List[str] = None) -> Dict[str, Any]:
        """Format a specific file to fix norminette errors."""
        if filepath not in self.scan_results:
            return {'success': False, 'error': 'File not found in scan results'}
        
        try:
            analyses = self.scan_results[filepath]['analyses']
            
            # Filter analyses if specific errors are selected
            if selected_errors:
                analyses = [a for a in analyses if a.rule in selected_errors]
            
            # Format the file
            format_result = self.formatter.format_file(filepath, analyses)
            
            if format_result.success:
                # Re-scan the file to update results
                new_result = self.scanner.scan_file(filepath)
                new_analyses = []
                if new_result.errors:
                    new_analyses = self.parser.analyze_file_errors(new_result.errors)
                
                # Update stored results
                self.scan_results[filepath] = {
                    'result': new_result,
                    'analyses': new_analyses
                }
                
                # Update aggregator
                self.aggregator.add_scan_result(new_result, new_analyses)
            
            return {
                'success': format_result.success,
                'message': format_result.message,
                'changes_made': format_result.changes_made,
                'new_error_count': len(new_analyses) if format_result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error formatting file {filepath}: {e}")
            return {'success': False, 'error': str(e)}


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Enable CORS for API endpoints
    CORS(app)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize dashboard
    dashboard = NorminetteDashboard()
    
    @app.route('/')
    def index():
        """Main dashboard page."""
        return render_template('index.html')
    
    @app.route('/api/scan', methods=['POST'])
    def api_scan():
        """API endpoint to scan a project directory."""
        data = request.get_json()
        project_path = data.get('project_path')
        
        if not project_path:
            return jsonify({'success': False, 'error': 'Project path is required'}), 400
        
        if not os.path.exists(project_path):
            return jsonify({'success': False, 'error': 'Project path does not exist'}), 400
        
        result = dashboard.scan_project(project_path)
        return jsonify(result)
    
    @app.route('/api/files')
    def api_files():
        """API endpoint to get list of files with filtering."""
        # Get filter parameters
        status = request.args.get('status')
        error_type = request.args.get('error_type')
        auto_fixable_only = request.args.get('auto_fixable_only', 'false').lower() == 'true'
        search_query = request.args.get('search', '')
        
        # Apply filters
        files = dashboard.aggregator.files
        
        if status and status != 'all':
            try:
                status_enum = FileStatus(status)
                files = [f for f in files if f.status == status_enum]
            except ValueError:
                pass
        
        if error_type and error_type != 'all':
            files = [f for f in files if error_type in f.error_types]
        
        if auto_fixable_only:
            files = [f for f in files if f.auto_fixable_count > 0]
        
        if search_query:
            files = [f for f in files if search_query.lower() in f.filename.lower() or 
                    search_query.lower() in f.filepath.lower()]
        
        # Convert to JSON-serializable format
        files_data = []
        for file_info in files:
            files_data.append({
                'filepath': file_info.filepath,
                'filename': file_info.filename,
                'status': file_info.status.value,
                'error_count': file_info.error_count,
                'auto_fixable_count': file_info.auto_fixable_count,
                'critical_errors': file_info.critical_errors,
                'high_errors': file_info.high_errors,
                'medium_errors': file_info.medium_errors,
                'low_errors': file_info.low_errors,
                'error_types': list(file_info.error_types),
                'lines_of_code': file_info.lines_of_code
            })
        
        return jsonify({
            'success': True,
            'files': files_data,
            'total_count': len(files_data)
        })
    
    @app.route('/api/files/<path:filepath>')
    def api_file_details(filepath):
        """API endpoint to get detailed information about a specific file."""
        result = dashboard.get_file_details(filepath)
        return jsonify(result)
    
    @app.route('/api/format', methods=['POST'])
    def api_format():
        """API endpoint to format files."""
        data = request.get_json()
        filepath = data.get('filepath')
        selected_errors = data.get('selected_errors', [])
        
        if not filepath:
            return jsonify({'success': False, 'error': 'Filepath is required'}), 400
        
        result = dashboard.format_file(filepath, selected_errors)
        return jsonify(result)
    
    @app.route('/api/format/bulk', methods=['POST'])
    def api_format_bulk():
        """API endpoint to format multiple files."""
        data = request.get_json()
        filepaths = data.get('filepaths', [])
        auto_fixable_only = data.get('auto_fixable_only', True)
        
        if not filepaths:
            return jsonify({'success': False, 'error': 'Filepaths are required'}), 400
        
        results = {}
        total_changes = 0
        
        for filepath in filepaths:
            if filepath in dashboard.scan_results:
                analyses = dashboard.scan_results[filepath]['analyses']
                
                # Filter to auto-fixable only if requested
                if auto_fixable_only:
                    analyses = [a for a in analyses if a.auto_fixable]
                
                if analyses:
                    result = dashboard.format_file(filepath)
                    results[filepath] = result
                    if result['success']:
                        total_changes += result['changes_made']
        
        return jsonify({
            'success': True,
            'results': results,
            'total_files_processed': len(results),
            'total_changes': total_changes
        })
    
    @app.route('/api/statistics')
    def api_statistics():
        """API endpoint to get project statistics."""
        statistics = dashboard.aggregator.get_statistics()
        return jsonify({
            'success': True,
            'statistics': statistics
        })
    
    @app.route('/api/recommendations')
    def api_recommendations():
        """API endpoint to get project recommendations."""
        recommendations = dashboard.aggregator.get_recommendations()
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    
    @app.route('/api/export')
    def api_export():
        """API endpoint to export project report."""
        format_type = request.args.get('format', 'json')
        report = dashboard.aggregator.export_report(format_type)
        
        if format_type == 'json':
            return jsonify(report)
        else:
            # For other formats, return JSON for now
            # In a full implementation, you'd generate CSV, HTML, etc.
            return jsonify(report)
    
    @app.route('/api/preview', methods=['POST'])
    def api_preview():
        """API endpoint to preview formatted file content."""
        data = request.get_json()
        filepath = data.get('filepath')
        
        if not filepath or filepath not in dashboard.scan_results:
            return jsonify({'success': False, 'error': 'Invalid filepath'}), 400
        
        try:
            analyses = dashboard.scan_results[filepath]['analyses']
            auto_fixable = [a for a in analyses if a.auto_fixable]
            
            if not auto_fixable:
                return jsonify({
                    'success': True,
                    'preview': 'No auto-fixable errors found',
                    'changes_count': 0
                })
            
            preview_content = dashboard.formatter.get_format_preview(filepath, auto_fixable)
            
            if preview_content is None:
                return jsonify({'success': False, 'error': 'Failed to generate preview'})
            
            return jsonify({
                'success': True,
                'preview': preview_content,
                'changes_count': len(auto_fixable)
            })
            
        except Exception as e:
            logger.error(f"Error generating preview for {filepath}: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/api/restore', methods=['POST'])
    def api_restore():
        """API endpoint to restore a file from backup."""
        data = request.get_json()
        filepath = data.get('filepath')
        
        if not filepath:
            return jsonify({'success': False, 'error': 'Filepath is required'}), 400
        
        try:
            success = dashboard.formatter.restore_from_backup(filepath)
            
            if success:
                # Re-scan the restored file
                new_result = dashboard.scanner.scan_file(filepath)
                new_analyses = []
                if new_result.errors:
                    new_analyses = dashboard.parser.analyze_file_errors(new_result.errors)
                
                # Update stored results
                dashboard.scan_results[filepath] = {
                    'result': new_result,
                    'analyses': new_analyses
                }
                
                # Update aggregator
                dashboard.aggregator.add_scan_result(new_result, new_analyses)
            
            return jsonify({
                'success': success,
                'message': 'File restored successfully' if success else 'Failed to restore file'
            })
            
        except Exception as e:
            logger.error(f"Error restoring file {filepath}: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8080)