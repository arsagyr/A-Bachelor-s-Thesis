let trendChart = null;
let forecastChart = null;
let elbowChart = null;
let clusterScatterChart = null;

// ==================== ЗАГРУЗКА ДАННЫХ ====================

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
        console.log('Страны загружены:', countries.length);
        
        loadDeleteCountrySelect();
        loadDeleteIndicatorsSelect();
    } catch (error) {
        console.error('Ошибка загрузки стран:', error);
    }
}

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
            datasets.push({ 
                label: 'Экспорт (млрд USD)', 
                data: exports, 
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'transparent',
                borderWidth: 2,
                fill: false,
                tension: 0,
                pointRadius: 4
            });
        }
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'import') {
            datasets.push({ 
                label: 'Импорт (млрд USD)', 
                data: imports, 
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'transparent',
                borderWidth: 2,
                fill: false,
                tension: 0,
                pointRadius: 4
            });
        }
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'gdp') {
            datasets.push({ 
                label: 'ВВП (млрд USD)', 
                data: gdps, 
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'transparent',
                borderWidth: 2,
                fill: false,
                tension: 0,
                pointRadius: 4
            });
        }
        
        trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: { labels: years, datasets: datasets },
            options: { 
                responsive: true, 
                maintainAspectRatio: true,
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('ru-RU').format(context.parsed.y);
                                    if (context.dataset.label.includes('ВВП')) {
                                        label += ' млрд  USD';
                                    } else {
                                        label += ' млрд USD';
                                    }
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        title: { display: true, text: indicatorTypeValue === 'gdp' ? 'млрд USD' : ' млрд USD' },
                        ticks: { callback: (value) => new Intl.NumberFormat('ru-RU').format(value) }
                    },
                    x: { title: { display: true, text: 'Год' } }
                }
            }
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
        } else {
            const uniqueCountries = [...new Set(data.map(d => d.country_name))];
            document.getElementById('statsContainer').innerHTML = `
                <div class="stat-card"><h3>🌍 Стран</h3><div class="value">${uniqueCountries.length}</div></div>
                <div class="stat-card"><h3>📊 Всего записей</h3><div class="value">${data.length}</div></div>
                <div class="stat-card"><h3>📅 Период</h3><div class="value">${Math.min(...years)} - ${Math.max(...years)}</div></div>
            `;
        }
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    }
}

// ==================== ПРОГНОЗИРОВАНИЕ ====================

document.getElementById('forecastModel').addEventListener('change', function() {
    const degreeControl = document.getElementById('degreeControl');
    if (degreeControl) degreeControl.style.display = this.value === 'polynomial' ? 'block' : 'none';
});

async function loadForecast() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) { alert('Сначала выберите страну'); return; }
    
    const indicator = document.getElementById('forecastIndicator').value;
    const steps = document.getElementById('forecastSteps').value;
    const model = document.getElementById('forecastModel').value;
    const degree = document.getElementById('forecastDegree')?.value || 2;
    
    showForecastLoading();
    
    try {
        let url = `/api/forecast/${countryId}/${indicator}?steps=${steps}&model=${model}`;
        if (model === 'polynomial') url += `&degree=${degree}`;
        
        const response = await fetch(url);
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
// Отображение прогноза с графиком на все года (история + прогноз)
function displayForecast(forecast) {
    document.getElementById('forecastResult').style.display = 'block';
    
    const metrics = forecast.metrics || {};
    const unit = forecast.unit || ' млрд USD';
    
    let metricsHtml = `
        <div class="metric-card"><h4>📊 Модель</h4><div class="value">${forecast.model_type || 'N/A'}</div></div>
        <div class="metric-card"><h4>📈 R²</h4><div class="value">${metrics.r2 ? metrics.r2.toFixed(4) : 'N/A'}</div></div>
        <div class="metric-card"><h4>📉 RMSE</h4><div class="value">${metrics.rmse ? metrics.rmse.toFixed(2) : 'N/A'} ${unit}</div></div>
        <div class="metric-card"><h4>📊 MAE</h4><div class="value">${metrics.mae ? metrics.mae.toFixed(2) : 'N/A'} ${unit}</div></div>
    `;
    
    if (metrics.mape) {
        metricsHtml += `<div class="metric-card"><h4>📊 MAPE</h4><div class="value">${metrics.mape.toFixed(1)}%</div></div>`;
    }
    
    document.getElementById('forecastMetrics').innerHTML = metricsHtml;
    
    const formulaHtml = `<div class="formula">${forecast.formula || 'Формула не доступна'}</div>`;
    document.getElementById('forecastFormula').innerHTML = formulaHtml;
    
    if (forecastChart) forecastChart.destroy();
    
    if (!forecast.historical_years || !forecast.forecast_years) return;
    
    const allYears = [...forecast.historical_years, ...forecast.forecast_years];
    const historicalData = [...forecast.historical_values, ...Array(forecast.forecast_years.length).fill(null)];
    const forecastData = [...Array(forecast.historical_years.length).fill(null), ...forecast.forecast];
    
    forecastChart = new Chart(document.getElementById('forecastChart'), {
        type: 'line',
        data: {
            labels: allYears,
            datasets: [
                {
                    label: 'Исторические данные',
                    data: historicalData,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.1)',
                    borderWidth: 2,
                    pointRadius: 4,
                    tension: 0,
                    fill: false
                },
                {
                    label: `Прогноз (${unit})`,
                    data: forecastData,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 4,
                    tension: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat('ru-RU').format(context.parsed.y) + ' ' + unit;
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: unit, font: { weight: 'bold', size: 12 } },
                    ticks: { callback: (value) => new Intl.NumberFormat('ru-RU').format(value) }
                },
                x: { title: { display: true, text: 'Год', font: { weight: 'bold', size: 12 } } }
            }
        }
    });
    
    let tableHtml = `<table><thead><tr><th>Год</th><th>Прогноз (${unit})</th></tr></thead><tbody>`;
    for (let i = 0; i < forecast.forecast.length; i++) {
        tableHtml += `<tr>
            <td><strong>${forecast.forecast_years[i]}</strong></td>
            <td>${forecast.forecast[i].toFixed(2)}</div>
        </tr>`;
    }
    tableHtml += '</tbody></table>';
    document.getElementById('forecastTable').innerHTML = tableHtml;
}

// ==================== CSV ИМПОРТ ====================

async function previewCSV() {
    const file = document.getElementById('csvFile').files[0];
    if (!file) { alert('Выберите файл'); return; }
    
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
                    <ul>${Object.entries(result.detected_mapping).map(([k,v]) => `<li>${k}: ${v || '❌ не найдено'}</li>`).join('')}</ul>
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

async function importCSV() {
    const file = document.getElementById('csvFile').files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/csv/import', { method: 'POST', body: formData });
        const result = await response.json();
        const resultDiv = document.getElementById('importResult');
        if (result.success) {
            resultDiv.innerHTML = `<div class="success-message"><strong>✅ Импорт завершен!</strong><br>📊 Всего строк: ${result.total_rows}<br>💾 Импортировано: ${result.imported_rows}<br>${result.errors?.length ? `<br>⚠️ Ошибок: ${result.errors.length}` : ''}</div>`;
            setTimeout(() => { loadCountries(); loadData(); document.getElementById('previewContainer').style.display = 'none'; document.getElementById('csvFile').value = ''; setTimeout(() => { resultDiv.innerHTML = ''; }, 3000); }, 2000);
        } else {
            resultDiv.innerHTML = `<div class="error-message"><strong>❌ Ошибка:</strong><br>${result.errors.join('<br>')}</div>`;
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

function downloadTemplate() { window.location.href = '/api/csv/template'; }

// ==================== УДАЛЕНИЕ ДАННЫХ ====================

async function loadDeleteCountrySelect() {
    try {
        const response = await fetch('/api/countries');
        const countries = await response.json();
        const select = document.getElementById('deleteCountrySelect');
        if (select) {
            select.innerHTML = '<option value="">Выберите страну</option>';
            countries.forEach(c => { const option = document.createElement('option'); option.value = c.id; option.textContent = c.name; select.appendChild(option); });
        }
        const select2 = document.getElementById('deleteCountryIndicatorsSelect');
        if (select2) {
            select2.innerHTML = '<option value="">Выберите страну</option>';
            countries.forEach(c => { const option = document.createElement('option'); option.value = c.id; option.textContent = c.name; select2.appendChild(option); });
        }
    } catch (error) { console.error('Ошибка:', error); }
}

async function loadDeleteIndicatorsSelect() {
    const countryId = document.getElementById('countrySelect').value;
    const select = document.getElementById('deleteIndicatorSelect');
    if (!select) return;
    if (!countryId) { select.innerHTML = '<option value="">Сначала выберите страну</option>'; return; }
    
    try {
        const response = await fetch(`/api/indicators/filter?country_id=${countryId}`);
        const data = await response.json();
        select.innerHTML = '<option value="">Выберите показатель</option>';
        data.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = `${item.year} - Экспорт: ${item.export_value || 0}, Импорт: ${item.import_value || 0}, ВВП: ${item.gdp_value || 0}`;
            select.appendChild(option);
        });
    } catch (error) { console.error('Ошибка:', error); }
}

async function deleteCountry() {
    const countryId = document.getElementById('deleteCountrySelect').value;
    if (!countryId) { alert('Выберите страну'); return; }
    const countryName = document.getElementById('deleteCountrySelect').options[document.getElementById('deleteCountrySelect').selectedIndex].text;
    if (!confirm(`ВНИМАНИЕ! Удалить страну "${countryName}" вместе со ВСЕМИ показателями?`)) return;
    
    try {
        const response = await fetch(`/api/countries/${countryId}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok && result.success) {
            alert(result.message);
            loadCountries(); loadData(); loadDeleteCountrySelect();
            document.getElementById('deleteIndicatorSelect').innerHTML = '<option value="">Выберите показатель</option>';
        } else { alert('Ошибка: ' + (result.error || 'Неизвестная ошибка')); }
    } catch (error) { alert('Ошибка: ' + error.message); }
}

async function deleteIndicator() {
    const indicatorId = document.getElementById('deleteIndicatorSelect').value;
    if (!indicatorId) { alert('Выберите показатель'); return; }
    if (!confirm('Удалить этот показатель?')) return;
    
    try {
        const response = await fetch(`/api/indicators/${indicatorId}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok && result.success) {
            alert(result.message);
            loadData(); loadDeleteIndicatorsSelect();
        } else { alert('Ошибка: ' + (result.error || 'Неизвестная ошибка')); }
    } catch (error) { alert('Ошибка: ' + error.message); }
}

async function deleteAllIndicators() {
    const countryId = document.getElementById('deleteCountryIndicatorsSelect').value;
    if (!countryId) { alert('Выберите страну'); return; }
    const countryName = document.getElementById('deleteCountryIndicatorsSelect').options[document.getElementById('deleteCountryIndicatorsSelect').selectedIndex].text;
    if (!confirm(`Удалить ВСЕ показатели страны "${countryName}"? Страна останется.`)) return;
    
    try {
        const response = await fetch(`/api/indicators/country/${countryId}`, { method: 'DELETE' });
        const result = await response.json();
        if (response.ok && result.success) {
            alert(result.message);
            loadData(); loadDeleteIndicatorsSelect();
        } else { alert('Ошибка: ' + (result.error || 'Неизвестная ошибка')); }
    } catch (error) { alert('Ошибка: ' + error.message); }
}

// ==================== ОБРАБОТЧИКИ ====================

document.getElementById('countrySelect').addEventListener('change', function() {
    loadData();
    loadDeleteIndicatorsSelect();
    const show = this.value ? 'block' : 'none';
    const forecastSection = document.getElementById('forecastSection');
    if (forecastSection) forecastSection.style.display = show;
});

function showForecastLoading() {
    const btn = document.querySelector('#forecastSection .btn-primary');
    if (btn) { btn.originalText = btn.textContent; btn.textContent = '⏳ Загрузка...'; btn.disabled = true; }
}

function hideForecastLoading() {
    const btn = document.querySelector('#forecastSection .btn-primary');
    if (btn) { btn.textContent = btn.originalText || '🔮 Построить прогноз'; btn.disabled = false; }
}

// ==================== КЛАСТЕРИЗАЦИЯ ====================
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
        
        console.log('Clustering result:', result);
        
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
    
    // Получаем количество стран по каждому типу
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
    
    // 2. Статистика кластеров
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
                    📤 Средний экспорт: ${avgExport.toFixed(2)} млрд USD<br>
                    📥 Средний импорт: ${avgImport.toFixed(2)} млрд USD
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
    
    // 4. График кластеров (ВВП vs Экспорт)
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
                    countryName: c.country_name
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
                                return `${value.countryName}: ${label}\nЭкспорт: ${value.x.toFixed(2)} млрд USD\nВВП: ${value.y.toFixed(2)} трлн USD`;
                            }
                        }
                    }
                },
                scales: {
                    x: { title: { display: true, text: 'Экспорт (млрд USD)' }, beginAtZero: true },
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

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

document.addEventListener('DOMContentLoaded', () => {
    loadCountries();
    loadData();
    loadDeleteCountrySelect();
    loadDeleteIndicatorsSelect();
    loadClusteringYears();  // Добавить эту строку
});