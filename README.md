# The Ook Catalog

![banner](documentation/static/ookcatalog_banner.png)

## Description

OokCatalog is a very simple data catalog made for PostgreSQL. It’s been programmed with the philosophy of being
maintained and/or modified by geomaticians / database administrator and not by web developers. Therefore, it makes the
simplest use of Python code and SQL requests, and is mostly powered by the SQL comments you have already defined, so it
can easily be understood.

Also, it’ll work directly on the database to be catalogued, but will create very few items on it. Only a user, one table
and an enum.

Based on Flask, Psycopg, and Bulma.

> [!CAUTION]
> This very little catalog has some really important limitations :
> - Reverse proxies might or might not work, since Flask doesn’t automatically adapt to it.
> - As for now, there isn’t any authentication. This project is intended for **intranet use** only, as a public use
    would exceed its performances.
> - Well, the website hasn’t been optimized, as it would heavily complexify the code. It should work for a small
    organization. I’ll add feedbacks here.
> - Textual search is fully re-processed at each search. That might have an impact on your database, and i’ll add
    feedbacks for this as well.

### Features

Features of this project are based on my work needs

- Displaying tables and views accessible by your users
- A page for each table, including:
    - A longer description
    - A full list of the columns and their comment
    - Months of the year when the data is updated
- Full text search through table and column names and descriptions
- Command-line interface for some administration of the catalog, including getting the list of table updates coming

These might come later :

- Correctly handle 404 when a table doesn’t exist
- Warning the administrators of the incoming updates
- A script to automatically add new tables in `public.ookcatalog`, and eventually to remove no-longer existing ones.
- Editing long description and months of update through a web based interface

### Sreenshots

![](documentation/static/ookcatalog_table.png)

![](documentation/static/ookcatalog_search.png)

## Installation

See [INSTALLATION](documentation/INSTALLATION.md) for detailed installation instructions.

## Usage

### Launching OokCatalog

See [INSTALLATION](documentation/INSTALLATION.md) for instructions on configuring and launching OokCatalog. Note that
the environment variable is also needed to use command-line commands.

### As a user

Going to the home page of OokCatalog will grant you with the full list of schemas and their corresponding tables of your
database.

You can clik on any table to go to a full page dedicated to it. You will be displayed a few lignes of description. Your
administrators can put any information they think is useful in there. Below, you’ll find a list of every field (or
column) in this table and a short description.

At the very bottom of the page is a list of the months when this table is updated along the year.

In the top right corner of the page, you’ll find a search button, next to a text entry. You can enter any text you want
for your search, and press enter or click the button to launch the research. OokCatalog will search in the table name,
table short and long description, and all the columns name and description. It’ll give more importance to table name,
and less to the columns. The search results are ordered by supposed pertinence, and limited to 20 results.

### As an administrator

You can modify the long description and update months in your new table `public.ookcatalog`. To add your existing tables
to it, see the next section and the command-line interface. You can also manually add the tables you want to describe,
for example if you don’t have access to the server command-line, by correctly entering `table_schema` and `table_name`
so it matches existing tables.

To enter update_months, you need to use the textual array syntax, for example: `'{Janvier, Mars, Septembre}'`. You need
to single quote the whole array and not individual months. Be wary that this is case-sensitive (`Janvier != janvier`).

### Command-line interface

OokCatalog packs a command-line interface for useful commands. Running `ookcatalog` without any argument will display a
list of the available commands.

> [!IMPORTANT]
> Launching OokCatalog commands still needs the setting environment variable to be set. We will omit it from the
> commands, like if it was exported as a permanent environment variable.
> See [INSTALLATION](documentation/INSTALLATION.md)
> for more details.

```commandline
ookcatalog tables-missing-comments
```

This command displays the list of all tables where description isn’t complete. It looks for table comment, column
comments, and for OokCatalog specific descriptions (in `public.catalog`), so long description and update months.

You can set up a cron task that would regularly check for missing descriptions and email you for details, or simply
lanch the command when needed.

```commandline
ookcatalog tables-updating
```

This command displays the list of tables that should update this month, based on what you inputted
in `public.ookcatalog.update_months`. It’ll also add:

- If launched between the 1st and 10th day of the month, the updates of the last month
- If launched between the 21st and the last day of the month, the updates coming the next month

I advise to set up a regular cron job that will warn you of updates (this being the goal of this command). You don’t
need to have it run everyday, but it could be on the first, 15th and 25th day of each month.

```commandline
ookcatalog update-tables-catalog
```

This command will update the `public.ookcatalog`, filling it with the tables that weren’t already inserted. It’ll
correctly input `table_schema` and `table_name` fields.

You should launch this command first after having installed OokCatalog, so you can start writing long descriptions and
filling update months. After that, you only need to launch it after adding new tables to your database.