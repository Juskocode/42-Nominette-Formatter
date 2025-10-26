"""
File Aggregator Module

This module provides functionality to aggregate and organize norminette scan results,
including file status categorization, filtering, and report generation.
"""

from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
from .scanner import NorminetteResult
from .parser import ErrorAnalysis, ErrorSeverity, FixComplexity

logger = logging.getLogger(__name__)


class FileStatus(Enum):
    """File status categories."""
    OK = "OK"
    ERROR = "Error"
    WARNING = "Warning"
    CRITICAL = "Critical"


@dataclass
class FileInfo:
    """Information about a single file."""
    filepath: str
    filename: str
    status: FileStatus
    error_count: int
    auto_fixable_count: int
    critical_errors: int
    high_errors: int
    medium_errors: int
    low_errors: int
    error_types: Set[str]
    lines_of_code: int
    last_modified: float


@dataclass
class ProjectSummary:
    """Summary statistics for the entire project."""
    total_files: int
    ok_files: int
    error_files: int
    warning_files: int
    critical_files: int
    total_errors: int
    auto_fixable_errors: int
    total_lines_of_code: int
    success_rate: float
    most_common_errors: List[Tuple[str, int]]
    error_distribution: Dict[str, int]
    severity_distribution: Dict[str, int]


class FileAggregator:
    """
    Aggregator for organizing and analyzing norminette scan results.
    
    This class provides:
    - File status categorization and organization
    - Advanced filtering and search capabilities
    - Statistical analysis and reporting
    - Project-wide insights and recommendations
    """
    
    def __init__(self):
        """Initialize the file aggregator."""
        self.files: List[FileInfo] = []
        self.scan_results: Dict[str, NorminetteResult] = {}
        self.error_analyses: Dict[str, List[ErrorAnalysis]] = {}
        
    def add_scan_result(self, result: NorminetteResult, analyses: List[ErrorAnalysis] = None):
        """
        Add a scan result to the aggregator.
        
        Args:
            result: NorminetteResult from scanner
            analyses: Optional list of ErrorAnalysis objects
        """
        self.scan_results[result.filepath] = result
        if analyses:
            self.error_analyses[result.filepath] = analyses
        
        # Create FileInfo
        file_info = self._create_file_info(result, analyses or [])
        
        # Update or add file info
        existing_index = None
        for i, existing_file in enumerate(self.files):
            if existing_file.filepath == result.filepath:
                existing_index = i
                break
        
        if existing_index is not None:
            self.files[existing_index] = file_info
        else:
            self.files.append(file_info)
    
    def _create_file_info(self, result: NorminetteResult, analyses: List[ErrorAnalysis]) -> FileInfo:
        """Create FileInfo from scan result and analyses."""
        filepath = result.filepath
        filename = Path(filepath).name
        
        # Determine file status
        if result.status == "OK":
            status = FileStatus.OK
        else:
            # Determine severity based on error analyses
            if analyses:
                critical_count = sum(1 for a in analyses if a.severity == ErrorSeverity.CRITICAL)
                high_count = sum(1 for a in analyses if a.severity == ErrorSeverity.HIGH)
                
                if critical_count > 0:
                    status = FileStatus.CRITICAL
                elif high_count > 0:
                    status = FileStatus.ERROR
                else:
                    status = FileStatus.WARNING
            else:
                status = FileStatus.ERROR
        
        # Count errors by severity
        critical_errors = sum(1 for a in analyses if a.severity == ErrorSeverity.CRITICAL)
        high_errors = sum(1 for a in analyses if a.severity == ErrorSeverity.HIGH)
        medium_errors = sum(1 for a in analyses if a.severity == ErrorSeverity.MEDIUM)
        low_errors = sum(1 for a in analyses if a.severity == ErrorSeverity.LOW)
        
        # Count auto-fixable errors
        auto_fixable_count = sum(1 for a in analyses if a.auto_fixable)
        
        # Get error types
        error_types = set(a.error_type for a in analyses)
        
        # Get file stats
        lines_of_code = self._count_lines_of_code(filepath)
        last_modified = self._get_last_modified(filepath)
        
        return FileInfo(
            filepath=filepath,
            filename=filename,
            status=status,
            error_count=result.error_count,
            auto_fixable_count=auto_fixable_count,
            critical_errors=critical_errors,
            high_errors=high_errors,
            medium_errors=medium_errors,
            low_errors=low_errors,
            error_types=error_types,
            lines_of_code=lines_of_code,
            last_modified=last_modified
        )
    
    def _count_lines_of_code(self, filepath: str) -> int:
        """Count lines of code in a file (excluding empty lines and comments)."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            loc = 0
            in_multiline_comment = False
            
            for line in lines:
                stripped = line.strip()
                
                # Skip empty lines
                if not stripped:
                    continue
                
                # Handle multi-line comments
                if '/*' in stripped:
                    in_multiline_comment = True
                if '*/' in stripped:
                    in_multiline_comment = False
                    continue
                
                if in_multiline_comment:
                    continue
                
                # Skip single-line comments
                if stripped.startswith('//') or stripped.startswith('*'):
                    continue
                
                loc += 1
            
            return loc
            
        except Exception as e:
            logger.warning(f"Failed to count lines in {filepath}: {e}")
            return 0
    
    def _get_last_modified(self, filepath: str) -> float:
        """Get last modified timestamp of a file."""
        try:
            return Path(filepath).stat().st_mtime
        except Exception:
            return 0.0
    
    def filter_files(self, 
                    status: Optional[FileStatus] = None,
                    error_type: Optional[str] = None,
                    min_errors: Optional[int] = None,
                    max_errors: Optional[int] = None,
                    auto_fixable_only: bool = False,
                    filename_pattern: Optional[str] = None) -> List[FileInfo]:
        """
        Filter files based on various criteria.
        
        Args:
            status: Filter by file status
            error_type: Filter by specific error type
            min_errors: Minimum number of errors
            max_errors: Maximum number of errors
            auto_fixable_only: Only files with auto-fixable errors
            filename_pattern: Pattern to match in filename
            
        Returns:
            List of filtered FileInfo objects
        """
        filtered = self.files
        
        # Filter by status
        if status:
            filtered = [f for f in filtered if f.status == status]
        
        # Filter by error type
        if error_type:
            filtered = [f for f in filtered if error_type in f.error_types]
        
        # Filter by error count range
        if min_errors is not None:
            filtered = [f for f in filtered if f.error_count >= min_errors]
        
        if max_errors is not None:
            filtered = [f for f in filtered if f.error_count <= max_errors]
        
        # Filter by auto-fixable errors
        if auto_fixable_only:
            filtered = [f for f in filtered if f.auto_fixable_count > 0]
        
        # Filter by filename pattern
        if filename_pattern:
            import fnmatch
            filtered = [f for f in filtered if fnmatch.fnmatch(f.filename.lower(), filename_pattern.lower())]
        
        return filtered
    
    def get_files_by_status(self) -> Dict[FileStatus, List[FileInfo]]:
        """Group files by their status."""
        groups = {status: [] for status in FileStatus}
        
        for file_info in self.files:
            groups[file_info.status].append(file_info)
        
        return groups
    
    def get_files_by_error_type(self) -> Dict[str, List[FileInfo]]:
        """Group files by error types."""
        groups = {}
        
        for file_info in self.files:
            for error_type in file_info.error_types:
                if error_type not in groups:
                    groups[error_type] = []
                groups[error_type].append(file_info)
        
        return groups
    
    def get_most_problematic_files(self, limit: int = 10) -> List[FileInfo]:
        """
        Get the most problematic files based on error count and severity.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of FileInfo objects sorted by problem severity
        """
        def problem_score(file_info: FileInfo) -> float:
            """Calculate a problem score for ranking files."""
            score = 0
            score += file_info.critical_errors * 10
            score += file_info.high_errors * 5
            score += file_info.medium_errors * 2
            score += file_info.low_errors * 1
            
            # Bonus for files with many errors relative to size
            if file_info.lines_of_code > 0:
                error_density = file_info.error_count / file_info.lines_of_code
                score += error_density * 50
            
            return score
        
        sorted_files = sorted(self.files, key=problem_score, reverse=True)
        return sorted_files[:limit]
    
    def get_easiest_fixes(self, limit: int = 10) -> List[FileInfo]:
        """
        Get files that are easiest to fix (high auto-fixable ratio).
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of FileInfo objects with highest auto-fixable ratios
        """
        def fix_score(file_info: FileInfo) -> float:
            """Calculate fix score (higher = easier to fix)."""
            if file_info.error_count == 0:
                return 0
            
            auto_fix_ratio = file_info.auto_fixable_count / file_info.error_count
            return auto_fix_ratio * file_info.auto_fixable_count
        
        fixable_files = [f for f in self.files if f.auto_fixable_count > 0]
        sorted_files = sorted(fixable_files, key=fix_score, reverse=True)
        return sorted_files[:limit]
    
    def generate_project_summary(self) -> ProjectSummary:
        """Generate comprehensive project summary."""
        if not self.files:
            return ProjectSummary(
                total_files=0, ok_files=0, error_files=0, warning_files=0,
                critical_files=0, total_errors=0, auto_fixable_errors=0,
                total_lines_of_code=0, success_rate=0.0, most_common_errors=[],
                error_distribution={}, severity_distribution={}
            )
        
        # Basic counts
        total_files = len(self.files)
        status_counts = {status: 0 for status in FileStatus}
        
        for file_info in self.files:
            status_counts[file_info.status] += 1
        
        # Error statistics
        total_errors = sum(f.error_count for f in self.files)
        auto_fixable_errors = sum(f.auto_fixable_count for f in self.files)
        total_lines_of_code = sum(f.lines_of_code for f in self.files)
        
        # Success rate
        success_rate = (status_counts[FileStatus.OK] / total_files * 100) if total_files > 0 else 0
        
        # Error type distribution
        error_type_counts = {}
        for file_info in self.files:
            for error_type in file_info.error_types:
                error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
        
        # Most common errors
        most_common_errors = sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Severity distribution
        severity_distribution = {
            'critical': sum(f.critical_errors for f in self.files),
            'high': sum(f.high_errors for f in self.files),
            'medium': sum(f.medium_errors for f in self.files),
            'low': sum(f.low_errors for f in self.files)
        }
        
        return ProjectSummary(
            total_files=total_files,
            ok_files=status_counts[FileStatus.OK],
            error_files=status_counts[FileStatus.ERROR],
            warning_files=status_counts[FileStatus.WARNING],
            critical_files=status_counts[FileStatus.CRITICAL],
            total_errors=total_errors,
            auto_fixable_errors=auto_fixable_errors,
            total_lines_of_code=total_lines_of_code,
            success_rate=success_rate,
            most_common_errors=most_common_errors,
            error_distribution=error_type_counts,
            severity_distribution=severity_distribution
        )
    
    def get_recommendations(self) -> List[str]:
        """Generate recommendations based on project analysis."""
        recommendations = []
        summary = self.generate_project_summary()
        
        # Success rate recommendations
        if summary.success_rate < 50:
            recommendations.append("🚨 Project has low norminette compliance (<50%). Consider running auto-fix on all files.")
        elif summary.success_rate < 80:
            recommendations.append("⚠️ Project needs improvement. Focus on files with the most errors first.")
        else:
            recommendations.append("✅ Good norminette compliance! Focus on remaining critical errors.")
        
        # Auto-fixable recommendations
        if summary.auto_fixable_errors > 0:
            auto_fix_percentage = (summary.auto_fixable_errors / summary.total_errors * 100) if summary.total_errors > 0 else 0
            recommendations.append(f"🔧 {summary.auto_fixable_errors} errors ({auto_fix_percentage:.1f}%) can be auto-fixed.")
        
        # Critical error recommendations
        if summary.critical_files > 0:
            recommendations.append(f"🔥 {summary.critical_files} files have critical errors. Address these immediately.")
        
        # Most common error recommendations
        if summary.most_common_errors:
            top_error = summary.most_common_errors[0]
            recommendations.append(f"📊 Most common error: {top_error[0]} ({top_error[1]} occurrences). Consider project-wide fix.")
        
        # File-specific recommendations
        problematic_files = self.get_most_problematic_files(3)
        if problematic_files:
            recommendations.append(f"📁 Focus on these problematic files: {', '.join(f.filename for f in problematic_files)}")
        
        easy_fixes = self.get_easiest_fixes(3)
        if easy_fixes:
            recommendations.append(f"🎯 Quick wins available in: {', '.join(f.filename for f in easy_fixes)}")
        
        return recommendations
    
    def export_report(self, format: str = "json") -> Dict[str, Any]:
        """
        Export comprehensive report in specified format.
        
        Args:
            format: Export format ("json", "csv", "html")
            
        Returns:
            Report data as dictionary
        """
        summary = self.generate_project_summary()
        recommendations = self.get_recommendations()
        
        # Prepare file details
        file_details = []
        for file_info in self.files:
            file_details.append({
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
        
        report = {
            'summary': {
                'total_files': summary.total_files,
                'ok_files': summary.ok_files,
                'error_files': summary.error_files,
                'warning_files': summary.warning_files,
                'critical_files': summary.critical_files,
                'total_errors': summary.total_errors,
                'auto_fixable_errors': summary.auto_fixable_errors,
                'total_lines_of_code': summary.total_lines_of_code,
                'success_rate': summary.success_rate,
                'most_common_errors': summary.most_common_errors,
                'error_distribution': summary.error_distribution,
                'severity_distribution': summary.severity_distribution
            },
            'recommendations': recommendations,
            'files': file_details,
            'most_problematic_files': [
                {
                    'filename': f.filename,
                    'error_count': f.error_count,
                    'status': f.status.value
                }
                for f in self.get_most_problematic_files(10)
            ],
            'easiest_fixes': [
                {
                    'filename': f.filename,
                    'auto_fixable_count': f.auto_fixable_count,
                    'total_errors': f.error_count
                }
                for f in self.get_easiest_fixes(10)
            ]
        }
        
        return report
    
    def search_files(self, query: str) -> List[FileInfo]:
        """
        Search files by filename or error content.
        
        Args:
            query: Search query
            
        Returns:
            List of matching FileInfo objects
        """
        query_lower = query.lower()
        matches = []
        
        for file_info in self.files:
            # Search in filename
            if query_lower in file_info.filename.lower():
                matches.append(file_info)
                continue
            
            # Search in filepath
            if query_lower in file_info.filepath.lower():
                matches.append(file_info)
                continue
            
            # Search in error types
            if any(query_lower in error_type.lower() for error_type in file_info.error_types):
                matches.append(file_info)
                continue
        
        return matches
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics for dashboard display."""
        summary = self.generate_project_summary()
        
        return {
            'overview': {
                'total_files': summary.total_files,
                'success_rate': summary.success_rate,
                'total_errors': summary.total_errors,
                'auto_fixable_percentage': (summary.auto_fixable_errors / summary.total_errors * 100) if summary.total_errors > 0 else 0
            },
            'file_status_distribution': {
                'OK': summary.ok_files,
                'Warning': summary.warning_files,
                'Error': summary.error_files,
                'Critical': summary.critical_files
            },
            'error_severity_distribution': summary.severity_distribution,
            'error_type_distribution': dict(summary.most_common_errors[:10]),
            'code_metrics': {
                'total_lines_of_code': summary.total_lines_of_code,
                'average_errors_per_file': summary.total_errors / summary.total_files if summary.total_files > 0 else 0,
                'error_density': summary.total_errors / summary.total_lines_of_code if summary.total_lines_of_code > 0 else 0
            }
        }