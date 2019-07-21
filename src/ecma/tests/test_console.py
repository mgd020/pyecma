from .base import compare


def test_console_log(capsys):
    compare(capsys, "console.log('hi')")


def test_console_log_objects(capsys):
    compare(capsys, "console.log([1], {a:2}, '3')")
