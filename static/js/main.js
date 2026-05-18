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
                    <div class="stat-card"><h3>🏭 Средний ВВП</h3><div class="value">${stats.avg_gdp ? stats.avg_gdp.toFixed(2) : '-'} трлн</div></div>
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
    const model = document.getElementById('forecastModel').value;
    
    showForecastLoading();
    
    try {
        const response = await fetch(`/api/forecast/${countryId}/${indicator}?steps=${steps}&model=${model}`);
        const result = await response.json();
        
        if (result.success) {
            displayForecast(result);
        } else {
            alert('Ошибка: ' + result.error);
            document.getElementById('forecastResult').style.display = 'none';
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
        document.getElementById('forecastResult').style.display = 'none';
    } finally {
        hideForecastLoading();
    }
}

function displayForecast(forecast) {
    document.getElementById('forecastResult').style.display = 'block';
    
    // Отображение метрик и информации о модели
    let metricsHtml = `
        <div class="metric-card">
            <h4>📊 Модель</h4>
            <div class="value">${forecast.model_type}</div>
        </div>
        <div class="metric-card">
            <h4>📈 RMSE</h4>
            <div class="value">${forecast.metrics?.rmse ? forecast.metrics.rmse.toFixed(2) : 'N/A'}</div>
        </div>
        <div class="metric-card">
            <h4>📉 MAE</h4>
            <div class="value">${forecast.metrics?.mae ? forecast.metrics.mae.toFixed(2) : 'N/A'}</div>
        </div>
    `;
    
    // Добавляем дополнительную информацию о модели
    if (forecast.intercept !== undefined) {
        metricsHtml += `<div class="metric-card"><h4>📐 Intercept</h4><div class="value">${forecast.intercept.toFixed(2)}</div></div>`;
    }
    if (forecast.slope !== undefined) {
        metricsHtml += `<div class="metric-card"><h4>📈 Slope</h4><div class="value">${forecast.slope.toFixed(4)}</div></div>`;
    }
    if (forecast.degree !== undefined) {
        metricsHtml += `<div class="metric-card"><h4>🔢 Степень</h4><div class="value">${forecast.degree}</div></div>`;
    }
    if (forecast.alpha !== undefined) {
        metricsHtml += `<div class="metric-card"><h4>α (alpha)</h4><div class="value">${forecast.alpha}</div></div>`;
    }
    
    document.getElementById('forecastMetrics').innerHTML = metricsHtml;
    
    // Построение графика
    if (forecastChart) forecastChart.destroy();
    
    const allYears = [...forecast.historical_years, ...forecast.forecast_years];
    const historical = [...forecast.historical_values, ...Array(forecast.forecast_years.length).fill(null)];
    const forecastValues = [...Array(forecast.historical_years.length).fill(null), ...forecast.forecast];
    
    forecastChart = new Chart(document.getElementById('forecastChart'), {
        type: 'line',
        data: {
            labels: allYears,
            datasets: [
                {
                    label: 'Исторические данные',
                    data: historical,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    pointRadius: 4,
                    tension: 0
                },
                {
                    label: 'Прогноз',
                    data: forecastValues,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 4,
                    tension: 0
                }
            ]
        },
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
    
    // Таблица прогнозов
    let tableHtml = `<table><thead><tr><th>Год</th><th>Прогноз</th></tr></thead><tbody>`;
    for (let i = 0; i < forecast.forecast.length; i++) {
        tableHtml += `<tr><td><strong>${forecast.forecast_years[i]}</strong></td><td>${forecast.forecast[i].toFixed(2)} млрд USD</td></tr>`;
    }
    tableHtml += '</tbody></tr>';
    document.getElementById('forecastTable').innerHTML = tableHtml;
}

function showForecastLoading() {
    const btn = document.querySelector('#forecastSection .btn-primary');
    if (btn) {
        btn.originalText = btn.textContent;
        btn.textContent = '⏳ Загрузка...';
        btn.disabled = true;
    }
}

function hideForecastLoading() {
    const btn = document.querySelector('#forecastSection .btn-primary');
    if (btn) {
        btn.textContent = btn.originalText || '🔮 Построить прогноз';
        btn.disabled = false;
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
        <div class="metric-card"><h4>📉 RMSE</h4><div class="value">${forecast.metrics.rmse.toFixed(2)} трлн</div></div>
        <div class="metric-card"><h4>🎯 MAE</h4><div class="value">${forecast.metrics.mae.toFixed(2)} трлн</div></div>
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
                                   new Intl.NumberFormat('ru-RU').format(context.parsed.y) + 'трлн USD';
                        }
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, title: { display: true, text: 'трлн USD' } },
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

// Загрузка списка показателей для удаления
async function loadIndicatorsForDelete() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) {
        document.getElementById('deleteIndicatorSelect').innerHTML = '<option value="">Сначала выберите страну</option>';
        return;
    }
    
    try {
        const response = await fetch(`/api/indicators/filter?country_id=${countryId}`);
        const data = await response.json();
        
        const select = document.getElementById('deleteIndicatorSelect');
        select.innerHTML = '<option value="">Выберите показатель</option>';
        
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = `${item.year} - Экспорт: ${item.export_value || 0}, Импорт: ${item.import_value || 0}, ВВП: ${item.gdp_value || 0}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Загрузка списка стран для удаления показателей
async function loadCountriesForDelete() {
    try {
        const response = await fetch('/api/countries');
        const countries = await response.json();
        
        const select1 = document.getElementById('deleteCountryIndicatorsSelect');
        const select2 = document.getElementById('deleteCountrySelect');
        
        select1.innerHTML = '<option value="">Выберите страну</option>';
        select2.innerHTML = '<option value="">Выберите страну</option>';
        
        countries.forEach(c => {
            const option1 = document.createElement('option');
            option1.value = c.id;
            option1.textContent = c.name;
            select1.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = c.id;
            option2.textContent = c.name;
            select2.appendChild(option2);
        });
    } catch (error) {
        console.error('Error:', error);
    }
}

// Удаление выбранного показателя
async function deleteSelectedIndicator() {
    const indicatorId = document.getElementById('deleteIndicatorSelect').value;
    if (!indicatorId) {
        alert('Выберите показатель для удаления');
        return;
    }
    
    if (!confirm('Вы уверены, что хотите удалить этот показатель?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/indicators/${indicatorId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok) {
            alert(result.message);
            loadData();
            loadIndicatorsForDelete();
        } else {
            alert('Ошибка: ' + result.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// Удаление всех показателей страны
async function deleteCountryIndicators() {
    const countryId = document.getElementById('deleteCountryIndicatorsSelect').value;
    if (!countryId) {
        alert('Выберите страну');
        return;
    }
    
    const countryName = document.getElementById('deleteCountryIndicatorsSelect').options[
        document.getElementById('deleteCountryIndicatorsSelect').selectedIndex
    ].text;
    
    if (!confirm(`Вы уверены, что хотите удалить ВСЕ показатели страны "${countryName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/indicators/country/${countryId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok) {
            alert(result.message);
            loadData();
            loadIndicatorsForDelete();
        } else {
            alert('Ошибка: ' + result.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// Удаление страны
async function deleteCountry() {
    const countryId = document.getElementById('deleteCountrySelect').value;
    if (!countryId) {
        alert('Выберите страну');
        return;
    }
    
    const countryName = document.getElementById('deleteCountrySelect').options[
        document.getElementById('deleteCountrySelect').selectedIndex
    ].text;
    
    if (!confirm(`ВНИМАНИЕ! Вы уверены, что хотите удалить страну "${countryName}" вместе со ВСЕМИ показателями? Это действие необратимо!`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/countries/${countryId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok) {
            alert(result.message);
            loadCountries();
            loadData();
            loadCountriesForDelete();
            document.getElementById('deleteIndicatorSelect').innerHTML = '<option value="">Выберите показатель</option>';
        } else {
            alert('Ошибка: ' + result.error);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// Обновите обработчик события выбора страны
document.getElementById('countrySelect').addEventListener('change', function() {
    const show = this.value ? 'block' : 'none';
    document.getElementById('forecastSection').style.display = show;
    document.getElementById('gdpForecastSection').style.display = show;
    
    // Загружаем показатели для удаления
    if (this.value) {
        loadIndicatorsForDelete();
    } else {
        document.getElementById('deleteIndicatorSelect').innerHTML = '<option value="">Выберите показатель</option>';
    }
});

// Загрузка стран для удаления при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    loadCountries();
    loadData();
    loadCountriesForDelete();
});

let elbowChart = null;
let clusterScatterChart = null;

// Загрузка доступных годов для кластеризации
async function loadClusteringYears() {
    try {
        const response = await fetch('/api/clustering/available-years');
        const result = await response.json();
        
        if (result.years) {
            const select = document.getElementById('clusteringYear');
            result.years.forEach(year => {
                const option = document.createElement('option');
                option.value = year;
                option.textContent = year;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading years:', error);
    }
}

// Запуск кластеризации
async function runClustering() {
    const year = document.getElementById('clusteringYear').value;
    
    showClusteringLoading();
    
    try {
        const url = year ? `/api/clustering/analyze?year=${year}` : '/api/clustering/analyze';
        const response = await fetch(url);
        const result = await response.json();
        
        console.log('Clustering result:', result); // Для отладки
        
        if (result.success) {
            displayClusteringResults(result);
        } else {
            alert('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
            document.getElementById('clusteringResult').style.display = 'none';
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка: ' + error.message);
        document.getElementById('clusteringResult').style.display = 'none';
    } finally {
        hideClusteringLoading();
    }
}

// Отображение результатов кластеризации
function displayClusteringResults(results) {
    document.getElementById('clusteringResult').style.display = 'block';
    
    // 1. График метода локтя
    if (results.elbow_analysis && results.elbow_analysis.k_values && results.elbow_analysis.k_values.length > 0) {
        if (elbowChart) elbowChart.destroy();
        
        const elbowCtx = document.getElementById('elbowChart').getContext('2d');
        elbowChart = new Chart(elbowCtx, {
            type: 'line',
            data: {
                labels: results.elbow_analysis.k_values,
                datasets: [{
                    label: 'Инерция (WCSS)',
                    data: results.elbow_analysis.inertias,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Инерция: ' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: 'Количество кластеров (k)' } },
                    y: { title: { display: true, text: 'Инерция (WCSS)' } }
                }
            }
        });
    }
    
    // Получаем количество стран по каждому типу из distribution
    const typeCounts = {
        'Передовые': 0,
        'Средние': 0,
        'Отстающие': 0
    };
    
    if (results.countries) {
        results.countries.forEach(country => {
            if (typeCounts.hasOwnProperty(country.cluster_type)) {
                typeCounts[country.cluster_type]++;
            }
        });
    }
    
    // 2. Статистика кластеров (используем актуальные данные из стран)
    let statsHtml = '';
    const colorMap = {
        'Передовые': '#2ecc71',
        'Средние': '#f39c12',
        'Отстающие': '#e74c3c'
    };
    
    const types = ['Передовые', 'Средние', 'Отстающие'];
    
    types.forEach(type => {
        const color = colorMap[type] || '#9b59b6';
        const clusterCountries = results.countries ? results.countries.filter(c => c.cluster_type === type) : [];
        const actualSize = clusterCountries.length;
        
        // Рассчитываем средние значения для кластера
        let avgGdp = 0, avgExport = 0, avgImport = 0;
        if (actualSize > 0) {
            avgGdp = clusterCountries.reduce((sum, c) => sum + c.gdp_value, 0) / actualSize;
            avgExport = clusterCountries.reduce((sum, c) => sum + c.export_value, 0) / actualSize;
            avgImport = clusterCountries.reduce((sum, c) => sum + c.import_value, 0) / actualSize;
        }
        
        statsHtml += `
            <div class="cluster-card" style="border-top-color: ${color};">
                <h4>${type}</h4>
                <div class="cluster-size">Число стран: ${actualSize}</div>
                <div class="cluster-avg">
                    📊 Средний ВВП: ${avgGdp.toFixed(2)} трлн USD<br>
                    📤 Средний экспорт: ${avgExport.toFixed(2)} трлн USD<br>
                    📥 Средний импорт: ${avgImport.toFixed(2)} трлн USD
                </div>
            </div>
        `;
    });
    
    if (statsHtml === '') {
        statsHtml = '<div class="info-message">Нет данных о кластерах</div>';
    }
    document.getElementById('clusterStats').innerHTML = statsHtml;
    
    // 3. Распределение стран по кластерам
    let countriesHtml = '';
    
    types.forEach(type => {
        const clusterCountries = results.countries ? results.countries.filter(c => c.cluster_type === type) : [];
        if (clusterCountries.length > 0) {
            const typeClass = type === 'Передовые' ? 'leading' : (type === 'Средние' ? 'middle' : 'lagging');
            
            countriesHtml += `
                <div class="cluster-group ${typeClass}">
                    <h5>${type} (${clusterCountries.length} стран)</h5>
                    ${clusterCountries.map(c => `<span class="country-tag">${c.country_name}</span>`).join('')}
                </div>
            `;
        }
    });
    
    if (countriesHtml === '') {
        countriesHtml = '<div class="info-message">Нет данных о странах</div>';
    }
    document.getElementById('clusterCountries').innerHTML = countriesHtml;
    
    // 4. График кластеров
    if (clusterScatterChart) clusterScatterChart.destroy();

    const datasets = [];
    const colors = {
        'Передовые': 'rgba(46, 204, 113, 0.7)',
        'Средние': 'rgba(243, 156, 18, 0.7)',
        'Отстающие': 'rgba(231, 76, 60, 0.7)'
    };

    types.forEach(type => {
        const clusterCountries = results.countries ? results.countries.filter(c => c.cluster_type === type) : [];
        if (clusterCountries.length > 0) {
            datasets.push({
                label: type,
                data: clusterCountries.map(c => ({
                    x: c.export_value || 0,
                    y: c.gdp_value || 0,
                    countryName: c.country_name  // Добавляем название страны
                })),
                backgroundColor: colors[type],
                borderColor: colors[type].replace('0.7', '1'),
                borderWidth: 1,
                pointRadius: 8,
                pointHoverRadius: 10
            });
        }
    });

    if (datasets.length > 0) {
        const scatterCtx = document.getElementById('clusterChart').getContext('2d');
        clusterScatterChart = new Chart(scatterCtx, {
            type: 'scatter',
            data: { datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.raw;
                                // Добавляем название страны в подсказку
                                return `${value.countryName}: ${label}\nЭкспорт: ${value.x.toFixed(2)} трлн USD\nВВП: ${value.y.toFixed(2)} трлн USD`;
                            }
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: 'Экспорт (трлн USD)' }, beginAtZero: true },
                    y: { title: { display: true, text: 'ВВП (трлн USD)' }, beginAtZero: true }
                }
            }
        });
    }
}

function showClusteringLoading() {
    const btn = document.querySelector('#clusteringSection .btn-primary');
    if (btn) {
        btn.originalText = btn.textContent;
        btn.textContent = '⏳ Анализ...';
        btn.disabled = true;
    }
}

function hideClusteringLoading() {
    const btn = document.querySelector('#clusteringSection .btn-primary');
    if (btn) {
        btn.textContent = btn.originalText || '🔍 Провести кластеризацию';
        btn.disabled = false;
    }
}

// Добавьте вызов в DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    loadCountries();
    loadData();
    loadClusteringYears();
});