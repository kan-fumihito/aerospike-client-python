##########################################################################
# Copyright 2013-2022 Aerospike, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################
'''
Helper functions to generate complex data type context (cdt_ctx) objects for use with operations on nested CDTs (list, map, etc).

Example::

    import aerospike
    from aerospike import exception as ex
    from aerospike_helpers import cdt_ctx
    from aerospike_helpers.operations import map_operations
    from aerospike_helpers.operations import list_operations
    import sys

    # Configure the client.
    config = {"hosts": [("127.0.0.1", 3000)]}

    # Create a client and connect it to the cluster.
    try:
        client = aerospike.client(config).connect()
    except ex.ClientError as e:
        print("Error: {0} [{1}]".format(e.msg, e.code))
        sys.exit(1)

    key = ("test", "demo", "foo")
    nested_list = [{"name": "John", "id": 100}, {"name": "Bill", "id": 200}]
    nested_list_bin_name = "nested_list"

    # Write the record.
    try:
        client.put(key, {nested_list_bin_name: nested_list})
    except ex.RecordError as e:
        print("Error: {0} [{1}]".format(e.msg, e.code))

    # EXAMPLE 1: read a value from the map nested at list index 1.
    try:
        ctx = [cdt_ctx.cdt_ctx_list_index(1)]

        ops = [
            map_operations.map_get_by_key(
                nested_list_bin_name, "id", aerospike.MAP_RETURN_VALUE, ctx
            )
        ]

        _, _, result = client.operate(key, ops)
        print("EXAMPLE 1, id is: ", result)
    except ex.ClientError as e:
        print("Error: {0} [{1}]".format(e.msg, e.code))
        sys.exit(1)

    # EXAMPLE 2: write a new nested map at list index 2 and get the value at its 'name' key.
    # NOTE: The map is appened to the list, then the value is read using the ctx.
    try:
        new_map = {"name": "Cindy", "id": 300}

        ctx = [cdt_ctx.cdt_ctx_list_index(2)]

        ops = [
            list_operations.list_append(nested_list_bin_name, new_map),
            map_operations.map_get_by_key(
                nested_list_bin_name, "name", aerospike.MAP_RETURN_VALUE, ctx
            ),
        ]

        _, _, result = client.operate(key, ops)
        print("EXAMPLE 2, name is: ", result)
    except ex.ClientError as e:
        print("Error: {0} [{1}]".format(e.msg, e.code))
        sys.exit(1)

    # Cleanup and close the connection to the Aerospike cluster.
    client.remove(key)
    client.close()

    """
    EXPECTED OUTPUT:
    EXAMPLE 1, id is:  {'nested_list': 200}
    EXAMPLE 2, name is:  {'nested_list': 'Cindy'}
    """
'''
from cmath import exp
import aerospike
from enum import Enum


class _Types(Enum):
    READ = 0
    WRITE = 1
    APPLY = 2
    REMOVE = 3


class BatchRecords:
    """ TODO refactor the description with Python types
        BatchRecords contasins a list of batch request/response (as_batch_base_record) records. The record types can be
        as_batch_read_record, as_batch_write_record, as_batch_apply_record or as_batch_remove_record.
    """
    def __init__(self, *, batch_records=None) -> None:
        self.batch_records = batch_records



class BatchRecord:
    """ 
        _BatchRecord provides the base fields for BtachRecord objects.
        key is the aerospike key to operate on.
        ops are the operations to use.
        record, the record for the requested key. TODO add conditions where it is populated.
        result is the status code of the operation.
        _type is the type of batch operation.
        _has_write does this batch subtransaction contain a write operation?
        in_doubt Is it possible that the write transaction completed even though this error was generated.
	        This may be the case when a client error occurs (like timeout) after the command was sent
	        to the server.
        policy Operation policy, type depends on batch type, write, read, apply, etc. TODO is this correct?
    """
    def __init__(self, key: tuple, ops: list) -> None:
        self.key = key
        self.ops = ops
        self.record = ()
        self.result = 0 # TODO set this as the ok status code using the constant
    
    def add_op(self, op: dict) -> None:
        self.ops.append(op)



class BatchWrite(BatchRecord):
    """
        BatchWrite defines the object used for Batch write operations and
        retrieving batch write results.
    """

    def __init__(self, key: str, ops: list, policy: dict = None) -> None:
        super().__init__(key, ops)
        self._type = _Types.WRITE
        self._has_write = True
        self.policy = policy


# TODO policy support
# class PolicyBatchWrite:
#     """
#         PolicyBatchWrite defines policy options for use with
#         BatchWrite operations.
#     """

#     def __init__(self) -> None:
#         self.expression = expression
#         self.key_policy = key_policy
