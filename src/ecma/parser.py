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
    Number = ast.Name(id="Number", ctx=ast.Load())
    String = ast.Name(id="String", ctx=ast.Load())
    typeof = ast.Name(id="typeof", ctx=ast.Load())
    strictly_equal = ast.Name(id="strictly_equal", ctx=ast.Load())

    def __call__(self, node, metadata):
        # esprima.Parser will call this as the delegate
        node.ast = self._parse(node)
        return node

    def _parse(self, node):
        try:
            parser = getattr(self, "_%s" % node.type)
        except AttributeError:
            pass
        else:
            py_ast = parser(node)
            if py_ast is not None:
                print("OLD")
                print(node)
                print("")
                print("NEW")
                print(astunparse.unparse(py_ast))
                return py_ast

        raise NotImplementedError(
            "Node type not implemented: (line %d col %d)\n%r"
            % (node.loc.start.line, node.loc.start.column, node)
        )

    def _Literal(self, node):
        if isinstance(node.value, float):
            return ast.Call(func=self.Number, args=[ast.Num(n=node.value)], keywords=[])
        if isinstance(node.value, str):
            return ast.Call(func=self.String, args=[ast.Str(s=node.value)], keywords=[])

    def _ExpressionStatement(self, node):
        return self._parse(node.expression)

    def _Identifier(self, node):
        return ast.Name(id=node.name.replace("$", "_dollar_"), ctx=ast.Load())

    UNARY_OPERATOR = {"!": ast.Not()}

    def _UnaryExpression(self, node):
        if node.operator == "typeof":
            return ast.Call(func=self.typeof, args=[node.argument.ast], keywords=[])
        try:
            op_ast = self.UNARY_OPERATOR[node.operator]
        except KeyError:
            pass
        else:
            return ast.UnaryOp(op=op_ast, operand=node.argument.ast)

    BINARY_OPERATORS = {"+": ast.Add(), "-": ast.Sub(), "*": ast.Mult(), "/": ast.Div()}

    COMPARE_OPERATORS = {
        "==": ast.Eq(),
        "<": ast.Lt(),
        ">": ast.Gt(),
        "<=": ast.LtE(),
        ">=": ast.GtE(),
        "!=": ast.NotEq(),
    }

    def _BinaryExpression(self, node):
        # strictly_equal
        if node.operator in ("===", "!=="):
            py = ast.Call(
                func=self.strictly_equal, args=[node.left.ast, node.right.ast], keywords=[]
            )
            if node.operator[0] == "!":
                py = ast.UnaryOp(op=ast.Not(), operand=py)
            return py

        # binary ops
        try:
            op_ast = self.BINARY_OPERATORS[node.operator]
        except KeyError:
            pass
        else:
            return ast.BinOp(left=node.left.ast, op=op, right=node.right.ast)

        # compare
        try:
            op_ast = self.COMPARE_OPERATORS[node.operator]
        except KeyError:
            pass
        else:
            return ast.Compare(left=node.left.ast, ops=[op], comparators=[node.right.ast])

    def _MemberExpression(self, node):
        if node.computed:
            return ast.Subscript(
                value=node.object.ast,
                slice=ast.Index(value=node.property.ast, ctx=ast.Load()),
                ctx=ast.Load(),
            )
        if node.property.type == "Identifier":
            return ast.Attribute(value=node.object.ast, attr=node.property.name, ctx=ast.Load())

    BOOLEAN_OPERATORS = {"&&": ast.And(), "||": ast.Or()}

    def _LogicalExpression(self, node):
        try:
            op_ast = self.BOOLEAN_OPERATORS[node.operator]
        except KeyError:
            pass
        else:
            return ast.BoolOp(op=op_ast, values=[node.left.ast, node.right.ast])

    def _ReturnStatement(self, node):
        return ast.Return(value=node.argument.ast)

    def _BlockStatement(self, node):
        return [n.ast for n in node.body]


if __name__ == "__main__":
    import sys
    code = sys.stdin.read()
    py_ast = parse_script(code)
    print(astunparse.unparse(py_ast))
