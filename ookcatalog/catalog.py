from flask import Blueprint, render_template, request
from ookcatalog.db import (
    get_db,
    db_read_schema,
    db_read_columns,
    db_read_informations,
    db_search,
)

bp = Blueprint("ookcatalog", __name__)


@bp.route("/")
def home() -> str:
    """Render the home page as a list of all schemas, and tables within schemas.

    Root route of the web app. Will use the home.html template.
    :return: HTML page
    """
    db = get_db()
    schemas = db_read_schema(db)
    return render_template("home.html", schemas=schemas)


@bp.route("/<string:schema>/<string:table>")
def table(schema: str, table: str) -> str:
    """Render a page detailing a table, including a full list of its columns.

    Route based on schema and table name. Will use the table.html template.
    :param schema: name of the table’s schema
    :param table: name of the table
    :return: HTML page
    """
    db = get_db()
    columns = db_read_columns(db, schema, table)
    table_informations = db_read_informations(db, schema, table)
    return render_template(
        "table.html",
        schema=schema,
        table=table,
        columns=columns,
        table_informations=table_informations,
    )


@bp.route("/search")
def search() -> str:
    """Render a search page for the `q` GET parameter of the request.

    The route is simply located on /search because it will use the GET parameters to define the text to search.
    :return: HTML page
    """
    db = get_db()
    query = request.args.get("q")
    search_results = db_search(db, query)
    return render_template(
        "search.html",
        search_results=search_results,
    )
