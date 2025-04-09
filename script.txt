CREATE TABLE categorias (
    id_categories INTEGER NOT NULL,
    CONSTRAINT pk_categories PRIMARY KEY (id_categories),
    name VARCHAR2(50) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE productos (
    id_product INTEGER NOT NULL,
    CONSTRAINT pk_product PRIMARY KEY (id_product),
    sku VARCHAR2(10) NOT NULL,
    name VARCHAR2(100) NOT NULL,
    description VARCHAR2(300) NOT NULL,
    price INTEGER NOT NULL,
    slug VARCHAR2(50) NOT NULL,
    category_id INTEGER NOT NULL,
    active VARCHAR2(5) NOT NULL CHECK (active IN ('TRUE', 'FALSE')),
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE sedes (
    id_site INTEGER NOT NULL,
    CONSTRAINT pk_site PRIMARY KEY (id_site),
    name VARCHAR2(25) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE departamentos (
    id_department INTEGER NOT NULL,
    CONSTRAINT pk_department PRIMARY KEY (id_department),
    name VARCHAR2(70) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE trabajadores (
    id_employee INTEGER NOT NULL,
    CONSTRAINT pk_workers PRIMARY KEY (id_employee),
    national_document VARCHAR2(9) NOT NULL,
    name VARCHAR2(40) NOT NULL,
    lastname VARCHAR2(40) NOT NULL,
    job VARCHAR2(45) NOT NULL,
    id_department INTEGER NOT NULL,
    FOREIGN KEY (id_department) REFERENCES departamentos(id_department),
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE info_contacto_trabajadores (
    id_inf_workers INTEGER NOT NULL,
    CONSTRAINT pk_inf_workers PRIMARY KEY (id_inf_workers),
    id_employee INTEGER NOT NULL,
    FOREIGN KEY (id_employee) REFERENCES trabajadores(id_employee),
    phone VARCHAR2(30) NOT NULL,
    email VARCHAR2(255) NOT NULL,
    id_location INTEGER NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE,
    active VARCHAR2(5) NOT NULL CHECK (active IN ('TRUE', 'FALSE'))
);

CREATE TABLE clientes (
    id_client INTEGER NOT NULL,
    CONSTRAINT pk_clients PRIMARY KEY (id_client),
    national_document VARCHAR2(9) NOT NULL,
    name VARCHAR2(50) NOT NULL,
    lastname VARCHAR2(50) NOT NULL,
    password VARCHAR2(255) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE informacion_contacto_clientes (
    id_inf_client INTEGER NOT NULL,
    CONSTRAINT pk_inf_client PRIMARY KEY (id_inf_client),
    id_client INTEGER NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clientes(id_client),
    phone VARCHAR2(50) NOT NULL,
    email VARCHAR2(255) NOT NULL,
    active VARCHAR2(5) NOT NULL CHECK (active IN ('TRUE', 'FALSE')),
    confirmed_email VARCHAR2(5) NOT NULL CHECK (confirmed_email IN ('TRUE', 'FALSE')),
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE direcciones (
    id_directions INTEGER NOT NULL,
    CONSTRAINT pk_directions PRIMARY KEY (id_directions),
    id_client INTEGER NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clientes(id_client),
    address VARCHAR2(255) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE metodos_pago (
    id_payment_method INTEGER NOT NULL,
    CONSTRAINT pk_payment_methods PRIMARY KEY (id_payment_method),
    -- metodo de pago en varchar bank, credit visa, etc
    payment_method VARCHAR2(70) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE pagos (
    id_payments INTEGER NOT NULL,
    CONSTRAINT pk_payments PRIMARY KEY (id_payments),
    id_client INTEGER NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clientes(id_client),
    id_payment_method INTEGER NOT NULL,
    FOREIGN KEY (id_payment_method) REFERENCES metodos_pago(id_payment_method),
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE movimientos (
    id_movement INTEGER NOT NULL,
    CONSTRAINT pk_movement PRIMARY KEY (id_movement),
    location_origin_id INTEGER NOT NULL,
    location_dest_id INTEGER NOT NULL,
    status VARCHAR2(9) NOT NULL CHECK (status IN ('APPROVED', 'PENDING', 'REJECTED', 'REQUESTED')),
    estimate_arrive_date DATE NOT NULL,
    requested_at DATE NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE movimientos_productos (
    id_movements_product INTEGER NOT NULL,
    CONSTRAINT pk_movements_product PRIMARY KEY (id_movements_product),
    id_movement INTEGER NOT NULL,
    FOREIGN KEY (id_movement) REFERENCES movimientos(id_movement),
    id_product INTEGER NOT NULL,
    FOREIGN KEY (id_product) REFERENCES productos(id_product),
    quantity INTEGER NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE

);

CREATE TABLE inventario (
    id_inventory INTEGER NOT NULL,
    CONSTRAINT pk_inventory PRIMARY KEY (id_inventory),
    id_product INTEGER NOT NULL,
    FOREIGN KEY (id_product) REFERENCES productos(id_product),
    id_location INTEGER,
    quantity INTEGER DEFAULT 0,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE imagenes (
    id_img INTEGER NOT NULL,
    CONSTRAINT pk_img PRIMARY KEY (id_img),
    id_product INTEGER NOT NULL,
    FOREIGN KEY (id_product) REFERENCES productos(id_product),
    image VARCHAR(255) NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE ordenes (
    id_order INTEGER NOT NULL,
    CONSTRAINT pk_order PRIMARY KEY (id_order),
    id_client INTEGER NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clientes(id_client),
    id_location INTEGER NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE ordenes_productos (
    id_order_product INTEGER NOT NULL,
    CONSTRAINT pk_order_product PRIMARY KEY (id_order_product),
    id_order INTEGER NOT NULL,
    FOREIGN KEY (id_order) REFERENCES ordenes(id_order),
    id_product INTEGER NOT NULL,
    FOREIGN KEY (id_product) REFERENCES productos(id_product),
    quantity INTEGER NOT NULL,
    price INTEGER NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE productos_devolucion (
    id_product_return INTEGER NOT NULL,
    CONSTRAINT pk_product_return PRIMARY KEY (id_product_return),
    id_order INTEGER NOT NULL,
    FOREIGN KEY (id_order) REFERENCES ordenes(id_order),
    description VARCHAR2(255) NOT NULL,
    status VARCHAR2(9) NOT NULL CHECK (status IN ('PENDING', 'REQUESTED','APPROVED', 'REJECTED')),
    requested_at DATE NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE pagos_ordenes (
    id_order_payment INTEGER NOT NULL,
    CONSTRAINT pk_order_payment PRIMARY KEY (id_order_payment),
    id_order INTEGER NOT NULL,
    FOREIGN KEY (id_order) REFERENCES ordenes(id_order),
    id_payment_method INTEGER NOT NULL,
    FOREIGN KEY (id_payment_method) REFERENCES metodos_pago(id_payment_method),
    status VARCHAR2(7) NOT NULL CHECK (status IN ('PAID', 'PENDING', 'FAILED')),
    total_amount INTEGER NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE ordenes_entregadas (
    id_order_delivered INTEGER NOT NULL,
    CONSTRAINT pk_order_delivered PRIMARY KEY (id_order_delivered),
    id_order INTEGER NOT NULL,
    FOREIGN KEY (id_order) REFERENCES ordenes(id_order),
    company VARCHAR2(100) NOT NULL,
    address VARCHAR2(255) NOT NULL,
    number_company_guide INTEGER NOT NULL,
    status VARCHAR2(9) NOT NULL CHECK (status IN ('DELIVERED', 'FAILED', 'COMMING')),
    delivered_at DATE NOT NULL,
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);

CREATE TABLE metodos_pago_cliente (
    id_client_payment_methods INTEGER NOT NULL,
    CONSTRAINT pk_client_payment_methods PRIMARY KEY (id_client_payment_methods),
    id_client INTEGER NOT NULL,
    FOREIGN KEY (id_client) REFERENCES clientes(id_client),
    id_payment_method INTEGER NOT NULL,
    FOREIGN KEY (id_payment_method) REFERENCES metodos_pago(id_payment_method),
    created_at DATE DEFAULT SYSDATE,
    updated_at DATE DEFAULT SYSDATE
);
