CREATE TABLE Contrato (
    Numero_Contrato SERIAL PRIMARY KEY,
    client_id INT REFERENCES clients(id) ON DELETE CASCADE,
    User_id INT REFERENCES users(id) ON DELETE CASCADE,
    valor_total NUMERIC(10, 2) NOT NULL,
    valor_hora NUMERIC(10, 2),
    prazo_estimado INTERVAL
);