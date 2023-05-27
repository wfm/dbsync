import unittest

from dbsync import intermediate as IM
from dbsync.comparing.unpacked_insert import UnpackedInsert


class TestUnpackedInsert(unittest.TestCase):
    def test_dedup_normal_case(self):
        name = "test_table"
        cols = ["a", "b", "c"]
        table = IM.Table(name, [], ["a", "b"])

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

        ui.dedup()
        nodups = ui.pack()
        v3 = [
            [1, 2, 3],
            [4, 5, 7],
            [8, 9, 10]
        ]
        self.assertListEqual(nodups.values, v3, "Unpacked without duplicates")

    def test_generator(self):
        name = "test_table"
        cols = ["f1", "f2", "f3", "f4"]
        pk = ["f1", "f2"]
        table = IM.Table(name, [], pk)

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
                dict(zip(cols, v[i])),
                f"Insert vals {i}")

            self.assertDictEqual(
                t.update_vals,
                dict(zip(cols[2:], v[i][2:])),
                f"Update vals {i}")

        with self.assertRaises(StopIteration):
            next(gen)

        gen.close()
