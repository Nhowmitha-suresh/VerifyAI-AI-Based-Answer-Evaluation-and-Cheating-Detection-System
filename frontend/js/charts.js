/**
 * VerifyAI Minimal Luxury Chart Manager.
 * Uses warm beige, muted gold, and soft brown palette.
 */

let riskChart = null;

function initRiskChart(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 160);
    gradient.addColorStop(0, 'rgba(199, 161, 90, 0.25)');
    gradient.addColorStop(1, 'rgba(199, 161, 90, 0.0)');

    riskChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Risk Index %',
                data: [],
                borderColor: '#C7A15A',
                borderWidth: 2,
                backgroundColor: gradient,
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: {
                x: {
                    display: false
                },
                y: {
                    min: 0,
                    max: 100,
                    grid: {
                        color: 'rgba(139, 107, 74, 0.1)'
                    },
                    ticks: {
                        color: '#7A736D',
                        font: { size: 10 }
                    }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

function updateRiskChart(timestamp, riskValue) {
    if (!riskChart) return;
    
    riskChart.data.labels.push(timestamp);
    riskChart.data.datasets[0].data.push(riskValue);

    if (riskChart.data.labels.length > 40) {
        riskChart.data.labels.shift();
        riskChart.data.datasets[0].data.shift();
    }

    riskChart.update('none');
}
