let progressChart = null;
let scaffoldingChart = null; // 新增
let isLoading = false;

async function loadMyAnalytics() {
    if (isLoading) return;

    isLoading = true;
    const refreshBtn = document.getElementById('refresh-text');
    refreshBtn.textContent = '載入中...';

    try {
        document.getElementById('error-container').innerHTML = '';
        document.getElementById('weaknessCards').innerHTML = '<div class="loading">載入中...</div>';
        document.getElementById('learningTimeline').innerHTML = '<div class="loading">載入中...</div>';

        const response = await fetch('/my_learning_analytics', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // 更新統計卡片
        updateOverallStats(data.overall_stats);

        // 繪製進度圖表
        drawProgressChart(data.unit_progress);

        // 繪製鷹架類型圖表 (新增)
        drawScaffoldingChart(data.scaffolding_stats);

        // 顯示弱點分析
        displayWeaknessAnalysis(data.unit_progress, data.weakness_analysis);

        // 顯示學習時間軸
        displayTimeline(data.timeline);

    } catch (error) {
        console.error('載入數據失敗:', error);
        showError('載入數據時發生錯誤：' + error.message);
    } finally {
        isLoading = false;
        refreshBtn.textContent = '重新整理';
    }
}

function showError(message) {
    const errorContainer = document.getElementById('error-container');
    errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
}

function updateOverallStats(stats) {
    document.getElementById('unitsStudied').textContent = stats.units_studied || 0;
    document.getElementById('avgLevel').textContent = stats.avg_level || '-';

    const mostDiscussed = stats.most_discussed_unit || '無';
    document.getElementById('mostDiscussed').textContent =
        mostDiscussed.length > 10 ? mostDiscussed.substring(0, 10) + '...' : mostDiscussed;

    // 新增：主要鷹架類型
    const mainScaffolding = stats.main_scaffolding || '無';
    document.getElementById('mainScaffolding').textContent = mainScaffolding;
}

function drawProgressChart(unitProgress) {
    const ctx = document.getElementById('unitProgressChart');
    if (!ctx) return;

    // 銷毀舊圖表
    if (progressChart) {
        progressChart.destroy();
    }

    const units = Object.keys(unitProgress);
    const avgLevels = units.map(unit => unitProgress[unit].avg_level);
    const conversations = units.map(unit => unitProgress[unit].conversations);

    if (units.length === 0) {
        const ctxContext = ctx.getContext('2d');
        ctxContext.clearRect(0, 0, ctx.width, ctx.height);
        ctxContext.font = "16px Arial";
        ctxContext.fillStyle = "#999";
        ctxContext.textAlign = "center";
        ctxContext.fillText("暫無學習數據", ctx.width / 2, ctx.height / 2);
        return;
    }

    progressChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: units.map(u => u.length > 8 ? u.substring(0, 8) + '...' : u),
            datasets: [
                {
                    label: '平均理解程度',
                    data: avgLevels,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1,
                    yAxisID: 'y'
                },
                {
                    label: '對話次數',
                    data: conversations,
                    backgroundColor: 'rgba(118, 75, 162, 0.6)',
                    borderColor: 'rgba(118, 75, 162, 1)',
                    borderWidth: 1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    type: 'linear',
                    position: 'left',
                    beginAtZero: true,
                    max: 3,
                    title: {
                        display: true,
                        text: '理解程度 (1-3)'
                    },
                    ticks: {
                        stepSize: 0.5
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '對話次數'
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}

// 新增：繪製鷹架類型分佈圖
function drawScaffoldingChart(scaffoldingStats) {
    const ctx = document.getElementById('scaffoldingChart');
    if (!ctx) return;

    // 銷毀舊圖表
    if (scaffoldingChart) {
        scaffoldingChart.destroy();
    }

    const labels = Object.keys(scaffoldingStats);
    const data = labels.map(label => scaffoldingStats[label].count);
    const percentages = labels.map(label => scaffoldingStats[label].percentage);

    if (labels.length === 0) {
        const ctxContext = ctx.getContext('2d');
        ctxContext.clearRect(0, 0, ctx.width, ctx.height);
        ctxContext.font = "16px Arial";
        ctxContext.fillStyle = "#999";
        ctxContext.textAlign = "center";
        ctxContext.fillText("暫無鷹架數據", ctx.width / 2, ctx.height / 2);
        return;
    }

    scaffoldingChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(141, 225, 141, 0.8)',  // 差異鷹架 - 綠色
                    'rgba(255, 206, 86, 0.8)',   // 重複鷹架 - 黃色
                    'rgba(255, 99, 132, 0.8)'    // 協同鷹架 - 紅色
                ],
                borderColor: [
                    'rgba(141, 225, 141, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 13
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = percentages[context.dataIndex];
                            return `${label}: ${value} 次 (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function displayWeaknessAnalysis(unitProgress, weaknessAnalysis) {
    const container = document.getElementById('weaknessCards');

    if (Object.keys(unitProgress).length === 0) {
        container.innerHTML = '<div class="loading">暫無學習數據</div>';
        return;
    }

    let html = '';

    for (const [unit, progress] of Object.entries(unitProgress)) {
        const weakness = weaknessAnalysis[unit] || {
            weakness: '分析中...',
            suggestions: [],
            confidence: '低'
        };

        html += `
            <div class="weakness-card">
                <div class="unit-name">${escapeHtml(unit)}</div>
                <div class="progress-info">
                    <span>
                        <span class="level-badge ${escapeHtml(progress.current_level)}">
                            ${escapeHtml(progress.current_level)}
                        </span>
                        <span class="trend-badge ${escapeHtml(progress.trend)}">
                            ${escapeHtml(progress.trend)}
                        </span>
                    </span>
                    <span style="color: #7f8c8d;">對話 ${progress.conversations} 次</span>
                </div>
                <div class="weakness-text">
                    <strong>⚠️ 主要弱點：</strong>
                    ${escapeHtml(weakness.weakness)}
                    <span class="confidence-badge ${escapeHtml(weakness.confidence)}">
                        信心度: ${escapeHtml(weakness.confidence)}
                    </span>
                </div>
                <div class="suggestions">
                    <h4>💡 改善建議</h4>
                    <ul>
                        ${weakness.suggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                    </ul>
                </div>
                <div style="margin-top: 15px; font-size: 12px; color: #7f8c8d;">
                    最後學習：${formatDate(progress.last_studied)}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function displayTimeline(timeline) {
    const container = document.getElementById('learningTimeline');

    if (!timeline || timeline.length === 0) {
        container.innerHTML = '<div class="loading">暫無學習軌跡</div>';
        return;
    }

    let html = '';

    timeline.forEach(item => {
        html += `
            <div class="timeline-item">
                <div class="timeline-content">
                    <div class="unit-title">${escapeHtml(item.unit)}</div>
                    <div class="timeline-meta">
                        <span class="level-badge ${escapeHtml(item.level)}">
                            ${escapeHtml(item.level)}
                        </span>
                        <span style="margin-left: 10px;">
                            ${formatDate(item.timestamp)}
                        </span>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '無';

    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return '今天';
        if (diffDays === 1) return '昨天';
        if (diffDays < 7) return `${diffDays}天前`;

        return date.toLocaleDateString('zh-TW');
    } catch (error) {
        return '無效日期';
    }
}

// 頁面載入時執行
document.addEventListener('DOMContentLoaded', () => {
    loadMyAnalytics();
});

// 視窗大小改變時重新調整圖表
window.addEventListener('resize', () => {
    if (progressChart) {
        progressChart.resize();
    }
    if (scaffoldingChart) {
        scaffoldingChart.resize();
    }
});