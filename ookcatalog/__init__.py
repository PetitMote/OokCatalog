from flask import Flask


def create_app(test_config=None):
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
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_envvar('OOKCATALOG_SETTINGS')
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # Activate some data functions
    from . import db

    db.init_app(app)

    # Register ookcatalog consulting views
    from . import catalog

    app.register_blueprint(catalog.bp)

    return app
