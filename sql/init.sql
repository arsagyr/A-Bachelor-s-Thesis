CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE indicators (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE statistics (
    country_id INT REFERENCES countries(id),
    year INT NOT NULL,
    indicator_id INT REFERENCES indicators(id),
    value NUMERIC(20,2) NOT NULL,

    PRIMARY KEY (country_id, year, indicator_id)
);
