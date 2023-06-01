# TODO
* Done: Look at "this is too dumb" in comparison.py
* If there are more than N diffs, truncate the dst table and reload?
* Done, test: use a timestamp column to decide whether or not to update
* Only output required columns for update statements
* Break up inserts into groups (of 50? 100?)
* (it'll come to me)
* Does it matter that we sort everything like a string when there are numeric PK columns?
- it would be easy to parse the ints...
* Integration tests
* Test with local MySQL
* Done: Accept command line args, merge with settings
* Put settings in a file or read them from a file using command line arg
* Parse settings at end of create table
* Refactoring
  - Complexity issues
  - Get rid of "parser_toy"
* Use separate InsertRecord and UpdateRecord?
* Do we need backticks on column names?
* Linter errors
 - increase line length
* Implement stage -> prod
* Implement sync between 2 databases
* Support more flavors of insert statements
* Support other DML statements?
