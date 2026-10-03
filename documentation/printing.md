# Printing

`printing/__init__.py` — console output helpers shared by every `print_*` function.

## `print_table`
```python
def print_table(headers: List[str], rows: List[List[str]], *, first_right_aligned_column: int, separators_after: Sequence[int] = ()) -> None
```
Prints a boxed table sized to its contents.
- `headers`, `rows` — cell text; every row has one string per header.
- `first_right_aligned_column` — columns from this index on are right-aligned (numbers); earlier ones left-aligned. Use `len(headers)` to left-align everything.
- `separators_after` — row indices after which a separator line is drawn (to group rows); ignored after the last row.

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
