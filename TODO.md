# TODO
* Look at "this is too dumb" in comparison.py
* use a timestamp column to decide whether or not to update
* Only output required columns for update statements
* Break up inserts into groups (of 50? 100?)
* Does it matter that we sort everything like a string when there are numeric PK columns?
- it would be easy to parse the ints...
* Integration tests
* Test with local MySQL
* Accept command line args, merge with settings
* Put settings in a file
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

> 16 results - 6 files
> 
> dbsync/intermediate.py:
>   43  
>   44:     # TODO we added the auto_increment stuff to the modifiers field
>   45      def generate_sql(self) -> str:
> 
>   86          sql[-1:][0].rstrip(",")
>   87:         # TODO should get all this crap from the prod table definition
>   88          sql.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 \
> 
> dbsync/settings.py:
>   132      def obj(cls):
>   133:         # TODO read this from a file
>   134          global _global_config
> 
> dbsync/comparing/compare_insert.py:
>    29  
>    30:     # TODO do we need backticks on the column names?
>    31      def _generate_insert(self) -> List[str]:
> 
>    38          sql.append(f"-- Inserting {l} {r}:")
>    39:         # TODO blows up here
>    40          # dst_cols = [list(a.keys()) for a in self.additions[0]]
> 
>   139                  # don't want to do anything
>   140:                 # TODO just update the columns that are different
>   141:                 # TODO use a timestamp column to decide whether or not to update
>   142:                 # TODO use separate InsertRecord and UpdateRecord?
>   143                  update.append(InsertRecord(src_item.key, None, src_item.key_vals, src_item.update_vals))
> 
> dbsync/comparing/comparison.py:
>   36      def _sanity_check(self, pair: tuple) -> None:
>   37:         # TODO throw an exception if the columns are different
>   38          pass
> 
>   59              self.table_seen[table.name] = True
>   60:             # TODO use src_prefix (would need to remove it here)
>   61              dst_name = dst_prefix + table.name
> 
>   66                  dst_inserts = self.repo.get_inserts(dst_name)
>   67:                 # TODO this is too dumb.
>   68                  self._pad_inserts(src_inserts, dst_inserts)
> 
>   85  
>   86:                 self._write("-- TODO disable pk constraints and auto_increment")
>   87                  for p in pairs:
> 
>   92                      self._write(sql)
>   93:                 self._write("-- TODO enable pk constraints and auto_increment")
>   94  
> 
> dbsync/comparing/unpacked_insert.py:
>    85          #
>    86:         # TODO re sorting
>    87          # The sort will use the collating sequence for strings
> 
>   130  
>   131:     # TODO maybe use __iter__ ????
>   132      def values_gen(self) -> Iterator[InsertRecord]:
> 
> dbsync/parsing/insert_statement.py:
>   75          if isinstance(t, sql.Values):
>   76:             # TODO was having trouble with this:
>   77              # ["staging_NhU_wps_hit", "`staging_NhU_wps_hit`"]:
> 