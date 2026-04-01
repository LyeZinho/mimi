from __future__ import annotations

from .base import BaseTool
import ast


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Avalia expressões aritméticas simples de forma segura."

    def _eval_node(self, node):
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = node.op
            if isinstance(op, ast.Add):
                return left + right
            if isinstance(op, ast.Sub):
                return left - right
            if isinstance(op, ast.Mult):
                return left * right
            if isinstance(op, ast.Div):
                return left / right
            if isinstance(op, ast.FloorDiv):
                return left // right
            if isinstance(op, ast.Mod):
                return left % right
            if isinstance(op, ast.Pow):
                return left ** right
            raise ValueError("Operador não suportado")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -self._eval_node(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +self._eval_node(node.operand)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Constante não numérica")
        # Compatibilidade com versões antigas do AST
        if isinstance(node, ast.Num):
            return node.n
        raise ValueError("Expressão inválida")

    async def execute(self, input_data: str) -> str:
        expr = (input_data or "").strip()
        if not expr:
            return "Por favor, forneça uma expressão aritmética."
        try:
            parsed = ast.parse(expr, mode="eval")
            result = self._eval_node(parsed)
            return str(result)
        except Exception as e:
            return f"Erro ao avaliar expressão: {e}"
