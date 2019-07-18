import ast
import astunparse
import esprima
from esprima import nodes


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
# https://github.com/tc39/test262


class _Parser:
    Number = ast.Name(id="Number", ctx=ast.Load())
    String = ast.Name(id="String", ctx=ast.Load())
    Object = ast.Name(id="Object", ctx=ast.Load())
    typeof = ast.Name(id="typeof", ctx=ast.Load())
    strictly_equal = ast.Name(id="strictly_equal", ctx=ast.Load())
    undefined = ast.Name(id="undefined", ctx=ast.Load())
    _Exception = ast.Name(id="_Exception", ctx=ast.Load())

    def __init__(self):
        self.unique_id = 1

    def __call__(self, node, metadata):
        # esprima.Parser will call this as the delegate
        self._parse(node)
        return node

    def _parse(self, node):
        try:
            parser = getattr(self, "_%s" % node.type)
        except AttributeError:
            pass
        else:
            parser(node)
            if node.stmts is not None:
                # print("OLD")
                # print(node)
                # print("")
                # print("NEW")
                # for stmt in self._node_stmts(node):
                #     print(astunparse.unparse(stmt))
                return

        raise NotImplementedError(
            "Node type not implemented: (line %d col %d)\n%r"
            % (node.loc.start.line, node.loc.start.column, node)
        )

    def _make_unique_name(self, base_name=""):
        base_name += "_%d" % self.unique_id
        self.unique_id += 1
        return base_name

    def _node_stmts(self, node):
        stmts = []
        if not node:
            return stmts
        stmts += node.stmts
        if node.expr:
            stmts.append(node.expr)
        return stmts

    # expressions

    def _Literal(self, node):
        node.stmts = []
        if isinstance(node.value, (float, int)):
            node.expr = ast.Call(func=self.Number, args=[ast.Num(n=node.value)], keywords=[])
        elif isinstance(node.value, str):
            node.expr = ast.Call(func=self.String, args=[ast.Str(s=node.value)], keywords=[])

    def _Identifier(self, node):
        node.stmts = []
        node.expr = ast.Name(id=node.name.replace("$", "_dollar_"), ctx=ast.Load())

    UNARY_OPERATOR = {"!": ast.Not()}

    def _UnaryExpression(self, node):
        node.stmts = node.argument.stmts

        if node.operator == "typeof":
            node.expr = ast.Call(func=self.typeof, args=[node.argument.expr], keywords=[])
            return

        try:
            op_ast = self.UNARY_OPERATOR[node.operator]
        except KeyError:
            pass
        else:
            node.expr = ast.UnaryOp(op=op_ast, operand=node.argument.expr)

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
        node.stmts = node.left.stmts + node.right.stmts

        # strictly_equal
        if node.operator in ("===", "!=="):
            node.expr = ast.Call(
                func=self.strictly_equal, args=[node.left.expr, node.right.expr], keywords=[]
            )
            if node.operator[0] == "!":
                node.expr = ast.UnaryOp(op=ast.Not(), operand=node.expr)
            return

        # binary ops
        try:
            op_ast = self.BINARY_OPERATORS[node.operator]
        except KeyError:
            pass
        else:
            node.expr = ast.BinOp(left=node.left.expr, op=op_ast, right=node.right.expr)
            return

        # compare
        try:
            op_ast = self.COMPARE_OPERATORS[node.operator]
        except KeyError:
            pass
        else:
            node.expr = ast.Compare(
                left=node.left.expr, ops=[op_ast], comparators=[node.right.expr]
            )
            return

    def _MemberExpression(self, node):
        node.stmts = node.object.stmts + node.property.stmts
        if node.computed:
            node.expr = ast.Subscript(
                value=node.object.expr,
                slice=ast.Index(value=node.property.expr, ctx=ast.Load()),
                ctx=ast.Load(),
            )
        elif node.property.type == "Identifier":
            node.expr = ast.Attribute(
                value=node.object.expr, attr=node.property.name, ctx=ast.Load()
            )

    BOOLEAN_OPERATORS = {"&&": ast.And(), "||": ast.Or()}

    def _LogicalExpression(self, node):
        node.stmts = node.left.stmts + node.right.stmts
        try:
            op_ast = self.BOOLEAN_OPERATORS[node.operator]
        except KeyError:
            pass
        else:
            node.expr = ast.BoolOp(op=op_ast, values=[node.left.expr, node.right.expr])

    def _FunctionExpression(self, node):
        if node.id:
            assert isinstance(node.id, nodes.Identifier)
            name = node.id.name
        else:
            name = self._make_unique_name()
            node.id = nodes.Identifier(name)
        self._FunctionDeclaration(node)  # sets node.stmts
        node.expr = ast.Name(id=name, ctx=ast.Load())

    def _ConditionalExpression(self, node):
        node.stmts = node.test.stmts + node.consequent.stmts + node.alternate.stmts
        node.expr = ast.IfExp(
            test=node.test.expr, body=node.consequent.expr, orelse=node.alternate.expr
        )

    def _CallExpression(self, node):
        node.stmts = node.callee.stmts
        for arg in node.arguments:
            node.stmts += arg.stmts
        node.expr = ast.Call(
            func=node.callee.expr, args=[arg.expr for arg in node.arguments], keywords=[]
        )

    def _VariableDeclarator(self, node):
        """
            b = 1
        """
        assert isinstance(node.id, nodes.Identifier)
        node.expr = ast.Name(id=node.id.name, ctx=ast.Load())

        """
            {init.stmts}
            {id.name} = {init.expr}
        """
        if node.init:
            node.stmts = node.init.stmts + [ast.Assign(targets=[node.expr], value=node.init.expr)]
            return

        """
            try:
                {id.name}
            except NameError:
                {id.name} = undefined
        """
        node.stmts = [
            ast.Try(
                body=[ast.Expr(value=node.expr)],
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id="NameError", ctx=ast.Load()),
                        name=None,
                        body=[ast.Assign(targets=[node.expr], value=self.undefined)],
                    )
                ],
                orelse=[],
                finalbody=[],
            )
        ]

    def _NewExpression(self, node):
        node.stmts = node.callee.stmts + sum((arg.stmts for arg in node.arguments), [])
        node.expr = ast.Call(
            func=ast.Attribute(value=node.callee.expr, attr="new", ctx=ast.Load()),
            args=[arg.expr for arg in node.arguments],
            keywords=[],
        )

    def _AssignmentExpression(self, node):
        node.stmts = (
            node.left.stmts
            + node.right.stmts
            + [ast.Assign(targets=[node.left.expr], value=node.right.expr)]
        )
        node.expr = node.left.expr

    def _SequenceExpression(self, node):
        """
            (a.b = 2, a)
        """
        node.stmts = sum((e.stmts for e in node.expressions), [])
        """
            {e.stmts for e in expressions}
            ({e.expr for e in expressions})[-1]
        """
        node.expr = ast.Subscript(
            value=ast.Tuple(elts=[e.expr for e in node.expressions], ctx=ast.Load()),
            slice=ast.Index(value=ast.UnaryOp(op=ast.USub(), operand=ast.Num(n=1))),
            ctx=ast.Load(),
        )

    def _ObjectExpression(self, node):
        node.stmts = sum((p.stmts for p in node.properties), [])
        node.expr = ast.Call(func=self.Object, args=[], keywords=[p.expr for p in node.properties])

    def _Property(self, node):
        node.stmts = node.key.stmts + node.value.stmts
        # technically not an expr but goes into _ObjectExpression
        node.expr = ast.keyword(
            arg=None, value=ast.Dict(keys=[node.key.expr], values=[node.value.expr])
        )

    # statements

    def _ExpressionStatement(self, node):
        """
            {expression};
        """
        node.expr = None
        node.stmts = node.expression.stmts + [node.expression.expr]

    def _ReturnStatement(self, node):
        """
            return {argument};
        """
        node.expr = None
        node.stmts = node.argument.stmts + [ast.Return(value=node.argument.expr)]

    def _BlockStatement(self, node):
        """
            {
                {body}
            }
        """
        node.expr = None
        node.stmts = []
        for n in node.body:
            node.stmts += n.stmts
            if n.expr:
                node.stmts.append(n.expr)

    def _FunctionDeclaration(self, node):
        """
            function {id.name}({params})
                {body}
        """
        assert isinstance(node.id, nodes.Identifier)
        node.expr = None
        """
            def {id.name}({params}):
                {body}
        """
        node.stmts = [
            ast.FunctionDef(
                name=node.id.name,
                args=ast.arguments(
                    args=[ast.arg(arg=param.name, annotation=None) for param in node.params],
                    defaults=[],
                    vararg=None,
                    kwarg=None,
                ),
                decorator_list=[],
                body=self._node_stmts(node.body),
            )
        ]

    def _VariableDeclaration(self, node):
        """
            var a = 1, b, c = 2;
        """
        node.expr = None
        # we are ignoring VariableDeclarator.expression because it's only name
        node.stmts = sum((n.stmts for n in node.declarations), [])

    def _IfStatement(self, node):
        node.expr = None
        node.stmts = node.test.stmts + [
            ast.If(
                test=node.test.expr,
                body=self._node_stmts(node.consequent),
                orelse=self._node_stmts(node.alternate),
            )
        ]

    def _ThrowStatement(self, node):
        node.expr = None
        node.stmts = node.argument.stmts + [
            ast.Raise(
                exc=ast.Call(func=self._Exception, args=[node.argument.expr], keywords=[]),
                cause=None,
            )
        ]


if __name__ == "__main__":
    import sys

    code = sys.stdin.read()
    py_ast = parse_script(code)
    print(astunparse.unparse(py_ast))
