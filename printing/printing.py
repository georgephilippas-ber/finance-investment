from typing import List, Sequence

__all__ = ["print_section", "print_subsection", "print_table"]


def print_table(
        headers: List[str],
        rows: List[List[str]],
        *,
        first_right_aligned_column: int,
        separators_after: Sequence[int] = (),
) -> None:
    widths_: List[int] = [
        max(len(header_), *(len(row_[column_]) for row_ in rows))
        for column_, header_ in enumerate(headers)
    ] if rows else [len(header_) for header_ in headers]
    border_ = "+" + "+".join("-" * (width_ + 2) for width_ in widths_) + "+"

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


def print_section(title: str) -> None:
    print(f"\n=== {title.upper()} ===")


def _capitalize(word: str) -> str:
    for index_, character_ in enumerate(word):
        if character_.isalpha():
            return word[:index_] + character_.upper() + word[index_ + 1:]
    return word


def print_subsection(title: str) -> None:
    print(f"\n====== {' '.join(_capitalize(word_) for word_ in title.split(' '))} ======")
