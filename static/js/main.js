// Глобальные переменные
let trendChart = null;
let arChart = null;

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
        console.log('Страны загружены:', countries.length);
        
        loadDeleteCountrySelect();
        loadDeleteIndicatorsSelect();
    } catch (error) {
        console.error('Ошибка загрузки стран:', error);
    }
}

// Загрузка списка стран для удаления
async function loadDeleteCountrySelect() {
    try {
        const response = await fetch('/api/countries');
        const countries = await response.json();
        const select = document.getElementById('deleteCountrySelect');
        if (select) {
            select.innerHTML = '<option value="">Выберите страну</option>';
            countries.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.name;
                select.appendChild(option);
            });
        }
        
        const select2 = document.getElementById('deleteCountryIndicatorsSelect');
        if (select2) {
            select2.innerHTML = '<option value="">Выберите страну</option>';
            countries.forEach(c => {
                const option = document.createElement('option');
                option.value = c.id;
                option.textContent = c.name;
                select2.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Ошибка загрузки списка стран:', error);
    }
}

// Загрузка списка показателей для удаления
async function loadDeleteIndicatorsSelect() {
    const countryId = document.getElementById('countrySelect').value;
    const select = document.getElementById('deleteIndicatorSelect');
    
    if (!select) return;
    
    if (!countryId) {
        select.innerHTML = '<option value="">Сначала выберите страну</option>';
        return;
    }
    
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
    } catch (error) {
        console.error('Ошибка загрузки показателей:', error);
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
    
    console.log('Запрос данных:', url);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('Получено данных:', data.length);
        
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
                pointRadius: 4,
                pointHoverRadius: 6
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
                pointRadius: 4,
                pointHoverRadius: 6
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
                pointRadius: 4,
                pointHoverRadius: 6
            });
        }
        
        trendChart = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: { labels: years, datasets: datasets },
            options: { 
                responsive: true, 
                maintainAspectRatio: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('ru-RU').format(context.parsed.y) + ' млрд USD';
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
                        ticks: {
                            callback: function(value) {
                                return new Intl.NumberFormat('ru-RU').format(value);
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: { 
                        title: { display: true, text: 'Год' },
                        grid: {
                            display: false
                        }
                    }
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
            } else {
                document.getElementById('statsContainer').innerHTML = `
                    <div class="stat-card" style="grid-column: 1/-1;"><h3>📭 Нет данных</h3><div class="value">-</div></div>
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

// ==================== CSV ИМПОРТ ====================

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
            resultDiv.innerHTML = `<div class="error-message"><strong>❌ Ошибка импорта:</strong><br>${result.errors.join('<br>')}</div>`;
        }
    } catch (error) {
        alert('Ошибка при импорте: ' + error.message);
    }
}

function downloadTemplate() {
    window.location.href = '/api/csv/template';
}

// ==================== УДАЛЕНИЕ ДАННЫХ ====================

async function deleteCountry() {
    const countryId = document.getElementById('deleteCountrySelect').value;
    if (!countryId) {
        alert('Выберите страну для удаления');
        return;
    }
    
    const select = document.getElementById('deleteCountrySelect');
    const countryName = select.options[select.selectedIndex].text;
    
    if (!confirm(`ВНИМАНИЕ! Вы уверены, что хотите удалить страну "${countryName}" вместе со ВСЕМИ показателями? Это действие необратимо!`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/countries/${countryId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok && result.success) {
            alert(result.message);
            loadCountries();
            loadData();
            document.getElementById('deleteCountrySelect').innerHTML = '<option value="">Выберите страну</option>';
            document.getElementById('deleteIndicatorSelect').innerHTML = '<option value="">Выберите показатель</option>';
            loadDeleteCountrySelect();
        } else {
            alert('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function deleteIndicator() {
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
        
        if (response.ok && result.success) {
            alert(result.message);
            loadData();
            loadDeleteIndicatorsSelect();
        } else {
            alert('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function deleteAllIndicators() {
    const countryId = document.getElementById('deleteCountryIndicatorsSelect').value;
    if (!countryId) {
        alert('Выберите страну');
        return;
    }
    
    const select = document.getElementById('deleteCountryIndicatorsSelect');
    const countryName = select.options[select.selectedIndex].text;
    
    if (!confirm(`Вы уверены, что хотите удалить ВСЕ показатели страны "${countryName}"? Сама страница останется.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/indicators/country/${countryId}`, { method: 'DELETE' });
        const result = await response.json();
        
        if (response.ok && result.success) {
            alert(result.message);
            loadData();
            loadDeleteIndicatorsSelect();
        } else {
            alert('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// ==================== АВТОРЕГРЕССИЯ ====================

// Показ/скрытие выбора степени полинома
document.getElementById('arModel').addEventListener('change', function() {
    const degreeGroup = document.getElementById('arDegreeGroup');
    if (degreeGroup) {
        degreeGroup.style.display = this.value === 'polynomial' ? 'block' : 'none';
    }
});

// Загрузка авторегрессионного прогноза
async function loadAutoRegression() {
    const countryId = document.getElementById('countrySelect').value;
    if (!countryId) {
        alert('Сначала выберите страну');
        return;
    }
    
    const indicator = document.getElementById('arIndicator').value;
    const model = document.getElementById('arModel').value;
    const steps = document.getElementById('arSteps').value;
    const degree = document.getElementById('arDegree')?.value || 2;
    const confidence = document.getElementById('arConfidence')?.value || 'false';
    
    showARLoading();
    
    try {
        let url = `/api/auto-regression/${countryId}/${indicator}?steps=${steps}&model=${model}`;
        if (model === 'polynomial') {
            url += `&degree=${degree}`;
        }
        if (confidence === 'true') {
            url += `&confidence=true`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success || result.best_model) {
            displayAutoRegression(result);
        } else {
            alert('Ошибка: ' + (result.error || 'Неизвестная ошибка'));
            document.getElementById('arResult').style.display = 'none';
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка: ' + error.message);
        document.getElementById('arResult').style.display = 'none';
    } finally {
        hideARLoading();
    }
}

// Отображение результатов авторегрессии
function displayAutoRegression(result) {
    document.getElementById('arResult').style.display = 'block';
    
    if (result.best_model) {
        displayAutoRegressionComparison(result);
        return;
    }
    
    const metricsHtml = `
        <div class="metric-card">
            <h4>📊 Модель</h4>
            <div class="value">${result.model_name || result.model_type || 'N/A'}</div>
        </div>
        <div class="metric-card">
            <h4>📈 R²</h4>
            <div class="value">${result.r2 ? result.r2.toFixed(4) : 'N/A'}</div>
        </div>
        <div class="metric-card">
            <h4>📉 RMSE</h4>
            <div class="value">${result.rmse ? result.rmse.toFixed(2) : 'N/A'}</div>
        </div>
        <div class="metric-card">
            <h4>📊 MAE</h4>
            <div class="value">${result.mae ? result.mae.toFixed(2) : 'N/A'}</div>
        </div>
    `;
    document.getElementById('arMetrics').innerHTML = metricsHtml;
    
    const formulaHtml = `
        <div class="formula-box">
            <h4>📐 Формула тренда</h4>
            <div class="formula">${result.formula || 'Формула не доступна'}</div>
        </div>
    `;
    document.getElementById('arFormula').innerHTML = formulaHtml;
    
    if (arChart) arChart.destroy();
    
    const allYears = [...(result.years || []), ...(result.forecast_years || [])];
    const historicalData = [...(result.historical || []), ...Array(result.forecast_years?.length || 0).fill(null)];
    const forecastData = [...Array(result.years?.length || 0).fill(null), ...(result.forecast || [])];
    
    const datasets = [
        {
            label: 'Исторические данные',
            data: historicalData,
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            borderWidth: 2,
            pointRadius: 4,
            tension: 0
        },
        {
            label: 'Прогноз',
            data: forecastData,
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            borderWidth: 2,
            borderDash: [5, 5],
            pointRadius: 4,
            tension: 0
        }
    ];
    
    if (result.lower_bounds && result.upper_bounds) {
        const lowerBounds = [...Array(result.years?.length || 0).fill(null), ...result.lower_bounds];
        const upperBounds = [...Array(result.years?.length || 0).fill(null), ...result.upper_bounds];
        
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
    
    arChart = new Chart(document.getElementById('arChart'), {
        type: 'line',
        data: { labels: allYears, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + (context.parsed.y?.toFixed(2) || 'N/A') + ' млрд USD';
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
    
    let tableHtml = `<table><thead><tr><th>Год</th><th>Прогноз</th>`;
    if (result.lower_bounds) tableHtml += `<th>Нижняя граница</th><th>Верхняя граница</th>`;
    tableHtml += `</thead><tbody>`;
    
    for (let i = 0; i < (result.forecast || []).length; i++) {
        tableHtml += `<tr>
            <td><strong>${result.forecast_years[i]}</strong></td>
            <td>${result.forecast[i]?.toFixed(2) || 'N/A'} млрд USD</div>`;
        if (result.lower_bounds) {
            tableHtml += `<td>${result.lower_bounds[i]?.toFixed(2) || 'N/A'}</div><td>${result.upper_bounds[i]?.toFixed(2) || 'N/A'}</div>`;
        }
        tableHtml += `</tr>`;
    }
    tableHtml += '</tbody></tr>';
    document.getElementById('arTable').innerHTML = tableHtml;
}

function displayAutoRegressionComparison(result) {
    let tableHtml = `<table><thead><tr><th>Модель</th><th>R²</th><th>RMSE</th><th>MAE</th></tr></thead><tbody>`;
    
    for (const [name, modelResult] of Object.entries(result.all_models || {})) {
        if (modelResult.success) {
            tableHtml += `<tr>
                <td>${modelResult.model_name || name}</div>
                <td>${modelResult.r2 ? modelResult.r2.toFixed(4) : 'N/A'}</div>
                <td>${modelResult.rmse ? modelResult.rmse.toFixed(2) : 'N/A'}</div>
                <td>${modelResult.mae ? modelResult.mae.toFixed(2) : 'N/A'}</div>
            </tr>`;
        }
    }
    tableHtml += `</tbody></table>`;
    
    const bestHtml = `
        <div class="best-model-info">
            <h4>🏆 Лучшая модель: ${result.best_model_name || 'N/A'}</h4>
            <p>R² = ${result.best_r2?.toFixed(4) || 'N/A'}</p>
        </div>
    `;
    
    document.getElementById('arMetrics').innerHTML = bestHtml + tableHtml;
    document.getElementById('arFormula').innerHTML = '';
    
    if (arChart) arChart.destroy();
    
    const allYears = [...(result.years || []), ...(result.forecast_years || [])];
    const historicalData = [...(result.historical || []), ...Array(result.forecast_years?.length || 0).fill(null)];
    
    const datasets = [
        {
            label: 'Исторические данные',
            data: historicalData,
            borderColor: 'rgb(75, 192, 192)',
            borderWidth: 2,
            pointRadius: 4,
            tension: 0
        }
    ];
    
    const colors = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f39c12'];
    let colorIndex = 0;
    
    for (const [name, modelResult] of Object.entries(result.all_models || {})) {
        if (modelResult.success && modelResult.forecast) {
            const forecastData = [...Array(result.years?.length || 0).fill(null), ...(modelResult.forecast || [])];
            datasets.push({
                label: modelResult.model_name || name,
                data: forecastData,
                borderColor: colors[colorIndex % colors.length],
                borderWidth: 1.5,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            });
            colorIndex++;
        }
    }
    
    arChart = new Chart(document.getElementById('arChart'), {
        type: 'line',
        data: { labels: allYears, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + (context.parsed.y?.toFixed(2) || 'N/A') + ' млрд USD';
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
    
    document.getElementById('arTable').innerHTML = '';
}

function showARLoading() {
    const btn = document.querySelector('#autoRegressionSection .btn-primary');
    if (btn) {
        btn.originalText = btn.textContent;
        btn.textContent = '⏳ Загрузка...';
        btn.disabled = true;
    }
}

function hideARLoading() {
    const btn = document.querySelector('#autoRegressionSection .btn-primary');
    if (btn) {
        btn.textContent = btn.originalText || '🔮 Построить прогноз';
        btn.disabled = false;
    }
}

// ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

document.getElementById('countrySelect').addEventListener('change', function() {
    loadData();
    loadDeleteIndicatorsSelect();
    
    const show = this.value ? 'block' : 'none';
    const arSection = document.getElementById('autoRegressionSection');
    if (arSection) arSection.style.display = show;
});

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

document.addEventListener('DOMContentLoaded', () => {
    loadCountries();
    loadData();
});