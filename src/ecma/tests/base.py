import subprocess

from ..parser import parse_script


def run_js(script):
    return subprocess.run(
        "node", input=script.encode("utf8"), check=True, stdout=subprocess.PIPE
    ).stdout


def compare(capsys, script):
    expected_output = run_js(script).decode("utf-8")
    output = parse_script(script)
    code = compile(output, "<js>", "exec")
    capsys.readouterr()
    exec(code, {}, {})
    captured = capsys.readouterr()
    assert captured.out == expected_output
