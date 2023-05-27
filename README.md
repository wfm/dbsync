# dbsync
Basic sync of data between tables in a MySQL database.

The current use case is to sync data between the prod and stage
databases in Wordpress sites hosted on Bluehost. The have a very
basic staging feature that copies the prod database to a set
of tables prefixed with staging_. When you deploy to prod, it
simply copies all the staging table to the corresponding prod
tables. That won't work for a variety of reasons. Hence this
program.
