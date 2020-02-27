#include "Python.h"
#include "tercalc.h"
#include <vector>


static bool PyListToVector(PyObject* listObj, vector<string>& outVector) {

    /* get the number of words passed to us */
    int numWords = PyList_Size(listObj);

    /* should raise an error here. */
    if (numWords < 0)   return false; /* Not a list */


    PyObject * strObj;  /* one string in the list */
    /* iterate over items of the list, grabbing strings */
    for (int i=0; i<numWords; i++){
        /* grab the string object from the next element of the list */
        strObj = PyList_GetItem(listObj, i); /* Can't fail */
        char* str = PyUnicode_AsUTF8(strObj); //PyBytes_AsString( strObj );

        /* push to output vector */
        if(str)
            outVector.push_back(str);
        else
            printf("Failed to convert object to string: %s\n", str);
    }
    return true;
}

static PyObject *
ter_fun(PyObject *self, PyObject *args)
{

    PyObject * srcObj; /* the list of strings */
    PyObject * tgtObj; /* the list of strings */

    /* the O! parses for a Python object (listObj) checked
       to be of type PyList_Type */
    if (! PyArg_ParseTuple( args, "O!O!", &PyList_Type, &srcObj, 
               &PyList_Type, &tgtObj )) return NULL;
    

    vector<string> src, tgt; 
    if (!PyListToVector(srcObj, src)) return NULL;
    if (!PyListToVector(tgtObj, tgt)) return NULL;
    
    TERCpp::terCalc tc;    
    TERCpp::terAlignment ta = tc.TER(src, tgt);
    return PyFloat_FromDouble(ta.score());
}



static PyMethodDef pytercpp_methods[] = {
    /* The cast of the function is necessary since PyCFunction values
     * only take two PyObject* parameters, and keywdarg_parrot() takes
     * three.
     */
    {"ter", (PyCFunction)ter_fun, METH_VARARGS | METH_KEYWORDS,
     "Calculates TER"},
    {NULL, NULL, 0, NULL}   /* sentinel */
};

static struct PyModuleDef pytercppmodule = {
    PyModuleDef_HEAD_INIT,
    "pytercpp",
    NULL,
    -1,
    pytercpp_methods
};

PyMODINIT_FUNC
PyInit_pytercpp(void)
{
    return PyModule_Create(&pytercppmodule);
}
