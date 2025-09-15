let charts = {}; // 儲存圖表實例
let isLoading = false; // 防止重複載入

// 載入所有分析數據
async function loadAnalytics() {
    if (isLoading) return;

    isLoading = true;
    const refreshBtn = document.getElementById('refresh-text');
    refreshBtn.innerHTML = '<span class="loading-spinner"></span> 載入中...';

    try {
        // 清除錯誤訊息
        document.getElementById('error-container').innerHTML = '';

        // 顯示載入狀態
        document.getElementById('studentTableBody').innerHTML =
            '<tr><td colspan="6" class="loading"><span class="loading-spinner"></span> 載入中...</td></tr>';

        const response = await fetch('/teacher_analytics', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // 更新統計卡片
        updateStatsCards(data.stats || {});

        // 繪製圖表
        drawCharts(data);

        // 更新學生表格
        updateStudentTable(data.students || []);

    } catch (error) {
        console.error('載入數據失敗:', error);
        showError('載入數據時發生錯誤：' + error.message);
    } finally {
        isLoading = false;
        refreshBtn.innerHTML = '重新載入';
    }
}

function showError(message) {
    const errorContainer = document.getElementById('error-container');
    errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
}

function updateStatsCards(stats) {
    document.getElementById('activeStudents').textContent = stats.activeStudents || 0;
    document.getElementById('totalConversations').textContent = stats.totalConversations || 0;
    document.getElementById('avgLevel').textContent = stats.avgLevel || '-';

    const popularUnit = stats.popularUnit || '無';
    document.getElementById('popularUnit').textContent = popularUnit.length > 10 ?
        popularUnit.substring(0, 10) + '...' : popularUnit;
}

function drawCharts(data) {
    // 銷毀舊的圖表實例
    Object.values(charts).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    charts = {};

    // 等待DOM更新後再繪製圖表
    setTimeout(() => {
        // 鷹架類型分佈圓餅圖
        drawScaffoldingChart(data.scaffolding_stats || {});

        // 學習單元長條圖
        drawUnitsChart(data.unit_stats || {});

        // 理解程度分佈圓餅圖
        drawLevelsChart(data.level_stats || {});

        // 每日活動折線圖
        drawDailyChart(data.daily_activity || {});
    }, 100);
}

function drawScaffoldingChart(scaffoldingData) {
    const ctx = document.getElementById('scaffoldingChart');
    if (!ctx) return;

    const ctxContext = ctx.getContext('2d');
    if (!ctxContext) return;

    const labels = Object.keys(scaffoldingData);
    const values = Object.values(scaffoldingData);

    if (labels.length === 0) {
        ctxContext.clearRect(0, 0, ctx.width, ctx.height);
        ctxContext.font = "16px Arial";
        ctxContext.fillStyle = "#999";
        ctxContext.textAlign = "center";
        ctxContext.fillText("暫無數據", ctx.width / 2, ctx.height / 2);
        return;
    }

    charts.scaffolding = new Chart(ctxContext, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0'],
                borderWidth: 2,
                borderColor: '#fff'
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
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

function drawUnitsChart(unitData) {
    const ctx = document.getElementById('unitsChart');
    if (!ctx) return;

    const ctxContext = ctx.getContext('2d');
    if (!ctxContext) return;

    // 取前8個最熱門的單元
    const sortedUnits = Object.entries(unitData)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8);

    const labels = sortedUnits.map(([label]) =>
        label.length > 8 ? label.substring(0, 8) + '...' : label
    );
    const values = sortedUnits.map(([, value]) => value);

    if (labels.length === 0) {
        ctxContext.clearRect(0, 0, ctx.width, ctx.height);
        ctxContext.font = "16px Arial";
        ctxContext.fillStyle = "#999";
        ctxContext.textAlign = "center";
        ctxContext.fillText("暫無數據", ctx.width / 2, ctx.height / 2);
        return;
    }

    charts.units = new Chart(ctxContext, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '討論次數',
                data: values,
                backgroundColor: 'rgba(102, 126, 234, 0.8)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
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
                    display: false
                }
            }
        }
    });
}

function drawLevelsChart(levelData) {
    const ctx = document.getElementById('levelsChart');
    if (!ctx) return;

    const ctxContext = ctx.getContext('2d');
    if (!ctxContext) return;

    const labels = Object.keys(levelData);
    const values = Object.values(levelData);

    if (labels.length === 0) {
        ctxContext.clearRect(0, 0, ctx.width, ctx.height);
        ctxContext.font = "16px Arial";
        ctxContext.fillStyle = "#999";
        ctxContext.textAlign = "center";
        ctxContext.fillText("暫無數據", ctx.width / 2, ctx.height / 2);
        return;
    }

    charts.levels = new Chart(ctxContext, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#FF6384', '#FFCE56', '#4BC0C0', '#36A2EB'],
                borderWidth: 2,
                borderColor: '#fff'
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
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

function drawDailyChart(dailyData) {
    const ctx = document.getElementById('dailyChart');
    if (!ctx) return;

    const ctxContext = ctx.getContext('2d');
    if (!ctxContext) return;

    const labels = Object.keys(dailyData);
    const values = Object.values(dailyData);

    if (labels.length === 0) {
        ctxContext.clearRect(0, 0, ctx.width, ctx.height);
        ctxContext.font = "16px Arial";
        ctxContext.fillStyle = "#999";
        ctxContext.textAlign = "center";
        ctxContext.fillText("暫無數據", ctx.width / 2, ctx.height / 2);
        return;
    }

    charts.daily = new Chart(ctxContext, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '對話次數',
                data: values,
                borderColor: 'rgba(118, 75, 162, 1)',
                backgroundColor: 'rgba(118, 75, 162, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: 'rgba(118, 75, 162, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
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

function updateStudentTable(students) {
    const tbody = document.getElementById('studentTableBody');

    if (!students || students.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="no-data">暫無學生數據</td></tr>';
        return;
    }

    tbody.innerHTML = students.map(student => `
                <tr>
                    <td><strong>${escapeHtml(student.username)}</strong></td>
                    <td>${student.total_conversations || 0}</td>
                    <td><span class="scaffolding-badge ${escapeHtml(student.main_scaffolding)}">${escapeHtml(student.main_scaffolding)}</span></td>
                    <td><span class="level-badge ${escapeHtml(student.current_level)}">${escapeHtml(student.current_level)}</span></td>
                    <td>${escapeHtml(student.favorite_unit)}</td>
                    <td>${formatDate(student.last_activity)}</td>
                </tr>
            `).join('');
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
    loadAnalytics();
});

// 每5分鐘自動重新載入數據
setInterval(loadAnalytics, 300000);

// 視窗大小改變時重新調整圖表
window.addEventListener('resize', () => {
    Object.values(charts).forEach(chart => {
        if (chart && typeof chart.resize === 'function') {
            chart.resize();
        }
    });
});