import ast
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


BLOCK_PRIORITY = {
    "entry": 0,
    "normal": 1,
    "loop_head": 2,
    "loop_body": 3,
    "try": 3,
    "then": 4,
    "else": 4,
    "condition": 5,
    "return": 6,
}


@dataclass
class BasicBlock:
    block_id: str
    block_type: str
    line_start: int
    line_end: int
    lines: List[int] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)
    source_snippet: str = ""


class CFGBuilder(ast.NodeVisitor):
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.blocks: Dict[str, BasicBlock] = {}
        self.line_to_block: Dict[int, str] = {}
        self._counter = 0

    def _new_block(self, block_type: str, line_start: int, line_end: int) -> str:
        bid = f"B{self._counter}"
        self._counter += 1
        snippet_lines = self.source_lines[line_start - 1:line_end]
        snippet = "\n".join(line.rstrip() for line in snippet_lines)
        self.blocks[bid] = BasicBlock(
            block_id=bid,
            block_type=block_type,
            line_start=line_start,
            line_end=line_end,
            source_snippet=snippet,
        )
        return bid

    def _register_lines(self, start: int, end: int, block_id: str) -> None:
        block_type = self.blocks[block_id].block_type
        for line_number in range(start, end + 1):
            existing = self.line_to_block.get(line_number)
            if existing is None:
                self.line_to_block[line_number] = block_id
                if line_number not in self.blocks[block_id].lines:
                    self.blocks[block_id].lines.append(line_number)
                continue

            existing_priority = BLOCK_PRIORITY.get(self.blocks[existing].block_type, 0)
            new_priority = BLOCK_PRIORITY.get(block_type, 0)
            if new_priority > existing_priority:
                self.line_to_block[line_number] = block_id
                if line_number not in self.blocks[block_id].lines:
                    self.blocks[block_id].lines.append(line_number)

    def _add_edge(self, from_id: str, to_id: str) -> None:
        if to_id not in self.blocks[from_id].successors:
            self.blocks[from_id].successors.append(to_id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        entry = self._new_block("entry", node.lineno, node.lineno)
        self._register_lines(node.lineno, node.lineno, entry)
        self._process_body(node.body, predecessor=entry)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _process_body(self, stmts: list, predecessor: str | None) -> str | None:
        current = predecessor
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                current = self._handle_if(stmt, current)
            elif isinstance(stmt, (ast.For, ast.While)):
                current = self._handle_loop(stmt, current)
            elif isinstance(stmt, ast.Return):
                bid = self._new_block("return", stmt.lineno, stmt.end_lineno)
                self._register_lines(stmt.lineno, stmt.end_lineno, bid)
                if current:
                    self._add_edge(current, bid)
                current = bid
            elif isinstance(stmt, ast.Try):
                current = self._handle_try(stmt, current)
            else:
                current = self._handle_normal(stmt, current)
        return current

    def _handle_normal(self, stmt: ast.stmt, predecessor: str | None) -> str:
        if predecessor and self.blocks[predecessor].block_type == "normal":
            bid = predecessor
            self.blocks[bid].line_end = stmt.end_lineno
            self._register_lines(stmt.lineno, stmt.end_lineno, bid)
            snippet_lines = self.source_lines[
                self.blocks[bid].line_start - 1:self.blocks[bid].line_end
            ]
            self.blocks[bid].source_snippet = "\n".join(
                line.rstrip() for line in snippet_lines
            )
        else:
            bid = self._new_block("normal", stmt.lineno, stmt.end_lineno)
            self._register_lines(stmt.lineno, stmt.end_lineno, bid)
            if predecessor:
                self._add_edge(predecessor, bid)
        return bid

    def _handle_if(self, node: ast.If, predecessor: str | None) -> str | None:
        condition = self._new_block("condition", node.lineno, node.lineno)
        self._register_lines(node.lineno, node.lineno, condition)
        if predecessor:
            self._add_edge(predecessor, condition)

        then_start = node.body[0].lineno
        then_end = node.body[-1].end_lineno
        then_block = self._new_block("then", then_start, then_end)
        self._register_lines(then_start, then_end, then_block)
        self._add_edge(condition, then_block)
        then_exit = self._process_body(node.body, then_block)

        if node.orelse:
            else_start = node.orelse[0].lineno
            else_end = node.orelse[-1].end_lineno
            else_block = self._new_block("else", else_start, else_end)
            self._register_lines(else_start, else_end, else_block)
            self._add_edge(condition, else_block)
            return self._process_body(node.orelse, else_block)

        return then_exit

    def _handle_loop(self, node: ast.For | ast.While, predecessor: str | None) -> str:
        head = self._new_block("loop_head", node.lineno, node.lineno)
        self._register_lines(node.lineno, node.lineno, head)
        if predecessor:
            self._add_edge(predecessor, head)

        body_start = node.body[0].lineno
        body_end = node.body[-1].end_lineno
        body = self._new_block("loop_body", body_start, body_end)
        self._register_lines(body_start, body_end, body)
        self._add_edge(head, body)

        body_exit = self._process_body(node.body, body)
        if body_exit:
            self._add_edge(body_exit, head)
        return head

    def _handle_try(self, node: ast.Try, predecessor: str | None) -> str | None:
        if not node.body:
            return predecessor
        try_start = node.body[0].lineno
        try_end = node.body[-1].end_lineno
        try_block = self._new_block("try", try_start, try_end)
        self._register_lines(try_start, try_end, try_block)
        if predecessor:
            self._add_edge(predecessor, try_block)
        return self._process_body(node.body, try_block)


def build_cfg(source_code: str) -> Tuple[Dict[int, str], Dict[str, BasicBlock]]:
    source_lines = source_code.splitlines()
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return {}, {}

    builder = CFGBuilder(source_lines)
    builder.visit(tree)
    return builder.line_to_block, builder.blocks


def format_cfg_for_prompt(blocks: Dict[str, BasicBlock]) -> str:
    if not blocks:
        return "(CFG parse failed; no basic blocks were generated.)"

    lines_out = []
    sorted_blocks = sorted(blocks.values(), key=lambda block: block.line_start)
    for block in sorted_blocks:
        source_lines = block.source_snippet.splitlines()
        first_line = source_lines[0] if source_lines else ""
        lines_out.append(
            f"[{block.block_id}] {block.block_type:<12} "
            f"line {block.line_start}-{block.line_end}:  {first_line}"
        )
        for rest_line in source_lines[1:]:
            lines_out.append(f"{'':>20}  {rest_line}")
    return "\n".join(lines_out)


def blocks_to_dict(blocks: Dict[str, BasicBlock]) -> dict:
    result = {}
    for bid, block in blocks.items():
        result[bid] = {
            "block_id": block.block_id,
            "block_type": block.block_type,
            "line_start": block.line_start,
            "line_end": block.line_end,
            "lines": block.lines,
            "successors": block.successors,
            "source_snippet": block.source_snippet,
        }
    return result


def blocks_from_dict(data: dict) -> Dict[str, BasicBlock]:
    return {bid: BasicBlock(**block_data) for bid, block_data in data.items()}


if __name__ == "__main__":
    test_code = """
def fun1(n):
    result = 0
    for i in range(n):
        if i % 2 == 0:
            result += i
        else:
            result -= 1
    return result
"""
    line_to_block, blocks = build_cfg(test_code)
    print(format_cfg_for_prompt(blocks))
    print("\nline to block:")
    for line_number in sorted(line_to_block):
        print(f"  line {line_number} -> {line_to_block[line_number]}")
