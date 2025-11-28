#include <Python.h>
#include <stdint.h>

/*
 * bitops para Xadrez_AI_Final
 *  - ctz: index do bit menos significativo
 *  - clz: index do bit mais significativo
 * Convenção: retorna -1 se bb == 0
 */

static PyObject* py_ctz(PyObject* self, PyObject* args) {
    unsigned long long x;
    if (!PyArg_ParseTuple(args, "K", &x))
        return NULL;

    if (x == 0)
        return PyLong_FromLong(-1);

    return PyLong_FromLong(__builtin_ctzll(x));
}

static PyObject* py_clz(PyObject* self, PyObject* args) {
    unsigned long long x;
    if (!PyArg_ParseTuple(args, "K", &x))
        return NULL;

    if (x == 0)
        return PyLong_FromLong(-1);

    return PyLong_FromLong(63 - __builtin_clzll(x));
}

static PyMethodDef BitOpsMethods[] = {
    {"ctz", py_ctz, METH_VARARGS, "Count trailing zeros"},
    {"clz", py_clz, METH_VARARGS, "Count leading zeros"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef bitopsmodule = {
    PyModuleDef_HEAD_INIT,
    "bitops",
    NULL,
    -1,
    BitOpsMethods
};

PyMODINIT_FUNC PyInit_bitops(void) {
    return PyModule_Create(&bitopsmodule);
}
