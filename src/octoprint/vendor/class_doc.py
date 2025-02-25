# class-doc is licensed under MIT
# 
# Originally from <https://github.com/danields761/class-doc>,
# vendored for compatibility reasons

import inspect
import itertools
import string
import sys
import textwrap
import tokenize
from typing import Dict, List, Optional, Union, Iterator, Any

import more_itertools as mitertools

import ast

if sys.version_info >= (3, 8, 0):
    AST_CONSTANT_TYPE = ast.Constant
    AST_CONSTANT_VALUE = lambda x: x.value
else:  # Python 3.7
    AST_CONSTANT_TYPE = ast.Str
    AST_CONSTANT_VALUE = lambda x: x.s


def _test_advanced_ast_presence() -> bool:
    return len({'end_lineno', 'end_col_offset'} & set(ast.ClassDef._attributes)) > 0


UniversalAssign = Union[ast.Assign, ast.AnnAssign]


_WHITESPACES = set(string.whitespace)


class _ASTTools:
    """
    Defines set of routines for such `ast` implementations, where no information
    about node end position is tracked.
    """

    @classmethod
    def _tokens_peekable_iter(cls, lines: List[str]) -> mitertools.peekable:
        lines_iter = iter(lines)
        return mitertools.peekable(tokenize.generate_tokens(lambda: next(lines_iter)))

    @classmethod
    def _get_first_lineno(cls, node: ast.AST) -> int:
        if isinstance(node, ast.Expr) and isinstance(node, AST_CONSTANT_TYPE):
            return node.lineno - AST_CONSTANT_VALUE(node.value).count('\n')
        return node.lineno

    @classmethod
    def _take_until_node(
        cls, tokens: Iterator[tokenize.TokenInfo], node: ast.AST
    ) -> Iterator[tokenize.TokenInfo]:
        for tok in tokens:
            yield tok
            if (
                tok.start[0] >= cls._get_first_lineno(node)
                and tok.start[1] >= node.col_offset
            ):
                break

    @classmethod
    def count_neighbor_newlines(
        cls, lines: List[str], first: ast.AST, second: ast.AST
    ) -> int:
        """
        Count only logical newlines between two nodes, e.g. any node may consist of
        multiple lines, so you can't just take difference of `lineno` attribute, this
        value will be pointless

        :return: number of logical newlines (result will be 0 if second node is placed
            right after first)
        """
        tokens_iter = cls._tokens_peekable_iter(lines)
        mitertools.consume(cls._take_until_node(tokens_iter, first))
        return (cls._get_first_lineno(second) - cls._get_first_lineno(first)) - sum(
            1
            for tok in cls._take_until_node(tokens_iter, second)
            if tok.type == tokenize.NEWLINE
        )

    @classmethod
    def extract_definition_line_comment(
        cls, lines: List[str], node: UniversalAssign
    ) -> Optional[str]:
        def valid_comment_or_none(comment):
            if comment.startswith('#:'):
                return comment[2:].strip()
            return None

        # will fetch all tokens until closing bracket of appropriate type occurs
        #  recursively calls himself when new opening bracket detected
        matching_brackets = {'{': '}', '[': ']', '(': ')'}

        def consume_between_bracers(iterable, bracket_type: str):
            closing_bracket = matching_brackets[bracket_type]
            for op in iterable:
                if op.string == closing_bracket:
                    return
                if op.string in matching_brackets:
                    return consume_between_bracers(iterable, op.string)
            # should never occurs because this lines already parsed and validated
            raise ValueError(f'no closing bracket for bracket of type "{bracket_type}"')

        # find last node
        if node.value is None:
            if not isinstance(node, ast.AnnAssign) or node.annotation is None:
                return None
            last_node = node.annotation
        else:
            if (
                isinstance(node.value, ast.Tuple)
                and lines[node.value.lineno - 1][node.value.col_offset - 1] != '('
            ):
                last_node = node.value.elts[-1]
            else:
                last_node = node.value

        tokens_iter = cls._tokens_peekable_iter(lines)

        # skip tokens until first token of last node occurred
        tokens_iter.prepend(
            mitertools.last(cls._take_until_node(tokens_iter, last_node))
        )

        # skip all except newline (for \ escaped newlines NEWLINE token isn't emitted)
        #  and comment token itself
        for tok in tokens_iter:
            if tok.type in (tokenize.COMMENT, tokenize.NEWLINE):
                tokens_iter.prepend(tok)
                break
            if tok.type == tokenize.OP and tok.string in matching_brackets:
                consume_between_bracers(tokens_iter, tok.string)

        try:
            maybe_comment = next(tokens_iter)
        except StopIteration:
            return None

        if maybe_comment.type == tokenize.COMMENT:
            return valid_comment_or_none(maybe_comment.string)

        return None

    @classmethod
    def extract_prev_node_comments(
        cls, lines: List[str], node: UniversalAssign
    ) -> List[str]:
        leading_whitespaces = ''.join(
            itertools.takewhile(
                lambda char: char in _WHITESPACES, lines[node.lineno - 1]
            )
        )
        comment_line_start = leading_whitespaces + '#:'

        return list(
            line[len(comment_line_start) :].strip()
            for line in itertools.takewhile(
                lambda line: line.startswith(comment_line_start),
                reversed(lines[: node.lineno - 1]),
            )
        )[::-1]


class _ASTToolsExtendedAST:
    """
    Defines set of routines for advanced `ast` implementation.
    """

    extract_prev_node_comments = _ASTTools.extract_prev_node_comments

    @classmethod
    def count_neighbor_newlines(
        cls, lines: List[str], first: ast.AST, second: ast.AST
    ) -> int:
        return second.lineno - first.end_lineno - 1

    @classmethod
    def extract_definition_line_comment(
        cls, lines: List[str], node: UniversalAssign
    ) -> Optional[str]:
        end_lineno = node.end_lineno - 1
        end_col_offset = node.end_col_offset - 1

        node_line = lines[end_lineno]
        comment_marker_pos = node_line.find('#:', end_col_offset)
        if comment_marker_pos == -1:
            return None

        return node_line[comment_marker_pos + 2 :].strip()


_ast_tools = _ASTToolsExtendedAST if _test_advanced_ast_presence() else _ASTTools


def _get_assign_targets(node: UniversalAssign) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Tuple):
                yield from (el.id for el in target.elts)
            else:
                yield target.id
    else:
        yield node.target.id


def extract_node_comments(lines: List[str], node: UniversalAssign) -> List[str]:
    # firstly prioritize "after assignment comment"
    res = _ast_tools.extract_definition_line_comment(lines, node)
    if res is not None:
        return [res]

    # then try to extract "right before assignment" comments
    return _ast_tools.extract_prev_node_comments(lines, node)


def extract_all_nodes_comments(
    lines: List[str], cls_def: ast.ClassDef
) -> Dict[str, List[str]]:
    return {
        target: comments
        for node, comments in (
            (node, extract_node_comments(lines, node))
            for node in cls_def.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        )
        if len(comments) > 0
        for target in _get_assign_targets(node)
    }


def extract_all_attr_docstrings(
    lines: List[str], cls_def: ast.ClassDef
) -> Dict[str, List[str]]:
    return {
        target: comments
        for node, comments in (
            (node, inspect.cleandoc(AST_CONSTANT_VALUE(next_node.value)).split('\n'))
            for node, next_node in mitertools.windowed(cls_def.body, 2)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            if isinstance(next_node, ast.Expr) and (isinstance(next_node.value, AST_CONSTANT_TYPE))
            if _ast_tools.count_neighbor_newlines(lines, node, next_node) == 0
        )
        for target in _get_assign_targets(node)
    }


def extract_docs(lines: List[str], cls_def: ast.ClassDef) -> Dict[str, List[str]]:
    """
    Extract attrs docstring and '#:' comments from class definition for hist attributes.
    Nodes comments are preferred over attr docstrings.

    TODO: cover all priority nuances

    :param lines: must be those lines from which `cls_def` has been compiled
    :param cls_def: class definition
    :return: per attribute doc lines
    """
    return {
        **extract_all_attr_docstrings(lines, cls_def),
        **extract_all_nodes_comments(lines, cls_def),
    }


def extract_docs_from_cls_obj(cls: Any):
    """
    Extract docs from class object using :py:func:`extract_docs`.

    :param cls: :py:func:`inspect.getsourcelines` must return sources of class
        definition
    :return: same as :py:func:`extract_docs`
    """
    lines, _ = inspect.getsourcelines(cls)

    # dedent the text for a inner classes declarations
    text = textwrap.dedent(''.join(lines))
    lines = text.splitlines(keepends=True)

    tree = ast.parse(text).body[0]
    if not isinstance(tree, ast.ClassDef):
        raise TypeError(f'Expecting "{ast.ClassDef.__name__}", but "{cls}" is received')

    return extract_docs(lines, tree)
