"""Pure logic for when photos may be unlocked. No DB/web imports so it is easy to test."""


def photos_unlocked(
    low_sent: int,
    high_sent: int,
    low_wants: bool,
    high_wants: bool,
    min_each: int,
) -> bool:
    """Photos unlock only when BOTH people have written enough AND BOTH opt in."""
    return (
        low_sent >= min_each
        and high_sent >= min_each
        and low_wants
        and high_wants
    )


def can_request_reveal(sent_by_me: int, sent_by_them: int, min_each: int) -> bool:
    return sent_by_me >= min_each and sent_by_them >= min_each
