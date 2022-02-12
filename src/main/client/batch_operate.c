/*******************************************************************************
 * Copyright 2013-2020 Aerospike, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 ******************************************************************************/
#include <Python.h>
#include <stdbool.h>

#include <aerospike/aerospike_index.h>
#include <aerospike/aerospike_key.h>
#include <aerospike/aerospike_batch.h>
#include <aerospike/as_error.h>
#include <aerospike/as_exp.h>
#include <aerospike/as_vector.h>
#include <aerospike/as_geojson.h>
#include <aerospike/as_msgpack_ext.h>

#include "client.h"
#include "conversions.h"
#include "serializer.h"
#include "exceptions.h"
#include "policy.h"
#include "cdt_operation_utils.h"
#include "geo.h"
#include "cdt_types.h"

// TODO define these as exposed aerospike constants so C and Python can both use them
#define FIELD_NAME_BATCH_RECORDS "batch_records"
#define FIELD_NAME_BATCH_TYPE "_type"
#define FIELD_NAME_BATCH_KEY "key"
#define FIELD_NAME_BATCH_OPS "ops"
#define FIELD_NAME_BATCH_RESULT "result"
#define FIELD_NAME_BATCH_RECORD "record"
#define FIELD_NAME_BATCH_POLICY "policy"
#define FIELD_NAME_BATCH_MODULE "module"
#define FIELD_NAME_BATCH_FUNCTION "function"
#define FIELD_NAME_BATCH_ARGS "args"

#define GET_BATCH_POLICY_FROM_PYOBJECT(__policy, __policy_type, __conversion_func)                \
    {                                                                                             \
        PyObject *py___policy = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_POLICY); \
        as_exp *expr = NULL;                                                                      \
        as_exp *expr_p = garb->expressions_to_free;                                               \
        if (py___policy != NULL) {                                                                \
            __policy = (__policy_type *)malloc(sizeof(__policy_type));                            \
            __conversion_func(self, err, py___policy, __policy, &__policy, expr, &expr_p);        \
            garb->policy_to_free = __policy;                                                      \
        }                                                                                         \
    }                                                                                             \

// TODO replace this with type checking the batch_records 
// and cleaning up at the end, no struct needed that way
typedef struct garbage_s {

    as_operations *ops_to_free;

    /**
     * NOTE this isn't used for anything but freeing the polices
     * so using void for all should be fine.
     */
    void* policy_to_free;

    as_exp *expressions_to_free;

    as_list *udf_args_to_free;

} garbage;

void garbage_destroy(garbage *garb) {
    as_exp *expr = garb->expressions_to_free;
    if (expr != NULL) {
        as_exp_destroy(expr);
    }

    void *pol = garb->policy_to_free;
    if (pol != NULL) {
        free(pol);
    }

    as_operations *ops = garb->ops_to_free;
    if (ops != NULL) {
        as_operations_destroy(ops);
    }

    as_list *args_l = garb->udf_args_to_free;
    if (ops != NULL) {
        as_list_destroy(args_l);
    }
}

/*
* AerospikeClient_BatchOperateInvoke
* Converts Python BatchRecords objects into a C client as_batch_records struct.
* Then calls aerospike_batch_records.
*/
static PyObject *AerospikeClient_BatchOperateInvoke(AerospikeClient *self, as_error *err, PyObject *py_policy, PyObject *py_obj)
{
    printf("1\n");

    Py_ssize_t py_batch_records_size = 0;
    as_batch_records batch_records;
    as_batch_records *batch_records_p;\

    as_policy_batch batch_policy;
    as_policy_batch *batch_policy_p = NULL;
	as_exp exp_list;
	as_exp *exp_list_p = NULL;

    as_vector garbage_list;
    as_vector *garbage_list_p = NULL;

    // setup for op conversion
    as_vector *unicodeStrVector = as_vector_create(sizeof(char *), 128);
	as_static_pool static_pool;
	memset(&static_pool, 0, sizeof(static_pool));

	if (py_obj == NULL) {
		as_error_update(err, AEROSPIKE_ERR_PARAM,
							   "py_obj value is null");
        goto CLEANUP;
	}
    printf("2\n");

    if (PyErr_Occurred()) {
        printf("err1\n");
        PyErr_Print();
    }

    if (py_policy != NULL) {
        if (pyobject_to_policy_batch(self, err, py_policy, &batch_policy, &batch_policy_p,
        &self->as->config.policies.batch, NULL, NULL, &exp_list, &exp_list_p) != AEROSPIKE_OK) {
            goto CLEANUP;
        }
    }

    // TODO check that py_object is an instance of class

    printf("3\n");

    if (PyErr_Occurred()) {
        printf("err2\n");
        PyErr_Print();
    }

    PyObject *py_batch_records = PyObject_GetAttrString(py_obj, FIELD_NAME_BATCH_RECORDS);
    if ( py_batch_records == NULL || !PyList_Check(py_batch_records)) {
		as_error_update(err, AEROSPIKE_ERR_PARAM,
							   "%s must be a list of BatchRecord", FIELD_NAME_BATCH_RECORDS);
        goto CLEANUP;
    }

    printf("4\n");

    if (PyErr_Occurred()) {
        printf("err3\n");
        PyErr_Print();
    }

    py_batch_records_size = PyList_Size(py_batch_records);
    as_batch_records_inita(&batch_records, py_batch_records_size);
    batch_records_p = &batch_records;

    as_vector_inita(&garbage_list, sizeof(garbage), py_batch_records_size);
    garbage_list_p = &garbage_list;
    for (Py_ssize_t i = 0; i < py_batch_records_size; i++) {
        garbage garb_to_free = {0};
        as_vector_set(&garbage_list, i, (void *)&garb_to_free);
    } 

    // NOTE this isn't used for anything but freeing the polices so using as_policy_batch_read for all should be fine.
    printf("6\n");

    if (PyErr_Occurred()) {
        printf("err4\n");
        PyErr_Print();
    }


    for (Py_ssize_t i = 0; i < py_batch_records_size; i++) {
        garbage *garb = as_vector_get(&garbage_list, i);

        PyObject *py_batch_record = PyList_GetItem(py_batch_records, i);
        // TODO check that this is an instance/subclass on BatchRecord
        if (py_batch_record == NULL) {
            as_error_update(err, AEROSPIKE_ERR_PARAM,
                               "py_batch_record is NULL, %s must be a list of BatchRecord", FIELD_NAME_BATCH_RECORDS);
            goto CLEANUP;
        }

        printf("7\n");

        if (PyErr_Occurred()) {
            printf("err5\n");
            PyErr_Print();
        }

        // extract as_batch_base_record fields
        // all batch_records classes should have these
        PyObject *py_key = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_KEY);
        if (py_key == NULL || !PyTuple_Check(py_key)) {
            as_error_update(err, AEROSPIKE_ERR_PARAM,
                               "py_key is NULL or not a tuple, %s must be a aerospike key tuple", FIELD_NAME_BATCH_KEY);
            goto CLEANUP;
        }

        PyObject *py_batch_type = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_TYPE);
        if (py_batch_type == NULL || !PyLong_Check(py_batch_type)) { // TODO figure away around this being an enum
            as_error_update(err, AEROSPIKE_ERR_PARAM,
                               "py_batch_type is NULL or not an int, %s must be an int from batch_records._Types", FIELD_NAME_BATCH_TYPE);
            goto CLEANUP;
        }

        PyObject *py_ops_list = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_OPS);
        if (py_ops_list == NULL || !PyList_Check(py_ops_list)) {
            as_error_update(err, AEROSPIKE_ERR_PARAM,
                               "py_ops_list is NULL or not a list, %s must be a list of aerospike operation dicts", FIELD_NAME_BATCH_OPS);
            goto CLEANUP;
        }

        printf("8\n");

        if (PyErr_Occurred()) {
            printf("err6\n");
            PyErr_Print();
        }

        as_key key;
        if (pyobject_to_key(err, py_key, &key) != AEROSPIKE_OK) {
            goto CLEANUP;
        }
        printf("9\n");

        if (PyErr_Occurred()) {
            printf("err7\n");
            PyErr_Print();
        }

        // Not checking for overflow here because type is private in python
        // so we shouldn't get anything unexpected.
        uint8_t batch_type = 0;
        batch_type = PyLong_AsLong(py_batch_type);
        if (PyErr_Occurred() && PyErr_ExceptionMatches(PyExc_OverflowError)) {
            as_error_update(err, AEROSPIKE_ERR_PARAM,
                               "py_batch_type aka %s is too large for C long", FIELD_NAME_BATCH_TYPE);
            goto CLEANUP;
        }

        printf("10\n");
        
        Py_ssize_t py_ops_size = PyList_Size(py_ops_list);

        if (PyErr_Occurred()) {
            printf("err8\n");
            PyErr_Print();
        }

        long operation = 0;
        long return_type = -1;
        // this probably wont work with more than 1?
        as_operations *ops = as_operations_new(py_ops_size);
        for (Py_ssize_t i = 0; i < py_ops_size; i++) {
            printf("11\n");

            PyObject *py_op = PyList_GetItem(py_ops_list, i);
            if (py_op == NULL || !PyDict_Check(py_op)) {
                as_error_update(err, AEROSPIKE_ERR_PARAM,
                                "py_op is NULL or not a dict, %s must be a dict \
                                 produced by an aerospike operation helper", FIELD_NAME_BATCH_OPS);
                goto CLEANUP;
            }
            
            printf("12 %d\n", py_op);

            if (add_op(self, err, py_op, unicodeStrVector,
                        &static_pool, ops, &operation,
                        &return_type) != AEROSPIKE_OK) {
                    goto CLEANUP;
                }
            
            garb->ops_to_free = ops;
        }

        if (PyErr_Occurred()) {
            printf("err9\n");
            PyErr_Print();
        }

        printf("13\n");
        switch (batch_type)
        {
        case AS_BATCH_READ:;
            printf("in AS_BATCH_READ\n");

            as_policy_batch_read *r_policy = NULL;
            GET_BATCH_POLICY_FROM_PYOBJECT(r_policy, as_policy_batch_read, pyobject_to_batch_read_policy)

            as_batch_read_record* rr;
            rr = as_batch_read_reserve(&batch_records);
            memcpy(&rr->key, &key, sizeof(as_key));
            rr->ops = ops;
            printf("breaking from AS_BATCH_READ\n");
            break;
        
        case AS_BATCH_WRITE:;
            printf("in AS_BATCH_WRITE\n");
            
            as_policy_batch_write *w_policy = NULL;
            GET_BATCH_POLICY_FROM_PYOBJECT(w_policy, as_policy_batch_write, pyobject_to_batch_write_policy)

            as_batch_write_record* wr;
            wr = as_batch_write_reserve(&batch_records);

            memcpy(&wr->key, &key, sizeof(as_key));
            wr->ops = ops;
            wr->policy = w_policy;
            printf("breaking from AS_BATCH_WRITE\n");
            break;
        
        case AS_BATCH_APPLY:;
            printf("in AS_BATCH_APPLY\n");

            as_policy_batch_apply *a_policy = NULL;
            GET_BATCH_POLICY_FROM_PYOBJECT(a_policy, as_policy_batch_apply, pyobject_to_batch_apply_policy)

            PyObject *py_mod = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_MODULE);
            if (py_mod != NULL || !PyUnicode_Check(py_mod)) {
                as_error_update(err, AEROSPIKE_ERR_PARAM, "%s must be a string", FIELD_NAME_BATCH_MODULE);
                goto CLEANUP;
            }

            PyObject *py_func = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_FUNCTION);
            if (py_func != NULL || !PyUnicode_Check(py_func)) {
                as_error_update(err, AEROSPIKE_ERR_PARAM, "%s must be a string", FIELD_NAME_BATCH_FUNCTION);
                goto CLEANUP;
            }

            PyObject *py_args = PyObject_GetAttrString(py_batch_record, FIELD_NAME_BATCH_ARGS);
            if (py_args != NULL || !PyList_Check(py_args)) {
                as_error_update(err, AEROSPIKE_ERR_PARAM, "%s must be a list of arguments for the UDF", FIELD_NAME_BATCH_ARGS);
                goto CLEANUP;
            }

            const char *mod = PyUnicode_AsUTF8(py_mod);
            const char *func =  PyUnicode_AsUTF8(py_func);

            // TODO free arglist
            as_list *arglist = NULL;
            pyobject_to_list(self, err, py_args, &arglist, &static_pool,
                            SERIALIZER_PYTHON);
            if (err->code != AEROSPIKE_OK) {
                goto CLEANUP;
            }
            garb->udf_args_to_free = arglist;

            as_batch_apply_record* ar;
            ar = as_batch_apply_reserve(&batch_records);
            memcpy(&ar->key, &key, sizeof(as_key));

            printf("breaking from AS_BATCH_APPLY\n");
            break;
        
        case AS_BATCH_REMOVE:;
            printf("in AS_BATCH_REMOVE\n");

            as_policy_batch_remove *re_policy = NULL;
            GET_BATCH_POLICY_FROM_PYOBJECT(re_policy, as_policy_batch_remove, pyobject_to_batch_remove_policy)

            as_batch_remove_record* rer;
            rer = as_batch_remove_reserve(&batch_records);
            memcpy(&rer->key, &key, sizeof(as_key));
            // rer->ops = &ops;
            printf("breaking from AS_BATCH_REMOVE\n");
            break;
        

        default:
            printf("hit default\n");
            as_error_update(err, AEROSPIKE_ERR_PARAM,
                            "batch_type unkown: %d", batch_type);
            goto CLEANUP;
            break;
        }
    }

    if (PyErr_Occurred()) {
        printf("err10\n");
        PyErr_Print();
    }

    printf("14\n");

    // TODO get result and populate batch record result
    Py_BEGIN_ALLOW_THREADS

    aerospike_batch_operate(self->as, err, NULL, &batch_records);

    Py_END_ALLOW_THREADS

    if (err->code != AEROSPIKE_OK) {
        goto CLEANUP;
    }

    printf("15\n");

    if (PyErr_Occurred()) {
        printf("err11\n");
        PyErr_Print();
    }

    // populate results
    as_vector* res_list = &batch_records.list;
    for (Py_ssize_t i = 0; i < py_batch_records_size; i++) {
        printf("16\n");
        PyObject *py_batch_record = PyList_GetItem(py_batch_records, i);

        as_batch_record *batch_record = as_vector_get(res_list, i);
        printf("17\n");

        as_status *result_code = &(((as_batch_base_record*)batch_record)->result);
        as_key *requested_key = &(((as_batch_base_record*)batch_record)->key);
        as_record *result_rec = &(((as_batch_base_record*)batch_record)->record);
        printf("18\n");

        PyObject *py_res = PyLong_FromLong((long)*result_code);
        PyObject_SetAttrString(py_batch_record, FIELD_NAME_BATCH_RESULT, py_res);
        printf("19\n");

        printf("res_code: %d\n", *result_code);

        if (*result_code == AEROSPIKE_OK) {
            printf("OK\n");
            int py_record_tuple_size = 3; // TODO define this
            PyObject *rec = PyTuple_New(py_record_tuple_size);
            record_to_pyobject(self, err, result_rec, requested_key, &rec);
            PyObject_SetAttrString(py_batch_record, FIELD_NAME_BATCH_RECORD, rec);
            printf("20\n");
        }
    }

    if (PyErr_Occurred()) {
        printf("err12\n");
        PyErr_Print();
    }

CLEANUP:
    printf("in cleanup\n");

    if (garbage_list_p != NULL) {
        for (int i = 0; i < py_batch_records_size; i++) {
            garbage *garb_to_free = as_vector_get(&garbage_list, i);
            printf("freeing garb: %d, %d\n", i, garb_to_free);
            garbage_destroy(garb_to_free);
        }
        
        as_vector_destroy(&garbage_list);
    }

    if (batch_records_p != NULL) {
        as_batch_records_destroy(&batch_records);
    }

	POOL_DESTROY(&static_pool);

	as_vector_destroy(unicodeStrVector);

    if (exp_list_p != NULL) {
        as_exp_destroy(exp_list_p);
    }

    // TODO cleanup
	if (err->code != AEROSPIKE_OK) {
		PyObject *py_err = NULL;
		error_to_pyobject(err, &py_err);
		PyObject *exception_type = raise_exception(err);
		PyErr_SetObject(exception_type, py_err);
		Py_DECREF(py_err);
		return NULL;
	}

    // TODO should trhis return anything? should it increase ref?
    // It probably shouldn't return anything, just modify py_obj
    Py_IncRef(py_obj);
	return py_obj;
}

/**
 ******************************************************************************************************
 * Returns data about a particular node in the database depending upon the request string.
 *
 * @param self                  AerospikeClient object.
 * @param args                  The args is a tuple object containing an argument
 *                              list passed from Python to a C function.
 * @param kwds                  Dictionary of keywords.
 *
 * Returns information about a host.
 ********************************************************************************************************/
PyObject *AerospikeClient_BatchOperate(AerospikeClient *self, PyObject *args,
										 PyObject *kwds)
{
	PyObject *py_policy = NULL;
	PyObject *py_batch_recs = NULL;

	as_error err;
	as_error_init(&err);

	static char *kwlist[] = {"batch_records", "policy", NULL};

	if (PyArg_ParseTupleAndKeywords(args, kwds, "O|O:batch_operate", kwlist,
									&py_batch_recs,
									&py_policy) == false) {
		return NULL;
	}

	return AerospikeClient_BatchOperateInvoke(self, &err, py_policy, py_batch_recs);
}