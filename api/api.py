from typing import Union
from typing import Optional
import oracledb
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi import HTTPException
from passlib.context import CryptContext
import uuid
from datetime import datetime

# Configuración para el hashing de las contraseñas
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10
)


class ContactInfo(BaseModel):
    phone: str
    email: str
    active: str
    confirmed_email: str


class Client(BaseModel):
    # id_client: int
    national_document: str
    name: str
    lastname: str
    password: str
    contact_info: ContactInfo
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Login(BaseModel):
    national_document: str
    password: str


class ProductCreate(BaseModel):
    sku: str
    name: str
    description: str
    price: int
    slug: str
    category_id: int
    active: str
    id_location: int
    quantity: int


class ProductDetail(BaseModel):
    id_product: int
    sku: str
    name: str
    description: str
    price: int
    slug: str
    category_id: int
    active: str
    created_at: str
    updated_at: str


class OrderItem(BaseModel):
    id_product: int
    quantity: int


class OrderCreate(BaseModel):
    id_client: int
    id_location: int
    items: list[OrderItem]
    id_payment_method: int


class OrderUpdateStatus(BaseModel):
    status: str


class PaymentCreate(BaseModel):
    orderId: int
    amount: float
    method: str


app = FastAPI(root_path="/api")

# conectar a la base de datos
dsn = 'system/bases1@localhost:1521/XE'


@app.get("/Hola_mundo")
def hola_mundo():
    return {"message": "Hola mundo"}


@app.get("/tablas")
def read_root():
    try:
        connection = oracledb.connect(dsn)
        cursor = connection.cursor()

        # Consulta las tablas disponibles
        cursor.execute("""
            SELECT table_name 
            FROM user_tables 
            ORDER BY table_name
        """)

        columns = [col.name for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))
        data = cursor.fetchall()

        cursor.close()
        connection.close()

        return {
            "connection_status": "success",
            "available_tables": data
        }
    except Exception as e:
        return {"error": str(e)}, 500

# Create client


@app.post("/users", response_model=Client, status_code=201)
async def create_client(cliente: Client):

    # Validar que todos los campos requeridos estén presentes
    required_fields = [
        cliente.national_document,
        cliente.name,
        cliente.lastname,
        cliente.password,
        cliente.contact_info.phone,
        cliente.contact_info.email,
        cliente.contact_info.active,
        cliente.contact_info.confirmed_email
    ]

    if not all(required_fields):
        raise HTTPException(
            status_code=400,
            detail="Todos los campos son requeridos"
        )

    # validar booleanos
    if cliente.contact_info.active.upper() not in ['TRUE', 'FALSE']:
        raise HTTPException(
            status_code=400,
            detail="El campo active debe ser 'TRUE' o 'FALSE'"
        )
    if cliente.contact_info.confirmed_email.upper() not in ['TRUE', 'FALSE']:
        raise HTTPException(
            status_code=400,
            detail="El campo confirmed_email debe ser 'TRUE' o 'FALSE'"
        )

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Verificar si el documento nacional ya existe
        cursor.execute(
            "SELECT COUNT(*) FROM CLIENTES WHERE national_document = :doc",
            [cliente.national_document]
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(
                status_code=409,
                detail="Documento nacional ya registrado"
            )

        # Verificar si el email ya existe
        cursor.execute(
            "SELECT COUNT(*) FROM informacion_contacto_clientes WHERE email = :email",
            [cliente.contact_info.email]
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(
                status_code=409,
                detail="Email ya registrado"
            )

        # Generar hash de la contraseña
        hash_password = pwd_context.hash(cliente.password)

        # Obtener ID disponible para cliente
        cursor.execute("SELECT COALESCE(MAX(id_client), 0) + 1 FROM clientes")
        nuevo_id = cursor.fetchone()[0]

        # Insertar nuevo cliente
        cursor.execute(
            """
                INSERT INTO clientes (
                    id_client,
                    national_document,
                    name,
                    lastname,
                    password,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    :doc,
                    :nombre,
                    :apellido,
                    :pwd,
                    SYSDATE,
                    SYSDATE
                )
                """,
            {
                "id": nuevo_id,
                "doc": cliente.national_document,
                "nombre": cliente.name,
                "apellido": cliente.lastname,
                "pwd": hash_password
            }
        )

        # Obtener ID disponible para información del cliente (otra tabla)
        cursor.execute(
            "SELECT COALESCE(MAX(id_inf_client), 0) + 1 FROM informacion_contacto_clientes")
        nuevo_id_inf = cursor.fetchone()[0]

        # Insertar información de contacto
        cursor.execute(
            """
                INSERT INTO informacion_contacto_clientes (
                    id_inf_client,
                    id_client,
                    phone,
                    email,
                    active,
                    confirmed_email,
                    created_at,
                    updated_at
                ) VALUES (
                    :id_inf,
                    :id_client,
                    :phone,
                    :email,
                    :active,
                    :confirmed_email,
                    SYSDATE,
                    SYSDATE
                )
                """,
            {
                "id_inf": nuevo_id_inf,
                "id_client": nuevo_id,
                "phone": cliente.contact_info.phone,
                "email": cliente.contact_info.email,
                "active": cliente.contact_info.active.upper(),
                "confirmed_email": cliente.contact_info.confirmed_email.upper()
            }
        )

        # Commit the transaction
        connection.commit()

        # Devolver los datos del cliente creado (sin la contraseña hash)
        response_data = {
            "national_document": cliente.national_document,
            "name": cliente.name,
            "lastname": cliente.lastname,
            "password": "********",  # No devolvemos la contraseña real
            "contact_info": {
                "phone": cliente.contact_info.phone,
                "email": cliente.contact_info.email,
                "active": cliente.contact_info.active.upper(),
                "confirmed_email": cliente.contact_info.confirmed_email.upper()
            }
        }
        return response_data

    except HTTPException:
        # Re-lanzar las excepciones HTTP que ya hemos manejado
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating client: {str(e)}"
        )
    finally:
        # Close the cursor and the connection
        cursor.close()
        connection.close()

# login cliente


@app.post("/users/login", status_code=200)
async def login_client(login_data: Login):

    # campos requeridos
    if not login_data.national_document or not login_data.password:
        raise HTTPException(
            status_code=400,
            detail="Falta algun campo requerido"
        )

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Buscar el cliente por national_document
        cursor.execute(
            """
            SELECT c.id_client, c.national_document, c.name, c.lastname, c.password,
                   ic.phone, ic.email, ic.active, ic.confirmed_email
            FROM clientes c
            JOIN informacion_contacto_clientes ic ON c.id_client = ic.id_client
            WHERE c.national_document = :doc
            """,
            {"doc": login_data.national_document}
        )

        client_data = cursor.fetchone()

        # Verificar si el documento nacional existe
        if not client_data:
            raise HTTPException(
                status_code=401,
                detail="Credenciales invalidas"
            )

        # Verificar la contraseña
        if not pwd_context.verify(login_data.password, client_data[4]):
            raise HTTPException(
                status_code=401,
                detail="Credenciales invalidas"
            )

        # Generar ID aleatorio (token) para la sesión
        session_id = str(uuid.uuid4())

        # respuesta
        response_data = {
            "status": "success",
            "message": "User authenticated",
            "SessionID": session_id,
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error durante el login: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# get un cliente


@app.get("/users/{id}", status_code=200)
async def get_client(id: int):
    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:

        # información de contacto
        cursor.execute(
            """
            SELECT c.id_client, c.national_document, c.name, c.lastname,
                   ic.phone, ic.email, ic.active, ic.confirmed_email,
                   TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI:SS'),
                   TO_CHAR(c.updated_at, 'YYYY-MM-DD HH24:MI:SS')
            FROM clientes c
            JOIN informacion_contacto_clientes ic ON c.id_client = ic.id_client
            WHERE c.id_client = :id
            """,
            {"id": id}
        )

        client_data = cursor.fetchone()

        # Verificar si el cliente existe
        if not client_data:
            raise HTTPException(
                status_code=404,
                detail="El usuario no existe"
            )

        # response
        response_data = {
            "id_client": client_data[0],
            "national_document": client_data[1],
            "name": client_data[2],
            "lastname": client_data[3],
            "contact_info": {
                "phone": client_data[4],
                "email": client_data[5],
                "active": client_data[6],
                "confirmed_email": client_data[7]
            },
            "created_at": client_data[8],
            "updated_at": client_data[9]
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener información del cliente: {str(e)}"
        )
    finally:

        cursor.close()
        connection.close()

# Actualizar cliente


@app.put("/users/{id}", status_code=200)
async def update_client(id: int, update_data: dict):
    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # ver si el usuario existe
        cursor.execute(
            "SELECT COUNT(*) FROM clientes WHERE id_client = :id",
            {"id": id}
        )

        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail="Usuario no existe"
            )

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar al menos un campo valido"
            )

        # Separar campos de clientes y contacto_cliente
        client_fields = {
            'national_document': 'national_document',
            'name': 'name',
            'lastname': 'lastname'
        }

        contact_fields = {
            'phone': 'phone',
            'email': 'email',
            'active': 'active',
            'confirmed_email': 'confirmed_email'
        }

        client_updates = []
        contact_updates = []
        params = {"id": id}

        # Procesar campos de clientes
        for field, db_field in client_fields.items():
            if field in update_data:
                client_updates.append(f"{db_field} = :{field}")
                params[field] = update_data[field]

        # Procesar campos de contacto_cliente
        for field, db_field in contact_fields.items():
            if field in update_data:
                # Validar campos booleanos
                if field in ['active', 'confirmed_email']:
                    if update_data[field].upper() not in ['TRUE', 'FALSE']:
                        raise HTTPException(
                            status_code=400,
                            detail=f"El campo {field} debe ser 'TRUE' o 'FALSE'"
                        )
                    params[field] = update_data[field].upper()
                else:
                    params[field] = update_data[field]
                contact_updates.append(f"{db_field} = :{field}")

        # Verificar si el nuevo email ya existe
        if 'email' in update_data:
            cursor.execute(
                """SELECT COUNT(*) FROM informacion_contacto_clientes 
                   WHERE email = :email AND id_client != :id""",
                {"email": update_data['email'], "id": id}
            )
            if cursor.fetchone()[0] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="El email ya está registrado por otro usuario"
                )

        # Verificar si el nuevo documento nacional ya existe
        if 'national_document' in update_data:
            cursor.execute(
                """SELECT COUNT(*) FROM clientes 
                   WHERE national_document = :doc AND id_client != :id""",
                {"doc": update_data['national_document'], "id": id}
            )
            if cursor.fetchone()[0] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="El documento nacional ya esta registrado por otro usuario"
                )

        # Actualizar tabla de clientes si hay campos
        if client_updates:
            update_query = f"""
                UPDATE clientes
                SET {', '.join(client_updates)}, updated_at = SYSDATE
                WHERE id_client = :id
            """
            cursor.execute(update_query, params)

        # Actualizar tabla de contacto
        if contact_updates:
            update_query = f"""
                UPDATE informacion_contacto_clientes
                SET {', '.join(contact_updates)}, updated_at = SYSDATE
                WHERE id_client = :id
            """
            cursor.execute(update_query, params)

        # Confirmar cambios si hubo actualizaciones
        if client_updates or contact_updates:
            connection.commit()
            return {"message": "Actualización exitosa"}
        else:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron campos válidos"
            )

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el cliente: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# Eliminar usuario


@app.delete("/users/{id}", status_code=200)
async def delete_client(id: int):
    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # ver si el usuario existe
        cursor.execute(
            "SELECT COUNT(*) FROM clientes WHERE id_client = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail="El usuario no existe"
            )

        # Eliminar información de contacto primero
        cursor.execute(
            "DELETE FROM informacion_contacto_clientes WHERE id_client = :id",
            {"id": id}
        )

        # Eliminar el cliente
        cursor.execute(
            "DELETE FROM clientes WHERE id_client = :id",
            {"id": id}
        )

        connection.commit()

        return {"message": "Usuario eliminado con exito"}

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar el cliente: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()


# ======== Productos =========
# Obtener lista de productos
@app.get("/products", status_code=200)
async def get_products():
    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Consulta para obtener los productos con su stock
        cursor.execute("""
            SELECT p.id_product, p.name, p.price, 
                   COALESCE(SUM(i.quantity), 0) as stock
            FROM productos p
            LEFT JOIN inventario i ON p.id_product = i.id_product
            WHERE p.active = 'TRUE'
            GROUP BY p.id_product, p.name, p.price
            ORDER BY p.id_product
        """)

        columns = [col[0].lower() for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))
        products = cursor.fetchall()

        return {"products": products}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los productos: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# Detalles de un producto


@app.get("/products/{id}", response_model=ProductDetail, status_code=200)
async def get_product_detail(id: int):

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Consultar información del producto
        cursor.execute(
            """
            SELECT 
                id_product, sku, name, description, price, 
                slug, category_id, active,
                TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS'),
                TO_CHAR(updated_at, 'YYYY-MM-DD HH24:MI:SS')
            FROM productos
            WHERE id_product = :id
            """,
            {"id": id}
        )

        product_data = cursor.fetchone()

        # Verificar si el producto existe
        if not product_data:
            raise HTTPException(
                status_code=404,
                detail="Producto no encontrado"
            )

        # respuesta
        response_data = {
            "id_product": product_data[0],
            "sku": product_data[1],
            "name": product_data[2],
            "description": product_data[3],
            "price": product_data[4],
            "slug": product_data[5],
            "category_id": product_data[6],
            "active": product_data[7],
            "created_at": product_data[8],
            "updated_at": product_data[9]
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener el producto: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()


# Crear producto


@app.post("/products", status_code=201)
async def create_product(product: ProductCreate):
    # Validar campos requeridos
    if not all([product.sku, product.name, product.description, product.slug, product.category_id]):
        raise HTTPException(
            status_code=400,
            detail="Faltan campos requeridos"
        )

    # Ver que active sea 'TRUE' o 'FALSE'
    if product.active.upper() not in ['TRUE', 'FALSE']:
        raise HTTPException(
            status_code=400,
            detail="El campo active debe ser 'TRUE' o 'FALSE'"
        )

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Verificar si el SKU ya existe
        cursor.execute(
            "SELECT COUNT(*) FROM productos WHERE sku = :sku",
            {"sku": product.sku}
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(
                status_code=409,
                detail="El SKU ya está registrado"
            )

        # Obtener ID disponible para producto
        cursor.execute(
            "SELECT COALESCE(MAX(id_product), 0) + 1 FROM productos")
        new_product_id = cursor.fetchone()[0]

        # Insertar nuevo producto
        cursor.execute(
            """
            INSERT INTO productos (
                id_product,
                sku,
                name,
                description,
                price,
                slug,
                category_id,
                active,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :sku,
                :name,
                :description,
                :price,
                :slug,
                :category_id,
                :active,
                SYSDATE,
                SYSDATE
            )
            """,
            {
                "id": new_product_id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "slug": product.slug,
                "category_id": product.category_id,
                "active": product.active.upper()
            }
        )

        # Obtener ID disponible para inventario
        cursor.execute(
            "SELECT COALESCE(MAX(id_inventory), 0) + 1 FROM inventario")
        new_inventory_id = cursor.fetchone()[0]

        # Insertar registro en inventario
        cursor.execute(
            """
            INSERT INTO inventario (
                id_inventory,
                id_product,
                id_location,
                quantity,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :product_id,
                :id_location,
                :quantity,
                SYSDATE,
                SYSDATE
            )
            """,
            {
                "id": new_inventory_id,
                "product_id": new_product_id,
                "id_location": product.id_location,
                "quantity": product.quantity
            }
        )

        # Commit the transaction
        connection.commit()

        # Respuesta con los datos del producto creado
        response_data = {
            "id_product": new_product_id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "price": product.price,
            "slug": product.slug,
            "category_id": product.category_id,
            "active": product.active.upper(),
            "inventory": {
                "id_location": product.id_location,
                "quantity": product.quantity
            }
        }

        return response_data

    except HTTPException:
        # Re-lanzar las excepciones HTTP
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating product: {str(e)}"
        )
    finally:

        cursor.close()
        connection.close()


# Actualizar producto
@app.put("/products/{id}", status_code=200)
async def update_product(id: int, update_data: dict):

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Verificar si el producto existe
        cursor.execute(
            "SELECT COUNT(*) FROM productos WHERE id_product = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail="Producto no encontrado"
            )

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="Se debe proporcionar al menos un campo valido para actualizar"
            )

        # Separar campos de producto e inventario
        product_fields = {
            'sku': 'sku',
            'name': 'name',
            'description': 'description',
            'price': 'price',
            'slug': 'slug',
            'category_id': 'category_id',
            'active': 'active'
        }

        inventory_fields = {
            'id_location': 'id_location',
            'quantity': 'quantity'
        }

        product_updates = []
        inventory_updates = []
        params = {"id": id}

        for field, db_field in product_fields.items():
            if field in update_data:
                # Validar campo active
                if field == 'active':
                    if update_data[field].upper() not in ['TRUE', 'FALSE']:
                        raise HTTPException(
                            status_code=400,
                            detail="El campo active debe ser 'TRUE' o 'FALSE'"
                        )
                    params[field] = update_data[field].upper()
                else:
                    params[field] = update_data[field]
                product_updates.append(f"{db_field} = :{field}")

        # inventario
        for field, db_field in inventory_fields.items():
            if field in update_data:
                inventory_updates.append(f"{db_field} = :{field}")
                params[field] = update_data[field]

        # Verificar si el nuevo SKU ya exist
        if 'sku' in update_data:
            cursor.execute(
                """SELECT COUNT(*) FROM productos 
                   WHERE sku = :sku AND id_product != :id""",
                {"sku": update_data['sku'], "id": id}
            )
            if cursor.fetchone()[0] > 0:
                raise HTTPException(
                    status_code=400,
                    detail="El SKU ya está registrado por otro producto"
                )

        # Actualizar tabla de productos
        if product_updates:
            update_query = f"""
                UPDATE productos
                SET {', '.join(product_updates)}, updated_at = SYSDATE
                WHERE id_product = :id
            """
            cursor.execute(update_query, params)

        # Actualizar tabla de inventario
        if inventory_updates:
            # Verificar si ya existe un registro de inventario para este producto
            cursor.execute(
                "SELECT COUNT(*) FROM inventario WHERE id_product = :id",
                {"id": id}
            )

            if cursor.fetchone()[0] > 0:
                # Actualizar registro existente
                update_query = f"""
                    UPDATE inventario
                    SET {', '.join(inventory_updates)}, updated_at = SYSDATE
                    WHERE id_product = :id
                """
            else:
                # Crear nuevo registro de inventario
                cursor.execute(
                    "SELECT COALESCE(MAX(id_inventory), 0) + 1 FROM inventario"
                )
                new_inventory_id = cursor.fetchone()[0]

                update_query = f"""
                    INSERT INTO inventario (
                        id_inventory,
                        id_product,
                        {', '.join(inventory_fields.values())},
                        created_at,
                        updated_at
                    ) VALUES (
                        :new_id,
                        :id,
                        {', '.join(f':{f}' for f in inventory_fields.keys() if f in update_data)},
                        SYSDATE,
                        SYSDATE
                    )
                """
                params["new_id"] = new_inventory_id

            cursor.execute(update_query, params)

        # Confirmar cambios
        if product_updates or inventory_updates:
            connection.commit()

            # Obtener los datos actualizados del producto
            cursor.execute(
                """
                SELECT 
                    p.id_product, p.sku, p.name, p.description, p.price, 
                    p.slug, p.category_id, p.active,
                    TO_CHAR(p.created_at, 'YYYY-MM-DD HH24:MI:SS'),
                    TO_CHAR(p.updated_at, 'YYYY-MM-DD HH24:MI:SS'),
                    i.id_location, i.quantity
                FROM productos p
                LEFT JOIN inventario i ON p.id_product = i.id_product
                WHERE p.id_product = :id
                """,
                {"id": id}
            )

            updated_data = cursor.fetchone()

            response_data = {
                "id_product": updated_data[0],
                "sku": updated_data[1],
                "name": updated_data[2],
                "description": updated_data[3],
                "price": updated_data[4],
                "slug": updated_data[5],
                "category_id": updated_data[6],
                "active": updated_data[7],
                "created_at": updated_data[8],
                "updated_at": updated_data[9],
                "inventory": {
                    "id_location": updated_data[10],
                    "quantity": updated_data[11]
                } if updated_data[10] is not None else None
            }

            return response_data
        else:
            raise HTTPException(
                status_code=400,
                detail="No se proporcionaron campos válidos para actualizar"
            )

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el producto: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# Eliminar producto


@app.delete("/products/{id}", status_code=200)
async def delete_product(id: int):

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Verificar si el producto existe
        cursor.execute(
            "SELECT COUNT(*) FROM productos WHERE id_product = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail="Producto no encontrado"
            )

        # Verificar si existen órdenes asociadas al producto
        cursor.execute(
            "SELECT COUNT(*) FROM ordenes_productos WHERE id_product = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar el producto porque tiene ordenes asociadas"
            )

        # Verificar si existen movimientos asociados al producto
        cursor.execute(
            "SELECT COUNT(*) FROM movimientos_productos WHERE id_product = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar el producto porque tiene movimientos asociados"
            )

        # Verificar si existen imágenes asociadas al producto
        cursor.execute(
            "SELECT COUNT(*) FROM imagenes WHERE id_product = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] > 0:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar el producto porque tiene imágenes asociadas"
            )

        # Eliminar registro de inventario primero
        cursor.execute(
            "DELETE FROM inventario WHERE id_product = :id",
            {"id": id}
        )

        # Eliminar el producto
        cursor.execute(
            "DELETE FROM productos WHERE id_product = :id",
            {"id": id}
        )

        connection.commit()

        return {"message": "Producto eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar el producto: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()


# ======== Ordenes =========
# NOTA:
# tablas que necesitan datos
# clientes, metodos_pago, productos

@app.post("/orders", status_code=201)
async def create_order(order_data: OrderCreate):
    # Validar que haya al menos un producto en la orden
    if not order_data.items or len(order_data.items) == 0:
        raise HTTPException(
            status_code=400,
            detail="La orden debe contener al menos un producto"
        )

    # Validar que las cantidades sean mayor a 0
    for item in order_data.items:
        if item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"La cantidad para el producto {item.id_product} debe ser mayor a 0"
            )

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Verificar que el cliente existe
        cursor.execute(
            "SELECT COUNT(*) FROM clientes WHERE id_client = :id",
            {"id": order_data.id_client}
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail="Cliente no encontrado"
            )

        # Verificar que el método de pago existe y está asociado al cliente
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM metodos_pago_cliente
            WHERE id_client = :id_client 
            AND id_payment_method = :id_payment_method
            """,
            {
                "id_client": order_data.id_client,
                "id_payment_method": order_data.id_payment_method
            }
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=400,
                detail="El método de pago no está asociado a este cliente o no existe"
            )

        # Verificar disponibilidad de productos y obtener precios
        products_info = []
        total_amount = 0

        for item in order_data.items:
            cursor.execute(
                """
                SELECT p.id_product, p.price, p.active, 
                       COALESCE(SUM(i.quantity), 0) as stock
                FROM productos p
                LEFT JOIN inventario i ON p.id_product = i.id_product
                WHERE p.id_product = :id_product AND i.id_location = :id_location
                GROUP BY p.id_product, p.price, p.active
                """,
                {
                    "id_product": item.id_product,
                    "id_location": order_data.id_location
                }
            )

            product_data = cursor.fetchone()

            if not product_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto {item.id_product} no encontrado"
                )

            if product_data[2] != 'TRUE':
                raise HTTPException(
                    status_code=400,
                    detail=f"Producto {item.id_product} no está activo"
                )

            if product_data[3] < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"No hay suficiente stock para el producto {item.id_product}"
                )

            products_info.append({
                "id_product": product_data[0],
                "price": product_data[1],
                "quantity": item.quantity,
                "subtotal": product_data[1] * item.quantity
            })

            total_amount += product_data[1] * item.quantity

        # Obtener ID para la nueva orden
        cursor.execute("SELECT COALESCE(MAX(id_order), 0) + 1 FROM ordenes")
        new_order_id = cursor.fetchone()[0]

        # Crear la orden
        cursor.execute(
            """
            INSERT INTO ordenes (
                id_order,
                id_client,
                id_location,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :id_client,
                :id_location,
                SYSDATE,
                SYSDATE
            )
            """,
            {
                "id": new_order_id,
                "id_client": order_data.id_client,
                "id_location": order_data.id_location
            }
        )

        # Insertar los productos de la orden
        for product in products_info:
            cursor.execute(
                "SELECT COALESCE(MAX(id_order_product), 0) + 1 FROM ordenes_productos"
            )
            new_order_product_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO ordenes_productos (
                    id_order_product,
                    id_order,
                    id_product,
                    quantity,
                    price,
                    created_at,
                    updated_at
                ) VALUES (
                    :id,
                    :id_order,
                    :id_product,
                    :quantity,
                    :price,
                    SYSDATE,
                    SYSDATE
                )
                """,
                {
                    "id": new_order_product_id,
                    "id_order": new_order_id,
                    "id_product": product["id_product"],
                    "quantity": product["quantity"],
                    "price": product["price"]
                }
            )

            # Actualizar el inventario
            cursor.execute(
                """
                UPDATE inventario
                SET quantity = quantity - :quantity,
                    updated_at = SYSDATE
                WHERE id_product = :id_product 
                AND id_location = :id_location
                """,
                {
                    "quantity": product["quantity"],
                    "id_product": product["id_product"],
                    "id_location": order_data.id_location
                }
            )

        # Crear registro de pago (CORRECCIÓN: sin caracteres especiales)
        cursor.execute(
            "SELECT COALESCE(MAX(id_order_payment), 0) + 1 FROM pagos_ordenes"
        )
        new_payment_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO pagos_ordenes (
                id_order_payment,
                id_order,
                id_payment_method,
                status,
                total_amount,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :id_order,
                :id_payment_method,
                'PENDING',
                :total_amount,
                SYSDATE,
                SYSDATE
            )
            """,
            {
                "id": new_payment_id,
                "id_order": new_order_id,
                "id_payment_method": order_data.id_payment_method,
                "total_amount": total_amount
            }
        )

        connection.commit()

        response_data = {
            "status": "success",
            "message": "Order created successfully",
            "id_order": new_order_id,
            "orderStatus": "processing",
            "total_amount": total_amount,
            "items": products_info
        }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating order: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# Tablas que se actualizan al crear orden:
# ordenes, ordenes_productos, pagos_ordenes, inventario


# Lista ordenes
@app.get("/orders", status_code=200)
async def get_orders():

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # obtener las ordenes
        cursor.execute("""
            SELECT 
                o.id_order,
                o.id_client,
                c.name || ' ' || c.lastname as client_name,
                o.id_location,
                TO_CHAR(o.created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at,
                TO_CHAR(o.updated_at, 'YYYY-MM-DD HH24:MI:SS') as updated_at,
                po.status as payment_status,
                pm.payment_method,
                po.total_amount  -- Añadido este campo
            FROM ordenes o
            JOIN clientes c ON o.id_client = c.id_client
            JOIN pagos_ordenes po ON o.id_order = po.id_order
            JOIN metodos_pago pm ON po.id_payment_method = pm.id_payment_method
            ORDER BY o.id_order DESC
        """)

        columns = [col[0].lower() for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))
        orders = cursor.fetchall()

        # Para cada orden, obtener sus productos
        for order in orders:
            cursor.execute("""
                SELECT 
                    op.id_product,
                    p.name as product_name,
                    op.quantity,
                    op.price,
                    (op.quantity * op.price) as subtotal
                FROM ordenes_productos op
                JOIN productos p ON op.id_product = p.id_product
                WHERE op.id_order = :order_id
            """, {"order_id": order['id_order']})

            product_columns = [col[0].lower() for col in cursor.description]
            cursor.rowfactory = lambda *args: dict(zip(product_columns, args))
            order['products'] = cursor.fetchall()

        return {"orders": orders}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener las órdenes: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# Detalles orden


@app.get("/orders/{id}", status_code=200)
async def get_order_detail(id: int):
    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Consulta para obtener la información básica de la orden (modificada para incluir total_amount)
        cursor.execute("""
            SELECT 
                o.id_order,
                o.id_client,
                c.name || ' ' || c.lastname as client_name,
                c.national_document as client_document,
                o.id_location,
                s.name as location_name,
                TO_CHAR(o.created_at, 'YYYY-MM-DD HH24:MI:SS') as created_at,
                TO_CHAR(o.updated_at, 'YYYY-MM-DD HH24:MI:SS') as updated_at,
                po.status as payment_status,
                pm.payment_method,
                pm.id_payment_method,
                po.total_amount,  -- Añadido este campo
                COALESCE(oe.status, 'NOT_SHIPPED') as shipping_status,
                COALESCE(oe.company, '') as shipping_company,
                COALESCE(TO_CHAR(oe.delivered_at, 'YYYY-MM-DD HH24:MI:SS'), '') as delivered_at
            FROM ordenes o
            JOIN clientes c ON o.id_client = c.id_client
            JOIN pagos_ordenes po ON o.id_order = po.id_order
            JOIN metodos_pago pm ON po.id_payment_method = pm.id_payment_method
            LEFT JOIN ordenes_entregadas oe ON o.id_order = oe.id_order
            LEFT JOIN sedes s ON o.id_location = s.id_site
            WHERE o.id_order = :order_id
        """, {"order_id": id})

        columns = [col[0].lower() for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))
        order = cursor.fetchone()

        # Verificar si la orden existe
        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Orden con ID {id} no encontrada"
            )

        # Consulta para obtener los productos de la orden (de la tabla ordenes_productos)
        cursor.execute("""
            SELECT 
                op.id_order_product,
                op.id_product,
                p.name as product_name,
                p.description as product_description,
                p.sku as product_sku,
                op.quantity,
                op.price as unit_price,
                (op.quantity * op.price) as subtotal,
                TO_CHAR(op.created_at, 'YYYY-MM-DD HH24:MI:SS') as added_at,
                TO_CHAR(op.updated_at, 'YYYY-MM-DD HH24:MI:SS') as updated_at
            FROM ordenes_productos op
            JOIN productos p ON op.id_product = p.id_product
            WHERE op.id_order = :order_id
            ORDER BY op.id_order_product
        """, {"order_id": id})

        product_columns = [col[0].lower() for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(product_columns, args))
        order_products = cursor.fetchall()

        calculated_total = sum(product['subtotal']
                               for product in order_products)

        # Construir la respuesta
        response = {
            "order_id": order['id_order'],
            "client": {
                "id": order['id_client'],
                "name": order['client_name'],
                "document": order['client_document']
            },
            "location": {
                "id": order['id_location'],
                "name": order.get('location_name', '')
            },
            "created_at": order['created_at'],
            "updated_at": order['updated_at'],
            "payment": {
                "method": order['payment_method'],
                "method_id": order['id_payment_method'],
                "status": order['payment_status'],
                "total_amount": order['total_amount'],
                "calculated_total": calculated_total  # Opcional: para verificación
            },
            "products": order_products
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los detalles de la orden: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# update order status


@app.put("/orders/{id}", status_code=200)
async def update_order_status(id: int, status_data: OrderUpdateStatus):

    # Validar que el estado
    valid_statuses = ['PAID', 'PENDING', 'FAILED']
    if status_data.status.upper() not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Debe ser uno de: {', '.join(valid_statuses)}"
        )

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Verificar si la orden existe
        cursor.execute(
            "SELECT COUNT(*) FROM ordenes WHERE id_order = :id",
            {"id": id}
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail="Orden no encontrada"
            )

        # Actualizar el estado en pagos_ordenes
        cursor.execute(
            """
            UPDATE pagos_ordenes
            SET status = :status,
                updated_at = SYSDATE
            WHERE id_order = :id
            """,
            {
                "status": status_data.status.upper(),
                "id": id
            }
        )

        connection.commit()

        return {
            "status": "success",
            "message": "Order updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar el estado de la orden: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# ======== Gestion de pagos =========

# Registrar pago


@app.post("/payments", status_code=201)
async def create_payment(payment_data: PaymentCreate):

    # Validar el monto
    if payment_data.amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="El monto del pago debe ser mayor a 0"
        )

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # verificar que la orden exista
        cursor.execute(
            "SELECT COUNT(*) FROM ordenes WHERE id_order = :order_id",
            {"order_id": payment_data.orderId}
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Orden con ID {payment_data.orderId} no encontrada"
            )

        # verificar que el método de pago existe
        cursor.execute(
            """
            SELECT id_payment_method 
            FROM metodos_pago 
            WHERE LOWER(payment_method) = LOWER(:method)
            """,
            {"method": payment_data.method}
        )
        method_data = cursor.fetchone()

        if not method_data:
            raise HTTPException(
                status_code=400,
                detail=f"Método de pago '{payment_data.method}' no válido"
            )

        method_id = method_data[0]

        # metodo de pago está asociado al cliente de la orden
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM metodos_pago_cliente mpc
            JOIN ordenes o ON mpc.id_client = o.id_client
            WHERE o.id_order = :order_id 
            AND mpc.id_payment_method = :method_id
            """,
            {
                "order_id": payment_data.orderId,
                "method_id": method_id
            }
        )
        if cursor.fetchone()[0] == 0:
            raise HTTPException(
                status_code=400,
                detail="El método de pago no está asociado al cliente de esta orden"
            )

        # Verificar el estado actual del pago
        cursor.execute(
            """
            SELECT status, total_amount 
            FROM pagos_ordenes 
            WHERE id_order = :order_id
            """,
            {"order_id": payment_data.orderId}
        )
        payment_info = cursor.fetchone()

        if not payment_info:
            raise HTTPException(
                status_code=404,
                detail="No se encontró información de pago para esta orden"
            )

        current_status = payment_info[0]
        order_amount = payment_info[1]

        if current_status == 'PAID':
            raise HTTPException(
                status_code=400,
                detail="Esta orden ya ha sido pagada completamente"
            )

        # 6. Validar que el monto coincida con el total de la orden
        if abs(payment_data.amount - order_amount):
            raise HTTPException(
                status_code=400,
                detail=f"El monto del pago (${payment_data.amount:.2f}) no coincide con el total de la orden (${order_amount:.2f})"
            )

        #  Actualizar el estado del pago
        cursor.execute(
            """
            UPDATE pagos_ordenes
            SET 
                status = 'PAID',
                updated_at = SYSDATE
            WHERE id_order = :order_id
            """,
            {"order_id": payment_data.orderId}
        )

        # Crear registro en la tabla pagos
        cursor.execute("SELECT COALESCE(MAX(id_payments), 0) + 1 FROM pagos")
        new_payment_id = cursor.fetchone()[0]

        # Obtener el ID del cliente asociado a la orden
        cursor.execute(
            "SELECT id_client FROM ordenes WHERE id_order = :order_id",
            {"order_id": payment_data.orderId}
        )
        client_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO pagos (
                id_payments,
                id_client,
                id_payment_method,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :client_id,
                :method_id,
                SYSDATE,
                SYSDATE
            )
            """,
            {
                "id": new_payment_id,
                "client_id": client_id,
                "method_id": method_id
            }
        )

        connection.commit()

        # Respuesta con los detalles del pago
        return {
            "status": "success",
            "message": "Pago registrado exitosamente",
            "paymentDetails": {
                "orderId": payment_data.orderId,
                "amountPaid": payment_data.amount,
                "paymentMethod": payment_data.method,
                "paymentStatus": "PAID",
                "paymentId": new_payment_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar el pago: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()

# Consulta de pagos

# Añadir al final del archivo api.py, antes de las últimas líneas


@app.get("/payments", status_code=200)
async def get_payments():

    # Conectar a la base de datos
    connection = oracledb.connect(dsn)
    cursor = connection.cursor()

    try:
        # Consulta para obtener los pagos con información relacionada
        cursor.execute("""
            SELECT 
                po.id_order_payment,
                po.id_order,
                c.id_client,
                c.name || ' ' || c.lastname as client_name,
                c.national_document,
                pm.payment_method,
                po.total_amount,
                po.status as payment_status,
                TO_CHAR(po.created_at, 'YYYY-MM-DD HH24:MI:SS') as payment_date,
                TO_CHAR(po.updated_at, 'YYYY-MM-DD HH24:MI:SS') as last_update
            FROM pagos_ordenes po
            JOIN ordenes o ON po.id_order = o.id_order
            JOIN clientes c ON o.id_client = c.id_client
            JOIN metodos_pago pm ON po.id_payment_method = pm.id_payment_method
            ORDER BY po.created_at DESC
        """)

        # Obtener nombres de columnas y configurar rowfactory
        columns = [col[0].lower() for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))
        payments = cursor.fetchall()

        return {"payments": payments}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener los pagos: {str(e)}"
        )
    finally:
        cursor.close()
        connection.close()
