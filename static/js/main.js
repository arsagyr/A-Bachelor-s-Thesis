let trendChart = null;
let forecastChart = null;
let gdpForecastChart = null;

// Загрузка списка стран
async function loadCountries() {
    try {
        const response = await fetch('/api/countries');
        const countries = await response.json();
        const select = document.getElementById('countrySelect');
        select.innerHTML = '<option value="">🌍 Все страны</option>';
        countries.forEach(c => {
            const option = document.createElement('option');
            option.value = c.id;
            option.textContent = c.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Загрузка данных для графика
async function loadData() {
    const countryId = document.getElementById('countrySelect').value;
    const indicatorType = document.getElementById('indicatorType').value;
    const startYear = document.getElementById('startYear').value;
    const endYear = document.getElementById('endYear').value;
    
    let url = `/api/indicators/filter?indicator_type=${indicatorType}`;
    if (countryId) url += `&country_id=${countryId}`;
    if (startYear) url += `&start_year=${startYear}`;
    if (endYear) url += `&end_year=${endYear}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        if (!data || data.length === 0) {
            document.getElementById('trendEmptyMessage').style.display = 'block';
            if (trendChart) trendChart.destroy();
            document.getElementById('statsContainer').innerHTML = '';
            return;
        }
        
        document.getElementById('trendEmptyMessage').style.display = 'none';
        
        const years = data.map(d => d.year);
        const exports = data.map(d => d.export_value || 0);
        const imports = data.map(d => d.import_value || 0);
        const gdps = data.map(d => d.gdp_value || 0);
        
        if (trendChart) trendChart.destroy();
        
        const datasets = [];
        const indicatorTypeValue = document.getElementById('indicatorType').value;
        
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'export') {
            datasets.push({ label: 'Экспорт', data: exports, borderColor: 'rgb(75, 192, 192)', tension: 0 });
        }
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'import') {
            datasets.push({ label: 'Импорт', data: imports, borderColor: 'rgb(255, 99, 132)', tension: 0 });
        }
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'gdp') {
            datasets.push({ label: 'ВВП', data: gdps, borderColor: 'rgb(54, 162, 235)', tension: 0 });
        }
        
        trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: { labels: years, datasets: datasets },
            options: { responsive: true, maintainAspectRatio: true }
        });
        
        if (countryId) {
            const statsRes = await fetch(`/api/stats/${countryId}`);
            const stats = await statsRes.json();
            if (stats && stats.years_count) {
                document.getElementById('statsContainer').innerHTML = `
                    <div class="stat-card"><h3>📊 Лет данных</h3><div class="value">${stats.years_count}</div></div>
                    <div class="stat-card"><h3>📅 Период</h3><div class="value">${stats.min_year} - ${stats.max_year}</div></div>
                    <div class="stat-card"><h3>💰 Средний экспорт</h3><div class="value">${stats.avg_export ? stats.avg_export.toFixed(2) : '-'} млрд</div></div>
                    <div class="stat-card"><h3>📥 Средний импорт</h3><div class="value">${stats.avg_import ? stats.avg_import.toFixed(2) : '-'} млрд</div></div>
                    <div class="stat-card"><h3>🏭 Средний ВВП</h3><div class="value">${stats.avg_gdp ? stats.avg_gdp.toFixed(2) : '-'} млрд</div></div>
                `;
            }
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Прогнозирование временных рядов
async function loadForecast() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) {
        alert('Сначала выберите страну');
        return;
    }
    
    const indicator = document.getElementById('forecastIndicator').value;
    const steps = document.getElementById('forecastSteps').value;
    
    try {
        const response = await fetch(`/api/forecast/${countryId}/${indicator}?steps=${steps}&model=linear`);
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('forecastResult').style.display = 'block';
            
            const allYears = [...result.historical_years, ...result.forecast_years];
            const historical = [...result.historical_values, ...Array(result.forecast_years.length).fill(null)];
            const forecast = [...Array(result.historical_years.length).fill(null), ...result.forecast];
            
            if (forecastChart) forecastChart.destroy();
            forecastChart = new Chart(document.getElementById('forecastChart'), {
                type: 'line',
                data: {
                    labels: allYears,
                    datasets: [
                        { label: 'Исторические данные', data: historical, borderColor: 'rgb(75, 192, 192)' },
                        { label: 'Прогноз', data: forecast, borderColor: 'rgb(255, 99, 132)', borderDash: [5, 5] }
                    ]
                },
                options: { responsive: true, maintainAspectRatio: true }
            });
            
            let metricsHtml = `
                <div class="metric-card"><h4>📊 Модель</h4><div class="value">${result.best_model}</div></div>
                <div class="metric-card"><h4>📈 RMSE</h4><div class="value">${result.metrics.rmse?.toFixed(2) || 'N/A'}</div></div>
                <div class="metric-card"><h4>📉 MAE</h4><div class="value">${result.metrics.mae?.toFixed(2) || 'N/A'}</div></div>
            `;
            document.getElementById('forecastMetrics').innerHTML = metricsHtml;
            
            let tableHtml = `<table><thead><tr><th>Год</th><th>Прогноз</th></tr></thead><tbody>`;
            for (let i = 0; i < result.forecast.length; i++) {
                tableHtml += `<tr><td><strong>${result.forecast_years[i]}</strong></td><td>${result.forecast[i].toFixed(2)} млрд</td></tr>`;
            }
            tableHtml += '</tbody></table>';
            document.getElementById('forecastTable').innerHTML = tableHtml;
        } else {
            alert('Ошибка: ' + result.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// Прогнозирование ВВП на основе экспорта и импорта
async function loadGDPForecast() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) {
        alert('Сначала выберите страну');
        return;
    }
    
    const steps = document.getElementById('gdpForecastSteps').value;
    const model = document.getElementById('gdpRegressionModel').value;
    
    showLoading();
    
    try {
        const response = await fetch(`/api/forecast/gdp-from-trade/${countryId}?steps=${steps}&model=${model}`);
        const result = await response.json();
        
        if (result.success) {
            displayGDPForecast(result);
        } else {
            alert('Ошибка: ' + result.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    } finally {
        hideLoading();
    }
}

function displayGDPForecast(forecast) {
    document.getElementById('gdpForecastResult').style.display = 'block';
    
    const metricsHtml = `
        <div class="metric-card"><h4>📊 Модель</h4><div class="value">${forecast.model_type}</div></div>
        <div class="metric-card"><h4>📈 R² Score</h4><div class="value">${forecast.metrics.r2.toFixed(4)}</div></div>
        <div class="metric-card"><h4>📉 RMSE</h4><div class="value">${forecast.metrics.rmse.toFixed(2)} млрд</div></div>
        <div class="metric-card"><h4>🎯 MAE</h4><div class="value">${forecast.metrics.mae.toFixed(2)} млрд</div></div>
    `;
    document.getElementById('gdpForecastMetrics').innerHTML = metricsHtml;
    
    if (gdpForecastChart) gdpForecastChart.destroy();
    
    const allYears = [...forecast.historical.years, ...forecast.forecast.years];
    const historicalGdp = [...forecast.historical.gdp, ...Array(forecast.forecast.years.length).fill(null)];
    const forecastGdp = [...Array(forecast.historical.years.length).fill(null), ...forecast.forecast.gdp];
    
    const datasets = [
        {
            label: 'Исторический ВВП',
            data: historicalGdp,
            borderColor: 'rgb(75, 192, 192)',
            borderWidth: 2,
            pointRadius: 4
        },
        {
            label: 'Прогноз ВВП',
            data: forecastGdp,
            borderColor: 'rgb(255, 99, 132)',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 4
        }
    ];
    
    if (forecast.confidence_intervals) {
        const lowerBounds = [...Array(forecast.historical.years.length).fill(null), ...forecast.confidence_intervals.lower];
        const upperBounds = [...Array(forecast.historical.years.length).fill(null), ...forecast.confidence_intervals.upper];
        
        datasets.push({
            label: 'Нижняя граница (95%)',
            data: lowerBounds,
            borderColor: 'rgba(255, 99, 132, 0.3)',
            borderWidth: 1,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0
        });
        
        datasets.push({
            label: 'Верхняя граница (95%)',
            data: upperBounds,
            borderColor: 'rgba(255, 99, 132, 0.3)',
            borderWidth: 1,
            borderDash: [5, 5],
            fill: '-1',
            pointRadius: 0
        });
    }
    
    gdpForecastChart = new Chart(document.getElementById('gdpForecastChart'), {
        type: 'line',
        data: { labels: allYears, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + 
                                   new Intl.NumberFormat('ru-RU').format(context.parsed.y) + ' млрд USD';
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'млрд USD' } },
                x: { title: { display: true, text: 'Год' } }
            }
        }
    });
    
    let tableHtml = `<table><thead><tr><th>Год</th><th>Прогноз экспорта</th><th>Прогноз импорта</th><th>Прогноз ВВП</th><th>Нижняя граница</th><th>Верхняя граница</th></tr></thead><tbody>`;
    
    for (let i = 0; i < forecast.forecast.years.length; i++) {
        tableHtml += `
            <tr>
                <td><strong>${forecast.forecast.years[i]}</strong></td>
                <td>${forecast.forecast.export[i].toFixed(2)} млрд</td>
                <td>${forecast.forecast.import[i].toFixed(2)} млрд</td>
                <td>${forecast.forecast.gdp[i].toFixed(2)} млрд</td>
                <td class="confidence-interval">${forecast.confidence_intervals.lower[i].toFixed(2)} млрд</td>
                <td class="confidence-interval">${forecast.confidence_intervals.upper[i].toFixed(2)} млрд</td>
            </tr>
        `;
    }
    
    tableHtml += '</tbody></table>';
    document.getElementById('gdpForecastTable').innerHTML = tableHtml;
}

// Предпросмотр CSV
async function previewCSV() {
    const file = document.getElementById('csvFile').files[0];
    if (!file) {
        alert('Выберите файл');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/csv/preview', { method: 'POST', body: formData });
        const result = await response.json();
        const previewDiv = document.getElementById('previewContainer');
        
        if (result.success) {
            previewDiv.style.display = 'block';
            previewDiv.innerHTML = `
                <div class="preview-container">
                    <h4>📋 Предпросмотр</h4>
                    <pre>${JSON.stringify(result.preview, null, 2)}</pre>
                    <p><strong>Определено соответствие:</strong></p>
                    <ul>${Object.entries(result.detected_mapping).map(([k,v]) => `<li>${k}: ${v || 'не найдено'}</li>`).join('')}</ul>
                    <button onclick="importCSV()" class="btn-primary">🚀 Импортировать</button>
                    <button onclick="document.getElementById('previewContainer').style.display='none'" class="btn-secondary">❌ Отмена</button>
                </div>
            `;
        } else {
            alert('Ошибка: ' + result.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// Импорт CSV
async function importCSV() {
    const file = document.getElementById('csvFile').files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/csv/import', { method: 'POST', body: formData });
        const result = await response.json();
        
        const resultDiv = document.getElementById('importResult');
        if (result.success) {
            resultDiv.innerHTML = `
                <div class="success-message">
                    <strong>✅ Импорт завершен!</strong><br>
                    📊 Всего строк: ${result.total_rows}<br>
                    💾 Импортировано: ${result.imported_rows}<br>
                    ${result.errors && result.errors.length ? `<br>⚠️ Ошибок: ${result.errors.length}` : ''}
                </div>
            `;
            setTimeout(() => {
                loadCountries();
                loadData();
                document.getElementById('previewContainer').style.display = 'none';
                document.getElementById('csvFile').value = '';
                setTimeout(() => { resultDiv.innerHTML = ''; }, 3000);
            }, 2000);
        } else {
            resultDiv.innerHTML = `<div class="error-message"><strong>❌ Ошибка:</strong><br>${result.errors.join('<br>')}</div>`;
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

function downloadTemplate() {
    window.location.href = '/api/csv/template';
}

function showLoading() {
    const btn = document.querySelector('#gdpForecastSection .btn-primary');
    if (btn) {
        btn.originalText = btn.textContent;
        btn.textContent = '⏳ Загрузка...';
        btn.disabled = true;
    }
}

function hideLoading() {
    const btn = document.querySelector('#gdpForecastSection .btn-primary');
    if (btn) {
        btn.textContent = btn.originalText || '📊 Прогноз ВВП';
        btn.disabled = false;
    }
}

// Обработчики событий
document.getElementById('countrySelect').addEventListener('change', function() {
    const show = this.value ? 'block' : 'none';
    document.getElementById('forecastSection').style.display = show;
    document.getElementById('gdpForecastSection').style.display = show;
});

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    loadCountries();
    loadData();
});