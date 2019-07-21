from .base import compare


def test_number_add_int(capsys):
    compare(capsys, "console.log(1 + 2)")


def test_number_add_frac(capsys):
    compare(capsys, "console.log(1.5 + 2)")
