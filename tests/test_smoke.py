import unittest
import sys
import io

class TestBONv14(unittest.TestCase):
    def setUp(self):
        # Utiliser une BD SQLite en mémoire pour isoler les tests
        from libs.database import BONDatabase, reset_database
        self.db = BONDatabase(":memory:")
        reset_database(self.db)
        
    def tearDown(self):
        from libs.database import reset_database
        self.db.close()
        reset_database(None)

    def test_cli_parser_v14(self):
        """Vérifie que le CLI v14 charge bien les commandes Pro."""
        from libs.cli_v14 import build_parser
        parser = build_parser()
        
        args = parser.parse_args(["status"])
        self.assertEqual(args.command, "status")
        
        args = parser.parse_args(["start", "--robots", "bot1"])
        self.assertEqual(args.command, "start")
        self.assertEqual(args.robots, ["bot1"])

if __name__ == '__main__':
    unittest.main()
