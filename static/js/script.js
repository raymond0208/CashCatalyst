console.log("Script loaded: " + new Date().toISOString());

const transactionTypeMapping = {
    "Cash from customers": "Cash-customer",
    "Salary & Supplier payments": "Salary-suppliers",
    "Interest paid": "Interest-paid",
    "Income taxes": "Income-tax",
    "Other operating cashflow": "Other-cfo",
    "Purchase of property&equipments": "Buy-property-equipments",
    "Sell of property&equipments": "Sell-property-equipments",
    "Purchase of investments": "Buy-investment",
    "Sale of investments": "Sell-investment",
    "Other investing cashflow": "Other-cfi",
    "Issuing shares": "Issue-shares",
    "Borrowings": "borrowings",
    "Repayment of borrowings": "Repay-borrowings",
    "Dividends paid": "Pay-dividends",
    "Other financing cashflow": "Other-cff"
};

// Define all functions first
function handleBalanceByDate() {
    console.log("Setting up balance by date handler");
    const balanceByDateForm = document.getElementById('balance-by-date-form');
    const balanceByDateResult = document.getElementById('balance-by-date-result');
    
    if (balanceByDateForm && balanceByDateResult) {
        console.log("Balance by date form and result div found");
        balanceByDateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log("Balance by date form submitted");

            const formData = new FormData(this);
            
            fetch('/balance-by-date', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                console.log("Response status:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("Received data:", data);
                if (data.error) {
                    throw new Error(data.error);
                }
                balanceByDateResult.innerHTML = `
                    <h4>Balance up to ${data.input_date}</h4>
                    <p>$${parseFloat(data.balance_sum).toFixed(2)}</p>
                `;
                console.log("Updated result div:", balanceByDateResult.innerHTML);
            })
            .catch(error => {
                console.error('Error:', error);
                balanceByDateResult.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
            });
        });
    } else {
        console.error("Balance by date form or result div not found");
        console.log("Form:", balanceByDateForm);
        console.log("Result div:", balanceByDateResult);
    }
}
// Handle Tab Switching
function handleTabSwitching() {
    console.log("Setting up tab switching");
    const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
    console.log("Found " + tabButtons.length + " tab buttons");
    
    if (tabButtons.length === 0) {
        console.error("No tab buttons found. Check your HTML structure.");
        return;
    }

    tabButtons.forEach(button => {
        console.log("Adding click listener to button:", button.id);
        button.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Get the target from href or data-bs-target
            const target = this.getAttribute('href') || this.getAttribute('data-bs-target');
            console.log("Tab clicked. Target:", target);
            
            if (!target) {
                console.error("No target found for this tab button");
                return;
            }

            const targetId = target.slice(1); // Remove the leading #
            
            console.log("Hiding all tab panes");
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('show', 'active');
                console.log("Removed classes from pane:", pane.id);
            });
            
            console.log("Deactivating all tab buttons");
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.setAttribute('aria-selected', 'false');
                console.log("Deactivated button:", btn.id);
            });
            
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                console.log("Activating tab pane:", targetId);
                targetPane.classList.add('show', 'active');
            } else {
                console.error("Target pane not found:", targetId);
            }
            
            console.log("Activating clicked tab button");
            this.classList.add('active');
            this.setAttribute('aria-selected', 'true');
        });
    });
}

// Generate AI analysis
function handleAIAnalysis() {
    var generateButton = document.querySelector('#generate-analysis');
    if (generateButton) {
        generateButton.addEventListener('click', function() {
            var loadingDiv = document.querySelector('#loading');
            var analysisContent = document.querySelector('#analysis-content');
            var analysisDashboard = document.querySelector('#analysis-dashboard');
            var rawAnalysis = document.querySelector('#raw-analysis');
            
            loadingDiv.style.display = 'block';
            analysisDashboard.style.display = 'none';
            rawAnalysis.innerHTML = '';
            
            fetch('/forecast')
                .then(response => response.json())
                .then(data => {
                    loadingDiv.style.display = 'none';
                    if (data.error) {
                        rawAnalysis.innerHTML = `<p class="text-danger">${data.error}</p>`;
                    } else {
                        // Show the dashboard
                        analysisDashboard.style.display = 'block';
                        
                        // Update pattern recognition
                        if (data.patterns) {
                            document.querySelector('#pattern-recognition-content').innerHTML = 
                                formatPatternAnalysis(data.patterns);
                        }
                        
                        // Update risk assessment
                        if (data.risk_metrics) {
                            document.querySelector('#risk-assessment-content').innerHTML = 
                                formatRiskMetrics(data.risk_metrics);
                        }
                        
                        // Update charts
                        if (data.patterns?.seasonal_pattern) {
                            updateSeasonalChart(data.patterns.seasonal_pattern);
                        }
                        if (data.forecasts) {
                            updateForecastChart(data.forecasts);
                        }
                        
                        // Display raw analysis
                        rawAnalysis.innerHTML = `<pre>${data.ai_analysis}</pre>`;
                    }
                })
                .catch(error => {
                    loadingDiv.style.display = 'none';
                    rawAnalysis.innerHTML = `<p class="text-danger">Failed to generate analysis: ${error}</p>`;
                });
        });
    }
}

// AI generates cashflow statement
function handleCashFlowStatement() {
    var generateButton = document.querySelector('#generate-cashflow-statement');
    if (generateButton) {
        generateButton.addEventListener('click', function() {
            var loadingDiv = document.querySelector('#loading');
            var analysisContent = document.querySelector('#analysis-content');
            loadingDiv.style.display = 'block';
            analysisContent.innerHTML = '';
            fetch('/generate_cashflow_statement')
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.error || `HTTP status ${response.status}`);
                        });
                    }
                    return response.blob();
                })
                .then(blob => {
                    loadingDiv.style.display = 'none';
                    var url = window.URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = 'cash_flow_statement.xlsx';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    analysisContent.innerHTML = '<p class="text-success">Cash flow statement generated and downloaded successfully.</p>';
                })
                .catch(error => {
                    loadingDiv.style.display = 'none';
                    console.error('Error:', error);
                    analysisContent.innerHTML = `<p class="text-danger">Failed to generate cash flow statement: ${error.message}</p>`;
                });
        });
    }
}

function handleInitialBalance() {
    // Add any specific handling for initial balance form if needed
}

function handleTransactionForm() {
    // Add any specific handling for transaction form if needed
}

function handleDeleteConfirmation() {
    var deleteButtons = document.querySelectorAll('form[action^="/delete/"]');
    deleteButtons.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm('Are you sure you want to delete this transaction?')) {
                e.preventDefault();
            }
        });
    });
}

function handleFileUpload() {
    var uploadForm = document.querySelector('#uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(uploadForm);
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    displayDataPreview(data.data);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }
}

function displayDataPreview(data) {
    console.log("displayDataPreview called with data:", data);
    var previewDiv = document.querySelector('#dataPreview');
    var table = document.createElement('table');
    table.className = 'table table-striped';
    var thead = document.createElement('thead');
    var tbody = document.createElement('tbody');

    // Define the correct column order
    const columnOrder = ['date', 'description', 'amount', 'type'];

    // Create table header
    var headerRow = document.createElement('tr');
    columnOrder.forEach(key => {
        var th = document.createElement('th');
        th.textContent = key.charAt(0).toUpperCase() + key.slice(1); // Capitalize first letter
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Define the allowed types with group structure
    const allowedTypes = [
        {
            group: "Cashflow from operation",
            options: [
                "Cash from customers",
                "Salary & Supplier payments",
                "Interest paid",
                "Income taxes",
                "Other operating cashflow"
            ]
        },
        {
            group: "Cashflow from investment",
            options: [
                "Purchase of property&equipments",
                "Sell of property&equipments",
                "Purchase of investments",
                "Sale of investments",
                "Other investing cashflow"
            ]
        },
        {
            group: "Cashflow from financing",
            options: [
                "Issuing shares",
                "Borrowings",
                "Repayment of borrowings",
                "Dividends paid",
                "Other financing cashflow"
            ]
        }
    ];

    // Create table body
    data.forEach((row, rowIndex) => {
        var tr = document.createElement('tr');
        columnOrder.forEach(key => {
            var td = document.createElement('td');
            if (key === 'type') {
                // Create a dropdown for the type field
                var select = document.createElement('select');
                select.className = 'form-select';
                select.name = `type_${rowIndex}`;

                let optionFound = false;
                allowedTypes.forEach(group => {
                    var optgroup = document.createElement('optgroup');
                    optgroup.label = group.group;
                    group.options.forEach(option => {
                        var optionElement = document.createElement('option');
                        optionElement.value = transactionTypeMapping[option] || option;
                        optionElement.textContent = option;
                        if (option === row[key] || transactionTypeMapping[option] === row[key]) {
                            optionElement.selected = true;
                            optionFound = true;
                        }
                        optgroup.appendChild(optionElement);
                    });
                    select.appendChild(optgroup);
                });

                // If no match found, set "Other operating cashflow" as default
                if (!optionFound) {
                    select.value = transactionTypeMapping["Other operating cashflow"] || "Other-cfo";
                }

                td.appendChild(select);
            } else {
                td.textContent = row[key];
            }
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    previewDiv.innerHTML = '';
    previewDiv.appendChild(table);
    previewDiv.style.display = 'block';

    // Add save button
    var saveButton = document.createElement('button');
    saveButton.textContent = 'Save Transactions';
    saveButton.className = 'btn btn-primary mt-3';
    saveButton.addEventListener('click', function() {
        saveTransactions(getUpdatedData(data));
    });
    previewDiv.appendChild(saveButton);
}

// Update getUpdatedData function to maintain the correct order
function getUpdatedData(originalData) {
    const columnOrder = ['date', 'description', 'amount', 'type'];
    var updatedData = originalData.map((row, index) => {
        var updatedRow = {};
        columnOrder.forEach(key => {
            if (key === 'type') {
                var typeSelect = document.querySelector(`select[name="type_${index}"]`);
                updatedRow[key] = typeSelect ? typeSelect.value : row[key];
            } else {
                updatedRow[key] = row[key];
            }
        });
        return updatedRow;
    });
    return updatedData;
}

function saveTransactions(data) {
    fetch('/save_transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        alert(result.message);
        window.location.href = '/home';
    })
    .catch(error => console.error('Error:', error));
}

function handleEditTransaction() {
    // Add any specific handling for edit transaction form if needed
}

function handleAuthForms() {
    // Add any specific handling for registration and login forms if needed
}


function handleMonthlyBalanceChart() {
    console.log("Setting up monthly balance chart handler");
    
    // Instead of looking for the tab link, we'll look for the tab content
    const balanceByDateTab = document.getElementById('balance-by-date');
    
    if (balanceByDateTab) {
        console.log("Balance by date tab found");
        
        // We'll use MutationObserver to detect when the tab becomes visible
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    if (balanceByDateTab.classList.contains('active') && balanceByDateTab.classList.contains('show')) {
                        console.log("Balance by date tab is now active");
                        fetchMonthlyBalances();
                    }
                }
            });
        });

        observer.observe(balanceByDateTab, { attributes: true });
    } else {
        console.error("Balance by date tab not found");
        console.log("Looking for element with id: balance-by-date");
    }
}

function fetchMonthlyBalances() {
    console.log("Fetching monthly balances");
    fetch('/monthly-balances')
        .then(response => response.json())
        .then(data => {
            console.log("Received monthly balance data:", data);
            const chartImg = document.getElementById('monthly-balance-chart');
            if (chartImg) {
                chartImg.src = data.chart_image;
                console.log("Updated chart image source");
            } else {
                console.error("Chart image element not found");
            }
        })
        .catch(error => console.error('Error fetching monthly balances:', error));
}

function formatPatternAnalysis(patterns) {
    const formatTrend = (trend) => {
        const [slope, intercept] = trend;
        const direction = slope > 0 ? 'Upward' : slope < 0 ? 'Downward' : 'Stable';
        return `${direction} (slope: ${slope.toFixed(2)})`;
    };

    return `
        <ul class="list-unstyled">
            <li><strong>Trend:</strong> ${formatTrend(patterns.trend)}</li>
            <li><strong>Volatility:</strong> $${patterns.volatility.toFixed(2)}</li>
            <li><strong>Seasonal Pattern:</strong> ${patterns.seasonal_pattern.length > 0 ? 'Detected' : 'Insufficient data'}</li>
        </ul>
    `;
}

function formatRiskMetrics(metrics) {
    const formatNumber = (num) => {
        if (num >= 9999) {
            return '∞';
        }
        return num.toFixed(2);
    };

    return `
        <ul class="list-unstyled">
            <li><strong>Liquidity Ratio:</strong> ${formatNumber(metrics.liquidity_ratio)}</li>
            <li><strong>Cash Flow Volatility:</strong> $${formatNumber(metrics.cash_flow_volatility)}</li>
            <li><strong>Burn Rate:</strong> $${formatNumber(metrics.burn_rate)}/month</li>
            <li><strong>Cash Runway:</strong> ${formatNumber(metrics.runway_months)} months</li>
        </ul>
    `;
}

function updateSeasonalChart(seasonalData) {
    const ctx = document.getElementById('seasonal-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.seasonalChart) {
        window.seasonalChart.destroy();
    }

    window.seasonalChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: seasonalData.length}, (_, i) => `Month ${i + 1}`),
            datasets: [{
                label: 'Seasonal Pattern',
                data: seasonalData,
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Seasonal Effect ($)'
                    }
                }
            }
        }
    });
}

function updateForecastChart(forecasts) {
    const ctx = document.getElementById('forecast-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.forecastChart) {
        window.forecastChart.destroy();
    }

    window.forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: 90}, (_, i) => `Day ${i + 1}`),
            datasets: [{
                label: '30-Day Forecast',
                data: forecasts['30_days'],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1,
                fill: false
            }, {
                label: '60-Day Forecast',
                data: forecasts['60_days'],
                borderColor: 'rgb(255, 159, 64)',
                tension: 0.1,
                fill: false
            }, {
                label: '90-Day Forecast',
                data: forecasts['90_days'],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Projected Amount ($)'
                    }
                }
            }
        }
    });
}

// Main execution
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded");

    // Flash message fade out (applicable to all pages)
    setTimeout(function() {
        var flashMessages = document.querySelectorAll('.alert');
        flashMessages.forEach(function(message) {
            message.style.transition = 'opacity 0.5s ease';
            message.style.opacity = '0';
            setTimeout(function() { message.remove(); }, 500);
        });
    }, 3000);

    // Sidebar collapse functionality
    const collapseButton = document.querySelector('.collapse-menu');
    const sidebar = document.querySelector('.sidebar');
    const menuTexts = document.querySelectorAll('.menu-item span, .collapse-menu span');
    
    if (collapseButton) {
        collapseButton.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            menuTexts.forEach(text => {
                text.style.display = sidebar.classList.contains('collapsed') ? 'none' : 'inline';
            });
            collapseButton.querySelector('i').classList.toggle('fa-angles-right');
            collapseButton.querySelector('i').classList.toggle('fa-angles-left');
        });
    }

    // Call all handler functions
    handleBalanceByDate();
    handleTabSwitching();
    handleAIAnalysis();
    handleCashFlowStatement();
    handleInitialBalance();
    handleTransactionForm();
    handleDeleteConfirmation();
    handleFileUpload();
    handleEditTransaction();
    handleAuthForms();
    handleMonthlyBalanceChart();
});