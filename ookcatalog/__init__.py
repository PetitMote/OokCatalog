"""OokCatalog package, a light PostgreSQL catalog.

It is a Flask web application.

For testing purposes, you can run it using Flask development server. You first need to set a config.py file.
Then, run `OOKCATALOG_CONFIG=/path/to/config.py ookcatalog run --debug`

See full documentation at: https://github.com/PetitMote/OokCatalog"""

from flask import Flask, request
from flask_babel import Babel
from locale import getlocale


def get_locale() -> str:
    """Get the preferred locale for the user, based on the navigator settings or the system locale.

    If the function is called because of a web request, looks for the accepted language of the request. If it’s called
    through the commandline interface, it will ask for the system locale.
    :return: string code of the locale
    """
    if request:
        return request.accept_languages.best_match(["en", "fr"])
    return getlocale()[0]


def create_app(test_config=None):
    """Create the Flask application

    :param test_config: test configuration to load to run code tests
    :return: Flask application
    """
    # Create the app
    app = Flask(__name__, instance_relative_config=True)
    # Default config for the app
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE={
            "HOST": "localhost",
            "PORT": "5432",
            "DBNAME": "ookcatalog",
            "USER": "ookcatalog",
            "PASSWORD": "ookcatalog_pass",
        },
        TEXT_SEARCH_LANG="english",
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_envvar("OOKCATALOG_SETTINGS")
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # Registering Babel
    babel = Babel(app, locale_selector=get_locale)

    # Activate some data functions
    from . import db

    db.init_app(app)

    # Register ookcatalog consulting views
    from . import catalog, commands

    app.register_blueprint(catalog.bp)

    return app
