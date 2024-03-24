# Installation

> [!Caution]
> Currently, there is no support for runnig OokCatalog behind a reverse proxy. Since it’s a very simple application, it
> might work, or it might need tweaking Flask parameters in the source code. Support for reverse proxies migth come
> later.

## Setting up the database

### Creating an access to the database

First, we create a user for ookcatalog.

```postgresql
CREATE USER ookcatalog WITH PASSWORD 'ookcatalog_pass';
```

Set the password to whichever pass you want. Then, we grant this user access to the same tables our users have access
to. There are 2 options :

- Grant it the same role as the normal users
- Or, if your users have writing access and you don’t want OokCatalog to have it, as it could be a threat to your
  data integrity, you can grant it usage and select on the same schemas and tables. But it’s longer.

My users have no writing access, so I can give it the same role :

```postgresql
GRANT grp_user_bdu TO ookcatalog;
```

### Setting up needed data

OokCatalog needs really few thing to work with : a custom enum type and a table.

We create a custom enum type holding all the months of the year:

```postgresql
CREATE TYPE ookcatalog_month AS ENUM (
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December'
    );
```

> [!TIP]
> You can translate month names in your language. No other change is needed, simply editing the request before creating
> the enum type will translate every use of these names. But do not change the order of the months, as a command relies
> on it.

We then create the table where the catalog will access some data (as of now, long descriptions of tables and months of
upadte).

```postgresql
CREATE TABLE public.ookcatalog
(
    table_schema     TEXT NOT NULL,
    table_name       TEXT NOT NULL,
    description_long TEXT,
    update_months    OOKCATALOG_MONTH[],
    PRIMARY KEY (table_schema, table_name)
);

ALTER TABLE public.ookcatalog
    OWNER TO ookcatalog;
```

That’s it for the database configuration!

## Deploying OokCatalog

### Create a python environment

Create a python virtual environment where you want to install OokCatalog. You can then use PyPi to download and install
the last
published version of the catalog inside the venv you juste creating by activating it using `source`.

```commandline
python -m venv /path/to/ookcatalog/environment/.venv
source  /path/to/ookcatalog/environment/.venv/bin/activate
pip install --upgrade ookcatalog
```

> [!NOTE]
> On Windows, or if you’re not using bash/zsh on Linux, the source command will
> change. [See python doc](https://docs.python.org/3/library/venv.html#how-venvs-work) for more information.

## Configure OokCatalog

Download [config_sample.py](../config_sample.py). Edit the file according to your situation and register it where you
want to keep it. When you launch OokCatalog, use the environment variable to point to your config file. If the
environment variable isn’t set, the app will crash.

```commandline
OOKCATALOG_SETTINGS='/absolute/path/to/config.py' server_run_command
```

You can also set the path to your config file as a relative path, but keep in mind that OokCatalog will look for it
based on the instance folder. That means that the root of the relative path will be based on your venv folder :

```commandline
.venv/var/ookcatalog-instance/
```

You can export / set the environment variable if desired, for example on Linux :

```commandline
export OOKCATALOG_SETTINGS='/absolute/path/to/config.py' server_run_command
```

I’ve tried on Windows 11 using the `set` command, which didn’t work (either because Windows, or because it needs
administrator rights but won’t tell you). You might need to set the environment variable through the graphical
interface.

## Launching OokCatalog

You’re going to need a WGSI server to actually run OokCatalog. You can install it within the virtual environment using
pip, for example:

```commandline
pip install --upgrade waitress
```

When launching the WSGI server, pass the OokCatalog app as a parameter. For example, full command with Waitress could
be :

```commandline
OOKCATALOGUE_SETTINGS='/var/www/ookcatalog/config.py' waitress-serve --call 'ookcatalog:create_app'
```

The environment variable is also needed to run command line requests.