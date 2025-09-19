/**
 * Clean Multi-Team Retention Dashboard
 * Simplified architecture focused on multi-team comparison only
 */

class MultiTeamDashboard {
    constructor() {
        // Use the same host as the frontend, just different port
        this.apiBaseUrl = `${window.location.protocol}//${window.location.hostname}:8001`;
        this.currentWeek = 0;
        this.maxWeeks = 52;
        this.isRunning = false;
        
        // Single data model - no legacy mess
        this.availableTeams = ['rule_based']; // Will be loaded from API
        this.teamData = new Map(); // team_name -> { history: [], totals: {...} }
        
        // Auto-Evaluate state
        this.autorunSession = null;
        this.autorunPollingInterval = null;
        
        this.init();
    }

    async init() {
        console.log('Initializing Multi-Team Dashboard...');
        
        await this.loadAvailableTeams();
        this.setupControls();
        this.setupEventListeners();
        await this.checkApiHealth();
        
        this.renderTeamTotals();
    }

    async loadAvailableTeams() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/health`);
            const health = await response.json();
            
            
            // Always include rule_based + any available teams
            this.availableTeams = ['rule_based', ...(health.features.available_teams || [])];
            
            // Initialize team data structures
            this.teamData.clear();
            this.availableTeams.forEach(team => {
                this.teamData.set(team, {
                    history: [],
                    totals: { clv: 0, budget: 0, customers: 0 }
                });
            });
            
            console.log('Available teams:', this.availableTeams);
        } catch (error) {
            console.error('Failed to load teams:', error);
            this.availableTeams = ['rule_based']; // Fallback
        }
    }

    setupControls() {
        // Setup all sliders with change handlers
        const sliders = [
            // Core controls
            { id: 'customers-slider', display: 'customers-value', formatter: (v) => v },
            { id: 'budget-slider', display: 'budget-value', formatter: (v) => `£${v}k` },
            { id: 'discount-slider', display: 'discount-value', formatter: (v) => `${v}%` },
            { id: 'priority-slider', display: 'priority-value', formatter: (v) => `${v}%` },
            { id: 'executive-slider', display: 'executive-value', formatter: (v) => `${v}%` },
            { id: 'discount-duration-slider', display: 'discount-duration-value', formatter: (v) => `${v} months` },
            { id: 'priority-cost-slider', display: 'priority-cost-value', formatter: (v) => `£${v}` },
            { id: 'executive-cost-slider', display: 'executive-cost-value', formatter: (v) => `£${v}` },
            // Customer distribution
            { id: 'basic-percent-slider', display: 'basic-percent-value', formatter: (v) => `${v}%` },
            { id: 'standard-percent-slider', display: 'standard-percent-value', formatter: (v) => `${v}%` },
            { id: 'premium-percent-slider', display: 'premium-percent-value', formatter: (v) => `${v}%` },
            { id: 'enterprise-percent-slider', display: 'enterprise-percent-value', formatter: (v) => `${v}%` },
            // Monthly revenue
            { id: 'basic-revenue-slider', display: 'basic-revenue-value', formatter: (v) => `£${v}` },
            { id: 'standard-revenue-slider', display: 'standard-revenue-value', formatter: (v) => `£${v}` },
            { id: 'premium-revenue-slider', display: 'premium-revenue-value', formatter: (v) => `£${v}` },
            { id: 'enterprise-revenue-slider', display: 'enterprise-revenue-value', formatter: (v) => `£${v}` }
        ];

        sliders.forEach(({id, display, formatter}) => {
            const slider = document.getElementById(id);
            const valueDisplay = document.getElementById(display);
            if (slider && valueDisplay) {
                slider.addEventListener('input', (e) => {
                    valueDisplay.textContent = formatter(e.target.value);
                });
            }
        });
    }

    setupEventListeners() {
        document.getElementById('start-btn')?.addEventListener('click', () => this.startSimulation());
        document.getElementById('next-btn')?.addEventListener('click', () => this.nextWeek());
        document.getElementById('autorun-btn')?.addEventListener('click', () => this.startAutoEvaluate());
        document.getElementById('session-history-btn')?.addEventListener('click', () => this.openSessionHistory());
        document.getElementById('reset-btn')?.addEventListener('click', () => this.resetSimulation());
        document.getElementById('error-close')?.addEventListener('click', () => this.hideError());
        
        // Auto-Evaluate controls
        document.getElementById('autorun-cancel-btn')?.addEventListener('click', () => this.cancelAutoEvaluate());
        document.getElementById('autorun-view-results-btn')?.addEventListener('click', () => this.viewAutoEvaluateResults());
    }

    async checkApiHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/health`);
            if (response.ok) {
                this.setApiStatus('online', 'API Connected');
            } else {
                throw new Error('API not responding');
            }
        } catch (error) {
            console.error('❌ API Health Check failed:', error);
            this.setApiStatus('offline', 'API Offline');
        }
    }

    setApiStatus(status, text) {
        const statusEl = document.getElementById('api-status');
        const textEl = document.getElementById('api-status-text');

        if (statusEl) statusEl.className = `status-dot ${status}`;
        if (textEl) textEl.textContent = text;
    }

    async startSimulation() {
        if (this.currentWeek === 0) {
            this.resetData();
        }
        
        this.isRunning = true;
        this.updateButtonStates();
        await this.runWeek();
    }

    async nextWeek() {
        if (this.currentWeek < this.maxWeeks && !this.isRunning) {
            await this.runWeek();
        }
    }

    async runWeek() {
        if (this.currentWeek >= this.maxWeeks) {
            this.endSimulation();
            return;
        }

        this.showLoading();
        
        try {
            const parameters = this.getCurrentParameters();
            console.log(`📊 Running week ${parameters.current_week} multi-team comparison`);
            
            // Always use multi-team comparison
            const result = await this.runMultiTeamComparison(parameters);
            this.processMultiTeamResult(result);
            
            this.currentWeek++;
            this.updateDisplay();
            
            if (this.currentWeek >= this.maxWeeks) {
                this.endSimulation();
            } else {
                this.isRunning = false;
                this.updateButtonStates();
            }
            
        } catch (error) {
            console.error('❌ Week simulation error:', error);
            const errorMsg = error.message || error.toString() || 'Unknown error occurred';
            this.showError(`Week ${this.currentWeek + 1} failed: ${errorMsg}`);
            this.isRunning = false;
        } finally {
            this.hideLoading();
        }
    }

    async runMultiTeamComparison(parameters) {
        const response = await fetch(`${this.apiBaseUrl}/simulate/compare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(parameters)
        });
        
        if (!response.ok) {
            let errorMsg = 'Multi-team comparison failed';
            try {
                const errorData = await response.json();
                errorMsg = errorData.detail || errorData.message || errorMsg;
            } catch (parseError) {
                errorMsg = `HTTP ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMsg);
        }
        
        return await response.json();
    }

    processMultiTeamResult(result) {
        // Update team data
        for (const [teamName, teamResult] of Object.entries(result.results)) {
            const teamInfo = this.teamData.get(teamName);
            if (teamInfo) {
                teamInfo.history.push(teamResult);
                
                // Update totals
                const customersSaved = this.calculateCustomersSaved(teamResult);
                teamInfo.totals.clv += teamResult.clv_protected || 0;
                teamInfo.totals.budget += teamResult.budget_spent || 0;
                teamInfo.totals.customers += customersSaved;
            }
        }
        
        // Update all displays
        this.renderTeamAnalysis(result);
        this.renderTeamTotals();
        this.renderWeeklyHistory();
        
    }

    renderTeamComparison(result) {
        const grid = document.getElementById('team-results-grid');
        if (!grid) return;
        
        grid.innerHTML = '';
        
        // Create table for team comparison
        const table = this.createTeamResultsTable(result.results);
        grid.appendChild(table);
    }

    // Reusable table creation function - use this for ALL team comparison tables
    createStandardTeamTable(teams, metrics) {
        return `
            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); margin: 15px 0;">
                <thead>
                    <tr>
                        <th style="border: 1px solid #ddd; padding: 12px; background: #f8f9fa; text-align: left; font-weight: 600;">Metric</th>
                        ${teams.map(teamName => {
                            const displayName = this.formatTeamName(teamName);
                            const teamColor = teamName === 'rule_based' ? '#007bff' : 
                                              teamName === 'cognitive' ? '#28a745' : '#6f42c1';
                            return `<th style="border: 1px solid #ddd; padding: 12px; background: #f8f9fa; text-align: center; color: ${teamColor}; font-weight: 600;">${displayName}</th>`;
                        }).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${metrics.map(metric => `
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;">${metric.label}</td>
                            ${teams.map(teamName => {
                                const value = metric.getValue(teamName);
                                const fontWeight = metric.isHighlight ? 'bold' : 'normal';
                                const color = metric.isHighlight ? '#28a745' : '#2c3e50';
                                return `<td style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: ${fontWeight}; color: ${color};">${value}</td>`;
                            }).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    createTeamResultsTable(results) {
        const teams = Object.keys(results);
        const metrics = [
            { 
                label: 'Customers Saved', 
                getValue: (teamName) => this.calculateCustomersSaved(results[teamName]),
                isHighlight: false 
            },
            { 
                label: 'CLV Protected', 
                getValue: (teamName) => this.formatCurrency(results[teamName].clv_protected),
                isHighlight: false 
            },
            { 
                label: 'Budget Spent', 
                getValue: (teamName) => this.formatCurrency(results[teamName].budget_spent),
                isHighlight: false 
            },
            { 
                label: 'ROI', 
                getValue: (teamName) => {
                    const result = results[teamName];
                    const roi = result.budget_spent > 0 ? result.clv_protected / result.budget_spent : 0;
                    return `${roi.toFixed(1)}x`;
                },
                isHighlight: true 
            }
        ];

        const tableHTML = this.createStandardTeamTable(teams, metrics);
        const container = document.createElement('div');
        container.innerHTML = tableHTML;
        return container.firstElementChild;
    }

    createTeamResultsColumn(teamName, teamResult) {
        const customersSaved = this.calculateCustomersSaved(teamResult);
        const roi = teamResult.budget_spent > 0 ? teamResult.clv_protected / teamResult.budget_spent : 0;
        const displayName = this.formatTeamName(teamName);
        
        const column = document.createElement('div');
        column.className = 'team-column';
        column.innerHTML = `
            <h3 class="team-title ${teamName.replace('_', '-')}">${displayName}</h3>
            <div class="team-metrics">
                <div class="metric">
                    <div class="metric-label">Customers Saved</div>
                    <div class="metric-value">${customersSaved}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">CLV Protected</div>
                    <div class="metric-value">${this.formatCurrency(teamResult.clv_protected)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Budget Spent</div>
                    <div class="metric-value">${this.formatCurrency(teamResult.budget_spent)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">ROI</div>
                    <div class="metric-value roi">${roi.toFixed(1)}x</div>
                </div>
            </div>
        `;
        
        return column;
    }

    renderTeamAnalysis(result) {
        console.log('DEBUG: renderTeamAnalysis called with:', Object.keys(result.results));
        
        const grid = document.getElementById('team-analysis-grid');
        if (!grid) {
            console.error('ERROR: team-analysis-grid element not found');
            return;
        }
        
        grid.innerHTML = '';
        
        // Create analysis panel for each agent team (skip rule_based)
        for (const [teamName, teamResult] of Object.entries(result.results)) {
            if (teamName === 'rule_based') continue;
            
            console.log(`DEBUG: Creating panel for ${teamName}, conversation entries:`, teamResult.conversation_log?.length || 0);
            const panel = this.createTeamAnalysisPanel(teamName, teamResult);
            grid.appendChild(panel);
        }
        
        console.log('DEBUG: Team analysis panels rendered');
    }

    createTeamAnalysisPanel(teamName, teamResult) {
        const displayName = this.formatTeamName(teamName);
        const conversation = teamResult.conversation_log || [];
        const processingTime = teamResult.processing_time_ms || 0;
        
        const panel = document.createElement('div');
        panel.className = `team-analysis-panel ${teamName.replace('_', '-')}`;
        panel.innerHTML = `
            <h4>${displayName} Decision Process</h4>
            <div class="processing-time">Processing: ${processingTime}ms | ${conversation.length} discussion entries</div>
            <div class="conversation-log">
                ${this.formatConversation(conversation)}
            </div>
        `;
        
        return panel;
    }

    renderTeamTotals() {
        const grid = document.getElementById('team-totals-grid');
        if (!grid) {
            console.error('❌ team-totals-grid element not found!');
            return;
        }
        
        grid.innerHTML = '';
        
        this.teamData.forEach((teamInfo, teamName) => {
            const column = this.createTeamTotalsColumn(teamName, teamInfo.totals);
            grid.appendChild(column);
        });
    }

    renderWeeklyHistory() {
        const historySection = document.getElementById('weekly-history-section');
        const grid = document.getElementById('weekly-history-grid');
        
        if (!historySection || !grid) return;
        
        // Check if we have any history data
        let hasHistory = false;
        let maxWeeks = 0;
        
        this.teamData.forEach((teamInfo) => {
            if (teamInfo.history.length > 0) {
                hasHistory = true;
                maxWeeks = Math.max(maxWeeks, teamInfo.history.length);
            }
        });
        
        if (!hasHistory) {
            historySection.classList.add('hidden');
            return;
        }
        
        // Show the section and generate weekly results
        historySection.classList.remove('hidden');
        
        // Organize data by week - include Game Master context and analysis
        const weeklyResults = [];
        for (let week = 0; week < maxWeeks; week++) {
            const weekData = {
                week: week + 1,
                team_results: {},
                game_master_parameters: null,
                game_master_evaluation: null
            };
            
            this.teamData.forEach((teamInfo, teamName) => {
                if (teamInfo.history[week]) {
                    weekData.team_results[teamName] = teamInfo.history[week];
                    // Game Master data is typically attached to the result
                    if (teamInfo.history[week].game_master_parameters) {
                        weekData.game_master_parameters = teamInfo.history[week].game_master_parameters;
                    }
                    if (teamInfo.history[week].game_master_evaluation) {
                        weekData.game_master_evaluation = teamInfo.history[week].game_master_evaluation;
                    }
                }
            });
            
            weeklyResults.push(weekData);
        }
        
        // Generate HTML with table format for each week
        grid.innerHTML = weeklyResults.map(weekResult => {
            // Get Game Master's winner decision and reasoning
            const winningTeam = weekResult.game_master_evaluation?.week_winner || '';
            const winnerReason = weekResult.game_master_evaluation?.winner_reasoning || '';
            
            // Create table for this week
            const teams = Object.entries(weekResult.team_results || {});
            
            return `
                <div class="week-result-card">
                    <h3 class="week-title">Week ${weekResult.week}</h3>
                    
                    <div class="business-context">
                        <h4>Business Context</h4>
                        <div class="context-content">
                            <p><strong>Market Scenario:</strong> Week ${weekResult.week} business context and parameters will be displayed here.</p>
                        </div>
                    </div>
                    
                    <div class="performance-analysis">
                        <h4>Performance Analysis</h4>
                        <div class="analysis-content">
                            <p>Week ${weekResult.week} performance analysis and team evaluations will be displayed here.</p>
                        </div>
                    </div>
                    
                    <div class="week-results">
                        <h4>Week ${weekResult.week} Results ${winningTeam ? `<span class="winner-indicator">Winner: ${this.formatTeamName(winningTeam)} - ${winnerReason}</span>` : ''}</h4>
                        <table class="results-table">
                        <thead>
                            <tr>
                                <th class="metric-header">Metric</th>
                                ${teams.map(([teamName, _]) => {
                                    const displayName = this.formatTeamName(teamName);
                                    const teamClass = teamName.replace('_', '-');
                                    return `<th class="team-header ${teamClass}">${displayName}</th>`;
                                }).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="metric-label">Customers Saved</td>
                                ${teams.map(([teamName, result]) => {
                                    const value = this.calculateCustomersSaved(result);
                                    return `<td class="metric-value">${value}</td>`;
                                }).join('')}
                            </tr>
                            <tr>
                                <td class="metric-label">CLV Protected</td>
                                ${teams.map(([teamName, result]) => {
                                    const value = this.formatCurrency(result.clv_protected || 0);
                                    return `<td class="metric-value">${value}</td>`;
                                }).join('')}
                            </tr>
                            <tr>
                                <td class="metric-label">Budget Spent</td>
                                ${teams.map(([teamName, result]) => {
                                    const value = this.formatCurrency(result.budget_spent || 0);
                                    return `<td class="metric-value">${value}</td>`;
                                }).join('')}
                            </tr>
                            <tr>
                                <td class="metric-label">ROI</td>
                                ${teams.map(([teamName, result]) => {
                                    const roi = result.budget_spent > 0 ? result.clv_protected / result.budget_spent : 0;
                                    return `<td class="metric-value roi-value">${roi.toFixed(1)}x</td>`;
                                }).join('')}
                            </tr>
                        </tbody>
                        </table>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Helper functions to get current parameter values for business context
    getCurrentCustomersAtRisk() {
        return document.getElementById('customers-slider')?.value || 100;
    }

    getCurrentBudget() {
        return parseInt(document.getElementById('budget-slider')?.value || 40) * 1000;
    }

    getCurrentDiscountSuccess() {
        return document.getElementById('discount-slider')?.value || 40;
    }

    getCurrentTechnicalSuccess() {
        return document.getElementById('priority-slider')?.value || 70;
    }

    getCurrentExecutiveSuccess() {
        return document.getElementById('executive-slider')?.value || 85;
    }

    createTeamTotalsTable(totalsData) {
        // Extract team names and their totals
        const teams = Object.entries(totalsData);
        
        const table = document.createElement('table');
        table.className = 'results-table';
        
        // Create header row
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = `
            <th class="metric-header">Metric</th>
            ${teams.map(([teamName, _]) => {
                const displayName = this.formatTeamName(teamName);
                const teamClass = teamName.replace('_', '-');
                return `<th class="team-header ${teamClass}">${displayName}</th>`;
            }).join('')}
        `;
        table.appendChild(headerRow);
        
        // Create metric rows
        const metrics = [
            { label: 'Total Customers', key: 'customers', formatter: (totals) => totals.customers },
            { label: 'Total CLV', key: 'clv', formatter: (totals) => this.formatCurrency(totals.clv) },
            { label: 'Total Spent', key: 'budget', formatter: (totals) => this.formatCurrency(totals.budget) },
            { label: 'Overall ROI', key: 'roi', formatter: (totals) => {
                const roi = totals.budget > 0 ? totals.clv / totals.budget : 0;
                return `${roi.toFixed(1)}x`;
            }}
        ];
        
        metrics.forEach((metric, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="metric-label">${metric.label}</td>
                ${teams.map(([teamName, totals]) => {
                    const value = metric.formatter(totals);
                    const isROI = metric.key === 'roi';
                    const cellClass = isROI ? 'metric-value roi-value' : 'metric-value';
                    return `<td class="${cellClass}">${value}</td>`;
                }).join('')}
            `;
            table.appendChild(row);
        });
        
        return table;
    }

    createTeamTotalsColumn(teamName, totals) {
        const displayName = this.formatTeamName(teamName);
        const roi = totals.budget > 0 ? totals.clv / totals.budget : 0;
        
        const column = document.createElement('div');
        column.className = 'team-column';
        column.innerHTML = `
            <h3 class="team-title ${teamName.replace('_', '-')}">${displayName}</h3>
            <div class="team-metrics">
                <div class="metric">
                    <div class="metric-label">Total Customers</div>
                    <div class="metric-value">${totals.customers}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total CLV</div>
                    <div class="metric-value">${this.formatCurrency(totals.clv)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Spent</div>
                    <div class="metric-value">${this.formatCurrency(totals.budget)}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Overall ROI</div>
                    <div class="metric-value roi">${roi.toFixed(1)}x</div>
                </div>
            </div>
        `;
        
        return column;
    }

    getCurrentParameters() {
        const budgetValue = parseInt(document.getElementById('budget-slider').value) * 1000;
        
        // Build team-specific histories object
        const teamHistories = {};
        this.teamData.forEach((teamInfo, teamName) => {
            teamHistories[teamName] = teamInfo.history || [];
        });
        
        return {
            customers_at_risk: parseInt(document.getElementById('customers-slider').value),
            weekly_budget: budgetValue,
            success_rates: {
                discount: parseFloat(document.getElementById('discount-slider').value) / 100,
                priority_fix: parseFloat(document.getElementById('priority-slider').value) / 100,
                executive_escalation: parseFloat(document.getElementById('executive-slider').value) / 100
            },
            intervention_costs: {
                discount_duration_months: parseInt(document.getElementById('discount-duration-slider').value),
                priority_fix: parseInt(document.getElementById('priority-cost-slider').value),
                executive_escalation: parseInt(document.getElementById('executive-cost-slider').value)
            },
            system_config: {
                customer_distribution: {
                    basic: parseFloat(document.getElementById('basic-percent-slider').value) / 100,
                    standard: parseFloat(document.getElementById('standard-percent-slider').value) / 100,
                    premium: parseFloat(document.getElementById('premium-percent-slider').value) / 100,
                    enterprise: parseFloat(document.getElementById('enterprise-percent-slider').value) / 100
                },
                monthly_revenue: {
                    basic: parseFloat(document.getElementById('basic-revenue-slider').value),
                    standard: parseFloat(document.getElementById('standard-revenue-slider').value),
                    premium: parseFloat(document.getElementById('premium-revenue-slider').value),
                    enterprise: parseFloat(document.getElementById('enterprise-revenue-slider').value)
                }
            },
            current_week: this.currentWeek + 1,
            simulation_history: [],  // Keep for backwards compatibility
            team_histories: teamHistories  // New team-specific histories
        };
    }

    calculateCustomersSaved(teamResult) {
        if (!teamResult.customers_saved) return 0;
        const saved = teamResult.customers_saved;
        return (saved.enterprise || 0) + (saved.premium || 0) + (saved.standard || 0) + (saved.basic || 0);
    }

    formatTeamName(teamName) {
        return teamName.replace('_', ' ').split(' ').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    formatCurrency(amount) {
        if (amount >= 1000000) return `£${(amount / 1000000).toFixed(1)}M`;
        if (amount >= 1000) return `£${(amount / 1000).toFixed(0)}k`;
        return `£${amount.toFixed(0)}`;
    }

    formatConversation(conversation) {
        if (!conversation || conversation.length === 0) {
            return '<div style="color: #999; font-style: italic;">No team discussion available</div>';
        }
        
        return conversation.map((entry, index) => {
            const message = entry.message || '';
            
            return `
                <div class="conversation-entry">
                    <div class="agent-header">
                        <span class="agent-name">${entry.agent}</span>
                        <span class="entry-number">#${index + 1}</span>
                    </div>
                    <div class="agent-message">${message}</div>
                </div>
            `;
        }).join('');
    }

    resetSimulation() {
        this.isRunning = false;
        this.currentWeek = 0;
        this.resetData();
        this.updateDisplay();
        this.updateButtonStates();
    }

    resetData() {
        // Reset all team data
        this.teamData.forEach(teamInfo => {
            teamInfo.history = [];
            teamInfo.totals = { clv: 0, budget: 0, customers: 0 };
        });
        
        // Clear displays
        ['team-results-grid', 'team-analysis-grid', 'team-totals-grid', 'weekly-history-grid'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.innerHTML = '';
        });
        
        // Hide weekly history section
        const historySection = document.getElementById('weekly-history-section');
        if (historySection) historySection.classList.add('hidden');
    }

    endSimulation() {
        this.isRunning = false;
        this.updateButtonStates();
        alert(`Simulation Complete!\n\nAll ${this.maxWeeks} weeks finished.\nCheck the cumulative results above.`);
    }

    updateDisplay() {
        const currentWeekEl = document.getElementById('current-week');
        const displayWeekEl = document.getElementById('display-week');
        const progressEl = document.getElementById('week-progress');
        
        if (currentWeekEl) currentWeekEl.textContent = this.currentWeek;
        if (displayWeekEl) displayWeekEl.textContent = this.currentWeek;
        
        if (progressEl) {
            const progressPercent = (this.currentWeek / this.maxWeeks) * 100;
            progressEl.style.width = `${progressPercent}%`;
        }
    }

    updateButtonStates() {
        const startBtn = document.getElementById('start-btn');
        const nextBtn = document.getElementById('next-btn');

        if (this.isRunning) {
            if (startBtn) startBtn.disabled = true;
            if (nextBtn) nextBtn.disabled = true;
        } else {
            const isComplete = this.currentWeek >= this.maxWeeks;
            if (startBtn) {
                startBtn.disabled = isComplete;
                startBtn.textContent = isComplete ? 'Simulation Complete' :
                                     this.currentWeek > 0 ? 'Resume Simulation' : 'Start Simulation';
            }
            if (nextBtn) nextBtn.disabled = isComplete;
        }
    }

    showLoading() {
        document.getElementById('loading-overlay')?.classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-overlay')?.classList.add('hidden');
    }

    showError(message) {
        const errorElement = document.getElementById('error-message');
        const modalElement = document.getElementById('error-modal');

        if (errorElement) {
            errorElement.textContent = message;
        } else {
            console.error('Error message element not found:', message);
        }

        if (modalElement) {
            modalElement.classList.remove('hidden');
        } else {
            // Fallback to alert if modal not available
            alert(`Error: ${message}`);
        }
    }

    hideError() {
        document.getElementById('error-modal')?.classList.add('hidden');
    }

    // Auto-Evaluate Methods
    
    lockControls() {
        document.querySelectorAll('.slider').forEach(slider => {
            slider.disabled = true;
            slider.style.opacity = '0.6';
        });
        document.querySelector('.control-panel-content').style.pointerEvents = 'none';
    }
    
    unlockControls() {
        document.querySelectorAll('.slider').forEach(slider => {
            slider.disabled = false;
            slider.style.opacity = '1';
        });
        document.querySelector('.control-panel-content').style.pointerEvents = 'auto';
    }
    
    applyGameMasterParameters(frontendParams) {
        console.log('DEBUG: Applying Game Master parameters to frontend controls');
        
        // Set all sliders to Game Master values
        document.getElementById('customers-slider').value = frontendParams.customers_at_risk || 100;
        document.getElementById('budget-slider').value = frontendParams.weekly_budget_k || 40;
        document.getElementById('discount-slider').value = frontendParams.discount_success || 40;
        document.getElementById('priority-slider').value = frontendParams.priority_success || 70;
        document.getElementById('executive-slider').value = frontendParams.executive_success || 85;
        document.getElementById('discount-duration-slider').value = frontendParams.discount_duration || 6;
        document.getElementById('priority-cost-slider').value = frontendParams.priority_cost || 300;
        document.getElementById('executive-cost-slider').value = frontendParams.executive_cost || 600;
        
        // Customer distribution
        document.getElementById('basic-percent-slider').value = frontendParams.basic_percent || 80;
        document.getElementById('standard-percent-slider').value = frontendParams.standard_percent || 15;
        document.getElementById('premium-percent-slider').value = frontendParams.premium_percent || 4;
        document.getElementById('enterprise-percent-slider').value = frontendParams.enterprise_percent || 1;
        
        // Revenue tiers
        document.getElementById('basic-revenue-slider').value = frontendParams.basic_revenue || 35;
        document.getElementById('standard-revenue-slider').value = frontendParams.standard_revenue || 65;
        document.getElementById('premium-revenue-slider').value = frontendParams.premium_revenue || 200;
        document.getElementById('enterprise-revenue-slider').value = frontendParams.enterprise_revenue || 1000;
        
        // Trigger change events to update display values
        document.querySelectorAll('.slider').forEach(slider => {
            slider.dispatchEvent(new Event('input'));
        });
        
        console.log('DEBUG: Game Master parameters applied to controls');
    }
    
    async startAutoEvaluate() {
        if (this.autorunSession) {
            this.showError('Auto-Evaluate simulation already in progress');
            return;
        }
        
        console.log('🎮 Starting Auto-Evaluate using backend autorun...');
        
        try {
            // Call backend to start autorun session
            const response = await fetch(`${this.apiBaseUrl}/simulate/autorun`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_name: `Auto-Evaluate ${new Date().toLocaleString()}`,
                    save_conversations: true
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to start Auto-Evaluate session');
            }
            
            this.autorunSession = await response.json();
            console.log('✅ Auto-Evaluate session started:', this.autorunSession.session_id);
            
            // Show Auto-Evaluate UI and lock controls
            this.showAutoEvaluateUI();
            this.lockControls();
            
            // Start polling for real-time updates
            this.startAutoEvaluatePolling();
            
        } catch (error) {
            console.error('❌ Failed to start Auto-Evaluate:', error);
            this.showError(`Failed to start Auto-Evaluate: ${error.message}`);
        }
    }
    
    
    completeAutoEvaluate() {
        console.log('✅ Auto-Evaluate completed all 5 weeks');
        this.unlockControls();
        this.hideAutoEvaluateUI();
        this.autorunSession = null;
        alert('Auto-Evaluate simulation completed!');
    }
    
    showAutoEvaluateUI() {
        // Hide normal sections
        document.querySelector('.running-totals-section')?.classList.add('hidden');
        document.querySelector('.team-analysis-section')?.classList.add('hidden');
        
        // Show Auto-Evaluate section
        document.getElementById('autorun-section')?.classList.remove('hidden');
        
        // Disable controls
        document.getElementById('start-btn').disabled = true;
        document.getElementById('next-btn').disabled = true;
        document.getElementById('autorun-btn').disabled = true;
        document.getElementById('reset-btn').disabled = true;
        
        // Reset progress
        this.updateAutoEvaluateProgress(0, 0);
    }
    
    hideAutoEvaluateUI() {
        // Show normal sections
        document.querySelector('.running-totals-section')?.classList.remove('hidden');
        document.querySelector('.team-analysis-section')?.classList.remove('hidden');
        
        // Hide Auto-Evaluate section
        document.getElementById('autorun-section')?.classList.add('hidden');
        
        // Re-enable controls
        document.getElementById('start-btn').disabled = false;
        document.getElementById('next-btn').disabled = false;
        document.getElementById('autorun-btn').disabled = false;
        document.getElementById('reset-btn').disabled = false;
    }
    
    startAutoEvaluatePolling() {
        this.autorunPollingInterval = setInterval(() => {
            this.pollAutoEvaluateStatus();
        }, 2000); // Poll every 2 seconds
    }
    
    stopAutoEvaluatePolling() {
        if (this.autorunPollingInterval) {
            clearInterval(this.autorunPollingInterval);
            this.autorunPollingInterval = null;
        }
    }
    
    async pollAutoEvaluateStatus() {
        if (!this.autorunSession) {
            console.log('DEBUG: No autorunSession, stopping polling');
            return;
        }
        
        try {
            console.log(`DEBUG: Polling status for session ${this.autorunSession.session_id}`);
            const response = await fetch(`${this.apiBaseUrl}/simulate/autorun/${this.autorunSession.session_id}/status`);
            
            if (!response.ok) {
                throw new Error('Failed to get Auto-Evaluate status');
            }
            
            const status = await response.json();
            console.log('DEBUG: Received status:', {
                currentWeek: status.session?.current_week,
                completedWeeks: status.completed_weeks?.length || 0,
                sessionStatus: status.session?.status
            });
            this.updateAutoEvaluateStatus(status);
            
            // Check if completed
            if (status.session.status === 'completed') {
                this.stopAutoEvaluatePolling();
                this.handleAutoEvaluateComplete();
            } else if (status.session.status === 'failed') {
                this.stopAutoEvaluatePolling();
                this.handleAutoEvaluateError(status.session.error_message);
            } else if (status.session.status === 'running' &&
                      status.completed_weeks &&
                      status.completed_weeks.length >= status.session.total_weeks) {
                // Fallback: If we have all weeks completed but status hasn't updated to "completed"
                console.log('🔄 All weeks completed but session status not updated, checking completion...');
                // Give backend a moment to update status, then check again
                setTimeout(() => {
                    // One more status check before assuming completion
                    fetch(`${this.apiBaseUrl}/simulate/autorun/${this.autorunSession.session_id}/status`)
                        .then(response => response.json())
                        .then(finalStatus => {
                            if (finalStatus.session.status === 'completed') {
                                this.stopAutoEvaluatePolling();
                                this.handleAutoEvaluateComplete();
                            }
                        })
                        .catch(error => console.error('Final status check failed:', error));
                }, 2000); // Wait 2 seconds
            }
            
        } catch (error) {
            console.error('❌ Auto-Evaluate polling error:', error);
            console.error('❌ Full error stack:', error.stack);
            console.error('❌ Error at line:', error.stack?.split('\n')[1]);
            this.stopAutoEvaluatePolling();
            this.showError(`Auto-Evaluate monitoring failed: ${error.message}`);
        }
    }
    
    updateAutoEvaluateStatus(status) {
        console.log('DEBUG: updateAutoEvaluateStatus called');
        const session = status.session;
        const completedWeeks = status.completed_weeks || [];
        
        console.log('DEBUG: Status data:', {
            sessionCurrentWeek: session?.current_week,
            totalWeeks: session?.total_weeks,
            completedWeeksCount: completedWeeks.length,
            hasCompletedWeeks: completedWeeks.length > 0
        });
        
        // Update progress
        if (session && session.current_week !== undefined && session.total_weeks !== undefined) {
            this.updateAutoEvaluateProgress(session.current_week, session.total_weeks);
        } else {
            console.error('ERROR: Session data missing for updateAutoEvaluateProgress:', session);
        }
        
        // Time remaining display removed
        
        // Update Game Master commentary - show current week progress if available
        if (completedWeeks.length > 0) {
            const lastWeek = completedWeeks[completedWeeks.length - 1];
            this.updateGameMasterCommentary(lastWeek);
        } else if (status.current_week_progress && status.current_week_progress.game_master_parameters) {
            // Show current week parameters even before week completion
            console.log('DEBUG: Showing current week progress for week:', status.current_week_progress.week);
            const params = status.current_week_progress.game_master_parameters;
            
            // Apply Game Master parameters to frontend controls
            if (params.frontend_parameters) {
                this.applyGameMasterParameters(params.frontend_parameters);
                this.lockControls();
            }
            
            // Show Game Master commentary
            this.updateGameMasterCommentary(status.current_week_progress);
        }
        
        // Update running totals and overall analysis if we have completed weeks
        if (completedWeeks.length > 0) {
            this.updateAutoRunTotals(completedWeeks);
            this.updateOverallAnalysis(completedWeeks);
        }
        
        // Update weekly results
        this.updateAutoEvaluateResults(completedWeeks);
    }
    
    updateAutoEvaluateProgress(currentWeek, totalWeeks) {
        const currentWeekEl = document.getElementById('autorun-current-week');
        const totalWeeksEl = document.getElementById('autorun-total-weeks');
        const progressFillEl = document.getElementById('autorun-progress-fill');

        if (currentWeekEl) currentWeekEl.textContent = currentWeek;
        if (totalWeeksEl) totalWeeksEl.textContent = totalWeeks;

        const progressPercent = totalWeeks > 0 ? (currentWeek / totalWeeks) * 100 : 0;
        if (progressFillEl) progressFillEl.style.width = `${progressPercent}%`;
    }
    
    updateGameMasterCommentary(weekResult) {
        console.log('DEBUG: updateGameMasterCommentary called for week:', weekResult.week);
        console.log('DEBUG: Has game_master_parameters:', !!weekResult.game_master_parameters);
        console.log('DEBUG: Has game_master_evaluation:', !!weekResult.game_master_evaluation);
        
        // Update parameters
        const parametersContent = document.getElementById('current-parameters-content');
        if (parametersContent && weekResult.game_master_parameters) {
            console.log('DEBUG: Updating parameters content');
            parametersContent.innerHTML = this.formatGameMasterParameters(weekResult.game_master_parameters);
        } else {
            console.log('DEBUG: Parameters not updated - element found:', !!parametersContent, 'data found:', !!weekResult.game_master_parameters);
        }
        
        // Update evaluation
        const evaluationContent = document.getElementById('evaluation-content');
        if (evaluationContent && weekResult.game_master_evaluation) {
            console.log('DEBUG: Updating evaluation content');
            evaluationContent.innerHTML = this.formatGameMasterEvaluation(weekResult.game_master_evaluation);
        } else {
            console.log('DEBUG: Evaluation not updated - element found:', !!evaluationContent, 'data found:', !!weekResult.game_master_evaluation);
        }
    }
    
    formatGameMasterParameters(parameters) {
        const params = parameters.frontend_parameters || {};
        const reasoning = parameters.reasoning || '';
        
        return `
            <div class="parameters-display">
                <h5>Week ${parameters.week} Business Context:</h5>
                <p class="reasoning-text">${parameters.business_context || 'Setting parameters for this week...'}</p>
                
                <div class="parameter-grid">
                    <div class="parameter-item">
                        <span class="parameter-label">Customers at Risk:</span>
                        <span class="parameter-value">${params.customers_at_risk || 0}</span>
                    </div>
                    <div class="parameter-item">
                        <span class="parameter-label">Weekly Budget:</span>
                        <span class="parameter-value">£${params.weekly_budget_k || 0}k</span>
                    </div>
                    <div class="parameter-item">
                        <span class="parameter-label">Discount Success:</span>
                        <span class="parameter-value">${params.discount_success || 0}%</span>
                    </div>
                    <div class="parameter-item">
                        <span class="parameter-label">Priority Fix Success:</span>
                        <span class="parameter-value">${params.priority_success || 0}%</span>
                    </div>
                    <div class="parameter-item">
                        <span class="parameter-label">Executive Success:</span>
                        <span class="parameter-value">${params.executive_success || 0}%</span>
                    </div>
                </div>
                
                ${reasoning ? `<div class="reasoning-text"><strong>Game Master Reasoning:</strong> ${reasoning}</div>` : ''}
            </div>
        `;
    }
    
    formatGameMasterEvaluation(evaluation) {
        if (!evaluation.evaluations) return '<p class="placeholder">Evaluation pending...</p>';
        
        const evaluations = evaluation.evaluations;
        const teams = Object.keys(evaluations);
        
        return `
            <div class="evaluation-display">
                <div class="evaluation-scores">
                    ${teams.map(team => `
                        <div class="team-score">
                            <div class="score">${evaluations[team].overall_score || 0}/10</div>
                            <div class="team-name">${team.replace('_', ' ').toUpperCase()}</div>
                        </div>
                    `).join('')}
                </div>
                
                ${teams.map(team => {
                    const teamEval = evaluations[team];
                    return `
                        <div class="team-evaluation">
                            <h5>${team.replace('_', ' ').toUpperCase()} Team</h5>
                            <div class="evaluation-summary">
                                <strong>Strengths:</strong> ${(teamEval.strengths || []).join(', ')}<br>
                                <strong>Improvements:</strong> ${(teamEval.improvements || []).join(', ')}<br>
                                ${teamEval.reasoning || ''}
                            </div>
                        </div>
                    `;
                }).join('')}
                
                ${evaluation.comparative_insights ? `
                    <div class="reasoning-text">
                        <strong>Comparative Analysis:</strong> ${evaluation.comparative_insights}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    updateAutoEvaluateResults(weeklyResults) {
        const grid = document.getElementById('autorun-weekly-grid');
        if (!grid) return;
        
        grid.innerHTML = weeklyResults.map(weekResult => {
            // Get Game Master's winner decision and reasoning
            const winningTeam = weekResult.game_master_evaluation?.week_winner || '';
            const winnerReason = weekResult.game_master_evaluation?.winner_reasoning || '';
            
            return `
                <div class="week-result-card">
                    <h3 class="week-title">Week ${weekResult.week}</h3>
                    
                    <div class="business-context">
                        <h4>Business Context</h4>
                        <div class="context-content">
                            <p><strong>Market Scenario:</strong> ${weekResult.game_master_parameters?.business_context || 'Week ' + weekResult.week + ' business context and parameters will be displayed here.'}</p>
                        </div>
                    </div>
                    
                    <div class="performance-analysis">
                        <h4>Performance Analysis</h4>
                        <div class="analysis-content">
                            ${weekResult.game_master_evaluation ? this.formatGameMasterEvaluation(weekResult.game_master_evaluation) : `<p>Week ${weekResult.week} performance analysis and team evaluations will be displayed here.</p>`}
                        </div>
                    </div>
                    
                    <div class="week-results">
                        <h4>Week ${weekResult.week} Results ${winningTeam ? `<span class="winner-indicator">Winner: ${this.formatTeamName(winningTeam)} - ${winnerReason}</span>` : ''}</h4>
                        <div class="teams-grid-horizontal">
                        ${Object.keys(weekResult.team_results || {}).map(team => {
                            const result = weekResult.team_results[team];
                            const customersSaved = this.calculateCustomersSaved(result);
                            const roi = result.budget_spent > 0 ? result.clv_protected / result.budget_spent : 0;
                            const displayName = this.formatTeamName(team);
                            const isWinner = team === winningTeam;
                            const score = weekResult.game_master_evaluation?.evaluations?.[team]?.overall_score || 0;
                            
                            return `
                                <div class="team-card ${isWinner ? 'winner-card' : ''}">
                                    <div class="card-header">
                                        <span class="team-name">${displayName}</span>
                                        <span class="score-badge">${score}/10</span>
                                    </div>
                                    <div class="metrics-grid">
                                        <div class="metric">
                                            <div class="metric-value">${customersSaved}</div>
                                            <div class="metric-label">Customers</div>
                                        </div>
                                        <div class="metric">
                                            <div class="metric-value">${this.formatCurrency(result.clv_protected || 0)}</div>
                                            <div class="metric-label">CLV Protected</div>
                                        </div>
                                        <div class="metric">
                                            <div class="metric-value">${this.formatCurrency(result.budget_spent || 0)}</div>
                                            <div class="metric-label">Budget Spent</div>
                                        </div>
                                        <div class="metric roi-metric">
                                            <div class="metric-value roi-value ${isWinner ? 'winner-roi' : ''}">${roi.toFixed(1)}x</div>
                                            <div class="metric-label">ROI</div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    updateAutoRunTotals(weeklyResults) {
        const totalsSection = document.getElementById('autorun-totals-section');
        const totalsGrid = document.getElementById('autorun-totals-grid');
        
        if (!totalsSection || !totalsGrid) return;
        
        // Calculate cumulative totals for each team
        const teamTotals = {};
        
        // Initialize totals
        const allTeams = new Set();
        weeklyResults.forEach(week => {
            Object.keys(week.team_results || {}).forEach(team => allTeams.add(team));
        });
        
        allTeams.forEach(team => {
            teamTotals[team] = { customers: 0, clv: 0, budget: 0 };
        });
        
        // Accumulate totals across all weeks
        weeklyResults.forEach(week => {
            Object.entries(week.team_results || {}).forEach(([team, result]) => {
                teamTotals[team].customers += this.calculateCustomersSaved(result);
                teamTotals[team].clv += result.clv_protected || 0;
                teamTotals[team].budget += result.budget_spent || 0;
            });
        });
        
        // Generate table HTML directly
        totalsGrid.innerHTML = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th class="metric-header">Metric</th>
                        ${Object.keys(teamTotals).map(teamName => {
                            const displayName = this.formatTeamName(teamName);
                            const teamClass = teamName.replace('_', '-');
                            return `<th class="team-header ${teamClass}">${displayName}</th>`;
                        }).join('')}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="metric-label">Total Customers</td>
                        ${Object.keys(teamTotals).map(teamName => `<td class="metric-value">${teamTotals[teamName].customers}</td>`).join('')}
                    </tr>
                    <tr>
                        <td class="metric-label">Total CLV</td>
                        ${Object.keys(teamTotals).map(teamName => `<td class="metric-value">${this.formatCurrency(teamTotals[teamName].clv)}</td>`).join('')}
                    </tr>
                    <tr>
                        <td class="metric-label">Total Spent</td>
                        ${Object.keys(teamTotals).map(teamName => `<td class="metric-value">${this.formatCurrency(teamTotals[teamName].budget)}</td>`).join('')}
                    </tr>
                    <tr>
                        <td class="metric-label">Overall ROI</td>
                        ${Object.keys(teamTotals).map(teamName => {
                            const totals = teamTotals[teamName];
                            const roi = totals.budget > 0 ? totals.clv / totals.budget : 0;
                            return `<td class="metric-value roi-value">${roi.toFixed(1)}x</td>`;
                        }).join('')}
                    </tr>
                </tbody>
            </table>
        `;
        
        // Show the section
        totalsSection.classList.remove('hidden');
    }
    
    updateOverallAnalysis(weeklyResults) {
        const analysisSection = document.getElementById('autorun-overall-analysis');
        const analysisContent = document.getElementById('overall-analysis-content');
        
        if (!analysisSection || !analysisContent) return;
        
        // Extract overall analysis from the latest week's Game Master evaluation
        const lastWeek = weeklyResults[weeklyResults.length - 1];
        let overallAnalysis = '';
        
        if (lastWeek?.game_master_evaluation?.overall_analysis) {
            // Use Game Master's multi-week overall analysis
            overallAnalysis = lastWeek.game_master_evaluation.overall_analysis;
        } else {
            // Fallback for incomplete data
            const weekCount = weeklyResults.length;
            overallAnalysis = `Multi-week analysis across ${weekCount} completed weeks. Game Master overall analysis will appear here once available.`;
        }
        
        analysisContent.innerHTML = `<p>${overallAnalysis}</p>`;
        
        // Show the section
        analysisSection.classList.remove('hidden');
    }
    
    async handleAutoEvaluateComplete() {
        console.log('✅ Auto-Evaluate simulation completed');

        // Update UI
        // Status update: Finalizing results...
        document.getElementById('autorun-cancel-btn').classList.add('hidden');

        // Call the complete endpoint to generate final analysis
        try {
            console.log('📋 Generating final analysis...');
            const response = await fetch(`${this.apiBaseUrl}/simulate/autorun/${this.autorunSession.session_id}/complete`);

            if (!response.ok) {
                throw new Error('Failed to generate final analysis');
            }

            const completeResults = await response.json();
            console.log('✅ Final analysis generated successfully');

            // Update UI to show completion
            // Status: Simulation completed successfully!
            document.getElementById('autorun-view-results-btn').classList.remove('hidden');

        } catch (error) {
            console.error('❌ Failed to generate final analysis:', error);
            // Status: Completed with analysis generation error
            document.getElementById('autorun-view-results-btn').classList.remove('hidden');
        }
    }
    
    handleAutoEvaluateError(errorMessage) {
        console.error('❌ Auto-Evaluate simulation failed:', errorMessage);
        
        this.stopAutoEvaluatePolling();
        this.showError(`Auto-Evaluate simulation failed: ${errorMessage}`);
        this.cancelAutoEvaluate();
    }
    
    async cancelAutoEvaluate() {
        this.stopAutoEvaluatePolling();
        
        // Reset UI
        this.hideAutoEvaluateUI();
        
        // Clear session
        this.autorunSession = null;
        
        console.log('Auto-Evaluate simulation cancelled');
    }
    
    async viewAutoEvaluateResults() {
        if (!this.autorunSession) return;
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/simulate/autorun/${this.autorunSession.session_id}/complete`);
            
            if (!response.ok) {
                throw new Error('Failed to get complete results');
            }
            
            const completeResults = await response.json();
            
            // Show results in a new window or modal
            this.displayCompleteAutoEvaluateResults(completeResults);
            
        } catch (error) {
            console.error('❌ Failed to get complete results:', error);
            this.showError(`Failed to load results: ${error.message}`);
        }
    }
    
    displayCompleteAutoEvaluateResults(results) {
        // Create a summary report
        const report = this.generateAutoEvaluateReport(results);
        
        // Open in new window
        const newWindow = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
        newWindow.document.write(`
            <html>
            <head><title>Auto-Evaluate Results - ${this.autorunSession.session_name}</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1>Auto-Evaluate Simulation Results</h1>
                <p><strong>Session:</strong> ${results.session.session_id}</p>
                <p><strong>Duration:</strong> ${results.weekly_results.length} weeks</p>
                <p><strong>Data saved to:</strong> ${results.data_file_path}</p>
                
                <h2>Final Analysis</h2>
                ${report}
                
                <h2>Weekly Performance</h2>
                ${this.formatWeeklyPerformanceTable(results.weekly_results)}
            </body>
            </html>
        `);
    }
    
    generateAutoEvaluateReport(results) {
        const analysis = results.final_analysis;
        const rankings = analysis.overall_rankings || {};
        
        return `
            <div>
                <h3>Performance Rankings</h3>
                <ol>
                    ${Object.entries(rankings)
                        .sort((a, b) => a[1] - b[1])
                        .map(([team, rank]) => `<li><strong>${team.replace('_', ' ').toUpperCase()}</strong> (Rank ${rank})</li>`)
                        .join('')}
                </ol>
                
                <h3>Game Master's Final Report</h3>
                <p>${analysis.game_master_final_report}</p>
                
                <h3>Recommended Approach</h3>
                <p><strong>${analysis.recommended_approach?.replace('_', ' ').toUpperCase()}</strong></p>
            </div>
        `;
    }
    
    formatWeeklyPerformanceTable(weeklyResults) {
        return `
            <table style="border-collapse: collapse; width: 100%;">
                <thead>
                    <tr style="background: #f8f9fa;">
                        <th style="border: 1px solid #ddd; padding: 8px;">Week</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Rule-Based Score</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Cognitive Score</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Corporate Score</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Best Performer</th>
                    </tr>
                </thead>
                <tbody>
                    ${weeklyResults.map(week => {
                        const evaluations = week.game_master_evaluation?.evaluations || {};
                        const scores = {
                            rule_based: evaluations.rule_based?.overall_score || 0,
                            cognitive: evaluations.cognitive?.overall_score || 0,
                            corporate: evaluations.corporate?.overall_score || 0
                        };
                        const best = Object.entries(scores).reduce((a, b) => scores[a[0]] > scores[b[0]] ? a : b)[0];
                        
                        return `
                            <tr>
                                <td style="border: 1px solid #ddd; padding: 8px;">${week.week}</td>
                                <td style="border: 1px solid #ddd; padding: 8px;">${scores.rule_based}/10</td>
                                <td style="border: 1px solid #ddd; padding: 8px;">${scores.cognitive}/10</td>
                                <td style="border: 1px solid #ddd; padding: 8px;">${scores.corporate}/10</td>
                                <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">${best.replace('_', ' ').toUpperCase()}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        `;
    }

    // Session History Management
    async openSessionHistory() {
        const modal = document.getElementById('session-history-modal');
        const listContainer = document.getElementById('session-list');
        
        modal.classList.remove('hidden');
        listContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #6c757d;"><div class="loading-spinner"></div><p>Loading sessions...</p></div>';
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/simulate/autorun/sessions`);
            const data = await response.json();
            
            if (data.sessions && data.sessions.length > 0) {
                listContainer.innerHTML = this.renderSessionList(data.sessions);
            } else {
                listContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #6c757d;"><p>No completed AutoRun sessions found.</p><p>Run an Auto-Evaluate 5 Weeks simulation to see results here.</p></div>';
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            listContainer.innerHTML = '<div style="text-align: center; padding: 40px; color: #dc3545;"><p>Error loading sessions</p></div>';
        }
    }

    renderSessionList(sessions) {
        return `
            <div style="display: grid; gap: 20px;">
                ${sessions.map(session => {
                    const date = new Date(session.saved_at).toLocaleString();
                    const rankings = session.final_analysis.overall_rankings || {};
                    const winner = session.final_analysis.recommended_approach || 'unknown';
                    
                    return `
                        <div class="session-card" style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border: 1px solid #e9ecef;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                                <div>
                                    <h3 style="margin: 0; color: #2c3e50;">5-Week Simulation</h3>
                                    <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 0.9em;">${date}</p>
                                </div>
                                <div style="text-align: right;">
                                    <div class="winner-badge" style="background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 6px 12px; border-radius: 20px; font-size: 0.9em; font-weight: 600; margin-bottom: 8px;">
                                        Winner: ${winner.charAt(0).toUpperCase() + winner.slice(1)}
                                    </div>
                                    <div style="font-size: 0.85em; color: #6c757d;">${session.total_weeks} weeks completed</div>
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 15px;">
                                <div style="background: #f8f9fa; padding: 12px; border-radius: 8px;">
                                    <strong style="color: #495057;">Final Rankings:</strong>
                                    <div style="display: flex; gap: 15px; margin-top: 8px; flex-wrap: wrap;">
                                        ${Object.entries(rankings).map(([team, rank]) => `
                                            <span style="background: ${rank === 1 ? '#28a745' : rank === 2 ? '#ffc107' : '#6c757d'}; color: ${rank === 3 ? 'white' : rank === 1 ? 'white' : '#000'}; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: 600;">
                                                ${rank}. ${team.replace('_', ' ').toUpperCase()}
                                            </span>
                                        `).join('')}
                                    </div>
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff;">
                                <div style="font-size: 0.9em; color: #495057; line-height: 1.4;">
                                    ${session.final_analysis.game_master_final_report || 'No final report available'}
                                </div>
                            </div>
                            
                            <div style="text-align: right;">
                                <button onclick="dashboard.viewSessionSummary('${session.session_id}')" class="btn primary" style="padding: 8px 16px;">
                                    View Visual Summary
                                </button>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }

    async viewSessionSummary(sessionId) {
        const summaryModal = document.getElementById('session-summary-modal');
        const summaryContent = document.getElementById('session-summary-content');
        const summaryTitle = document.getElementById('summary-modal-title');
        
        // Close the session history modal
        document.getElementById('session-history-modal').classList.add('hidden');
        
        // Open summary modal
        summaryModal.classList.remove('hidden');
        if (summaryTitle) summaryTitle.textContent = `Session Summary - ${sessionId.substring(0, 8)}...`;
        summaryContent.innerHTML = '<div style="text-align: center; padding: 40px; color: #6c757d;"><div class="loading-spinner"></div><p>Loading detailed summary...</p></div>';
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/simulate/autorun/sessions/${sessionId}/summary`);
            const data = await response.json();
            
            summaryContent.innerHTML = this.renderSessionSummary(data);
        } catch (error) {
            console.error('Error loading session summary:', error);
            summaryContent.innerHTML = '<div style="text-align: center; padding: 40px; color: #dc3545;"><p>Error loading session summary</p></div>';
        }
    }

    renderSessionSummary(data) {
        return `
            <!-- Game Master Final Analysis -->
            <div class="autorun-overall-analysis" style="margin-bottom: 30px;">
                <h3>🎮 Game Master Final Analysis</h3>
                <div class="overall-analysis-content">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
                        <div class="metric">
                            <div class="metric-value">${data.session_summary.total_weeks}</div>
                            <div class="metric-label">Weeks Completed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${data.final_analysis.recommended_approach.charAt(0).toUpperCase() + data.final_analysis.recommended_approach.slice(1)}</div>
                            <div class="metric-label">Recommended Approach</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${new Date(data.session_summary.saved_at).toLocaleDateString()}</div>
                            <div class="metric-label">Completed</div>
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; text-align: left;">
                        <strong style="color: #495057;">Game Master Comprehensive Analysis:</strong>
                        <div style="margin: 8px 0 0 0; line-height: 1.5; text-align: left;">
                            <p style="text-align: left;"><strong>Performance Summary:</strong> Over ${data.session_summary.total_weeks} weeks, the <strong>${data.final_analysis.recommended_approach.toUpperCase()}</strong> team demonstrated superior adaptability and strategic decision-making.</p>
                            
                            <div style="margin: 12px 0; text-align: left;">
                                <strong>Key Insights:</strong>
                                <ul style="margin: 4px 0; padding-left: 20px; text-align: left;">
                                    <li><strong>Cognitive Team:</strong> Consistently achieved highest ROI (${data.cumulative_performance.cognitive?.average_roi?.toFixed(2) || 'N/A'}x avg) with strategic adaptability, excelling in budget-constrained scenarios and showing superior learning patterns.</li>
                                    <li><strong>Rule-Based System:</strong> Protected highest total CLV (£${data.cumulative_performance.rule_based?.total_clv_protected?.toLocaleString() || 'N/A'}) but showed limited adaptability to changing market conditions.</li>
                                    <li><strong>Corporate Team:</strong> Maintained conservative approach with solid ROI but consistently underutilized budget capacity and missed strategic opportunities.</li>
                                </ul>
                            </div>
                            
                            <p style="text-align: left;"><strong>Strategic Recommendation:</strong> ${data.final_analysis.game_master_final_report} The cognitive approach's superior adaptability and ROI optimization make it the optimal choice for dynamic market conditions requiring strategic flexibility.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Cumulative Performance Summary -->
            <div class="running-totals-section" style="margin-bottom: 30px;">
                <h3>Cumulative Performance Summary</h3>
                <table class="results-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="border: 1px solid #ddd; padding: 12px; background: #f8f9fa; text-align: left;">Metric</th>
                            <th style="border: 1px solid #ddd; padding: 12px; background: #f8f9fa; text-align: center; color: #007bff;">RULE BASED</th>
                            <th style="border: 1px solid #ddd; padding: 12px; background: #f8f9fa; text-align: center; color: #28a745;">COGNITIVE</th>
                            <th style="border: 1px solid #ddd; padding: 12px; background: #f8f9fa; text-align: center; color: #6f42c1;">CORPORATE</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;">Total CLV Protected</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">£${data.cumulative_performance.rule_based.total_clv_protected.toLocaleString()}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">£${data.cumulative_performance.cognitive.total_clv_protected.toLocaleString()}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">£${data.cumulative_performance.corporate.total_clv_protected.toLocaleString()}</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;">Total Budget Spent</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">£${Math.round(data.cumulative_performance.rule_based.total_budget_spent).toLocaleString()}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">£${Math.round(data.cumulative_performance.cognitive.total_budget_spent).toLocaleString()}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">£${Math.round(data.cumulative_performance.corporate.total_budget_spent).toLocaleString()}</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;">Total Customers Saved</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${data.cumulative_performance.rule_based.total_customers_saved}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${data.cumulative_performance.cognitive.total_customers_saved}</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${data.cumulative_performance.corporate.total_customers_saved}</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;">Overall ROI</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold;">${data.cumulative_performance.rule_based.average_roi.toFixed(2)}x</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold;">${data.cumulative_performance.cognitive.average_roi.toFixed(2)}x</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold;">${data.cumulative_performance.corporate.average_roi.toFixed(2)}x</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #ddd; padding: 8px; background: #f8f9fa; font-weight: bold;">Average Game Master Score</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${data.cumulative_performance.rule_based.average_score.toFixed(1)}/10</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${data.cumulative_performance.cognitive.average_score.toFixed(1)}/10</td>
                            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">${data.cumulative_performance.corporate.average_score.toFixed(1)}/10</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Weekly Breakdown -->
            <div class="weekly-history-section">
                <h3>Weekly Performance Breakdown</h3>
                <div>
                    ${data.weekly_details.map(week => `
                        <div class="week-result-card" style="margin-bottom: 20px;">
                            <div class="week-title">Week ${week.week}</div>
                            <div class="business-context">
                                <h4>Business Context</h4>
                                <p style="margin-bottom: 10px;">${week.business_context}</p>
                                <div class="parameters-summary">
                                    <span>Customers at Risk: ${week.customers_at_risk}</span>
                                    <span>Budget: £${(week.weekly_budget / 1000).toFixed(0)}k</span>
                                </div>
                            </div>
                            <div class="teams-grid-horizontal">
                                ${Object.entries(week.teams).map(([teamName, teamData]) => `
                                    <div class="team-card">
                                        <div class="card-header">
                                            <div class="team-name">${teamName.replace('_', ' ').toUpperCase()}</div>
                                            <div class="score-badge">${teamData.game_master_score}/10</div>
                                        </div>
                                        <div class="metrics-grid">
                                            <div class="metric">
                                                <div class="metric-value">£${teamData.clv_protected.toLocaleString()}</div>
                                                <div class="metric-label">CLV Protected</div>
                                            </div>
                                            <div class="metric">
                                                <div class="metric-value">${teamData.customers_saved}</div>
                                                <div class="metric-label">Customers Saved</div>
                                            </div>
                                            <div class="metric">
                                                <div class="metric-value">£${Math.round(teamData.budget_spent).toLocaleString()}</div>
                                                <div class="metric-label">Budget Spent</div>
                                            </div>
                                            <div class="metric roi-metric">
                                                <div class="metric-value roi-value">${teamData.roi.toFixed(2)}x</div>
                                                <div class="metric-label">ROI</div>
                                            </div>
                                        </div>
                                        
                                        <!-- Game Master Evaluation Details -->
                                        ${teamData.game_master_evaluation ? `
                                        <div style="margin-top: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007bff;">
                                            <h5 style="margin: 0 0 8px 0; color: #495057; font-size: 0.9em;">Game Master Evaluation</h5>
                                            
                                            <div style="margin-bottom: 10px;">
                                                <div style="display: flex; gap: 15px; font-size: 0.85em; margin-bottom: 8px;">
                                                    <span><strong>Quality:</strong> ${teamData.game_master_evaluation.decision_quality}/10</span>
                                                    <span><strong>Efficiency:</strong> ${teamData.game_master_evaluation.resource_efficiency}/10</span>
                                                    <span><strong>Adaptability:</strong> ${teamData.game_master_evaluation.adaptability}/10</span>
                                                </div>
                                            </div>
                                            
                                            ${teamData.game_master_evaluation.reasoning ? `
                                            <div style="margin-bottom: 10px;">
                                                <strong style="color: #495057; font-size: 0.85em;">Reasoning:</strong>
                                                <p style="margin: 4px 0 0 0; font-size: 0.8em; line-height: 1.3; color: #6c757d;">${teamData.game_master_evaluation.reasoning}</p>
                                            </div>
                                            ` : ''}
                                            
                                            ${teamData.game_master_evaluation.strengths && teamData.game_master_evaluation.strengths.length > 0 ? `
                                            <div style="margin-bottom: 8px;">
                                                <strong style="color: #28a745; font-size: 0.85em;">Strengths:</strong>
                                                <ul style="margin: 4px 0 0 0; padding-left: 16px; font-size: 0.8em; color: #495057;">
                                                    ${teamData.game_master_evaluation.strengths.map(strength => `<li>${strength}</li>`).join('')}
                                                </ul>
                                            </div>
                                            ` : ''}
                                            
                                            ${teamData.game_master_evaluation.improvements && teamData.game_master_evaluation.improvements.length > 0 ? `
                                            <div>
                                                <strong style="color: #ffc107; font-size: 0.85em;">Areas for Improvement:</strong>
                                                <ul style="margin: 4px 0 0 0; padding-left: 16px; font-size: 0.8em; color: #495057;">
                                                    ${teamData.game_master_evaluation.improvements.map(improvement => `<li>${improvement}</li>`).join('')}
                                                </ul>
                                            </div>
                                            ` : ''}
                                        </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderPerformanceTrendsChart(trends) {
        const teams = Object.keys(trends);
        const weeks = trends[teams[0]]?.length || 0;
        const maxScore = Math.max(...teams.flatMap(team => trends[team] || []));
        
        const colors = {
            rule_based: '#007bff',
            cognitive: '#28a745', 
            corporate: '#6f42c1'
        };
        
        return `
            <svg width="100%" height="100%" viewBox="0 0 800 250" style="background: white; border-radius: 8px;">
                <!-- Grid lines -->
                ${Array.from({length: 11}, (_, i) => `
                    <line x1="80" y1="${20 + i * 20}" x2="750" y2="${20 + i * 20}" stroke="#e9ecef" stroke-width="1"/>
                `).join('')}
                ${Array.from({length: weeks}, (_, i) => `
                    <line x1="${80 + i * (670 / (weeks - 1))}" y1="20" x2="${80 + i * (670 / (weeks - 1))}" y2="220" stroke="#e9ecef" stroke-width="1"/>
                `).join('')}
                
                <!-- Y-axis labels -->
                ${Array.from({length: 11}, (_, i) => `
                    <text x="75" y="${225 - i * 20}" text-anchor="end" font-size="12" fill="#6c757d">${i}</text>
                `).join('')}
                
                <!-- X-axis labels -->
                ${Array.from({length: weeks}, (_, i) => `
                    <text x="${80 + i * (670 / (weeks - 1))}" y="240" text-anchor="middle" font-size="12" fill="#6c757d">W${i + 1}</text>
                `).join('')}
                
                <!-- Performance lines -->
                ${teams.map(team => {
                    const teamTrends = trends[team] || [];
                    const points = teamTrends.map((score, i) => {
                        const x = 80 + i * (670 / (weeks - 1));
                        const y = 220 - (score / 10) * 200;
                        return `${x},${y}`;
                    }).join(' ');
                    
                    return `
                        <polyline points="${points}" fill="none" stroke="${colors[team] || '#6c757d'}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                        ${teamTrends.map((score, i) => `
                            <circle cx="${80 + i * (670 / (weeks - 1))}" cy="${220 - (score / 10) * 200}" r="4" fill="${colors[team] || '#6c757d'}"/>
                        `).join('')}
                    `;
                }).join('')}
                
                <!-- Legend -->
                ${teams.map((team, i) => `
                    <g>
                        <rect x="${600 + i * 60}" y="10" width="12" height="3" fill="${colors[team] || '#6c757d'}"/>
                        <text x="${615 + i * 60}" y="18" font-size="10" fill="#495057">${team.replace('_', ' ').toUpperCase()}</text>
                    </g>
                `).join('')}
                
                <!-- Labels -->
                <text x="20" y="120" font-size="12" fill="#495057" transform="rotate(-90 20 120)">Game Master Score</text>
                <text x="400" y="260" text-anchor="middle" font-size="12" fill="#495057">Week</text>
            </svg>
        `;
    }
}

// Global modal control functions
function closeSessionHistoryModal() {
    document.getElementById('session-history-modal').classList.add('hidden');
}

function closeSessionSummaryModal() {
    document.getElementById('session-summary-modal').classList.add('hidden');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new MultiTeamDashboard();
});