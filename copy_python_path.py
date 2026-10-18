# -*- coding: utf-8 -*-

import io
import keyword
import os
import tokenize

import sublime
import sublime_plugin


ASSIGNMENT_OPERATORS = {
    '=', '+=', '-=', '*=', '/=', '//=', '%=', '**=', '@=',
    '&=', '|=', '^=', '>>=', '<<=',
}
OPENING_BRACKETS = {'(', '[', '{'}
CLOSING_BRACKETS = {')', ']', '}'}
# Tokens that may directly precede or follow a name in an assignment target
# list, e.g. `a, (b, *c) = ...` or `a = b = ...`.
TARGET_PREFIXES = {None, ',', '(', '[', '*'} | ASSIGNMENT_OPERATORS
TARGET_SUFFIXES = {',', ')', ']'} | ASSIGNMENT_OPERATORS
LINE_BOUNDARY_TOKENS = {
    tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER,
}


def get_module_path(file_name):
    python_path_items = []
    head, tail = os.path.split(file_name)

    module = tail.rsplit('.', 1)[0]
    if module != '__init__':
        python_path_items.append(module)

    head, tail = os.path.split(head)

    while tail:
        if '__init__.py' in os.listdir(os.path.join(head, tail)):
            python_path_items.insert(0, tail)
        else:
            break

        head, tail = os.path.split(head)

    return python_path_items


def get_object_path(text, row, col):
    """Return names leading from the module to the object defined at the caret.

    `row` and `col` are zero-based, as returned by `View.rowcol()`.
    Supported objects are classes, functions, methods, module variables, class
    attributes and `self.x` / `cls.x` attributes assigned in methods.
    An empty list means that the caret is not on such a definition, or the
    object is not reachable from the module (e.g. a local variable).

    The source is tokenized instead of relying on syntax scopes: scopes differ
    between Python syntax definitions and don't mark assignment targets or
    class bodies.
    """
    position = (row + 1, col)
    blocks = []  # enclosing blocks: ('class' | 'def', name) or None for others
    pending_block = None  # header of the block opened by the next INDENT
    line = []  # tokens of the current logical line

    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type in (tokenize.NL, tokenize.COMMENT):
                continue

            if token.type in LINE_BOUNDARY_TOKENS and line:
                if line[0].start > position:
                    return []
                if line[-1].end >= position:
                    return _resolve_name(line, position, blocks)
                pending_block = _get_block_header(line)
                line = []

            if token.type == tokenize.INDENT:
                blocks.append(pending_block)
            elif token.type == tokenize.DEDENT:
                if blocks:
                    blocks.pop()
            elif token.type not in (tokenize.NEWLINE, tokenize.ENDMARKER):
                line.append(token)

            if token.type != tokenize.NEWLINE:
                pending_block = None
    except (tokenize.TokenError, SyntaxError):
        # Incomplete code, e.g. an unclosed bracket on the caret line.
        if line and line[0].start <= position <= line[-1].end:
            return _resolve_name(line, position, blocks)

    return []


def _get_block_header(line):
    start = 1 if line[0].string == 'async' else 0
    if (
        len(line) > start + 1
        and line[start].string in ('class', 'def')
        and line[start + 1].type == tokenize.NAME
    ):
        return line[start].string, line[start + 1].string
    return None


def _resolve_name(line, position, blocks):
    for index, token in enumerate(line):
        if token.type == tokenize.NAME and token.start <= position <= token.end:
            break
    else:
        return []

    name = line[index].string
    blocks = [block for block in blocks if block is not None]
    kinds = [kind for kind, _ in blocks]
    names = [block_name for _, block_name in blocks]

    if _is_definition_name(line, index) or _is_assignment_target(line, index, index):
        if 'def' in kinds:
            return []
        return names + [name]

    if _is_self_attribute_target(line, index):
        if len(kinds) >= 2 and kinds[-1] == 'def' and 'def' not in kinds[:-1]:
            return names[:-1] + [name]

    return []


def _is_definition_name(line, index):
    start = 1 if line[0].string == 'async' else 0
    if index == start + 1 and line[start].string in ('class', 'def'):
        return True

    # Type alias statement: `type Name = ...` or `type Name[T] = ...`.
    return (
        index == 1
        and line[0].string == 'type'
        and len(line) > 2
        and line[2].string in ('=', '[')
    )


def _is_self_attribute_target(line, index):
    return (
        index >= 2
        and line[index - 1].string == '.'
        and line[index - 2].string in ('self', 'cls')
        and _is_assignment_target(line, index - 2, index)
    )


def _is_assignment_target(line, first, last):
    """Check that tokens line[first:last + 1] form a single assignment target."""
    if keyword.iskeyword(line[0].string) or keyword.iskeyword(line[first].string):
        return False

    previous = line[first - 1].string if first > 0 else None
    following = line[last + 1].string if last + 1 < len(line) else None

    # Annotated assignment: `name: type` or `name: type = value`.
    if first == 0 and following == ':':
        return True

    if previous not in TARGET_PREFIXES or following not in TARGET_SUFFIXES:
        return False

    targets_end = None
    depth = 0
    for index, token in enumerate(line):
        if token.string == 'lambda':
            break
        if token.string in OPENING_BRACKETS:
            depth += 1
        elif token.string in CLOSING_BRACKETS:
            depth -= 1
        elif depth == 0 and token.string in ASSIGNMENT_OPERATORS:
            targets_end = index

    if targets_end is None or last >= targets_end:
        return False

    # Brackets around the target must group targets, not call or subscript.
    grouping = []
    for index in range(first):
        token = line[index].string
        if token in OPENING_BRACKETS:
            before = line[index - 1].string if index > 0 else None
            grouping.append(token != '{' and before in TARGET_PREFIXES)
        elif token in CLOSING_BRACKETS and grouping:
            grouping.pop()

    return all(grouping)


class CopyPythonPathCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        python_path_items = get_module_path(self.view.file_name())

        caret_point = self.view.sel()[0].begin()
        row, col = self.view.rowcol(caret_point)
        text = self.view.substr(sublime.Region(0, self.view.size()))
        python_path_items += get_object_path(text, row, col)

        python_path = '.'.join(python_path_items)
        sublime.set_clipboard(python_path)

        sublime.status_message('"%s" copied to clipboard' % python_path)

    def is_enabled(self):
        matcher = 'source.python'
        return self.view.match_selector(self.view.sel()[0].begin(), matcher)
