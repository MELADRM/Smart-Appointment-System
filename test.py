"""SmartBook Pro — basic CI tests."""

import os
import unittest
import compileall

ROOT = os.path.dirname(os.path.abspath(__file__))


class CompileTests(unittest.TestCase):
    def test_all_python_files_compile(self):
        ok = compileall.compile_dir(ROOT, quiet=1, force=True)
        self.assertTrue(ok)


if __name__ == '__main__':
    unittest.main(verbosity=2)
