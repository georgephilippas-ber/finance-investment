# Printing

`printing/__init__.py` — console output helpers shared by every `print_*` function.

## `print_table`
```python
def print_table(headers: List[str], rows: List[List[str]], *, first_right_aligned_column: int, separators_after: Sequence[int] = (), title: Optional[str] = None) -> None
```
Prints a boxed table sized to its contents.
- `headers`, `rows` — cell text; every row has one string per header.
- `first_right_aligned_column` — columns from this index on are right-aligned (numbers); earlier ones left-aligned. Use `len(headers)` to left-align everything.
- `separators_after` — row indices after which a separator line is drawn (to group rows); ignored after the last row.
- `title` — optional title printed as a framed, centered top row spanning the table; the last column is widened
  if the title is longer than the table.

## `print_grouped_table`
```python
def print_grouped_table(headers: List[str], groups: List[List[List[str]]], *, title: Optional[str] = None) -> None
```
A two-column field/value table given as groups of rows: a separator is drawn after each group, so separator positions
never need counting by hand. The value column is right-aligned. Used by the account summary and the bond sheet.

## `print_row_count`
```python
def print_row_count(count: int, detail: Optional[str] = None) -> None
```
Prints the footer under a table: `(1 row)`, `(21 rows)`, or with `detail` appended, `(5 rows, 3 with IBKR)`. Used by
every table that shows a row count.

## `print_section`
```python
def print_section(title: str) -> None
```
Prints a blank line and `=== TITLE ===` in upper case.

## `print_subsection`
```python
def print_subsection(title: str) -> None
```
Prints a blank line and `====== Title ======` in Proper Case: the first letter of each word is capitalised and the rest kept as written, so acronyms survive (`lookup by ISIN` → `Lookup By ISIN`).
