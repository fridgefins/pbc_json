# json_scalar.py
import graphene
from graphql.language import ast

class JSONScalar(graphene.Scalar):
    """
    Custom scalar to handle arbitrary JSON objects.
    """
    @staticmethod
    def serialize(value):
        # When returning data to the client, simply return the Python object.
        return value

    @staticmethod
    def parse_literal(node):
        # This is used when the client sends a literal in the query.
        if isinstance(node, ast.ObjectValue):
            return {field.name.value: JSONScalar.parse_literal(field.value) for field in node.fields}
        elif isinstance(node, ast.ListValue):
            return [JSONScalar.parse_literal(item) for item in node.values]
        elif isinstance(node, ast.StringValue):
            return node.value
        elif isinstance(node, ast.IntValue):
            return int(node.value)
        elif isinstance(node, ast.FloatValue):
            return float(node.value)
        elif isinstance(node, ast.BooleanValue):
            return node.value
        return None

    @staticmethod
    def parse_value(value):
        # This is used when the client sends data as a variable.
        return value
