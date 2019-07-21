from .base import compare


def test_object_empty(capsys):
    compare(capsys, "console.log(JSON.stringify({}))")


def test_object_uniq_keys(capsys):
    compare(capsys, "console.log(JSON.stringify({'a': 1}))")


def test_object_dupe_keys(capsys):
    compare(capsys, "console.log(JSON.stringify({'a': 1, 'a': 2}))")


def test_object_ident_key(capsys):
    compare(capsys, "console.log(JSON.stringify({a: 1}))")


def test_object_value_key(capsys):
    compare(capsys, "a = 'b'; console.log(JSON.stringify({[a]: 1}))")


def test_object_value_key(capsys):
    compare(capsys, "a = 'b'; console.log(JSON.stringify({a}))")


def test_object_number_key(capsys):
    compare(capsys, "console.log(JSON.stringify({1: 2}))")
