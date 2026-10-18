"""Tests for the editor-independent part of the plugin.

Run from the repository root: python3 -m unittest discover tests
"""

import os
import sys
import tempfile
import textwrap
import types
import unittest

# The plugin imports Sublime Text API modules, which only exist inside the
# editor. The tested functions don't use them.
sys.modules.setdefault('sublime', types.ModuleType('sublime'))
sublime_plugin = sys.modules.setdefault('sublime_plugin', types.ModuleType('sublime_plugin'))
sublime_plugin.TextCommand = getattr(sublime_plugin, 'TextCommand', object)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copy_python_path import get_module_path, get_object_path  # noqa: E402

CARET = '|'


def object_path(source):
    """Call get_object_path for source where `|` marks the caret."""
    source = textwrap.dedent(source)
    offset = source.index(CARET)
    text = source[:offset] + source[offset + 1:]
    row = text.count('\n', 0, offset)
    col = offset - (text.rfind('\n', 0, offset) + 1)
    return '.'.join(get_object_path(text, row, col))


class ClassesAndFunctionsTest(unittest.TestCase):

    def test_class(self):
        self.assertEqual(object_path('class |A:\n    pass\n'), 'A')

    def test_caret_after_name(self):
        self.assertEqual(object_path('class A|:\n    pass\n'), 'A')

    def test_class_with_bases(self):
        self.assertEqual(object_path('class A|(Base, metaclass=Meta):\n    pass\n'), 'A')

    def test_function(self):
        self.assertEqual(object_path('def |f():\n    pass\n'), 'f')

    def test_async_function(self):
        self.assertEqual(object_path('async def f|():\n    pass\n'), 'f')

    def test_method(self):
        self.assertEqual(object_path('''
            class A:
                def f|(self):
                    pass
        '''), 'A.f')

    def test_decorated_method(self):
        self.assertEqual(object_path('''
            class A:
                @property
                def |f(self):
                    pass
        '''), 'A.f')

    def test_nested_class(self):
        self.assertEqual(object_path('''
            class A:
                class |B:
                    pass
        '''), 'A.B')

    def test_method_of_nested_class(self):
        self.assertEqual(object_path('''
            class A:
                class B:
                    def |f(self):
                        pass
        '''), 'A.B.f')

    def test_method_of_second_class(self):
        self.assertEqual(object_path('''
            class A:
                def f(self):
                    pass


            class B:
                def |g(self):
                    pass
        '''), 'B.g')

    def test_function_after_class(self):
        self.assertEqual(object_path('''
            class A:
                def f(self):
                    pass


            def |g():
                pass
        '''), 'g')

    def test_method_after_nested_class(self):
        self.assertEqual(object_path('''
            class A:
                class B:
                    def f(self):
                        pass

                def |g(self):
                    pass
        '''), 'A.g')

    def test_nested_function_is_not_addressable(self):
        self.assertEqual(object_path('''
            class A:
                pass


            def g():
                def |h():
                    pass
        '''), '')

    def test_class_inside_function_is_not_addressable(self):
        self.assertEqual(object_path('''
            def g():
                class |A:
                    pass
        '''), '')

    def test_one_line_class_does_not_open_block(self):
        self.assertEqual(object_path('''
            class A: pass
            if True:
                def |f():
                    pass
        '''), 'f')

    def test_method_inside_conditional_block(self):
        self.assertEqual(object_path('''
            class A:
                if True:
                    def |f(self):
                        pass
        '''), 'A.f')

    def test_type_alias(self):
        self.assertEqual(object_path('type |Alias = int\n'), 'Alias')


class AttributesTest(unittest.TestCase):

    def test_issue_example(self):
        source = '''
            class Bar(object):
                baz = "Lorem ipsum"

                def xyz(self):
                    pass
        '''
        self.assertEqual(object_path(source.replace('baz', '|baz')), 'Bar.baz')
        self.assertEqual(object_path(source.replace('xyz', 'xyz|')), 'Bar.xyz')

    def test_module_variable(self):
        self.assertEqual(object_path('|FOO = 1\n'), 'FOO')

    def test_annotated_attribute(self):
        self.assertEqual(object_path('''
            class A:
                x|: int = 1
        '''), 'A.x')

    def test_annotation_without_value(self):
        self.assertEqual(object_path('''
            class A:
                |x: int
        '''), 'A.x')

    def test_annotation_type_is_not_target(self):
        self.assertEqual(object_path('''
            class A:
                x: |int = 1
        '''), '')

    def test_augmented_assignment(self):
        self.assertEqual(object_path('|counter += 1\n'), 'counter')

    def test_chained_assignment(self):
        self.assertEqual(object_path('a = |b = 1\n'), 'b')

    def test_value_is_not_target(self):
        self.assertEqual(object_path('a = |b\n'), '')

    def test_tuple_unpacking(self):
        self.assertEqual(object_path('a, |b = 1, 2\n'), 'b')

    def test_nested_unpacking(self):
        self.assertEqual(object_path('a, (b, *|c) = 1, (2, 3)\n'), 'c')

    def test_subscript_is_not_target(self):
        self.assertEqual(object_path('x[|i] = 1\n'), '')
        self.assertEqual(object_path('|x[i] = 1\n'), '')

    def test_attribute_of_other_object_is_not_target(self):
        self.assertEqual(object_path('obj.|attr = 1\n'), '')
        self.assertEqual(object_path('|obj.attr = 1\n'), '')

    def test_keyword_argument_is_not_target(self):
        self.assertEqual(object_path('x = f(|y=1)\n'), '')

    def test_lambda_default_is_not_target(self):
        self.assertEqual(object_path('f = lambda |x=1: x\n'), '')

    def test_comparison_is_not_assignment(self):
        self.assertEqual(object_path('|x == 1\n'), '')

    def test_local_variable_is_not_addressable(self):
        self.assertEqual(object_path('''
            def f():
                |x = 1
        '''), '')

    def test_attribute_after_multiline_value(self):
        self.assertEqual(object_path('''
            class A:
                x = foo(
            1,
                )
                |y = 2
        '''), 'A.y')

    def test_attribute_after_docstring(self):
        self.assertEqual(object_path('''
            class A:
                """Docstring.

            Not indented.
                """
                # comment
            # comment
                |y = 2
        '''), 'A.y')


class InstanceAttributesTest(unittest.TestCase):

    def test_self_attribute(self):
        self.assertEqual(object_path('''
            class A:
                def __init__(self):
                    self.|x = 1
        '''), 'A.x')

    def test_cls_attribute(self):
        self.assertEqual(object_path('''
            class A:
                @classmethod
                def setup(cls):
                    cls.x| = 1
        '''), 'A.x')

    def test_annotated_self_attribute(self):
        self.assertEqual(object_path('''
            class A:
                def __init__(self):
                    self.|x: int = 1
        '''), 'A.x')

    def test_self_attribute_unpacking(self):
        self.assertEqual(object_path('''
            class A:
                def __init__(self):
                    self.x, self.|y = 1, 2
        '''), 'A.y')

    def test_self_attribute_in_conditional_block(self):
        self.assertEqual(object_path('''
            class A:
                def __init__(self):
                    if True:
                        self.|x = 1
        '''), 'A.x')

    def test_self_attribute_read_is_not_target(self):
        self.assertEqual(object_path('''
            class A:
                def f(self):
                    y = self.|x
        '''), '')

    def test_self_attribute_in_nested_function_is_not_addressable(self):
        self.assertEqual(object_path('''
            class A:
                def f(self):
                    def g():
                        self.|x = 1
        '''), '')

    def test_self_attribute_outside_method(self):
        self.assertEqual(object_path('''
            def f(self):
                self.|x = 1
        '''), '')


class OtherPositionsTest(unittest.TestCase):

    def test_caret_on_keyword(self):
        self.assertEqual(object_path('cla|ss A:\n    pass\n'), '')

    def test_caret_on_blank_line(self):
        self.assertEqual(object_path('x = 1\n|\ny = 2\n'), '')

    def test_caret_inside_body(self):
        self.assertEqual(object_path('''
            class A:
                def f(self):
                    return |g()
        '''), '')

    def test_caret_in_string(self):
        self.assertEqual(object_path('x = "a |b"\n'), '')

    def test_no_trailing_newline(self):
        self.assertEqual(object_path('class A:\n    |x = 1'), 'A.x')

    def test_syntax_error_after_caret(self):
        self.assertEqual(object_path('''
            class A:
                |x = 1

            def broken(:
                """unterminated
        '''), 'A.x')

    def test_unclosed_bracket_on_caret_line(self):
        self.assertEqual(object_path('class A:\n    |x = foo(\n'), 'A.x')


class ModulePathTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.package = os.path.join(self.root, 'pkg')
        os.makedirs(self.package)
        open(os.path.join(self.package, '__init__.py'), 'w').close()

    def test_module_in_package(self):
        self.assertEqual(get_module_path(os.path.join(self.package, 'mod.py')), ['pkg', 'mod'])

    def test_package_init(self):
        self.assertEqual(get_module_path(os.path.join(self.package, '__init__.py')), ['pkg'])


if __name__ == '__main__':
    unittest.main()
