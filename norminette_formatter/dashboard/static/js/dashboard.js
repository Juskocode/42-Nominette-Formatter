/**
 * 42-Norminette-Formatter Dashboard JavaScript
 * 
 * This file handles all the interactive functionality of the dashboard
 * including API calls, UI updates, filtering, and user interactions.
 */

class NorminetteDashboard {
    constructor() {
        this.currentProject = null;
        this.currentFiles = [];
        this.selectedFiles = new Set();
        this.currentFileDetails = null;
        
        this.initializeEventListeners();
        this.initializeTooltips();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Project scanning
        document.getElementById('scan-btn').addEventListener('click', () => this.scanProject());
        document.getElementById('rescan-btn').addEventListener('click', () => this.rescanProject());
        
        // Enter key support for project path input
        document.getElementById('project-path-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.scanProject();
            }
        });

        // Filtering
        document.getElementById('status-filter').addEventListener('change', () => this.applyFilters());
        document.getElementById('error-type-filter').addEventListener('change', () => this.applyFilters());
        document.getElementById('auto-fixable-only').addEventListener('change', () => this.applyFilters());
        document.getElementById('search-input').addEventListener('input', () => this.debounce(() => this.applyFilters(), 300)());

        // Actions
        document.getElementById('fix-all-btn').addEventListener('click', () => this.fixAllAutoFixable());
        document.getElementById('fix-selected-btn').addEventListener('click', () => this.fixSelectedFiles());
        document.getElementById('export-btn').addEventListener('click', () => this.exportReport());

        // File selection
        document.getElementById('select-all-files').addEventListener('change', (e) => this.toggleSelectAll(e.target.checked));

        // Modal actions
        document.getElementById('preview-fixes-btn').addEventListener('click', () => this.previewFixes());
        document.getElementById('apply-fixes-btn').addEventListener('click', () => this.applyFixes());
        document.getElementById('confirm-apply-btn').addEventListener('click', () => this.confirmApplyFixes());
    }

    /**
     * Initialize Bootstrap tooltips
     */
    initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Debounce function for search input
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Show loading spinner
     */
    showLoading() {
        document.getElementById('loading-spinner').classList.remove('d-none');
    }

    /**
     * Hide loading spinner
     */
    hideLoading() {
        document.getElementById('loading-spinner').classList.add('d-none');
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastBody = document.getElementById('toast-body');
        
        toastBody.textContent = message;
        
        // Update toast styling based on type
        toast.className = `toast ${type === 'success' ? 'bg-success text-white' : 
                                  type === 'error' ? 'bg-danger text-white' : 
                                  type === 'warning' ? 'bg-warning text-dark' : 'bg-info text-white'}`;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    /**
     * Scan project for norminette errors
     */
    async scanProject() {
        const projectPath = document.getElementById('project-path-input').value.trim();
        
        if (!projectPath) {
            this.showToast('Please enter a project path', 'warning');
            return;
        }

        this.showLoading();
        document.getElementById('scan-progress').style.display = 'block';

        try {
            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ project_path: projectPath })
            });

            const result = await response.json();

            if (result.success) {
                this.currentProject = result;
                this.updateProjectOverview(result);
                this.updateRecommendations(result.recommendations);
                await this.loadFiles();
                this.showProjectSections();
                this.showToast('Project scanned successfully!', 'success');
                
                // Update UI elements
                document.getElementById('project-path').textContent = projectPath;
                document.getElementById('rescan-btn').style.display = 'inline-block';
            } else {
                this.showToast(`Scan failed: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Scan error:', error);
            this.showToast('Failed to scan project. Please check the console for details.', 'error');
        } finally {
            this.hideLoading();
            document.getElementById('scan-progress').style.display = 'none';
        }
    }

    /**
     * Re-scan current project
     */
    async rescanProject() {
        const projectPath = document.getElementById('project-path-input').value.trim();
        if (projectPath) {
            await this.scanProject();
        }
    }

    /**
     * Update project overview section
     */
    updateProjectOverview(result) {
        const summary = result.summary;
        
        document.getElementById('total-files').textContent = summary.total_files;
        document.getElementById('ok-files').textContent = summary.ok_files;
        document.getElementById('error-files').textContent = summary.error_files;
        document.getElementById('success-rate').textContent = `${summary.success_rate.toFixed(1)}%`;
        document.getElementById('total-errors').textContent = summary.total_errors;
        document.getElementById('auto-fixable').textContent = summary.auto_fixable_errors;
    }

    /**
     * Update recommendations section
     */
    updateRecommendations(recommendations) {
        const container = document.getElementById('recommendations-list');
        container.innerHTML = '';

        recommendations.forEach(recommendation => {
            const item = document.createElement('div');
            item.className = 'recommendation-item';
            
            // Determine recommendation type based on emoji
            if (recommendation.includes('🚨')) {
                item.classList.add('critical');
            } else if (recommendation.includes('⚠️')) {
                item.classList.add('warning');
            } else if (recommendation.includes('✅')) {
                item.classList.add('success');
            }
            
            item.textContent = recommendation;
            container.appendChild(item);
        });
    }

    /**
     * Show project sections after successful scan
     */
    showProjectSections() {
        document.getElementById('overview-section').style.display = 'block';
        document.getElementById('recommendations-section').style.display = 'block';
        document.getElementById('filters-section').style.display = 'block';
        document.getElementById('files-section').style.display = 'block';
        
        // Add fade-in animation
        document.getElementById('overview-section').classList.add('fade-in');
        document.getElementById('recommendations-section').classList.add('fade-in');
        document.getElementById('filters-section').classList.add('fade-in');
        document.getElementById('files-section').classList.add('fade-in');
    }

    /**
     * Load files list
     */
    async loadFiles() {
        try {
            const response = await fetch('/api/files');
            const result = await response.json();

            if (result.success) {
                this.currentFiles = result.files;
                this.populateErrorTypeFilter();
                this.renderFilesTable();
            } else {
                this.showToast('Failed to load files', 'error');
            }
        } catch (error) {
            console.error('Load files error:', error);
            this.showToast('Failed to load files', 'error');
        }
    }

    /**
     * Populate error type filter dropdown
     */
    populateErrorTypeFilter() {
        const errorTypes = new Set();
        this.currentFiles.forEach(file => {
            file.error_types.forEach(type => errorTypes.add(type));
        });

        const select = document.getElementById('error-type-filter');
        // Clear existing options except "All Types"
        select.innerHTML = '<option value="all">All Types</option>';

        Array.from(errorTypes).sort().forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type.replace('_', ' ').toUpperCase();
            select.appendChild(option);
        });
    }

    /**
     * Apply filters to files list
     */
    async applyFilters() {
        const status = document.getElementById('status-filter').value;
        const errorType = document.getElementById('error-type-filter').value;
        const autoFixableOnly = document.getElementById('auto-fixable-only').checked;
        const search = document.getElementById('search-input').value;

        const params = new URLSearchParams();
        if (status !== 'all') params.append('status', status);
        if (errorType !== 'all') params.append('error_type', errorType);
        if (autoFixableOnly) params.append('auto_fixable_only', 'true');
        if (search) params.append('search', search);

        try {
            const response = await fetch(`/api/files?${params}`);
            const result = await response.json();

            if (result.success) {
                this.currentFiles = result.files;
                this.renderFilesTable();
            }
        } catch (error) {
            console.error('Filter error:', error);
            this.showToast('Failed to apply filters', 'error');
        }
    }

    /**
     * Render files table
     */
    renderFilesTable() {
        const tbody = document.getElementById('files-table-body');
        tbody.innerHTML = '';

        document.getElementById('files-count').textContent = `${this.currentFiles.length} files`;

        this.currentFiles.forEach(file => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox" class="file-checkbox" value="${file.filepath}" 
                           ${this.selectedFiles.has(file.filepath) ? 'checked' : ''}>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <i class="fas fa-file-code me-2"></i>
                        <div>
                            <div class="fw-bold">${file.filename}</div>
                            <small class="text-muted">${file.filepath}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="status-badge status-${file.status.toLowerCase()}">${file.status}</span>
                </td>
                <td>
                    <span class="badge ${file.error_count > 0 ? 'bg-danger' : 'bg-success'}">
                        ${file.error_count}
                    </span>
                </td>
                <td>
                    <span class="badge ${file.auto_fixable_count > 0 ? 'bg-success' : 'bg-secondary'}">
                        ${file.auto_fixable_count}
                    </span>
                </td>
                <td>
                    ${file.error_types.map(type => 
                        `<span class="error-type-badge">${type.replace('_', ' ')}</span>`
                    ).join('')}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="dashboard.viewFileDetails('${file.filepath}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                    ${file.auto_fixable_count > 0 ? 
                        `<button class="btn btn-sm btn-outline-success" onclick="dashboard.quickFix('${file.filepath}')">
                            <i class="fas fa-magic"></i> Fix
                        </button>` : ''
                    }
                </td>
            `;
            tbody.appendChild(row);
        });

        // Add event listeners for checkboxes
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedFiles.add(e.target.value);
                } else {
                    this.selectedFiles.delete(e.target.value);
                }
                this.updateSelectedFilesUI();
            });
        });
    }

    /**
     * Toggle select all files
     */
    toggleSelectAll(checked) {
        this.selectedFiles.clear();
        
        if (checked) {
            this.currentFiles.forEach(file => {
                this.selectedFiles.add(file.filepath);
            });
        }

        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
        });

        this.updateSelectedFilesUI();
    }

    /**
     * Update UI based on selected files
     */
    updateSelectedFilesUI() {
        const selectedCount = this.selectedFiles.size;
        const fixSelectedBtn = document.getElementById('fix-selected-btn');
        
        if (selectedCount > 0) {
            fixSelectedBtn.textContent = `Fix Selected (${selectedCount})`;
            fixSelectedBtn.disabled = false;
        } else {
            fixSelectedBtn.textContent = 'Fix Selected';
            fixSelectedBtn.disabled = true;
        }
    }

    /**
     * View file details in modal
     */
    async viewFileDetails(filepath) {
        this.showLoading();

        try {
            const response = await fetch(`/api/files/${encodeURIComponent(filepath)}`);
            const result = await response.json();

            if (result.success) {
                this.currentFileDetails = result;
                this.renderFileDetailsModal(result);
                const modal = new bootstrap.Modal(document.getElementById('file-details-modal'));
                modal.show();
            } else {
                this.showToast('Failed to load file details', 'error');
            }
        } catch (error) {
            console.error('File details error:', error);
            this.showToast('Failed to load file details', 'error');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Render file details modal content
     */
    renderFileDetailsModal(fileData) {
        const container = document.getElementById('file-details-content');
        
        let html = `
            <div class="mb-3">
                <h6>File Information</h6>
                <p><strong>Path:</strong> ${fileData.filepath}</p>
                <p><strong>Status:</strong> <span class="status-badge status-${fileData.status.toLowerCase()}">${fileData.status}</span></p>
                <p><strong>Total Errors:</strong> ${fileData.error_count}</p>
                <p><strong>Auto-fixable:</strong> ${fileData.auto_fixable_count}</p>
            </div>
        `;

        if (Object.keys(fileData.error_groups).length > 0) {
            html += '<h6>Errors by Type</h6>';
            
            Object.entries(fileData.error_groups).forEach(([errorType, errors]) => {
                html += `
                    <div class="error-group">
                        <div class="error-group-header">
                            ${errorType.replace('_', ' ').toUpperCase()} (${errors.length})
                        </div>
                `;
                
                errors.forEach(error => {
                    html += `
                        <div class="error-item">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="error-rule">${error.rule}</span>
                                <div>
                                    <span class="severity-${error.severity}">${error.severity.toUpperCase()}</span>
                                    <span class="auto-fixable-indicator ${error.auto_fixable ? 'auto-fixable-yes' : 'auto-fixable-no'}" 
                                          title="${error.auto_fixable ? 'Auto-fixable' : 'Manual fix required'}"></span>
                                </div>
                            </div>
                            <div class="error-location">Line ${error.line}, Column ${error.column}</div>
                            <div class="error-description">${error.description}</div>
                            <div class="error-suggestion">${error.fix_suggestion}</div>
                        </div>
                    `;
                });
                
                html += '</div>';
            });
        } else {
            html += '<div class="alert alert-success">No errors found in this file!</div>';
        }

        container.innerHTML = html;

        // Update modal buttons
        const previewBtn = document.getElementById('preview-fixes-btn');
        const applyBtn = document.getElementById('apply-fixes-btn');
        
        if (fileData.auto_fixable_count > 0) {
            previewBtn.style.display = 'inline-block';
            applyBtn.style.display = 'inline-block';
        } else {
            previewBtn.style.display = 'none';
            applyBtn.style.display = 'none';
        }
    }

    /**
     * Preview fixes for current file
     */
    async previewFixes() {
        if (!this.currentFileDetails) return;

        this.showLoading();

        try {
            const response = await fetch('/api/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filepath: this.currentFileDetails.filepath })
            });

            const result = await response.json();

            if (result.success) {
                document.getElementById('preview-content').textContent = result.preview;
                const modal = new bootstrap.Modal(document.getElementById('preview-modal'));
                modal.show();
            } else {
                this.showToast('Failed to generate preview', 'error');
            }
        } catch (error) {
            console.error('Preview error:', error);
            this.showToast('Failed to generate preview', 'error');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Apply fixes to current file
     */
    async applyFixes() {
        if (!this.currentFileDetails) return;

        await this.formatFile(this.currentFileDetails.filepath);
        
        // Close modal and refresh data
        const modal = bootstrap.Modal.getInstance(document.getElementById('file-details-modal'));
        modal.hide();
        
        await this.loadFiles();
    }

    /**
     * Confirm and apply fixes from preview modal
     */
    async confirmApplyFixes() {
        if (!this.currentFileDetails) return;

        await this.formatFile(this.currentFileDetails.filepath);
        
        // Close modals and refresh data
        const previewModal = bootstrap.Modal.getInstance(document.getElementById('preview-modal'));
        const detailsModal = bootstrap.Modal.getInstance(document.getElementById('file-details-modal'));
        
        previewModal.hide();
        if (detailsModal) detailsModal.hide();
        
        await this.loadFiles();
    }

    /**
     * Quick fix for a single file
     */
    async quickFix(filepath) {
        await this.formatFile(filepath);
        await this.loadFiles();
    }

    /**
     * Format a single file
     */
    async formatFile(filepath) {
        this.showLoading();

        try {
            const response = await fetch('/api/format', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filepath: filepath })
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(`Fixed ${result.changes_made} errors in ${filepath.split('/').pop()}`, 'success');
            } else {
                this.showToast(`Failed to fix ${filepath.split('/').pop()}: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Format error:', error);
            this.showToast('Failed to format file', 'error');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Fix all auto-fixable errors
     */
    async fixAllAutoFixable() {
        const autoFixableFiles = this.currentFiles.filter(file => file.auto_fixable_count > 0);
        
        if (autoFixableFiles.length === 0) {
            this.showToast('No auto-fixable errors found', 'warning');
            return;
        }

        if (!confirm(`This will fix auto-fixable errors in ${autoFixableFiles.length} files. Continue?`)) {
            return;
        }

        await this.bulkFormat(autoFixableFiles.map(file => file.filepath));
    }

    /**
     * Fix selected files
     */
    async fixSelectedFiles() {
        if (this.selectedFiles.size === 0) {
            this.showToast('No files selected', 'warning');
            return;
        }

        if (!confirm(`This will fix auto-fixable errors in ${this.selectedFiles.size} selected files. Continue?`)) {
            return;
        }

        await this.bulkFormat(Array.from(this.selectedFiles));
    }

    /**
     * Bulk format multiple files
     */
    async bulkFormat(filepaths) {
        this.showLoading();

        try {
            const response = await fetch('/api/format/bulk', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    filepaths: filepaths,
                    auto_fixable_only: true
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(`Successfully processed ${result.total_files_processed} files with ${result.total_changes} total changes`, 'success');
                await this.loadFiles();
                
                // Clear selections
                this.selectedFiles.clear();
                document.getElementById('select-all-files').checked = false;
                this.updateSelectedFilesUI();
            } else {
                this.showToast('Bulk format failed', 'error');
            }
        } catch (error) {
            console.error('Bulk format error:', error);
            this.showToast('Bulk format failed', 'error');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Export project report
     */
    async exportReport() {
        try {
            const response = await fetch('/api/export?format=json');
            const result = await response.json();

            // Create and download file
            const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `norminette-report-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showToast('Report exported successfully', 'success');
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Failed to export report', 'error');
        }
    }
}

// Initialize dashboard when DOM is loaded
let dashboard;
document.addEventListener('DOMContentLoaded', function() {
    dashboard = new NorminetteDashboard();
});

// Make dashboard globally available for onclick handlers
window.dashboard = dashboard;