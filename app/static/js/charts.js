// Chart.js configuration and helper functions
let incomeExpenseChart = null;

// 1. Declare this globally at the TOP of charts.js 
// so the function can track and destroy the previous instance.
let incomeExpenseChartInstance = null;

function createIncomeExpenseChart(chartData) {
    const canvas = document.getElementById('incomeExpenseChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // 2. Properly destroy the existing chart to prevent layout jumping 
    // and "ghost" tooltips when hovering.
    if (incomeExpenseChartInstance) {
        incomeExpenseChartInstance.destroy();
    }
    
    incomeExpenseChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'Income',
                    data: chartData.income,
                    borderColor: '#2ecc71',
                    backgroundColor: 'rgba(46, 204, 113, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3
                },
                {
                    label: 'Expense',
                    data: chartData.expense,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Allows CSS to control height
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            label += 'KES ' + context.raw.toLocaleString();
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false // Cleaner look
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'K' + (value >= 1000 ? (value / 1000) + 'k' : value);
                        }
                    }
                }
            }
        }
    });
}

function updateChartsLanguage(lang) {
    // Update chart labels based on language
    if (incomeExpenseChart) {
        const labels = {
            en: { income: 'Income', expense: 'Expense' },
            sw: { income: 'Mapato', expense: 'Matumizi' }
        };
        
        incomeExpenseChart.data.datasets[0].label = labels[lang].income;
        incomeExpenseChart.data.datasets[1].label = labels[lang].expense;
        incomeExpenseChart.update();
    }
}