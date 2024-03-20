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
            EnumInfo.fetch(g.db, "ookcatalog_month"),
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
        SELECT table_schema as schema_name, array_agg(table_name order by table_name)::text[] as tables
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
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
        # Reading the table information from the ookcatalog table
        cur.execute(
            """
            SELECT obj_description(to_regclass(%s)) as description,
            description_long,
            array_agg(update_month order by update_month) as update_months
            FROM public.ookcatalog
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


def db_search(db, query: str):
    with db.cursor() as cur:
        # Searching for tables matching the query
        cur.execute(
            """
            SELECT table_schema, table_name, table_comment, ts_rank('{0.2, 0.5, 0.7, 1.0}', vector, query) as rank
            FROM (SELECT *,
                         setweight(to_tsvector('french', table_name), 'A') ||
                         setweight(to_tsvector('french', table_comment), 'A') ||
                         setweight(to_tsvector('french', description_long), 'B') ||
                         setweight(to_tsvector('french', column_names), 'C') ||
                         setweight(to_tsvector('french', column_comments), 'C') as vector
                  FROM (SELECT tables.table_schema,
                               tables.table_name,
                               coalesce(obj_description(to_regclass(tables.table_schema || '.' || tables.table_name)),
                                        '')                                  AS table_comment,
                               coalesce(cat.description_long, '')            AS description_long,
                               coalesce(string_agg(column_name, ' '), '')    as column_names,
                               coalesce(string_agg(column_comment, ' '), '') as column_comments
                        FROM information_schema.tables
                                 LEFT JOIN public.ookcatalog cat
                                           on tables.table_schema = cat.table_schema AND tables.table_name = cat.table_name
                                 CROSS JOIN LATERAL (
                            SELECT column_name,
                                   col_description(to_regclass(table_schema || '.' || table_name),
                                                   ordinal_position) as column_comment
                            FROM information_schema.columns
                            WHERE columns.table_schema = tables.table_schema
                              AND columns.table_name = tables.table_name
                            ) AS columns
                        WHERE tables.table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
                        GROUP BY tables.table_schema, tables.table_name, description_long) AS tables_strings) AS tables_vectors,
                websearch_to_tsquery('french', (%s)) AS query
            WHERE vector @@ query
            ORDER BY rank DESC
            LIMIT 20;
            """,
            (query,),
        )
        # Fetching the result
        search_results = cur.fetchall()
        return search_results
