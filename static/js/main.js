// ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================
let trendChart = null;
let forecastChart = null;
let regressionChart = null;

// ==================== ЗАГРУЗКА ДАННЫХ ====================

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
        
        const oldInfo = document.querySelector('.info-message');
        if (oldInfo) oldInfo.remove();
        
        if (countries.length === 0) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'info-message';
            infoDiv.innerHTML = 'ℹ️ Нет добавленных стран. Загрузите данные через CSV или добавьте страны вручную.';
            document.querySelector('.controls').after(infoDiv);
        }
    } catch (error) {
        console.error('Error loading countries:', error);
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
        
        const hasData = data && data.length > 0;
        
        if (!hasData) {
            document.getElementById('trendEmptyMessage').style.display = 'block';
            if (trendChart) {
                trendChart.destroy();
                trendChart = null;
            }
            document.getElementById('statsContainer').innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <h3>📭 Нет данных для отображения</h3>
                    <p>Загрузите данные через CSV файл или добавьте вручную</p>
                    <button onclick="document.getElementById('csvFile').click()" class="btn-primary">📁 Загрузить CSV</button>
                </div>
            `;
            return;
        }
        
        document.getElementById('trendEmptyMessage').style.display = 'none';
        
        let chartData = data;
        if (!countryId) {
            const yearsMap = new Map();
            data.forEach(item => {
                const year = item.year;
                if (!yearsMap.has(year)) {
                    yearsMap.set(year, {
                        year: year,
                        export_value: 0,
                        import_value: 0,
                        gdp_value: 0
                    });
                }
                const yearData = yearsMap.get(year);
                if (item.export_value) yearData.export_value += item.export_value;
                if (item.import_value) yearData.import_value += item.import_value;
                if (item.gdp_value) yearData.gdp_value += item.gdp_value;
            });
            chartData = Array.from(yearsMap.values()).sort((a, b) => a.year - b.year);
        }
        
        const years = chartData.map(d => d.year);
        const exports = chartData.map(d => d.export_value !== null && d.export_value !== undefined ? d.export_value : null);
        const imports = chartData.map(d => d.import_value !== null && d.import_value !== undefined ? d.import_value : null);
        const gdps = chartData.map(d => d.gdp_value !== null && d.gdp_value !== undefined ? d.gdp_value : null);
        
        if (trendChart) trendChart.destroy();
        
        const ctx = document.getElementById('trendChart').getContext('2d');
        const datasets = [];
        const indicatorTypeValue = document.getElementById('indicatorType').value;
        
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'export') {
            datasets.push({
                label: 'Экспорт (млрд USD)',
                data: exports,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                borderWidth: 2,
                tension: 0,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        }
        
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'import') {
            datasets.push({
                label: 'Импорт (млрд USD)',
                data: imports,
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                borderWidth: 2,
                tension: 0,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        }
        
        if (indicatorTypeValue === 'all' || indicatorTypeValue === 'gdp') {
            datasets.push({
                label: 'ВВП (млрд USD)',
                data: gdps,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                borderWidth: 2,
                tension: 0,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        }
        
        trendChart = new Chart(ctx, {
            type: 'line',
            data: { labels: years, datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, boxWidth: 10 } },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label && context.parsed.y !== null) {
                                    label += ': ' + new Intl.NumberFormat('ru-RU').format(context.parsed.y) + ' млрд USD';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'млрд USD' },
                        ticks: { callback: (value) => new Intl.NumberFormat('ru-RU').format(value) },
                        grid: { color: 'rgba(0, 0, 0, 0.05)' }
                    },
                    x: {
                        title: { display: true, text: 'Год' },
                        grid: { display: false },
                        ticks: { stepSize: 1, autoSkip: true, maxRotation: 45, minRotation: 0 }
                    }
                }
            }
        });
        
        await loadStats(countryId, chartData);
        
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('trendEmptyMessage').style.display = 'block';
        if (trendChart) {
            trendChart.destroy();
            trendChart = null;
        }
    }
}

// Загрузка статистики
async function loadStats(countryId, chartData) {
    if (countryId) {
        try {
            const response = await fetch(`/api/stats/${countryId}`);
            const stats = await response.json();
            
            if (stats && stats.years_count > 0) {
                const statsHtml = `
                    <div class="stat-card"><h3>📊 Лет данных</h3><div class="value">${stats.years_count || 0}</div></div>
                    <div class="stat-card"><h3>📅 Период</h3><div class="value">${stats.min_year || '-'} - ${stats.max_year || '-'}</div></div>
                    <div class="stat-card"><h3>💰 Средний экспорт</h3><div class="value">${stats.avg_export ? stats.avg_export.toFixed(2) : '-'} млрд</div></div>
                    <div class="stat-card"><h3>📥 Средний импорт</h3><div class="value">${stats.avg_import ? stats.avg_import.toFixed(2) : '-'} млрд</div></div>
                    <div class="stat-card"><h3>🏭 Средний ВВП</h3><div class="value">${stats.avg_gdp ? stats.avg_gdp.toFixed(2) : '-'} млрд</div></div>
                `;
                document.getElementById('statsContainer').innerHTML = statsHtml;
            } else {
                document.getElementById('statsContainer').innerHTML = `
                    <div class="empty-state" style="grid-column: 1/-1;">
                        <h3>📭 Нет статистики для выбранной страны</h3>
                        <p>Добавьте данные через CSV</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    } else if (chartData && chartData.length > 0) {
        const uniqueCountries = [...new Set(chartData.map(d => d.country_name))].filter(c => c);
        const totalRecords = chartData.length;
        const years = chartData.map(d => d.year);
        const yearsRange = `${Math.min(...years)} - ${Math.max(...years)}`;
        const totalExport = chartData.reduce((sum, d) => sum + (d.export_value || 0), 0);
        const totalImport = chartData.reduce((sum, d) => sum + (d.import_value || 0), 0);
        
        document.getElementById('statsContainer').innerHTML = `
            <div class="stat-card"><h3>🌍 Стран</h3><div class="value">${uniqueCountries.length || 0}</div></div>
            <div class="stat-card"><h3>📊 Всего записей</h3><div class="value">${totalRecords}</div></div>
            <div class="stat-card"><h3>📅 Период</h3><div class="value">${yearsRange}</div></div>
            <div class="stat-card"><h3>💰 Сумма экспорта</h3><div class="value">${totalExport.toFixed(1)} млрд</div></div>
            <div class="stat-card"><h3>📥 Сумма импорта</h3><div class="value">${totalImport.toFixed(1)} млрд</div></div>
        `;
    } else {
        document.getElementById('statsContainer').innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <h3>📭 Нет данных</h3>
                <p>Загрузите данные для отображения статистики</p>
            </div>
        `;
    }
}

// ==================== CSV ИМПОРТ ====================

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
                    <h4>📋 Предпросмотр данных</h4>
                    <p><strong>Найдено колонок:</strong> ${result.columns.length}</p>
                    <p><strong>Определено соответствие:</strong></p>
                    <ul>
                        ${Object.entries(result.detected_mapping).map(([k,v]) => `<li><strong>${k}:</strong> ${v || '❌ не найдено'}</li>`).join('')}
                    </ul>
                    <p><strong>Первые 3 строки:</strong></p>
                    <pre style="background: #f5f5f5; padding: 10px; overflow-x: auto; border-radius: 5px; font-size: 12px;">${JSON.stringify(result.preview, null, 2)}</pre>
                    <button onclick="importCSV()" class="btn-primary" style="margin-top: 10px;">🚀 Начать импорт</button>
                    <button onclick="document.getElementById('previewContainer').style.display='none'" class="btn-secondary" style="margin-top: 10px; margin-left: 10px;">❌ Отмена</button>
                </div>
            `;
        } else {
            previewDiv.style.display = 'block';
            previewDiv.innerHTML = `<div class="error-message"><strong>❌ Ошибка:</strong> ${result.error}</div>`;
        }
    } catch (error) {
        alert('Ошибка при предпросмотре: ' + error.message);
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
                    ⏭️ Пропущено: ${result.skipped_rows || 0}
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
            resultDiv.innerHTML = `<div class="error-message"><strong>❌ Ошибка импорта:</strong><br>${result.errors.join('<br>')}</div>`;
        }
    } catch (error) {
        alert('Ошибка при импорте: ' + error.message);
    }
}

// Скачивание шаблона
async function downloadTemplate() {
    try {
        const response = await fetch('/api/csv/template');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'import_template.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (error) {
        alert('Ошибка при скачивании шаблона: ' + error.message);
    }
}

// ==================== ПРОГНОЗИРОВАНИЕ ====================

// Загрузка прогноза
async function loadForecast() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) {
        alert('Сначала выберите страну');
        return;
    }
    
    const indicator = document.getElementById('forecastIndicator').value;
    const steps = document.getElementById('forecastSteps').value;
    const model = document.getElementById('forecastModel').value;
    
    const modelNames = {
        'auto': 'Автоматический выбор',
        'arima': 'ARIMA',
        'holt_winters': 'Хольта-Винтерса',
        'linear': 'Линейная регрессия',
        'exponential': 'Экспоненциальное сглаживание'
    };
    
    showLoading('forecast');
    
    try {
        const response = await fetch(`/api/forecast/${countryId}/${indicator}?steps=${steps}&model=${model}`);
        const result = await response.json();
        
        if (result.success) {
            displayForecast(result, modelNames[model]);
        } else {
            alert('Ошибка: ' + result.error);
            document.getElementById('forecastResult').style.display = 'none';
        }
    } catch (error) {
        alert('Ошибка при загрузке прогноза: ' + error.message);
    } finally {
        hideLoading('forecast');
    }
}

// Отображение прогноза
function displayForecast(forecast, modelName) {
    document.getElementById('forecastResult').style.display = 'block';
    
    const historicalYears = forecast.historical_years;
    const historicalValues = forecast.historical_values;
    const forecastYears = forecast.forecast_years;
    const forecastValues = forecast.forecast;
    
    const allYears = [...historicalYears, ...forecastYears];
    const allValues = [...historicalValues, ...Array(forecastYears.length).fill(null)];
    const forecastValuesForPlot = [...Array(historicalYears.length).fill(null), ...forecastValues];
    
    const lowerBounds = [...Array(historicalYears.length).fill(null), ...(forecast.lower_bounds || [])];
    const upperBounds = [...Array(historicalYears.length).fill(null), ...(forecast.upper_bounds || [])];
    
    if (forecastChart) forecastChart.destroy();
    
    const ctx = document.getElementById('forecastChart').getContext('2d');
    const datasets = [
        {
            label: 'Исторические данные',
            data: allValues,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            borderWidth: 2,
            tension: 0,
            pointRadius: 4,
            pointHoverRadius: 6
        },
        {
            label: 'Прогноз',
            data: forecastValuesForPlot,
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0,
            pointRadius: 4,
            pointHoverRadius: 6
        }
    ];
    
    if (lowerBounds.some(v => v !== null)) {
        datasets.push({
            label: 'Нижняя граница (95% CI)',
            data: lowerBounds,
            borderColor: 'rgba(255, 99, 132, 0.3)',
            backgroundColor: 'rgba(255, 99, 132, 0.05)',
            borderWidth: 1,
            borderDash: [5, 5],
            fill: false,
            pointRadius: 0
        });
        
        datasets.push({
            label: 'Верхняя граница (95% CI)',
            data: upperBounds,
            borderColor: 'rgba(255, 99, 132, 0.3)',
            backgroundColor: 'rgba(255, 99, 132, 0.05)',
            borderWidth: 1,
            borderDash: [5, 5],
            fill: '-1',
            pointRadius: 0
        });
    }
    
    forecastChart = new Chart(ctx, {
        type: 'line',
        data: { labels: allYears, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label && context.parsed.y !== null) {
                                label += ': ' + new Intl.NumberFormat('ru-RU').format(context.parsed.y) + ' млрд USD';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'млрд USD' },
                    ticks: { callback: (value) => new Intl.NumberFormat('ru-RU').format(value) }
                },
                x: { title: { display: true, text: 'Год' } }
            }
        }
    });
    
    let metricsHtml = `
        <div class="metric-card"><h4>🎯 Использованная модель</h4><div class="value">${modelName || forecast.best_model}</div></div>
        <div class="metric-card"><h4>📈 Точность (RMSE)</h4><div class="value">${forecast.metrics?.rmse ? forecast.metrics.rmse.toFixed(2) : 'N/A'}</div></div>
        <div class="metric-card"><h4>📊 Средняя ошибка (MAE)</h4><div class="value">${forecast.metrics?.mae ? forecast.metrics.mae.toFixed(2) : 'N/A'}</div></div>
        <div class="metric-card"><h4>📊 Стационарность</h4><div class="value">${forecast.stationarity?.is_stationary ? '✅ Да' : '❌ Нет'}</div></div>
    `;
    
    if (forecast.metrics?.r2) {
        metricsHtml += `<div class="metric-card"><h4>📐 R² Score</h4><div class="value">${forecast.metrics.r2.toFixed(3)}</div></div>`;
    }
    
    document.getElementById('forecastMetrics').innerHTML = metricsHtml;
    
    let infoHtml = `
        <div class="forecast-info">
            <div class="model-description">
                <span class="model-badge">ℹ️ Информация</span>
                <span>Модель: <strong>${modelName || forecast.best_model}</strong></span>
                <span>Данных использовано: <strong>${forecast.data_points || forecast.historical_values?.length}</strong> точек</span>
            </div>
    `;
    
    if (forecast.models_tested && forecast.models_tested.length > 1) {
        infoHtml += `
            <div class="models-compare">
                <strong>📊 Сравнение моделей:</strong><br>
                ${forecast.models_tested.map(m => `• ${m}`).join('<br>')}
            </div>
        `;
    }
    
    infoHtml += `</div>`;
    document.getElementById('forecastInfo').innerHTML = infoHtml;
    
    let tableHtml = `<table><thead><tr><th>Год</th><th>Прогноз (млрд USD)</th><th>Нижняя граница</th><th>Верхняя граница</th></tr></thead><tbody>`;
    
    for (let i = 0; i < forecastYears.length; i++) {
        tableHtml += `
            <tr>
                <td><strong>${forecastYears[i]}</strong></td>
                <td>${forecastValues[i].toFixed(2)}</div>
                <td class="confidence-interval">${forecast.lower_bounds && forecast.lower_bounds[i] ? forecast.lower_bounds[i].toFixed(2) : '-'}</div>
                <td class="confidence-interval">${forecast.upper_bounds && forecast.upper_bounds[i] ? forecast.upper_bounds[i].toFixed(2) : '-'}</div>
            </tr>
        `;
    }
    
    tableHtml += '</tbody></table>';
    document.getElementById('forecastTable').innerHTML = tableHtml;
}

// ==================== РЕГРЕССИОННЫЙ АНАЛИЗ ====================

// Запуск регрессионного анализа
async function runRegressionAnalysis() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) {
        alert('Сначала выберите страну');
        return;
    }
    
    const model = document.getElementById('regressionModel').value;
    
    showLoading('regression');
    
    try {
        const response = await fetch(`/api/regression/country/${countryId}?model=${model}`);
        const result = await response.json();
        
        if (result.success) {
            displayRegressionResults(result);
        } else {
            let errorMessage = result.error || 'Неизвестная ошибка';
            
            if (result.suggestion) {
                errorMessage += '\n\n💡 ' + result.suggestion;
            }
            if (result.data_points !== undefined) {
                errorMessage += `\n\n📊 Найдено точек: ${result.data_points}`;
            }
            if (result.years && result.years.length > 0) {
                errorMessage += `\n📅 Доступные годы: ${result.years.join(', ')}`;
            }
            
            alert('Ошибка: ' + errorMessage);
            document.getElementById('regressionResult').style.display = 'none';
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка при анализе: ' + error.message);
        document.getElementById('regressionResult').style.display = 'none';
    } finally {
        hideLoading('regression');
    }
}

// Отображение результатов регрессии
function displayRegressionResults(results) {
    document.getElementById('regressionResult').style.display = 'block';
    
    const trainMetrics = results.train_metrics || {};
    const testMetrics = results.test_metrics || {};
    
    const metricsHtml = `
        <div class="metric-item">
            <div class="label">📊 Train R²</div>
            <div class="value">${trainMetrics.r2 ? trainMetrics.r2.toFixed(4) : 'N/A'}</div>
        </div>
        <div class="metric-item">
            <div class="label">📊 Test R²</div>
            <div class="value">${testMetrics.r2 ? testMetrics.r2.toFixed(4) : 'N/A'}</div>
        </div>
        <div class="metric-item">
            <div class="label">📈 Train MAE</div>
            <div class="value">${trainMetrics.mae ? trainMetrics.mae.toFixed(2) : 'N/A'} млрд</div>
        </div>
        <div class="metric-item">
            <div class="label">📈 Test MAE</div>
            <div class="value">${testMetrics.mae ? testMetrics.mae.toFixed(2) : 'N/A'} млрд</div>
        </div>
        <div class="metric-item">
            <div class="label">📉 Train RMSE</div>
            <div class="value">${trainMetrics.rmse ? trainMetrics.rmse.toFixed(2) : 'N/A'} млрд</div>
        </div>
        <div class="metric-item">
            <div class="label">📉 Test RMSE</div>
            <div class="value">${testMetrics.rmse ? testMetrics.rmse.toFixed(2) : 'N/A'} млрд</div>
        </div>
    `;
    document.getElementById('regressionMetrics').innerHTML = metricsHtml;
    
}

// Прогнозирование ВВП
async function predictGDP() {
    const countryId = document.getElementById('countrySelect').value;
    const exportValue = parseFloat(document.getElementById('predictExport').value);
    const importValue = parseFloat(document.getElementById('predictImport').value);
    const model = document.getElementById('regressionModel').value;
    
    if (!countryId) {
        alert('Сначала выберите страну');
        return;
    }
    
    if (isNaN(exportValue) || isNaN(importValue)) {
        alert('Введите значения экспорта и импорта');
        return;
    }
    
    // Показываем индикатор загрузки
    const predictBtn = event.target;
    const originalText = predictBtn.textContent;
    predictBtn.textContent = '⏳ Прогнозирование...';
    predictBtn.disabled = true;
    
    try {
        const response = await fetch('/api/regression/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                country_id: parseInt(countryId),
                export_value: exportValue,
                import_value: importValue,
                model_type: model
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            let warningHtml = '';
            if (result.predicted_gdp < 0.01) {
                warningHtml = '<div style="background: #fff3cd; padding: 10px; margin-top: 10px; border-radius: 5px; color: #856404;">⚠️ Внимание: Прогноз показывает очень низкое значение. Проверьте корректность входных данных.</div>';
            }
            
            if (result.model_metrics.r2 < 0.3) {
                warningHtml += '<div style="background: #fff3cd; padding: 10px; margin-top: 10px; border-radius: 5px; color: #856404;">⚠️ Качество модели низкое (R² < 0.3). Прогноз может быть неточным.</div>';
            }
            
            document.getElementById('predictionResult').innerHTML = `
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px;">
                    <strong>📊 Прогноз ВВП для ${result.country_name}:</strong><br>
                    При экспорте ${result.input_values.export.toFixed(2)} млрд USD и импорте ${result.input_values.import.toFixed(2)} млрд USD<br>
                    <span style="font-size: 24px; color: #2e7d32; margin-top: 10px; display: inline-block;">
                        ${result.predicted_gdp.toFixed(2)} млрд USD
                    </span><br>
                    <small style="font-size: 12px; color: #666;">
                        Модель: ${result.model_type}<br>
                        Качество: R² = ${result.model_metrics.r2.toFixed(4)}, RMSE = ${result.model_metrics.rmse.toFixed(2)}<br>
                        Данных использовано: ${result.data_points} точек (${result.data_range?.years || 'неизвестно'})
                    </small>
                    ${warningHtml}
                </div>
            `;
        } else {
            let errorDetails = '';
            if (result.current_data_points) {
                errorDetails = `<br>📊 Найдено точек: ${result.current_data_points}`;
            }
            if (result.data_range) {
                errorDetails += `<br>📅 Диапазон данных: ${result.data_range}`;
            }
            
            document.getElementById('predictionResult').innerHTML = `
                <div style="background: #ffebee; padding: 15px; border-radius: 8px; color: #c62828;">
                    <strong>❌ Ошибка:</strong><br>
                    ${result.error}
                    ${errorDetails}
                    ${result.suggestion ? `<br><br>💡 ${result.suggestion}` : ''}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('predictionResult').innerHTML = `
            <div style="background: #ffebee; padding: 15px; border-radius: 8px; color: #c62828;">
                <strong>❌ Ошибка:</strong><br>
                ${error.message}
            </div>
        `;
    } finally {
        predictBtn.textContent = originalText;
        predictBtn.disabled = false;
    }
}

// ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

function getFeatureName(name) {
    const names = {
        'export': 'Экспорт',
        'import': 'Импорт',
        'export_import_interaction': 'Экспорт × Импорт',
        'export_squared': 'Экспорт²',
        'import_squared': 'Импорт²',
        'trade_balance': 'Торговое сальдо',
        'trade_turnover': 'Торговый оборот'
    };
    return names[name] || name;
}

function showLoading(section) {
    let btn;
    if (section === 'forecast') {
        btn = document.querySelector('#forecastSection .btn-primary');
    } else if (section === 'regression') {
        btn = document.querySelector('#regressionSection .btn-primary');
    }
    
    if (btn) {
        btn.originalText = btn.textContent;
        btn.textContent = '⏳ Загрузка...';
        btn.disabled = true;
    }
}

function hideLoading(section) {
    let btn;
    if (section === 'forecast') {
        btn = document.querySelector('#forecastSection .btn-primary');
    } else if (section === 'regression') {
        btn = document.querySelector('#regressionSection .btn-primary');
    }
    
    if (btn) {
        btn.textContent = btn.originalText || (section === 'forecast' ? '🔮 Построить прогноз' : '🔬 Провести анализ');
        btn.disabled = false;
    }
}

// ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

document.getElementById('countrySelect').addEventListener('change', function() {
    const forecastSection = document.getElementById('forecastSection');
    const regressionSection = document.getElementById('regressionSection');
    
    if (this.value) {
        forecastSection.style.display = 'block';
        regressionSection.style.display = 'block';
    } else {
        forecastSection.style.display = 'none';
        regressionSection.style.display = 'none';
        if (forecastChart) {
            forecastChart.destroy();
            forecastChart = null;
        }
        if (regressionChart) {
            regressionChart.destroy();
            regressionChart = null;
        }
        document.getElementById('forecastResult').style.display = 'none';
        document.getElementById('regressionResult').style.display = 'none';
    }
});

// ==================== ИНИЦИАЛИЗАЦИЯ ====================
document.addEventListener('DOMContentLoaded', () => {
    loadCountries();
    loadData();
});