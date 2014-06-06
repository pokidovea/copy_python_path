# -*- coding: utf-8 -*-

import os

import sublime
import sublime_plugin


class CopyPythonPathCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        path_items = self.view.file_name().split('/')

        module = path_items.pop().split('.')[0]
        python_path_items = [module, ]

        while len(path_items) > 0:
            if '__init__.py' in os.listdir('/%s/' % '/'.join(path_items)):
                python_path_items.insert(0, path_items.pop())
            else:
                break

        caret_point = self.view.sel()[0].begin()

        if 'entity.name.type.class.python' in self.view.scope_name(caret_point):
            python_path_items.append(self.view.substr(self.view.word(caret_point)))

        if 'entity.name.function.python' in self.view.scope_name(caret_point):
            method_name = self.view.substr(self.view.word(caret_point))
            if self.view.indentation_level(caret_point) > 0:
                regions = self.view.find_by_selector('entity.name.type.class.python')
                possible_class_point = 0
                for region in regions:
                    if region.b < caret_point:
                        possible_class_point = region.a
                    else:
                        break

                class_name = self.view.substr(self.view.word(possible_class_point))

                python_path_items.append(class_name)

            python_path_items.append(method_name)

        python_path = '.'.join(python_path_items)
        sublime.set_clipboard(python_path)

        sublime.status_message('"%s" copied to clipboard' % python_path)

    def is_enabled(self):
        matcher = 'source.python'
        return self.view.match_selector(self.view.sel()[0].begin(), matcher)
