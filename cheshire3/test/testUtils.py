u"""Cheshire3 Utilities Unittests."""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from cheshire3.utils import SimpleBitfield


class SimpleBitfieldTestCase(unittest.TestCase):
    
    def test_init_int(self):
        "Test init with integers."
        for x in range(51, 0, 3):
            field = SimpleBitfield(x)
            self.assertEqual(field._d, x)
        
    def test_init_hex(self):
        "Test init with hexadecimal strings."
        field = SimpleBitfield('0x10')
        self.assertEqual(field._d, 16)
        for x in range(51, 0, 3):
            field = SimpleBitfield(hex(x))
            self.assertEqual(field._d, x)

    def test_init_bin(self):
        "Test init with binary strings"
        field = SimpleBitfield('101')
        self.assertEqual(field._d, 5)
        for x in range(51, 0, 3):
            field = SimpleBitfield(bin(x))
            self.assertEqual(field._d, x)

    def test_int(self):
        "Test coercion to integer."
        for x in range(51, 0, 3):
            field = SimpleBitfield(x)
            self.assertEqual(int(field), x)

    # Expected failure - under investigation
    @unittest.expectedFailure
    def test_len(self):
        "Test length."
        field = SimpleBitfield('101')
        self.assertEqual(len(field), 3)

    # Expected failure inherited from failure detected by test_len
    @unittest.expectedFailure
    def test_getitem(self):
        "Test getting individual items."
        field = SimpleBitfield(5)
        self.assertEqual(field[0], 1)
        self.assertEqual(field[1], 0)
        self.assertEqual(field[2], 1)
    
    def test_setitem(self):
        "Test setting individual items."
        field = SimpleBitfield('101')
        field[1] = 1
        self.assertEqual(field._d, int('111', 2))

    def test_union(self):
        "Test union of two SimpleBitfields."
        field = SimpleBitfield('110011')
        field.union(SimpleBitfield('001100'))
        self.assertEqual(field._d, int('111111', 2))
        field = SimpleBitfield('000011')
        field.union(SimpleBitfield('001100'))
        self.assertEqual(field._d, int('001111', 2))
        field = SimpleBitfield('010010')
        field.union(SimpleBitfield('011110'))
        self.assertEqual(field._d, int('011110', 2))

    def test_intersection(self):
        "Test intersection of two SimpleBitfields."
        field = SimpleBitfield('110011')
        field.intersection(SimpleBitfield('001100'))
        self.assertEqual(field._d, int('000000', 2))
        field = SimpleBitfield('110011')
        field.intersection(SimpleBitfield('001110'))
        self.assertEqual(field._d, int('000010', 2))
        field = SimpleBitfield('110011')
        field.intersection(SimpleBitfield('011100'))
        self.assertEqual(field._d, int('010000', 2))

    def test_difference(self):
        "Test difference (i.e. AND NOT) of two SimpleBitfields."
        field = SimpleBitfield('110011')
        field.difference(SimpleBitfield('001100'))
        self.assertEqual(field._d, int('110011', 2))
        field = SimpleBitfield('110011')
        field.difference(SimpleBitfield('001110'))
        self.assertEqual(field._d, int('110001', 2))
        field = SimpleBitfield('110011')
        field.difference(SimpleBitfield('011100'))
        self.assertEqual(field._d, int('100011', 2))

    def test_lenTrueItems(self):
        "Test lenTrueItems method."
        field = SimpleBitfield('110011')
        self.assertEqual(field.lenTrueItems(), 4)
        field = SimpleBitfield('100011')
        self.assertEqual(field.lenTrueItems(), 3)
        field = SimpleBitfield('0011')
        self.assertEqual(field.lenTrueItems(), 2)
        field = SimpleBitfield('1')
        self.assertEqual(field.lenTrueItems(), 1)

    # Expected failure - under investigation
    @unittest.expectedFailure
    def test_trueItems(self):
        "Test lenTrueItems method."
        field = SimpleBitfield('110011')
        self.assertListEqual(field.trueItems(),
                             [0, 1, 4, 5])
        field = SimpleBitfield('110001')
        self.assertListEqual(field.trueItems(),
                             [0, 1, 5])
        field = SimpleBitfield('1011')
        self.assertListEqual(field.trueItems(),
                             [0, 2, 3])
        field = SimpleBitfield('1')
        self.assertListEqual(field.trueItems(),
                             [0])


def load_tests(loader, tests, pattern):
    # Alias loader.loadTestsFromTestCase for sake of line lengths
    ltc = loader.loadTestsFromTestCase
    suite = ltc(SimpleBitfieldTestCase)
    return suite


if __name__ == '__main__':
    tr = unittest.TextTestRunner(verbosity=2)
    tr.run(load_tests(unittest.defaultTestLoader, [], 'test*.py'))
