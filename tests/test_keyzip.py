"""Tests the keyzip function"""
import pytest
from dataclasses import dataclass, field
from typing import List
from operator import attrgetter

from dbsync.keyzip import keyzip

OFFSET=1000


@dataclass
class Fixture:
    """These are the things we are zipping"""
    keys: List[int]
    value: int


@dataclass
class DataForTest:
    source_data: List[List[int]]
    lholes: List
    rholes: List
    left: List[Fixture]=field(default_factory=list)
    right: List[Fixture]=field(default_factory=list)
    expected_len: int=field(default_factory=int)

    def _make_fixture(self, holes, offset: int=0):
        def get_fixture(v, k):
            if v in holes:
                return None
            return Fixture(k, v + offset)

        x=[get_fixture(v, k) for v, k in enumerate(self.source_data)]
        return [item for item in x if item is not None]

    def __post_init__(self):
        self.left=self._make_fixture(self.lholes)
        self.right=self._make_fixture(self.rholes, OFFSET)
        self.expected_len=len(self.source_data)

    def check_results(self, zipped):
        assert len(zipped) == self.expected_len                     # noqa S101
        for idx, z in enumerate(zipped):
            if idx in self.lholes:
                assert z[0] == None                                 # noqa S101
                assert z[1].keys == self.source_data[idx]           # noqa S101
                assert z[1].value == idx + OFFSET                   # noqa S101
            elif idx in self.rholes:
                assert z[0].keys == self.source_data[idx]           # noqa S101
                assert z[0].value == idx                            # noqa S101
                assert z[1] == None                                 # noqa S101
            else:
                assert z[0].keys == self.source_data[idx]           # noqa S101
                assert z[0].keys == z[1].keys                       # noqa S101
                assert z[0].value == idx                            # noqa S101
                assert z[1].value == idx + OFFSET                   # noqa S101

class TestTests:
# test the tests
    params={
        "test_1hole": [dict(x="x")],
        "test_3holes": [dict(x="x")],
        }

    def test_1hole(self, x):
        test_data=DataForTest([[1]], [], [0])
        assert len(test_data.left) == 1
        assert isinstance(test_data.left[0], Fixture)
        assert len(test_data.right) == 0

    def test_3holes(self, x):
            test_data = DataForTest(
                source_data=[[1, 2, 3], [3, 2, 1], [9, 9], [1], [4, 5, 6]],
                lholes=[2],
                rholes=[1, 3]
                )
            assert len(test_data.left) == len(test_data.source_data) - 1
            assert len(test_data.right) == len(test_data.source_data) - 2


# copied from https://docs.pytest.org/en/6.2.x/example/parametrize.html
#   #parametrizing-test-methods-through-per-class-configuration
def pytest_generate_tests(metafunc):
    # called once per each test function
    funcarglist=metafunc.cls.params[metafunc.function.__name__]
    argnames=sorted(funcarglist[0])
    metafunc.parametrize(
        argnames,
        [[funcargs[name] for name in argnames] for funcargs in funcarglist]
    )


class TestKeyZip:
    _getter = attrgetter("keys")
    params = {
        "test_normal": [
            # no holes
            dict(
                data=[[1, 2, 3], [3, 2, 1], [9, 9], [1], [4, 5, 6]],
                lholes=[],
                rholes=[]
            ),
            # hole at start of left side
            dict(
                data=[[1, 2, 3]],
                lholes=[0],
                rholes=[]
            ),
            # hole at start of right side
            dict(
                data=[[1, 2, 3]],
                lholes=[],
                rholes=[0]
            ),
            # hole at the end of the left side
            dict(
                data=[[1, 2, 3], [3, 2, 1], [9, 9], [1], [4, 5, 6]],
                lholes=[4],
                rholes=[]
            ),
            # hole at the end of the right side
            dict(
                data=[[1, 2, 3], [3, 2, 1], [9, 9], [1], [4, 5, 6]],
                lholes=[],
                rholes=[4]
            ),
            # lotsa holes
            dict(
                data=[[1, 2, 3], [3, 2, 1], [9, 9], [1], [4, 5, 6]],
                lholes=[2],
                rholes=[1, 3]
            ),
        ]
    }

    def test_normal(self, data: List[List[int]], lholes: List[int], rholes: List[int]):
        assert set(lholes) & set(rholes) == set()                   # noqa S101
        test_data=DataForTest(data, lholes, rholes)
        zipped=keyzip(test_data.left, test_data.right, TestKeyZip._getter)
        test_data.check_results(zipped)
