# -*- coding: utf-8 -*-
import pytest
from aerospike import exception as e

import aerospike
from .test_base_class import TestBaseClass

Server61 = True

if TestBaseClass.major_ver < 6 or (TestBaseClass.major_ver == 6 and TestBaseClass.minor_ver == 0):
    if pytest.__version__ < "3.0.0":
        Server61 = False
    else:
        Server61 = False


def get_list_result_from_operation(client, key, operation, bin):
    _, _, result_bins = client.operate(key, [operation])
    return result_bins[bin]


class TestNewListOperations(object):
    @pytest.fixture(autouse=True)
    def setup(self, request, as_connection):
        """
        Setup Method
        """
        self.keys = []
        # INDEXES    0, 1, 2, 3, 4, 05
        # RINDEX     5, 4, 3, 2, 1, 0
        # RANK       2, 1, 0, 3, 4, 5
        # RRANK     -4,-5,-6,-3,-2,-1
        self.test_list = [7, 6, 5, 8, 9, 10]

        self.test_key = "test", "demo", "new_list_op"
        self.test_bin = "list"
        self.as_connection.put(self.test_key, {self.test_bin: self.test_list})
        self.keys.append(self.test_key)

        yield

        for key in self.keys:
            try:
                self.as_connection.remove(key)
            except e.AerospikeError:
                pass

    @pytest.mark.parametrize("index, expected", ((2, 5), (-2, 9)))
    def test_get_by_index(self, index, expected):
        """
        Without a return type this should return the value
        """
        operation = {
            "op": aerospike.OP_LIST_GET_BY_INDEX,
            "bin": "list",
            "index": index,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == expected

    @pytest.mark.parametrize(
        "return_type, expected",
        (
            (aerospike.LIST_RETURN_VALUE, 5),
            (aerospike.LIST_RETURN_INDEX, 2),
            (aerospike.LIST_RETURN_REVERSE_INDEX, 3),
            (aerospike.LIST_RETURN_RANK, 0),
            (aerospike.LIST_RETURN_REVERSE_RANK, 5),
        ),
    )
    def test_list_get_by_index_return_types(self, return_type, expected):
        """
        Without a return type this should return the value
        """
        operation = {"op": aerospike.OP_LIST_GET_BY_INDEX, "bin": "list", "index": 2, "return_type": return_type}
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == expected

    @pytest.mark.parametrize("index, count", ((0, 3), (-2, 1), (0, 100)))
    def test_get_by_index_range_both_present(self, index, count):
        expected = self.test_list[index : index + count]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_INDEX_RANGE,
            "bin": self.test_bin,
            "index": index,
            "count": count,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == expected

    def test_get_by_index_range_no_count(self):
        operation = {
            "op": aerospike.OP_LIST_GET_BY_INDEX_RANGE,
            "bin": self.test_bin,
            "index": 2,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == self.test_list[2:]

    def test_get_by_index_range_inverted(self):
        start = 0
        count = 3
        expected = self.test_list[start + count :]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_INDEX_RANGE,
            "bin": self.test_bin,
            "index": start,
            "count": count,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == expected

    @pytest.mark.parametrize("rank, expected", ((0, 5), (-1, 10)))
    def test_get_by_rank(self, rank, expected):
        """
        Without a return type this should return the value
        """
        operation = {
            "op": aerospike.OP_LIST_GET_BY_RANK,
            "bin": "list",
            "rank": rank,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == expected

    @pytest.mark.parametrize(
        "return_type, expected",
        (
            (aerospike.LIST_RETURN_VALUE, 5),
            (aerospike.LIST_RETURN_INDEX, 2),
            (aerospike.LIST_RETURN_REVERSE_INDEX, 3),
            (aerospike.LIST_RETURN_RANK, 0),
            (aerospike.LIST_RETURN_REVERSE_RANK, 5),
        ),
    )
    def test_list_get_by_rank_return_types(self, return_type, expected):
        """
        Without a return type this should return the value
        """
        operation = {"op": aerospike.OP_LIST_GET_BY_RANK, "bin": "list", "rank": 0, "return_type": return_type}
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == expected

    @pytest.mark.parametrize("rank, count", ((0, 3), (-2, 1), (0, 100)))
    def test_get_by_rank_range_both_present(self, rank, count):
        expected = sorted(self.test_list)[rank : rank + count]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_RANK_RANGE,
            "bin": self.test_bin,
            "rank": rank,
            "count": count,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert set(result) == set(expected)

    def test_get_by_rank_range_no_count(self):
        operation = {
            "op": aerospike.OP_LIST_GET_BY_RANK_RANGE,
            "bin": self.test_bin,
            "rank": 2,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == sorted(self.test_list)[2:]

    def test_get_by_rank_range_inverted(self):
        rank_start = 0
        rank_count = 3
        # All of the values except for those in the specified rank range
        expected = sorted(self.test_list)[rank_start + rank_count :]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_RANK_RANGE,
            "bin": self.test_bin,
            "rank": rank_start,
            "count": rank_count,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert set(result) == set(expected)

    def test_get_by_value_no_duplicates(self):
        """
        7 is in the 0th position, so we expect [0] as the result
        """
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE,
            "bin": self.test_bin,
            "val": 7,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == [0]

    def test_get_by_value_no_duplicates_inverted(self):
        """
        7 is in the 0th position, so we expect [0] as the result
        """
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE,
            "bin": self.test_bin,
            "val": 7,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        # Every value except for 7
        assert result == [6, 5, 8, 9, 10]

    def test_get_by_value_with_duplicates(self):
        """
        Add a list [0, 1, 0, 2, 0] with 3 0's
        We expect [0, 2, 4] as the results
        """
        dup_list = [0, 1, 0, 2, 0]
        dup_key = "test", "list", "dup"
        self.keys.append(dup_key)

        self.as_connection.put(dup_key, {self.test_bin: dup_list})

        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE,
            "bin": self.test_bin,
            "val": 0,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, dup_key, operation, self.test_bin)
        assert result == [0, 2, 4]

    def test_get_by_value_list(self):
        values = [7, 5, 9]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_LIST,
            "bin": self.test_bin,
            "value_list": values,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == [0, 2, 4]

    def test_get_by_value_list_inverted(self):
        values = [7, 5, 9]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_LIST,
            "bin": self.test_bin,
            "value_list": values,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert set(result) == set([6, 8, 10])

    def test_get_by_value_range(self):
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_begin": 5,
            "value_end": 8,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert len(result) == 3 and set(result) == set([0, 1, 2])

    def test_get_by_value_range_inverted(self):
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_begin": 6,
            "value_end": 8,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert len(result) == 4 and set(result) == set([5, 8, 9, 10])

    def test_get_exists_by_index_range_no_count(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        operation = {
            "op": aerospike.OP_LIST_GET_BY_INDEX_RANGE,
            "bin": self.test_bin,
            "index": 2,
            "return_type": aerospike.LIST_RETURN_EXISTS,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result is True

    def test_get_exists_by_index_range_inverted(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        start = 0
        count = 3
        expected = True
        operation = {
            "op": aerospike.OP_LIST_GET_BY_INDEX_RANGE,
            "bin": self.test_bin,
            "index": start,
            "count": count,
            "return_type": aerospike.LIST_RETURN_EXISTS,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == expected

    def test_get_exists_by_rank_range_no_count(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        operation = {
            "op": aerospike.OP_LIST_GET_BY_RANK_RANGE,
            "bin": self.test_bin,
            "rank": 2,
            "return_type": aerospike.LIST_RETURN_EXISTS,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result is True

    def test_get_exists_by_value_no_duplicates(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        """
        7 is in the 0th position, so we expect it exists
        """
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE,
            "bin": self.test_bin,
            "val": 7,
            "return_type": aerospike.LIST_RETURN_EXISTS,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result is True

    def test_get_exists_by_value_with_duplicates(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        """
        Add a list [0, 1, 0, 2, 0] with 3 0's
        We expect True as the results
        """
        dup_list = [0, 1, 0, 2, 0]
        dup_key = "test", "list", "dup"
        self.keys.append(dup_key)

        self.as_connection.put(dup_key, {self.test_bin: dup_list})

        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE,
            "bin": self.test_bin,
            "val": 0,
            "return_type": aerospike.LIST_RETURN_EXISTS,
        }
        result = get_list_result_from_operation(self.as_connection, dup_key, operation, self.test_bin)
        assert result is True

    def test_get_exists_by_value_list(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        values = [7, 5, 9]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_LIST,
            "bin": self.test_bin,
            "value_list": values,
            "return_type": aerospike.LIST_RETURN_EXISTS,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result is True

    def test_get_exists_by_value_list_inverted(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        values = [7, 5, 9]
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_LIST,
            "bin": self.test_bin,
            "value_list": values,
            "return_type": aerospike.LIST_RETURN_EXISTS,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result is True

    def test_get_exists_by_value_range(self):
        if not Server61:
            pytest.skip("It only applies to >= 6.1 enterprise edition")
        operation = {
            "op": aerospike.OP_LIST_GET_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_begin": 5,
            "value_end": 8,
            "return_type": aerospike.LIST_RETURN_EXISTS,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result is True

    #  REMOVE Family of operations
    def test_remove_by_index(self):
        """
        Remove the 3rd item, a 5
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_INDEX,
            "bin": "list",
            "index": 2,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == 5
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[:2] + self.test_list[3:]

    def test_remove_by_index_range(self):
        """
        Remove the 3rd item, a 5
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_INDEX_RANGE,
            "bin": "list",
            "index": 2,
            "count": 2,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == [5, 8]
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[:2] + self.test_list[4:]

    def test_remove_by_index_range_inverted(self):
        """
        Remove the 3rd item, a 5
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_INDEX_RANGE,
            "bin": "list",
            "index": 2,
            "count": 2,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert set(result) == set([7, 6, 9, 10])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [5, 8]

    def test_remove_by_rank(self):
        """
        Remove the 3rd smallest item, a 7 at index 0
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_RANK,
            "bin": "list",
            "rank": 2,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == 7
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[1:]

    def test_remove_by_rank_range(self):
        """
        Remove the 3rd smallest item, a 7 at index 0
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_RANK_RANGE,
            "bin": "list",
            "rank": 0,
            "count": 3,
            "return_type": aerospike.LIST_RETURN_VALUE,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert result == [7, 6, 5]
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[3:]

    def test_remove_by_rank_range_inverted(self):
        """
        Remove the 3rd smallest item, a 7 at index 0
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_RANK_RANGE,
            "bin": "list",
            "rank": 0,
            "count": 3,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)

        assert set(result) == set([8, 9, 10])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[0:3]

    def test_remove_by_value_no_duplicates(self):
        """
        7 is in the 0th position, so we expect [0] as the result
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE,
            "bin": self.test_bin,
            "val": 7,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == [0]
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[1:]

    def test_remove_by_value_inverted(self):
        """
        7 is in the 0th position, so we expect [0] as the result
        """
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE,
            "bin": self.test_bin,
            "val": 7,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == [6, 5, 8, 9, 10]
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == self.test_list[0:1]

    def test_remove_by_value_with_duplicates(self):
        """
        Add a list [0, 1, 0, 2, 0] with 3 0's
        We expect [0, 2, 4] as the results
        """
        dup_list = [0, 1, 0, 2, 0]
        dup_key = "test", "list", "dup"
        self.keys.append(dup_key)

        self.as_connection.put(dup_key, {self.test_bin: dup_list})

        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE,
            "bin": self.test_bin,
            "val": 0,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, dup_key, operation, self.test_bin)
        assert result == [0, 2, 4]

        _, _, bins = self.as_connection.get(dup_key)
        assert bins[self.test_bin] == [1, 2]

    def test_remove_by_value_list(self):
        values = [7, 5, 9]
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE_LIST,
            "bin": self.test_bin,
            "value_list": values,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert result == [0, 2, 4]

        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [6, 8, 10]

    def test_remove_by_value_list_inverted(self):
        values = [7, 5, 9]
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE_LIST,
            "bin": self.test_bin,
            "value_list": values,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert set(result) == set([6, 8, 10])

        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [7, 5, 9]

    def test_remove_by_value_range(self):
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_begin": 5,
            "value_end": 8,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert len(result) == 3 and set(result) == set([0, 1, 2])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [8, 9, 10]

    def test_remove_by_value_range_inverted(self):
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_begin": 6,
            "value_end": 8,
            "return_type": aerospike.LIST_RETURN_VALUE,
            "inverted": True,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert len(result) == 4 and set(result) == set([5, 8, 9, 10])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [7, 6]

    def test_remove_by_value_range_no_begin(self):
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_end": 8,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert len(result) == 3 and set(result) == set([0, 1, 2])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [8, 9, 10]

    def test_remove_by_value_range_no_end(self):
        operation = {
            "op": aerospike.OP_LIST_REMOVE_BY_VALUE_RANGE,
            "bin": self.test_bin,
            "value_begin": 7,
            "return_type": aerospike.LIST_RETURN_INDEX,
        }
        result = get_list_result_from_operation(self.as_connection, self.test_key, operation, self.test_bin)
        assert len(result) == 4 and set(result) == set([0, 3, 4, 5])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == [6, 5]

    def test_list_set_order(self):
        operation = {"op": aerospike.OP_LIST_SET_ORDER, "list_order": aerospike.LIST_ORDERED, "bin": self.test_bin}
        self.as_connection.operate(self.test_key, [operation])
        _, _, bins = self.as_connection.get(self.test_key)
        assert bins[self.test_bin] == sorted(self.test_list)

    def test_list_sort(self):
        unsorted_dups = [2, 5, 2, 5]
        sort_key = "test", "demo", "dup_list"
        self.keys.append(sort_key)
        self.as_connection.put(sort_key, {self.test_bin: unsorted_dups})

        operation = {
            "op": aerospike.OP_LIST_SORT,
            "sort_flags": aerospike.LIST_SORT_DROP_DUPLICATES,
            "bin": self.test_bin,
        }

        self.as_connection.operate(sort_key, [operation])
        _, _, bins = self.as_connection.get(sort_key)
        assert bins[self.test_bin] == [2, 5]
