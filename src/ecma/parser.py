import ast
import astunparse
import esprima
from esprima import nodes
from functools import singledispatch


__ALL__ = ["parse_script"]


def parse_script(code):
    parser = _Parser()
    js_ast = esprima.parseScript(code, options={"tolerant": True, "loc": True}, delegate=parser)
    return js_ast.ast


# def parse_module(code):
#     parser = _Parser()
#     esprima.parseScript(code, delegate=parser)
#     return parser.result


# https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference
# https://tc39.github.io/ecma262/


class _Parser:
    def __call__(self, node, metadata):
        # esprima.Parser will call this as the delegate
        node.ast = self._parse(node)
        return node

    def _parse(self, node):
        try:
            parser = getattr(self, "_%s" % node.type)
        except AttributeError:
            self._unhandled(node)
        return parser(node)

    def _unhandled(self, node):
        raise NotImplementedError(
            "Node type not implemented: (line %d col %d)\n%r"
            % (node.loc.start.line, node.loc.start.column, node)
        )


if __name__ == "__main__":
    import sys
    code = sys.stdin.read()
    py_ast = parse_script(code)
    print(astunparse.unparse(py_ast))
