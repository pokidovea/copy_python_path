CopyPythonPath
================
A Sublime Text plugin.

Puts python path of the currently selected python module, class, function, method or attribute to the clipboard.

Install
=======

The easiest way to install this is with [Package Control](http://wbond.net/sublime_packages/package_control).

Usage
=====

To copy the python import path of the module select an option from the context menu of side bar or tab.
To copy the path of the python class or method put caret on it and press <kbd>Ctrl+Shift+K</kbd> or `right-click` and select an option from the context menu.

The caret should be on the name in its definition:

```python
# pkg/mod.py
TIMEOUT = 10                 # pkg.mod.TIMEOUT


class Bar:                   # pkg.mod.Bar
    baz: str = "Lorem ipsum"  # pkg.mod.Bar.baz

    class Meta:              # pkg.mod.Bar.Meta
        ordering = "id"      # pkg.mod.Bar.Meta.ordering

    def __init__(self):      # pkg.mod.Bar.__init__
        self.qux = 1         # pkg.mod.Bar.qux


def xyz():                   # pkg.mod.xyz
    local = 1                # pkg.mod (not reachable from the module)
```

In any other position the path of the module is copied.
