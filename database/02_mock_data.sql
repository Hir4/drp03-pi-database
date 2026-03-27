-- Inserindo Clientes
INSERT INTO clients (company_name, contact_name, email, phone) VALUES 
('TechCorp', 'Carlos Silva', 'carlos@techcorp.com', '11999999999'),
('Padaria do João', 'João Souza', 'joao@padaria.com', '12988888888');

-- Inserindo Usuários
INSERT INTO users (full_name, email, password_hash, role) VALUES 
('Ana Desenvolvedora', 'ana@nossati.com', 'hash123', 'Analista N2'),
('Pedro Suporte', 'pedro@nossati.com', 'hash456', 'Atendimento N1');

-- Inserindo Categorias
INSERT INTO categories (name, description) VALUES 
('Infraestrutura', 'Problemas com rede, servidores e hardware'),
('Software', 'Bugs ou dúvidas em sistemas e aplicativos');

-- Inserindo Chamados
INSERT INTO tickets (client_id, user_id, category_id, title, description, status, priority, opened_at, closed_at) VALUES 
(1, 1, 1, 'Servidor fora do ar', 'O servidor principal caiu após a chuva', 'Resolvido', 'Alta', '2026-03-20 08:00:00', '2026-03-20 14:00:00'),
(2, 2, 2, 'Sistema de caixa travando', 'O PDV fecha sozinho na hora de pagar', 'Em Andamento', 'Média', '2026-03-26 10:30:00', NULL),
(1, 2, 2, 'Dúvida na emissão de nota', 'Como configuro o novo imposto?', 'Resolvido', 'Baixa', '2026-03-25 09:00:00', '2026-03-25 09:45:00'),
(2, 1, 1, 'Internet caindo', 'Roteador reiniciando sozinho', 'Aberto', 'Alta', '2026-03-27 08:15:00', NULL);