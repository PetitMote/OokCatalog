import psycopg
from psycopg.rows import dict_row
from psycopg.types.enum import EnumInfo, register_enum
from flask import current_app, g


def init_app(app):
    # Register the close_db function so it’s called at the end of each request
    app.teardown_appcontext(close_db)


def get_db():
    if "db" not in g:
        g.db = psycopg.connect(
            f"""
        host={current_app.config['DATABASE']['HOST']}
        port={current_app.config['DATABASE']['PORT']}
        dbname={current_app.config['DATABASE']['DBNAME']}
        user={current_app.config['DATABASE']['USER']}
        password={current_app.config['DATABASE']['PASSWORD']}
        """,
            row_factory=dict_row,
        )
        # Registering months Enum information so it’s correctly interpreted by psycopg
        register_enum(
            EnumInfo.fetch(g.db, 'pgeasycatalog_month'),
            g.db,
        )

    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def db_read_schema(db):
    with db.cursor() as cur:
        # Reading the schemas from the information schema
        cur.execute(
            """
        SELECT schema_name, array_agg(table_name order by table_name)::text[] as tables
        FROM information_schema.schemata
        INNER JOIN information_schema.tables ON tables.table_schema = schemata.schema_name
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'topology')
        GROUP BY schema_name
        ORDER BY schema_name;"""
        )
        # Fetching the result
        schemas = {schema["schema_name"]: schema["tables"] for schema in cur.fetchall()}
        # Sending back the result
        return schemas


def db_read_columns(db, schema: str, table: str):
    with db.cursor() as cur:
        # Reading the table columns from the information schema
        cur.execute(
            """
            SELECT column_name, data_type, col_description(to_regclass(%s), ordinal_position) as description
            FROM information_schema.columns
            WHERE table_schema = (%s) AND table_name = (%s)
            ORDER BY ordinal_position;
            """,
            (
                f"{schema}.{table}",
                schema,
                table,
            ),  # Passing correctly the variables to avoid SQL injection
        )
        # Fetching the result
        columns = cur.fetchall()
        return columns


def db_read_informations(db, schema: str, table: str):
    with db.cursor() as cur:
        # Reading the table information from the catalog table
        cur.execute(
            """
            SELECT obj_description(to_regclass(%s)) as description,
            description_long,
            array_agg(update_month order by update_month) as update_months
            FROM public.pgeasycatalog
            CROSS JOIN LATERAL unnest(update_months) as update_month
            WHERE table_schema = (%s) AND table_name = (%s)
            GROUP BY table_schema, table_name, description_long;
            """,
            (
                f"{schema}.{table}",
                schema,
                table,
            ),  # Passing correctly the variables to avoid SQL injection
        )
        # Fetching the result
        table_informations = cur.fetchone()
        return table_informations
