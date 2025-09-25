INSERT INTO users (name, email, password_hash) 
VALUES ('João Vitor Biston Nunes', 'biston.nunes@gmail.com', '$2b$12$u89BL3mep7wyc7qrLvclhu/CoU3GSKchdKj73yFKwATpnS/r6ENaS');

INSERT INTO categories (user_id, name, budget_amount) VALUES
(1, "ALUGUEL", 2605.05),
(1, "MERCADO", 900.00),
(1, "CONTAS", 480.00),
(1, "ROLES", 1500.00),
(1, "COMBUSTIVEL", 600.00),
(1, "COMIDA", 400.00),
(1, "OUTROS", 961.95);
