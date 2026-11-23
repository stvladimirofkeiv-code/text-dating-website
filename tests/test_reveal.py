from app.reveal import can_request_reveal, photos_unlocked


def test_needs_both_consent():
    assert not photos_unlocked(5, 5, True, False, 5)
    assert not photos_unlocked(5, 5, False, True, 5)
    assert photos_unlocked(5, 5, True, True, 5)


def test_needs_enough_messages_from_each():
    assert not photos_unlocked(10, 4, True, True, 5)
    assert not photos_unlocked(4, 10, True, True, 5)


def test_can_request_reveal():
    assert can_request_reveal(5, 5, 5)
    assert not can_request_reveal(5, 0, 5)
