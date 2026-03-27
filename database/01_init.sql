-- Tabela de Clientes
CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(150),
    contact_name VARCHAR(100),
    email VARCHAR(150),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Usuários (Equipe de TI)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150),
    email VARCHAR(150) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Categorias de Chamados
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    description TEXT
);

-- Tabela de Chamados
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    client_id INT REFERENCES clients(id),
    user_id INT REFERENCES users(id),
    category_id INT REFERENCES categories(id),
    title VARCHAR(200),
    description TEXT,
    status VARCHAR(50), -- 'Aberto', 'Em Andamento', 'Resolvido'
    priority VARCHAR(50), -- 'Baixa', 'Média', 'Alta'
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);