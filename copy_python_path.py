# -*- coding: utf-8 -*-

import os

import sublime
import sublime_plugin

# The class name scope differs between Python syntax definitions:
# newer ones (e.g. Sublime Text 4) use `entity.name.class.python`,
# older ones use `entity.name.type.class.python`.
CLASS_SELECTOR = 'entity.name.class.python, entity.name.type.class.python'
FUNCTION_SELECTOR = 'entity.name.function.python'


class CopyPythonPathCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        python_path_items = []
        head, tail = os.path.split(self.view.file_name())

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

        caret_point = self.view.sel()[0].begin()
        # Scopes are checked at the start of the word under the caret, because
        # the scope at the caret itself belongs to the character to its right
        # (e.g. `:` for `class A|:`).
        name_region = self.view.word(caret_point)
        name_point = name_region.a
        name = self.view.substr(name_region)

        if self.view.match_selector(name_point, CLASS_SELECTOR):
            python_path_items.append(name)

        if self.view.match_selector(name_point, FUNCTION_SELECTOR):
            method_name = name
            if self.view.indentation_level(caret_point) > 0:
                class_region = None
                for region in self.view.find_by_selector(CLASS_SELECTOR):
                    if region.b < caret_point:
                        class_region = region
                    else:
                        break

                if class_region is not None:
                    python_path_items.append(self.view.substr(class_region))

            python_path_items.append(method_name)

        python_path = '.'.join(python_path_items)
        sublime.set_clipboard(python_path)

        sublime.status_message('"%s" copied to clipboard' % python_path)

    def is_enabled(self):
        matcher = 'source.python'
        return self.view.match_selector(self.view.sel()[0].begin(), matcher)
