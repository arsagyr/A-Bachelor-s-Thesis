-- Таблица стран
CREATE TABLE IF NOT EXISTS countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица показателей
CREATE TABLE IF NOT EXISTS indicators (
    id SERIAL PRIMARY KEY,
    country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    export_value DECIMAL(15, 2),   -- млрд USD
    import_value DECIMAL(15, 2),
    gdp_value DECIMAL(15, 2),
    UNIQUE(country_id, year)
);