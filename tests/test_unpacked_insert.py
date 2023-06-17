import unittest

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert
from tests.fixtures import *


class TestUnpackedInsert(unittest.TestCase):
    def test_dedup_normal_case(self):
        name = TABLE_NAME
        cols = ["a", "b", "c"]
        key_list = [
            IM.Key("", [
                IM.KeyColumn("a"),
                IM.KeyColumn("b")
            ], True, False)
        ]
        table = IM.Table(name, [], keys=key_list)

        v1 = [
            [1, 2, 3],
            [4, 5, 6]
        ]
        i1 = IM.Insert(name, cols, v1)
        ui = UnpackedInsert(table, i1)

        v2 = [
            [8, 9, 10],
            [4, 5, 7]
        ]
        i2 = IM.Insert(name, cols, v2)
        ui.append(i2)

        dups = ui.pack()
        self.assertListEqual(dups.values, v1 + v2, "Unpacked with duplicates")

        ui.sort()
        nodups = ui.pack()
        v3 = [
            [1, 2, 3],
            [4, 5, 7],
            [8, 9, 10]
        ]
        self.assertListEqual(nodups.values, v3, "Unpacked without duplicates")

    def test_generator(self):
        name = TABLE_NAME
        cols = ["f1", "f2", "f3", "f4"]
        key_list = [
            IM.Key("", [
                IM.KeyColumn("f1"),
                IM.KeyColumn("f2")
            ], True, False)
        ]

        table = IM.Table(name, [], keys=key_list)

        v = [
            ["1", "2", "3", "4"],
            ["5", "6", "7", "8"],
            ["9", "a", "b", "c"],
            ["d", "e", "f", "0"]
        ]
        ins = IM.Insert(name, cols, v)
        ui = UnpackedInsert(table, ins)

        gen = ui.values_gen()
        for i in range(len(v)):
            t = next(gen)
            self.assertEqual(t.key, [v[i][0], v[i][1]], f"Key {i}")

            self.assertDictEqual(
                t.insert_vals,
                dict(zip(cols, v[i], strict=True)),
                f"Insert vals {i}")

            self.assertDictEqual(
                t.update_vals,
                dict(zip(cols[2:], v[i][2:], strict=True)),
                f"Update vals {i}")

        with self.assertRaises(StopIteration):
            next(gen)

        gen.close()
