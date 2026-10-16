
import os
import ast
import operator

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


mcp = FastMCP(
    "Utility MCP Server",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "utility-mcp.urumi.svc.cluster.local:8002",
            "utility-mcp.urumi.svc.cluster.local",
            "localhost:8002",
            "127.0.0.1:8002",
        ],
    ),
)


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a basic arithmetic expression."""

    operations = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value

        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent is too large")

            result = operations[type(node.op)](left, right)

            if abs(result) > 1e100:
                raise ValueError("Result is too large")

            return result

        if isinstance(node, ast.UnaryOp) and type(node.op) in operations:
            return operations[type(node.op)](evaluate(node.operand))

        raise ValueError("Only basic arithmetic is allowed")

    try:
        tree = ast.parse(expression, mode="eval")
        return str(evaluate(tree))
    except Exception as exc:
        return f"Calculation error: {exc}"


@mcp.tool()
def convert_temperature(value: float, from_unit: str, to_unit: str) -> str:
    """Convert temperatures between Celsius, Fahrenheit, and Kelvin."""

    from_unit = from_unit.strip().lower()
    to_unit = to_unit.strip().lower()

    to_celsius = {
        "celsius": lambda x: x,
        "fahrenheit": lambda x: (x - 32) * 5 / 9,
        "kelvin": lambda x: x - 273.15,
    }

    from_celsius = {
        "celsius": lambda x: x,
        "fahrenheit": lambda x: x * 9 / 5 + 32,
        "kelvin": lambda x: x + 273.15,
    }

    if from_unit not in to_celsius or to_unit not in from_celsius:
        return "Unsupported unit. Use celsius, fahrenheit, or kelvin."

    if from_unit == "kelvin" and value < 0:
        return "Kelvin cannot be below zero."

    celsius = to_celsius[from_unit](value)

    if celsius < -273.15:
        return "Temperature cannot be below absolute zero."

    return (
        f"{value} {from_unit} = "
        f"{from_celsius[to_unit](celsius):.2f} {to_unit}"
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
