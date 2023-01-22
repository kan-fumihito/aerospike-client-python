# -*- coding: utf-8 -*-

from .test_base_class import TestBaseClass
from .as_status_codes import AerospikeStatus
import aerospike
from aerospike import exception as e
import time

DEFAULT_MAX_ERROR_RATE = 100

class TestMaxErrorRate(TestBaseClass):

    def test_max_error_rate_is_default(self):
        """
        error count reaches default limit.
        """
        config = TestBaseClass.get_connection_config()
        config["tend_interval"] = 1000 * 100 # prevent for healthcheck thread to reset error count
        client = aerospike.client(config)

        query = client.query("test", "demo")

        def callback(input_tuple):
            raise Exception

        for i in range(2 * DEFAULT_MAX_ERROR_RATE):
            
            try:
                query.foreach(callback)
            except e.ClientError as ex:
                if i <= DEFAULT_MAX_ERROR_RATE:
                    assert ex.code == AerospikeStatus.AEROSPIKE_ERR_CLIENT
                else:
                    assert ex.code == AerospikeStatus.AEROSPIKE_MAX_ERROR_RATE


    def test_max_error_rate_is_over_default(self):
        """
        error count reaches limit over default.
        """
        MAX_ERROR_RATE = DEFAULT_MAX_ERROR_RATE + 1
        config = TestBaseClass.get_connection_config()
        config["tend_interval"] = 1000 * 100 # prevent for healthcheck thread to reset error count
        config["max_error_rate"] = MAX_ERROR_RATE
        client = aerospike.client(config)

        query = client.query("test", "demo")

        def callback(input_tuple):
            raise Exception

        for i in range(2 * MAX_ERROR_RATE):
            try:
                query.foreach(callback)
            except e.ClientError as ex:
                if i <= MAX_ERROR_RATE:
                    assert ex.code == AerospikeStatus.AEROSPIKE_ERR_CLIENT
                else:
                    assert ex.code == AerospikeStatus.AEROSPIKE_MAX_ERROR_RATE
    
    def test_max_error_rate_is_below_default(self):
        """
        error count reaches limit below default.
        """
        MAX_ERROR_RATE = DEFAULT_MAX_ERROR_RATE - 1
        config = TestBaseClass.get_connection_config()
        config["tend_interval"] = 1000 * 100 # prevent for healthcheck thread to reset error count
        config["max_error_rate"] = MAX_ERROR_RATE
        client = aerospike.client(config)

        query = client.query("test", "demo")

        def callback(input_tuple):

            raise Exception

        for i in range(2 * MAX_ERROR_RATE):
            try:
                query.foreach(callback)
            except e.ClientError as ex:
                if i <= MAX_ERROR_RATE:
                    assert ex.code == AerospikeStatus.AEROSPIKE_ERR_CLIENT
                else:
                    assert ex.code == AerospikeStatus.AEROSPIKE_MAX_ERROR_RATE

    def test_max_error_rate_is_reseted_by_healthcheck_thread(self):
        """
        error count is reseted by healthcheck thread.
        """
        MAX_ERROR_RATE = 2
        config = TestBaseClass.get_connection_config()
        config["tend_interval"] = 250 # mininum tend_interval (250ms)
        config["max_error_rate"] = MAX_ERROR_RATE
        client = aerospike.client(config)

        query = client.query("test", "demo")

        def callback(input_tuple):
            time.sleep(2) # wait for mote than tend_interval
            raise Exception

        for i in range(2 * MAX_ERROR_RATE):
            try:
                query.foreach(callback)
            except e.ClientError as ex:
                assert ex.code == AerospikeStatus.AEROSPIKE_ERR_CLIENT
