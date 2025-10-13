// main.js - Handles clause analysis form submission, results display, and dashboard functionality

document.addEventListener('DOMContentLoaded', function() {
    // Only initialize analyze functionality if we're on the analyze page (not dashboard)
    if (document.getElementById('analyses-container')) {
        initializeDashboard();
        return;
    }

    // Analyze page functionality
    const form = document.getElementById('clause-form');
    if (!form) return; // Not on analyze page

    const textarea = document.getElementById('clause-text');
    const submitBtn = document.getElementById('submit-btn');
    const resultsDiv = document.getElementById('results');
    const ruleResultsDiv = document.getElementById('rule-results');
    const aiResultsDiv = document.getElementById('ai-results');
    const saveBtn = document.getElementById('save-btn');
    const loadingDiv = document.getElementById('loading');
    const errorDiv = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');

    let currentAnalysis = null;
    let analysisStartTime = null;

    // Form submission handler
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const clauseText = textarea.value.trim();
        if (!clauseText) {
            showError('Please enter clause text to analyze.');
            return;
        }

        if (clauseText.length > 10000) {
            showError('Clause text is too long (maximum 10,000 characters).');
            return;
        }

        // Reset state
        currentAnalysis = null;
        analysisStartTime = Date.now();
        showLoading(true);
        hideResults();
        hideError();

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ clause_text: clauseText })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Analysis failed');
            }

            // Store current analysis for saving
            currentAnalysis = data;

            // Display results
            displayResults(data);
            showLoading(false);

        } catch (error) {
            showError(getErrorMessage(error));
            showLoading(false);
        }
    });

    // Save to GitHub handler
    saveBtn.addEventListener('click', async function() {
        if (!currentAnalysis) {
            showError('No analysis to save. Please analyze a clause first.');
            return;
        }

        // Show loading state
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';

        try {
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ analysis_data: currentAnalysis })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Save failed');
            }

            alert(`Analysis saved successfully! ID: ${data.analysis_id}`);
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save to GitHub';

        } catch (error) {
            showError(getErrorMessage(error));
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save to GitHub';
        }
    });

    function displayResults(data) {
        const analysisTime = Date.now() - analysisStartTime;

        // Display rule-based results
        const ruleResult = data.rule_based;
        ruleResultsDiv.innerHTML = `
            <div class="mb-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-xl font-semibold text-blue-900">Rule-Based Analysis</h3>
                    <span class="text-xs bg-blue-200 text-blue-800 px-2 py-1 rounded-full">Completed in ${analysisTime}ms</span>
                </div>
            </div>
            <div class="space-y-3">
                <div class="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span class="font-medium">Clause Type:</span>
                    <span class="text-blue-700">${ruleResult.clause_type}</span>
                </div>
                <div class="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span class="font-medium">Risk Score:</span>
                    <span class="text-blue-700">${ruleResult.risk_score}/10</span>
                </div>
                <div class="p-3 bg-blue-50 rounded-lg">
                    <span class="font-medium">Flags:</span>
                    <div class="mt-1 text-blue-700">
                        ${ruleResult.flags.length > 0 ? ruleResult.flags.map(flag => `<div>• ${flag}</div>`).join('') : '<div>No flags raised</div>'}
                    </div>
                </div>
                <div class="p-3 bg-blue-50 rounded-lg">
                    <span class="font-medium">Summary:</span>
                    <div class="mt-1 text-blue-700">${ruleResult.summary}</div>
                </div>
            </div>
        `;

        // Display AI-based results
        const aiResult = data.ai_based;
        const hasError = aiResult.error;
        aiResultsDiv.innerHTML = `
            <div class="mb-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-xl font-semibold text-green-900">AI Analysis</h3>
                    <span class="text-xs ${hasError ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'} px-2 py-1 rounded-full">
                        ${hasError ? 'Error' : 'Completed'}
                    </span>
                </div>
            </div>
            <div class="space-y-3">
                ${hasError ? `
                    <div class="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <div class="flex items-center text-red-700">
                            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                            </svg>
                            ${aiResult.error}
                        </div>
                    </div>
                ` : `
                    <div class="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                        <span class="font-medium">Clause Type:</span>
                        <span class="text-green-700">${aiResult.clause_type}</span>
                    </div>
                    <div class="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                        <span class="font-medium">Risk Level:</span>
                        <span class="text-green-700">${aiResult.risk_level}</span>
                    </div>
                    <div class="p-3 bg-green-50 rounded-lg">
                        <span class="font-medium">Key Terms:</span>
                        <div class="mt-1 flex flex-wrap gap-1">
                            ${aiResult.key_terms.map(term => `<span class="px-2 py-1 bg-green-200 text-green-800 text-xs rounded-full">${term}</span>`).join('')}
                        </div>
                    </div>
                    <div class="p-3 bg-green-50 rounded-lg">
                        <span class="font-medium">Summary:</span>
                        <div class="mt-1 text-green-700">${aiResult.summary}</div>
                    </div>
                    <div class="p-3 bg-green-50 rounded-lg">
                        <span class="font-medium">Recommendations:</span>
                        <ul class="mt-1 text-green-700 list-disc list-inside">
                            ${aiResult.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                        </ul>
                    </div>
                `}
            </div>
        `;

        resultsDiv.style.display = 'block';
        saveBtn.style.display = 'block';

        // Update comparison bars
        if (window.updateComparisonBars) {
            window.updateComparisonBars(data);
        }
    }

    function showLoading(show) {
        loadingDiv.style.display = show ? 'block' : 'none';
        submitBtn.disabled = show;
        if (show) {
            submitBtn.textContent = 'Analyzing...';
        } else {
            submitBtn.textContent = 'Analyze Clause';
        }
    }

    function hideResults() {
        resultsDiv.style.display = 'none';
        saveBtn.style.display = 'none';
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
        // Scroll to error
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    function hideError() {
        errorDiv.style.display = 'none';
    }

    function getErrorMessage(error) {
        const message = error.message || error.toString();

        // Provide user-friendly error messages
        if (message.includes('rate limit')) {
            return 'API rate limit exceeded. Please wait a moment and try again.';
        } else if (message.includes('timeout')) {
            return 'Request timed out. Please check your internet connection and try again.';
        } else if (message.includes('network') || message.includes('fetch')) {
            return 'Network error. Please check your internet connection and try again.';
        } else if (message.includes('GitHub service not configured')) {
            return 'GitHub service is not configured. Please check your settings.';
        } else if (message.includes('OpenAI API key not configured')) {
            return 'OpenAI API key is not configured. Please configure it in settings to enable AI analysis.';
        } else {
            return message;
        }
    }

    // Network status monitoring
    window.addEventListener('online', function() {
        console.log('Network connection restored');
    });

    window.addEventListener('offline', function() {
        showError('Network connection lost. Please check your internet connection.');
    });

    // Auto-hide error after 10 seconds
    let errorTimeout;
    function showError(message) {
        clearTimeout(errorTimeout);
        errorMessage.textContent = message;
        errorDiv.style.display = 'block';
        errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });

        errorTimeout = setTimeout(() => {
            hideError();
        }, 10000); // Hide after 10 seconds
    }

    // Dashboard functionality is now handled at the top of the file
});

function initializeDashboard() {
    const searchInput = document.getElementById('search-input');
    const sortSelect = document.getElementById('sort-select');
    const analysesContainer = document.getElementById('analyses-container');
    const analysisCards = document.querySelectorAll('.analysis-card');
    const viewDetailsBtns = document.querySelectorAll('.view-details-btn');
    const modal = document.getElementById('analysis-modal');
    const modalContent = document.getElementById('modal-content');

    let analyses = [];
    let filteredAnalyses = [];

    // Load analyses data from the page (passed from Flask)
    function loadAnalysesData() {
        analyses = Array.from(analysisCards).map(card => {
            const analysisId = card.dataset.analysisId;
            const title = card.querySelector('h4').textContent;
            const riskBadge = card.querySelector('.risk-badge').textContent.trim();
            const summary = card.querySelector('p').textContent;
            const date = card.querySelectorAll('span')[1].textContent;
            const riskScore = card.querySelectorAll('span')[2]?.textContent.match(/(\d+)\/10/)?.[1] || 0;

            return {
                id: analysisId,
                title: title,
                risk: riskBadge,
                summary: summary,
                date: date,
                riskScore: parseInt(riskScore),
                element: card
            };
        });
        filteredAnalyses = [...analyses];
        updateStatistics();
        initializeCharts();
    }

    // Update statistics cards
    function updateStatistics() {
        const totalAnalyses = filteredAnalyses.length;
        document.getElementById('total-analyses').textContent = totalAnalyses;

        let highRisk = 0, mediumRisk = 0, lowRisk = 0;
        filteredAnalyses.forEach(analysis => {
            if (analysis.risk === 'High' || analysis.riskScore >= 7) {
                highRisk++;
            } else if (analysis.risk === 'Medium' || analysis.riskScore >= 4) {
                mediumRisk++;
            } else {
                lowRisk++;
            }
        });

        document.getElementById('high-risk-count').textContent = highRisk;
        document.getElementById('medium-risk-count').textContent = mediumRisk;
        document.getElementById('low-risk-count').textContent = lowRisk;
    }

    // Initialize charts
    function initializeCharts() {
        const riskChartCanvas = document.getElementById('riskChart');
        const activityChartCanvas = document.getElementById('activityChart');

        if (!riskChartCanvas || !activityChartCanvas) return;

        // Risk distribution chart
        const riskCounts = { High: 0, Medium: 0, Low: 0 };
        filteredAnalyses.forEach(analysis => {
            if (analysis.risk === 'High' || analysis.riskScore >= 7) {
                riskCounts.High++;
            } else if (analysis.risk === 'Medium' || analysis.riskScore >= 4) {
                riskCounts.Medium++;
            } else {
                riskCounts.Low++;
            }
        });

        new Chart(riskChartCanvas, {
            type: 'doughnut',
            data: {
                labels: ['High Risk', 'Medium Risk', 'Low Risk'],
                datasets: [{
                    data: [riskCounts.High, riskCounts.Medium, riskCounts.Low],
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Activity timeline chart (simplified - showing analyses per day)
        const activityData = {};
        filteredAnalyses.forEach(analysis => {
            const date = analysis.date;
            activityData[date] = (activityData[date] || 0) + 1;
        });

        const sortedDates = Object.keys(activityData).sort();
        const activityCounts = sortedDates.map(date => activityData[date]);

        new Chart(activityChartCanvas, {
            type: 'line',
            data: {
                labels: sortedDates,
                datasets: [{
                    label: 'Analyses',
                    data: activityCounts,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Search and filter functionality
    function filterAnalyses() {
        const searchTerm = searchInput.value.toLowerCase();
        const sortBy = sortSelect.value;

        filteredAnalyses = analyses.filter(analysis =>
            analysis.title.toLowerCase().includes(searchTerm) ||
            analysis.summary.toLowerCase().includes(searchTerm) ||
            analysis.id.toLowerCase().includes(searchTerm)
        );

        // Sort analyses
        filteredAnalyses.sort((a, b) => {
            switch (sortBy) {
                case 'date-desc':
                    return new Date(b.date) - new Date(a.date);
                case 'date-asc':
                    return new Date(a.date) - new Date(b.date);
                case 'risk-desc':
                    return b.riskScore - a.riskScore;
                case 'risk-asc':
                    return a.riskScore - b.riskScore;
                default:
                    return 0;
            }
        });

        renderAnalyses();
        updateStatistics();
        initializeCharts();
    }

    // Render filtered analyses
    function renderAnalyses() {
        // Hide all cards first
        analysisCards.forEach(card => card.style.display = 'none');

        // Show filtered cards
        filteredAnalyses.forEach(analysis => {
            analysis.element.style.display = 'block';
        });
    }

    // Modal functionality
    function openModal(analysisId) {
        // Fetch detailed analysis data
        fetch(`/api/analysis/${analysisId}`)
            .then(response => response.json())
            .then(data => {
                modalContent.innerHTML = generateModalContent(data);
                modal.classList.remove('hidden');
            })
            .catch(error => {
                console.error('Error loading analysis details:', error);
                modalContent.innerHTML = '<p class="text-red-600">Error loading analysis details.</p>';
                modal.classList.remove('hidden');
            });
    }

    function closeModal() {
        modal.classList.add('hidden');
        modalContent.innerHTML = '';
    }

    function generateModalContent(data) {
        return `
            <div class="space-y-6">
                <div class="border-b pb-4">
                    <h3 class="text-xl font-semibold text-slate-800">${data.rule_based?.clause_type || data.ai_based?.clause_type || 'Analysis Details'}</h3>
                    <p class="text-sm text-slate-600">Analysis ID: ${data.analysis_id} | Generated: ${new Date(data.timestamp).toLocaleString()}</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Rule-Based Analysis -->
                    <div class="space-y-4">
                        <h4 class="text-lg font-medium text-blue-900">Rule-Based Analysis</h4>
                        <div class="space-y-3">
                            <div class="flex justify-between p-3 bg-blue-50 rounded">
                                <span class="font-medium">Clause Type:</span>
                                <span>${data.rule_based?.clause_type || 'N/A'}</span>
                            </div>
                            <div class="flex justify-between p-3 bg-blue-50 rounded">
                                <span class="font-medium">Risk Score:</span>
                                <span>${data.rule_based?.risk_score || 0}/10</span>
                            </div>
                            <div class="p-3 bg-blue-50 rounded">
                                <span class="font-medium">Flags:</span>
                                <div class="mt-2 space-y-1">
                                    ${data.rule_based?.flags?.map(flag => `<div class="text-sm">• ${flag}</div>`).join('') || '<div class="text-sm">No flags</div>'}
                                </div>
                            </div>
                            <div class="p-3 bg-blue-50 rounded">
                                <span class="font-medium">Summary:</span>
                                <p class="mt-2 text-sm">${data.rule_based?.summary || 'No summary available'}</p>
                            </div>
                        </div>
                    </div>

                    <!-- AI Analysis -->
                    <div class="space-y-4">
                        <h4 class="text-lg font-medium text-green-900">AI Analysis</h4>
                        <div class="space-y-3">
                            ${data.ai_based?.error ? `
                                <div class="p-3 bg-red-50 border border-red-200 rounded">
                                    <div class="flex items-center text-red-700">
                                        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                                        </svg>
                                        ${data.ai_based.error}
                                    </div>
                                </div>
                            ` : `
                                <div class="flex justify-between p-3 bg-green-50 rounded">
                                    <span class="font-medium">Clause Type:</span>
                                    <span>${data.ai_based?.clause_type || 'N/A'}</span>
                                </div>
                                <div class="flex justify-between p-3 bg-green-50 rounded">
                                    <span class="font-medium">Risk Level:</span>
                                    <span>${data.ai_based?.risk_level || 'N/A'}</span>
                                </div>
                                <div class="p-3 bg-green-50 rounded">
                                    <span class="font-medium">Key Terms:</span>
                                    <div class="mt-2 flex flex-wrap gap-1">
                                        ${data.ai_based?.key_terms?.map(term => `<span class="px-2 py-1 bg-green-200 text-green-800 text-xs rounded-full">${term}</span>`).join('') || 'None identified'}
                                    </div>
                                </div>
                                <div class="p-3 bg-green-50 rounded">
                                    <span class="font-medium">Summary:</span>
                                    <p class="mt-2 text-sm">${data.ai_based?.summary || 'No summary available'}</p>
                                </div>
                                <div class="p-3 bg-green-50 rounded">
                                    <span class="font-medium">Recommendations:</span>
                                    <ul class="mt-2 text-sm list-disc list-inside space-y-1">
                                        ${data.ai_based?.recommendations?.map(rec => `<li>${rec}</li>`).join('') || '<li>No recommendations</li>'}
                                    </ul>
                                </div>
                            `}
                        </div>
                    </div>
                </div>

                <div class="flex justify-end space-x-3 pt-4 border-t">
                    <button onclick="closeModal()" class="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300">Close</button>
                    <button onclick="generatePDF('${data.analysis_id}')" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Download PDF</button>
                </div>
            </div>
        `;
    }

    // Event listeners
    searchInput.addEventListener('input', filterAnalyses);
    sortSelect.addEventListener('change', filterAnalyses);

    viewDetailsBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const analysisId = e.target.dataset.analysisId;
            openModal(analysisId);
        });
    });

    // Close modal when clicking backdrop
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Initialize dashboard
    loadAnalysesData();
}

function generatePDF(analysisId) {
    // This would trigger the PDF generation endpoint
    window.open(`/api/generate-pdf?analysis_id=${analysisId}`, '_blank');
}
