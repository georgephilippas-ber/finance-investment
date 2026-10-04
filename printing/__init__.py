from typing import List, Optional, Sequence

__all__ = ["print_grouped_table", "print_row_count", "print_section", "print_subsection", "print_table"]


def print_table(
        headers: List[str],
        rows: List[List[str]],
        *,
        first_right_aligned_column: int,
        separators_after: Sequence[int] = (),
        title: Optional[str] = None,
) -> None:
    widths_: List[int] = [
        max(len(header_), *(len(row_[column_]) for row_ in rows))
        for column_, header_ in enumerate(headers)
    ] if rows else [len(header_) for header_ in headers]
    inner_ = sum(width_ + 3 for width_ in widths_) - 3
    if title is not None and len(title) > inner_:
        widths_[-1] += len(title) - inner_
        inner_ = len(title)
    border_ = "+" + "+".join("-" * (width_ + 2) for width_ in widths_) + "+"

    if title is not None:
        print("+" + "-" * (inner_ + 2) + "+")
        print("| " + title.center(inner_) + " |")
    print(border_)
    print("| " + " | ".join(header_.ljust(width_) for header_, width_ in zip(headers, widths_)) + " |")
    print(border_)
    for index_, row_ in enumerate(rows):
        print("| " + " | ".join(
            value_.rjust(widths_[column_]) if column_ >= first_right_aligned_column else value_.ljust(widths_[column_])
            for column_, value_ in enumerate(row_)
        ) + " |")
        if index_ in separators_after and index_ != len(rows) - 1:
            print(border_)
    print(border_)


def print_grouped_table(headers: List[str], groups: List[List[List[str]]], *, title: Optional[str] = None) -> None:
    rows_ = [row_ for group_ in groups for row_ in group_]
    ends_, end_ = [], -1
    for group_ in groups:
        end_ += len(group_)
        ends_.append(end_)
    print_table(headers, rows_, first_right_aligned_column=1, separators_after=ends_, title=title)


def print_row_count(count: int, detail: Optional[str] = None) -> None:
    print(f"({count} {'row' if count == 1 else 'rows'}{f', {detail}' if detail else ''})")


def print_section(title: str) -> None:
    print(f"\n=== {title.upper()} ===")


def _capitalize(word: str) -> str:
    for index_, character_ in enumerate(word):
        if character_.isalpha():
            return word[:index_] + character_.upper() + word[index_ + 1:]
    return word


def print_subsection(title: str) -> None:
    print(f"\n====== {' '.join(_capitalize(word_) for word_ in title.split(' '))} ======")
