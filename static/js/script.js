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
                    <div class="alert alert-info">
                        <h4>Balance as of ${data.date}</h4>
                        <p class="h3">$${parseFloat(data.balance).toFixed(2)}</p>
                    </div>
                `;
                console.log("Updated result div:", balanceByDateResult.innerHTML);
            })
            .catch(error => {
                console.error('Error:', error);
                balanceByDateResult.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
            });
        });
    }
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
            
            // Show loading state
            const submitButton = uploadForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
            }

            var formData = new FormData(uploadForm);
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.error || 'Failed to upload file');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                // Clear any previous error messages
                const errorDiv = document.getElementById('uploadError');
                if (errorDiv) {
                    errorDiv.style.display = 'none';
                }
                displayDataPreview(data.data);
            })
            .catch(error => {
                console.error('Error:', error);
                // Display error message on the page
                const errorDiv = document.getElementById('uploadError');
                if (errorDiv) {
                    errorDiv.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
                    errorDiv.style.display = 'block';
                } else {
                    alert(error.message || 'An error occurred during upload');
                }
            })
            .finally(() => {
                // Reset button state
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Upload File';
                }
            });
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
    const saveButton = document.querySelector('#dataPreview button');
    if (saveButton) {
        saveButton.disabled = true;
        saveButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    }

    fetch('/save_transactions', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                // Extract the main error message from SQLAlchemy error
                let errorMessage = err.error;
                if (errorMessage.includes('IntegrityError')) {
                    errorMessage = 'Failed to save transactions. Please try logging in again.';
                }
                throw new Error(errorMessage);
            });
        }
        return response.json();
    })
    .then(result => {
        if (result.error) {
            throw new Error(result.error);
        }
        // Show success message
        const previewDiv = document.getElementById('dataPreview');
        if (previewDiv) {
            previewDiv.innerHTML = `
                <div class="alert alert-success">
                    ${result.message}
                    <div class="mt-2">
                        <a href="/cash-activities" class="btn btn-primary">View Transactions</a>
                    </div>
                </div>
            `;
        } else {
            alert(result.message || 'Transactions saved successfully');
            window.location.href = '/cash-activities';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        // Show error in the preview div if possible
        const previewDiv = document.getElementById('dataPreview');
        if (previewDiv) {
            previewDiv.innerHTML = `
                <div class="alert alert-danger">
                    ${error.message}
                    <div class="mt-2">
                        <button onclick="window.location.reload()" class="btn btn-primary">Try Again</button>
                    </div>
                </div>
            `;
        } else {
            alert(error.message || 'An error occurred while saving transactions');
        }
    })
    .finally(() => {
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.innerHTML = 'Save Transactions';
        }
    });
}

function handleEditTransaction() {
    // Add any specific handling for edit transaction form if needed
}

function handleAuthForms() {
    // Add any specific handling for registration and login forms if needed
}

function handleMonthlyBalanceChart() {
    console.log("Setting up monthly balance chart handler");
    fetchMonthlyBalances();
}

function fetchMonthlyBalances() {
    console.log("Fetching monthly balances");
    fetch('/monthly-balances')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch monthly balances');
            }
            return response.json();
        })
        .then(response => {
            if (!response.success) {
                throw new Error(response.error || 'Failed to fetch data');
            }
            
            const data = response.data;
            const existingChart = Chart.getChart('monthly-balance-chart');
            if (existingChart) {
                existingChart.destroy();
            }
            
            const ctx = document.getElementById('monthly-balance-chart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Monthly Balance',
                        data: data.balances,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: value => '$' + value.toLocaleString()
                            }
                        }
                    },
                    plugins: {
                        title: {
                            display: false
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching monthly balances:', error);
            const chartContainer = document.querySelector('.monthly-chart-section');
            if (chartContainer) {
                chartContainer.innerHTML += `
                    <div class="alert alert-danger mt-3">
                        Failed to load monthly balance chart: ${error.message}
                    </div>
                `;
            }
        });
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
    const formatNumber = (num, allowInfinity = false) => {
        if (num === undefined || num === null || !isFinite(num)) {
            return '0.00';
        }
        if (!allowInfinity && (num >= 9999 || num <= -9999)) {
            return '0.00';
        }
        return num.toFixed(2);
    };

    const formatBurnRate = (rate) => {
        if (rate === undefined || rate === null || !isFinite(rate)) {
            return '0.00';
        }
        // Ensure burn rate is positive for display
        return Math.abs(rate).toFixed(2);
    };

    return `
        <ul class="list-unstyled">
            <li><strong>Liquidity Ratio:</strong> ${formatNumber(metrics.liquidity_ratio)}</li>
            <li><strong>Cash Flow Volatility:</strong> $${formatNumber(metrics.cash_flow_volatility)}</li>
            <li><strong>Burn Rate:</strong> $${formatBurnRate(metrics.burn_rate)}/month</li>
            <li><strong>Cash Runway:</strong> ${formatNumber(metrics.runway_months, true)} months</li>
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

function handleMonthlyIncomeExpense() {
    fetch('/monthly-income-expense')
        .then(response => response.json())
        .then(response => {
            if (!response.success) {
                throw new Error(response.error || 'Failed to fetch data');
            }
            
            const data = response.data;
            
            // Destroy existing charts if they exist
            const existingIncomeChart = Chart.getChart('monthly-income-chart');
            if (existingIncomeChart) {
                existingIncomeChart.destroy();
            }
            
            const existingExpenseChart = Chart.getChart('monthly-expense-chart');
            if (existingExpenseChart) {
                existingExpenseChart.destroy();
            }
            
            // Create Income Chart
            const incomeCtx = document.getElementById('monthly-income-chart').getContext('2d');
            new Chart(incomeCtx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Monthly Income',
                        data: data.income,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: value => '$' + value.toLocaleString()
                            }
                        }
                    }
                }
            });

            // Create Expense Chart
            const expenseCtx = document.getElementById('monthly-expense-chart').getContext('2d');
            new Chart(expenseCtx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Monthly Expenses',
                        data: data.expense,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: value => '$' + value.toLocaleString()
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching monthly income/expense data:', error);
        });
}

function handleCashoutCategories() {
    fetch('/cashout-categories')
        .then(response => response.json())
        .then(response => {
            if (!response.success) {
                throw new Error(response.error || 'Failed to fetch data');
            }
            
            const data = response.data;
            const existingChart = Chart.getChart('cashout-categories-chart');
            if (existingChart) {
                existingChart.destroy();
            }
            
            const ctx = document.getElementById('cashout-categories-chart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Cash-out Amount',
                        data: data.amounts,
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.6)',
                            'rgba(54, 162, 235, 0.6)',
                            'rgba(255, 206, 86, 0.6)',
                            'rgba(75, 192, 192, 0.6)',
                            'rgba(153, 102, 255, 0.6)',
                        ],
                        borderColor: [
                            'rgba(255, 99, 132, 1)',
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)',
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: value => '$' + value.toLocaleString()
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `$${value.toLocaleString()} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching cashout categories:', error);
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
    handleAIAnalysis();
    handleCashFlowStatement();
    handleInitialBalance();
    handleTransactionForm();
    handleDeleteConfirmation();
    handleFileUpload();
    handleEditTransaction();
    handleAuthForms();

    // Initialize all charts if we're on the cash overview page
    const monthlyChartsSection = document.querySelector('.monthly-charts-section');
    if (monthlyChartsSection) {
        handleMonthlyBalanceChart();
        handleMonthlyIncomeExpense();
        handleCashoutCategories();
    }
});