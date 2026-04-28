"""SmartBook Pro — automated tests (basic CI suite)."""

import os
import sys
import unittest
import compileall

ROOT = os.path.dirname(os.path.abspath(__file__))


class CompileTests(unittest.TestCase):
    def test_all_python_files_compile(self):
        ok = compileall.compile_dir(ROOT, quiet=1, force=True)
        self.assertTrue(ok)


class ProjectLayoutTests(unittest.TestCase):
    def test_core_files_exist(self):
        for name in ('app.py', 'config.py', 'db.py', 'helpers.py',
                     'seed.py', 'requirements.txt'):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, name)))

    def test_core_folders_exist(self):
        for name in ('routes', 'templates', 'static', 'models', 'services'):
            self.assertTrue(os.path.isdir(os.path.join(ROOT, name)))


class RequirementsTests(unittest.TestCase):
    def test_requirements_lists_core_packages(self):
        with open(os.path.join(ROOT, 'requirements.txt'), encoding='utf-8') as f:
            text = f.read().lower()
        for pkg in ('flask', 'werkzeug', 'mysql-connector-python', 'pillow'):
            self.assertIn(pkg, text)


class PureModuleImportTests(unittest.TestCase):
    def test_decorators_imports(self):
        sys.path.insert(0, ROOT)
        import decorators  # noqa: F401

    def test_app_utils_imports(self):
        sys.path.insert(0, ROOT)
        import app_utils  # noqa: F401


if __name__ == '__main__':
    unittest.main(verbosity=2)
