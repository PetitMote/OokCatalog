"""Database interface for Ookcatalog

Holds database connection and every database request.
"""

import psycopg
from psycopg.rows import dict_row
from psycopg.types.enum import EnumInfo, register_enum
from flask import current_app, g


def init_app(app) -> None:
    """Execute DB related code at the initialization of the Flask app.

    For now, it only registers a function that need to be called at the end of each request.
    :param app: Flask app that is starting
    """
    # Register the close_db function so it’s called at the end of each request
    app.teardown_appcontext(close_db)


def get_db() -> psycopg.Connection:
    """Establish a psycopg connection to the database.

    Use the parameters set in OokCatalog config to establish the connection. Save the connection in the `g` object of
    the request context.

    Also fetch the custom ookcatalog_month enum type and save it in the `g` object.
    :return: psycopg 3 connection to the database
    """
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
        g.db_enum_months = EnumInfo.fetch(g.db, "ookcatalog_month")
        register_enum(
            g.db_enum_months,
            context=g.db,
        )

    return g.db


def close_db(e=None) -> None:
    """Close the database connection if still existing.

    This function is registered to the Flask app (see `init_app`) so it’s called at the end of each request.
    """
    db = g.pop("db", None)

    if db is not None:
        db.close()


def db_read_schema(db) -> dict:
    """Read schemas list and associated tables from database.

    The SQL request pulls the information from pg_catalog.pg_class and aggregates the tables in an array.
    :param db: database connection, it should be the one returned by `get_db()`
    :return: a list of all schemas in the database. Each schema is a dictionary with the following keys: 'schema_name',
    'schema_description' (schema comment), 'tables'. 'tables' is a list of all tables in the schema, and each table is a
    list with two values: the table name, and the table comment/description.
    """
    with db.cursor() as cur:
        # Reading the schemas from the information schema
        cur.execute(
            """
            WITH tables as
                     (SELECT nspname AS table_schema, relname AS table_name
                      FROM pg_catalog.pg_class
                               INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                      WHERE relpersistence = 'p'
                        AND relkind in ('r', 'v', 'm', 'f', 'p')
                        AND has_table_privilege(pg_class.oid, 'select'))
            SELECT table_schema                                                   AS schema_name,
                   obj_description(to_regnamespace(table_schema), 'pg_namespace') AS schema_description,
                   array_agg(array [table_name::text,
                                 obj_description(
                                         to_regclass(table_schema || '.' || table_name),
                                         'pg_class')::text]
                             order by table_name)::text[][]                       AS tables
            FROM tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
            GROUP BY schema_name
            ORDER BY schema_name;
            """
        )
        # Fetching the result
        schemas = cur.fetchall()
        # Sending back the result
        return schemas


def db_read_columns(db, schema: str, table: str) -> list[dict]:
    """Read columns name, type and comment for a given schema and table.

    Given the schema and table names, will list and describe every column of that table. It won’t check the given
    values, if the database user hasn’t access to it or the table doesn’t exist, it will return empty values.

    The SQL request pulls the information from `pg_catalog.pg_attribute`. For the description, or column comment, it
    makes use of the `col_description()` function of PostgreSQL.
    :param db: database connection, it should be the one returned by `get_db()`
    :param schema: schema name of the table to look up
    :param table: name of the table to look up
    :return: a list of rows, each row being a dictionary with the following keys: `column_name`, `data_type`,
        `description`
    """
    with db.cursor() as cur:
        # Reading the table columns from the information schema
        cur.execute(
            """
            WITH columns AS (SELECT pg_namespace.nspname AS table_schema,
                                    pg_class.relname     AS table_name,
                                    attname              AS column_name,
                                    pg_type.typname      AS data_type,
                                    attnum               AS ordinal_position
                             FROM pg_catalog.pg_attribute
                                      INNER JOIN pg_catalog.pg_class ON pg_attribute.attrelid = pg_class.oid
                                      INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                                      INNER JOIN pg_catalog.pg_type ON pg_attribute.atttypid = pg_type.oid
                             WHERE pg_class.relkind in ('r', 'v', 'm', 'f', 'p') -- Only get tables attributes, not index or others
                               AND attnum >= 1 -- Get only columns and not other attributes
            )
            SELECT column_name, data_type, col_description(to_regclass(%s), ordinal_position) as description
            FROM columns
            WHERE table_schema = (%s)
              AND table_name = (%s)
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


def db_read_informations(db, schema: str, table: str) -> dict:
    """Read table description and OokCatalog specific descriptions for a given schema and table.

    Given the schema and table names, will retrieve its comment / description, and OokCatalago special descriptions of
    that table stored in `public.ookcatalog`. It won’t check the given values, if the database user hasn’t access to it
    or the table doesn’t exist, it will return empty values

    The SQL request pulls the information from `public.ookcatalog`. For the description, or table comment, it
    makes use of the `obj_description()` function of PostgreSQL.

    Today, only two things are stored in `public.ookcatalog`: a long description and the update months.
    :param db: database connection, it should be the one returned by `get_db()`
    :param schema: schema name of the table to look up
    :param table: name of the table to look up
    :return: a dictionary with the following keys: `description`, `description_long`, `update_months` - update_months
        are sorted in calendar order
    """
    with db.cursor() as cur:
        # Reading the table information from the ookcatalog table
        cur.execute(
            """
            SELECT description, description_long, array_agg(updates.month) AS update_months
            FROM (VALUES (obj_description(to_regclass((%s)), 'pg_class'))) AS table_comment (description)
                     LEFT JOIN public.ookcatalog AS details ON details.table_schema = (%s) AND details.table_name = (%s)
                     LEFT JOIN LATERAL (SELECT DISTINCT unnest(update_months) AS month ORDER BY month) AS updates ON TRUE
            GROUP BY description, description_long
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


def db_search(db, query: str) -> list[dict]:
    """Search (textual search) the table names and descriptions for the given query using database search capabilities.

    With the given query, this function will perform a more complex SQL request than the others:
        1. From all tables, get the schema name, table name, and table comment
        2. Join OokCatalog information from `public.ookcatalog` to select the long description
        3. Cross join lateral (with a sub-request) the column names and column comments and aggregate them in strings
        4. From all that, prepare the tsvector for the text search, assigning weights for each field and concatenating all of the tsvector
        5. Prepare and join the query with `websearch_to_query()` (so it really needs `query` to be formatted as a web query)
        6. Compare the tsvectors and the prepared query, this is when the query actually happens. It gives a score to each table, and ranks them.

    One really important thing to know is that all the potential impact of OokCatalog is probably here. For each search,
    it’ll ask PostgreSQL to process table names and descriptions (and all the rest) again, because the vectors aren’t
    stored in database (as this would need complex triggers on the database to keep up to date). It shouldn’t have a
    significant impact since it isn’t much text and OokCatalog isn’t made for thousands of users.

    The app config is used to get the TEXT_SEARCH_LANG setting. This is the lang used for the text search, and is very
    important so PostgreSQL interprets both the table descriptions and the query correctly. It’s injected several times,
    when we create the tsvectors and when we prepare the query. Note that it’s not a locale code but a full name.

    It’s possible to tweak the weighting of the text search to get better results.
        When creating the tsvectors, we give them a category with a letter, A being the most important and D the less
        important. We can change this based on the importance we give to each element. If you think the column names are
        more important, you can give them the 'B' category.

        Then, there are the weights attributed to each category. It’s the first argument of the `ts_rank()` function. It
        takes the form of an array, the first element being the weight for the D category and the last for the A
        category (so, from less important to most important). You can alter these weights, to give more or less
        importance to a category. For example, if you want to give an even greater importance to the table name and
        comment, you could inpute '{0.2, 0.5, 0.7, 1.3}'. There are no generic answer for these values.

    :param db: database connection, it should be the one returned by `get_db()`
    :param query: textual search query, formatted as an HTTP GET parameter (the part after the `q=` in
        `https://example.com?q=query`)
    :return: a list of tables, most pertinent first, each table being a dictionary with the following keys:
        `table_schema`, `table_name`, `table_comment`, `rank``
    """
    with db.cursor() as cur:
        # Searching for tables matching the query
        cur.execute(
            """
            WITH tables AS (SELECT nspname AS table_schema, relname AS table_name
                            FROM pg_catalog.pg_class
                                     INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                            WHERE relpersistence = 'p'
                              AND relkind in ('r', 'v', 'm', 'f', 'p')
                              AND has_table_privilege(pg_class.oid, 'select')),
                 columns AS (SELECT pg_namespace.nspname AS table_schema,
                                    pg_class.relname     AS table_name,
                                    attname              AS column_name,
                                    pg_type.typname      AS data_type,
                                    attnum               AS ordinal_position
                             FROM pg_catalog.pg_attribute
                                      INNER JOIN pg_catalog.pg_class ON pg_attribute.attrelid = pg_class.oid
                                      INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                                      INNER JOIN pg_catalog.pg_type ON pg_attribute.atttypid = pg_type.oid
                             WHERE pg_class.relkind in ('r', 'v', 'm', 'f', 'p') -- Only get tables attributes, not index or others
                               AND attnum >= 1 -- Get only columns and not other attributes
                 )
            SELECT table_schema, table_name, table_comment, ts_rank('{0.2, 0.5, 0.7, 1.0}', vector, query) as rank
            FROM (SELECT *,
                         setweight(to_tsvector(%(text_search_lang)s, table_name), 'A') ||
                         setweight(to_tsvector(%(text_search_lang)s, table_comment), 'A') ||
                         setweight(to_tsvector(%(text_search_lang)s, description_long), 'B') ||
                         setweight(to_tsvector(%(text_search_lang)s, column_names), 'C') ||
                         setweight(to_tsvector(%(text_search_lang)s, column_comments), 'C') as vector
                  FROM (SELECT tables.table_schema,
                               tables.table_name,
                               coalesce(obj_description(to_regclass(tables.table_schema || '.' || tables.table_name),
                               'pg_class'), '')                              AS table_comment,
                               coalesce(cat.description_long, '')            AS description_long,
                               coalesce(string_agg(column_name, ' '), '')    as column_names,
                               coalesce(string_agg(column_comment, ' '), '') as column_comments
                        FROM tables
                                 LEFT JOIN public.ookcatalog cat
                                           on tables.table_schema = cat.table_schema AND tables.table_name = cat.table_name
                                 CROSS JOIN LATERAL (
                                    SELECT column_name,
                                           col_description(to_regclass(table_schema || '.' || table_name),
                                                           ordinal_position) as column_comment
                                    FROM columns
                                    WHERE columns.table_schema = tables.table_schema
                                      AND columns.table_name = tables.table_name
                                    ) AS columns
                        WHERE tables.table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
                        GROUP BY tables.table_schema, tables.table_name, description_long) AS tables_strings) AS tables_vectors,
                websearch_to_tsquery(%(text_search_lang)s, (%(query)s)) AS query
            WHERE vector @@ query
            ORDER BY rank DESC
            LIMIT 20;
            """,
            {
                "query": query,
                "text_search_lang": current_app.config["TEXT_SEARCH_LANG"],
            },
        )
        # Fetching the result
        search_results = cur.fetchall()
        return search_results


def db_tables_updating(db, month: int) -> list[dict]:
    """Get the tables updating in the given month, from OokCatalog table.

    This function gets back the enum from `g.db_enum_months` so it can translate the month number to the label as
    defined in the ENUM TYPE at the set-up of the database. The SQL request checks the presence of that month in the
    update_months array of `public.ookcatalog`.
    :param db: database connection, it should be the one returned by `get_db()`
    :param month: month number, from 1 (january) to 12 (december)
    :return: a list of dictionaries, with the two values `table_schema` and `table_name`. The list is sorted by schema
        and table name
    """
    # Getting back the enum
    Months = g.db_enum_months.enum
    # Getting month label
    month_label = Months(month).name
    with db.cursor() as cur:
        cur.execute(  # Getting all the tables updating on that month
            """
            SELECT table_schema, table_name
            FROM public.ookcatalog
            WHERE update_months::text[] && ARRAY [(%s)]
            ORDER BY table_schema, table_name
            """,
            (month_label,),
        )
        # Fetching the result
        tables_updating = cur.fetchall()
        return tables_updating


def db_catalog_retrieve_tables(db) -> list[dict]:
    """Retrieve missing tables in `public.ookcatalog`.

    This function will list all tables in the database (that the configured user has access to) and insert those which
    aren’t already in the `public.ookcatalog` table. This avoids typos, or allows to easily insert a lot of tables.

    The function will commit after that.
    :param db: database connection, it should be the one returned by `get_db()`
    :return: a list of the inserted tables, ordered by table_schema and table_name, each table being a dictionary with
        the `table_schema` and `table_name` values.
    """
    with db.cursor() as cur:
        cur.execute(  # PostgreSQL request to insert all tables in the catalog, returning these tables
            """
            WITH tables AS (SELECT nspname AS table_schema, relname AS table_name
                            FROM pg_catalog.pg_class
                                     INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                            WHERE relpersistence = 'p'
                              AND relkind in ('r', 'v', 'm', 'f', 'p')
                              AND has_table_privilege(pg_class.oid, 'select')),
                inserted AS (INSERT INTO public.ookcatalog (table_schema, table_name)
                    SELECT tables.table_schema, tables.table_name
                    FROM tables
                             LEFT JOIN public.ookcatalog AS cat
                                       ON tables.table_schema = cat.table_schema AND tables.table_name = cat.table_name
                    WHERE tables.table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
                      AND cat.table_schema is null
                    RETURNING table_schema, table_name)
            SELECT *
            FROM inserted
            ORDER BY table_schema, table_name;
            """
        )
        tables_inserted = (
            cur.fetchall()
        )  # Execute the query and retrieve the list of inserted tables
        db.commit()  # We need to commit the transaction so changes are applied
        return tables_inserted


def db_tables_missing_comment(db) -> list[dict]:
    """Retrieve tables without a table comment / description.

    :param db: database connection, it should be the one returned by `get_db()`
    :return: a list of tables, ordered by schema and table name, each table being a dictionary with the following keys:
        `table_schema`, `table_name`
    """
    with db.cursor() as cur:
        cur.execute(  # PostgreSQL request to get table without a comment
            """
            WITH tables AS (SELECT nspname AS table_schema, relname AS table_name
                            FROM pg_catalog.pg_class
                                     INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                            WHERE relpersistence = 'p'
                              AND relkind in ('r', 'v', 'm', 'f', 'p')
                              AND has_table_privilege(pg_class.oid, 'select'))
            SELECT table_schema,
                   table_name
            FROM tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
              AND obj_description(to_regclass(table_schema || '.' || table_name), 'pg_class') IS NULL
            ORDER BY table_schema, table_name
            """
        )
        tables_missing_comment = (
            cur.fetchall()
        )  # Execute the query and fetch the result
        return tables_missing_comment


def db_tables_with_columns_missing_comment(db) -> list[dict]:
    """Retrieve tables with a column without comment / description.

    :param db: database connection, it should be the one returned by `get_db()`
    :return: a list of tables, ordered by schema and table name, each table being a dictionary with the following keys:
        `table_schema`, `table_name`
    """
    with db.cursor() as cur:
        cur.execute(
            """
            WITH columns AS (SELECT pg_namespace.nspname AS table_schema,
                                    pg_class.relname     AS table_name,
                                    attname              AS column_name,
                                    pg_type.typname      AS data_type,
                                    attnum               AS ordinal_position
                             FROM pg_catalog.pg_attribute
                                      INNER JOIN pg_catalog.pg_class ON pg_attribute.attrelid = pg_class.oid
                                      INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                                      INNER JOIN pg_catalog.pg_type ON pg_attribute.atttypid = pg_type.oid
                             WHERE pg_class.relkind in ('r', 'v', 'm', 'f', 'p') -- Only get tables attributes, not index or others
                               AND attnum >= 1 -- Get only columns and not other attributes
            )
            SELECT table_schema,
                   table_name
            FROM columns
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
              AND col_description(to_regclass(table_schema || '.' || table_name), ordinal_position) IS NULL
            GROUP BY table_schema, table_name
            ORDER BY table_schema, table_name
            """
        )
        tables_with_columns_missing_comment = (
            cur.fetchall()
        )  # Execute the query and fetch the result
        return tables_with_columns_missing_comment


def db_tables_missing_ookcatalog_details(db) -> list[dict]:
    """Retrieve tables without long description or update months (from `public.ookcatalog`).

    :param db: database connection, it should be the one returned by `get_db()`
    :return: a list of tables, ordered by schema and table name, each table being a dictionary with the following keys:
        `table_schema`, `table_name`
    """
    with db.cursor() as cur:
        cur.execute(
            """
            WITH tables AS (SELECT nspname AS table_schema, relname AS table_name
                            FROM pg_catalog.pg_class
                                     INNER JOIN pg_catalog.pg_namespace ON pg_class.relnamespace = pg_namespace.oid
                            WHERE relpersistence = 'p'
                              AND relkind in ('r', 'v', 'm', 'f', 'p')
                              AND has_table_privilege(pg_class.oid, 'select'))
            SELECT tables.table_schema,
                   tables.table_name
            FROM tables
                     LEFT JOIN public.ookcatalog cat
                               ON tables.table_schema = cat.table_schema AND tables.table_name = cat.table_name
            WHERE tables.table_schema NOT IN ('information_schema', 'pg_catalog', 'topology')
              AND (cat.description_long IS NULL OR cat.update_months IS NULL)
            ORDER BY table_schema, table_name;
            """
        )
        tables_missing_ookcatalog_details = (
            cur.fetchall()
        )  # Execute the query and fetch the result
        return tables_missing_ookcatalog_details
