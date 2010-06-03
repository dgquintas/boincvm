#include <Python.h>
#include "boinc_api.h"
#include "filesys.h"
#include "error_numbers.h"
#include "diagnostics.h"
#include <iostream>

// Exception used when boinc is clearly to blame for an error
static PyObject *BoincError;

static PyObject *bindings_boinc_init(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_init_options(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_finish(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_resolve_filename(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_fopen(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_time_to_checkpoint(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_checkpoint_completed(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_begin_critical_section(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_end_critical_section(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_fraction_done(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_get_fraction_done(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_is_standalone(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_need_network(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_network_poll(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_network_done(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_ops_per_cpu_sec(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_ops_cumulative(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_upload_file(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_upload_status(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_receive_trickle_down(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_send_trickle_up(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_get_status(PyObject *self, PyObject *args);
static PyObject *bindings_boinc_report_app_status(PyObject *self, PyObject *args);



/* Unfortunately (as far as I know) we can't make the pydoc strings look 
perfect and we have no way of telling pydoc to override its header 
giving the method's name and arguments. Therefore the following will 
have to suffice as documentation */

char boinc__doc__[] = "\
C{boinc} module\n\n\
This module provides bindings to standard and some less commonly \n\
features of the BOINC API. Each method is documented individually \n\
in docstrings, with python-specific behaviour mentioned. \n\
\n\
\t- For more information about BOINC in general, please visit:\n\
\tU{http://boinc.berkeley.edu/}\n\
\t- API functions provided here include most of the Basic API:\n\
\tU{http://boinc.berkeley.edu/trac/wiki/BasicApi}\n\
\t- We also provide access to the Intermediate Upload API:\n\
\tU{http://boinc.berkeley.edu/trac/wiki/IntermediateUpload}\n\
\t- Support for the trickle messages API is forthcoming....\n\
\n\
C{Py_BuildValue} does not support C{Bool} types, so python code should\n\
test for zero or nonzero results rather than C{True} or C{False} when\n\
calling functions from this API.\n\
";


char boinc_init__doc__[] = "\
boinc_init()\n\n\
Initialises a BOINC application.\n\n\
Applications must call this before calling other BOINC functions. \
";

char boinc_init_options__doc__[] = "\
boinc_init_options(boinc_options)\n\n\
Initialises a BOINC application when using compound applications.\n\n\
Applications must call this before calling other BOINC functions. \
";

char boinc_finish__doc__[] = "\
boinc_finish(status)\n\n\
Ends a BOINC application.\n\n\
Applications that have completed should call this. The call does not \n\
return. The argument status should be nonzero if an error was \n\
encountered. \
";


char boinc_resolve_filename__doc__[] = "\
boinc_resolve_filename(logical_name)\n\n\
Resolve a filename from a logical name to a physical path.\n\n\
Applications that use name input or output files should call this to \n\
convert logical file names to physical names. It does not need to be \n\
used for temporary files. For example, instead of \n\
C{\tfh = open(\'filename\',\'r\')}\n\
the application might use::\n\n\
   try: \n\
       open(boinc.boinc_resolve_filename(\'filename\'),\'r\')\n\
   except boinc.error:\n\
      boinc.boinc_finish(1)\n\
";


char boinc_fopen__doc__[] = "\
boinc_fopen(path, mode)\n\n\
Handles BOINC-specific issues related to the opening of files and \n\
returns a python file object.\n\n\
The BasicApi documentation states that \"applications should replace \n\
fopen calls with boinc_fopen\". As python's built-in open() function \n\
should be expected to handle EINTR perhaps the main reason is to \n\
circumvent temporary locking on Windows. Otherwise, the mode specified \n\
should follow the format for fopen(3). A python file object is returned.\n\
";


char boinc_time_to_checkpoint__doc__[] = "\
boinc_time_to_checkpoint()\n\n\
Polls the core client to see if the application should checkpoint.\n\n\
An application must call boinc_time_to_checkpoint whenever it reaches \n\
a point where it is able to checkpoint. If it returns nonzero then the \n\
application should checkpoint immediately (i.e., write the state file \n\
and flush all output files), then call L{boinc_checkpoint_completed}.\n\
\n\
boinc_time_to_checkpoint is fast, so it can be called frequently \n\
(hundreds or thousands of times a second).\n\
\n\
If you're using replication, ensure that your application generates \n\
the same results regardless of where and how often it restarts, by \n\
saving the state of the random number generator and avoiding loss \n\
of precision when saving floating-point numbers.\
";


char boinc_checkpoint_completed__doc__[] = "\
boinc_checkpoint_completed()\n\n\
Indicates that checkpointing has been completed by the application.\n\n\
When a call to L{boinc_time_to_checkpoint} returns nonzero, BOINC expects \n\
the application to write its current state to disk. \n\
When it has done so, it should call boinc_checkpoint_completed.\
";


char boinc_begin_critical_section__doc__[] = "\
boinc_begin_critical_section()\n\n\
Denotes a section that should not be interrupted.\n\n\
Call boinc_begin_critical_section before code segments during which \n\
you don't want to be suspended or killed by the core client. \n\
Critical sections are recursive, so each boinc_begin_critical_section \n\
must be balanced by a L{boinc_end_critical_section}.\
";


char boinc_end_critical_section__doc__[] = "\
boinc_end_critical_section()\n\n\
Ends a section that should not be interruped.\n\n\
Call boinc_end_critical_section after code segments, indicated by \n\
L{boinc_begin_critical_section}, during which you don\'t want to be \n\
suspended or killed by the core client. Critical sections are \n\
recursive, so each boinc_begin_critical_section must be \n\
balanced by a boinc_end_critical_section.\
";


char boinc_fraction_done__doc__[] = "\
boinc_fraction_done(fraction_done)\n\n\
Report fraction of workunit completed to core client.\n\n\
The core client GUI displays the percent done of workunits in \n\
progress. To keep this display current, an application should \n\
periodically call boinc_fraction_done. The fraction_done argument \n\
is an estimate of the workunit fraction complete (from 0 to 1). \n\
This function is fast and can be called frequently. The sequence \n\
of arguments in successive calls should be non-decreasing. \n\
An application should never \'reset\' and start over if an \n\
error occurs; it should exit with an error code. \
";


char boinc_get_fraction_done__doc__[] = "\
boinc_get_fraction_done()\n\n\
Request from core client last set value of workunit fraction completed.\n\n\
The core client GUI displays the percent done of workunits in \n\
progress. If this has been set using L{boinc_fraction_done} then this \n\
method returns the last value set, or -1 if none has been set (this \n\
would typically be called from graphics code). \
";


char boinc_is_standalone__doc__[] = "\
boinc_is_standalone()\n\n\
Check for presence of the BOINC core client.\n\n\
Returns nonzero if the application is running standalone and zero if \n\
the application is running under the control of the BOINC client. \n\n\
BOINC applications can be run in \"standalone\" mode for testing, or \n\
under the control of the BOINC client. You might want your application \n\
to behave differently in the two cases. For example you might want \n\
to output debugging information if the application is running \n\
standalone.\
";


char boinc_need_network__doc__[] = "\
boinc_need_network()\n\n\
Request use of a network connection.\n\n\
Alerts the user that a network connection is neded, but has been \n\
determined by the application to be unavailable (eg. a call to \n\
socket.gethostbyname() returns socket.error). When a network \n\
connection becomes available, then L{boinc_network_poll} will return \n\
nonzero. \
";


char boinc_network_poll__doc__[] = "\
boinc_network_poll()\n\n\
Check to see if the requested network connection is available.\n\n\
Should be called periodically if L{boinc_need_network} has been \n\
called, upon determining that no network connection is available to \n\
the application. It will return nonzero when a network connection is \n\
available, otherwise it will return zero. When whatever network \n\
communication was necessary has been completed, the application \n\
should call L{boinc_network_done}. \
";


char boinc_network_done__doc__[] = "\
boinc_network_done()\n\n\
Indicate completion of network activity to core client.\n\n\
Should be called after all necessary network communication has been \n\
completed, where the connection was made after a successful call to \n\
L{boinc_network_poll}. \
";


char boinc_ops_per_cpu_sec__doc__[] = "\
boinc_ops_per_cpu_sec(floating_point_ops, integer_ops)\n\n\
Set application-specfic benchmark.\n\n\
This lets the application report the results of an application-specific \n\
benchmark to the core client, expressed as number of floating-point and \n\
integer operations per CPU second. \
";


char boinc_ops_cumulative__doc__[] = "\
boinc_ops_cumulative(floating_point_ops[, integer_ops])\n\n\
Report total number of operations to core client.\n\n\
This lets the application report the total number of floating-point \n\
and/or integer operations since the start of the result. If \n\
floating_point_ops is nonzero, it's used to compute credit and \n\
integer_ops is ignored (making it an optional argument in these \n\
python bindings). boinc_ops_cumulative may be called multiple \n\
times, but only the last call makes any difference. \
";


char boinc_upload_file__doc__[] = "\
boinc_upload_file(name)\n\n\
Upload a file before workunit has finished.\n\n\
Long-running applications can upload particular output files before \n\
the result as a whole is finished. To initiate the upload of an \n\
output file, call boinc_upload_file with the logical name of the \n\
file. The application cannot modify the file after making this call. \n\
The application may check on the status of the upload with \n\
L{boinc_upload_status} \
";

char boinc_upload_status__doc__[] = "\
boinc_upload_status(name)\n\n\
Check status of file tagged for upload.\n\n\
Used to check on the status of intermediate upload requests made \n\
with L{boinc_upload_file}. It will return zero when the upload \n\
of the file has finished successfully. \
";




char boinc_send_trickle_up__doc__[] = "\
boinc_send_trickle_up(variety,text)\n\n\
Check status of file tagged for upload.\n\n\
Used to send trickle-down messages. These are used to communicate \n\
with the server while the application is running. A message has \n\
a variety, a string of length 256 or less (a C{ValueError} will be \n\
thrown if the string is longer, although the BOINC documentation \n\
is not clear on whether the 256 length limit is part of the \n\
protocol). This allows different types of messages \n\
to be handled separately. \n\n\
The message itself should be sent in the argument text, and may \n\
be of any length. The message is expected to be an XML document. \n\n\
During testing, this method was observed to cause an interactive \n\
python session (or equivalent C++ code that blocked for input) \n\
to die with C{SIGSEGV}, probably a pthreads issue. \
";

char boinc_receive_trickle_down__doc__[] = "\
boinc_receive_trickle_down()\n\n\
Check for, and receive, trickle-down messages.\n\n\
Used to receive trickle-down messages. Trickle-down messages are \n\
sent by the server. If there is a message for the application, \n\
this method will return it as a string. If there was no message \n\
(or messages are not enabled) then the method will return C{None}. \n\n\
If L{boinc_init} has not been called then do not depend on the output. \
";


char boinc_get_status__doc__[] = "\
boinc_get_status()\n\n\
Get the status of the runtime system.\n\n\
Internally, the status of the runtime system is represented by \n\
the following structure:: \n\
    typedef struct BOINC_STATUS { \n\
       int no_heartbeat; \n\
       int suspended; \n\
       int quit_request; \n\
       int reread_init_data_file; \n\
       int abort_request; \n\
       double working_set_size; \n\
       double max_working_set_size; } BOINC_STATUS; \n\n\
The result is returned as a python C{dict}, the keywords being the \n\
variable names, and the values either python C{integer} or C{float} \n\
as appropriate. \
";

char boinc_report_app_status__doc__[] = "\
boinc_report_app_status(cpu_time, checkpoint_cpu_time, fraction_done)\n\n\
Report application status to the core client.\n\n\
This comes from the compound application API. \n\
If the main program is responsible for reporting application status to \n\
the core client, it should periodically call this function. \
";



static PyMethodDef BoincMethods[] = {
{"boinc_init", bindings_boinc_init, METH_VARARGS, boinc_init__doc__},
{"boinc_init_options", bindings_boinc_init_options, METH_VARARGS, boinc_init_options__doc__},
{"boinc_finish", bindings_boinc_finish, METH_VARARGS, boinc_finish__doc__}, 
{"boinc_resolve_filename", bindings_boinc_resolve_filename, METH_VARARGS, boinc_resolve_filename__doc__}, 
{"boinc_fopen", bindings_boinc_fopen, METH_VARARGS, boinc_fopen__doc__}, 
{"boinc_time_to_checkpoint", bindings_boinc_time_to_checkpoint, METH_VARARGS, boinc_time_to_checkpoint__doc__}, 
{"boinc_checkpoint_completed", bindings_boinc_checkpoint_completed, METH_VARARGS, boinc_checkpoint_completed__doc__}, 
{"boinc_begin_critical_section", bindings_boinc_begin_critical_section, METH_VARARGS, boinc_begin_critical_section__doc__},
{"boinc_end_critical_section", bindings_boinc_end_critical_section, METH_VARARGS, boinc_end_critical_section__doc__},
{"boinc_fraction_done", bindings_boinc_fraction_done, METH_VARARGS, boinc_fraction_done__doc__},
{"boinc_get_fraction_done", bindings_boinc_get_fraction_done, METH_VARARGS, boinc_get_fraction_done__doc__},
{"boinc_is_standalone", bindings_boinc_is_standalone, METH_VARARGS, boinc_is_standalone__doc__},
{"boinc_need_network", bindings_boinc_need_network, METH_VARARGS, boinc_need_network__doc__},
{"boinc_network_poll", bindings_boinc_network_poll, METH_VARARGS, boinc_network_poll__doc__},
{"boinc_network_done", bindings_boinc_network_done, METH_VARARGS, boinc_network_done__doc__},
{"boinc_ops_per_cpu_sec", bindings_boinc_ops_per_cpu_sec, METH_VARARGS, boinc_ops_per_cpu_sec__doc__},
{"boinc_ops_cumulative", bindings_boinc_ops_cumulative, METH_VARARGS, boinc_ops_cumulative__doc__},
{"boinc_upload_file", bindings_boinc_upload_file, METH_VARARGS, boinc_upload_file__doc__},
{"boinc_upload_status", bindings_boinc_upload_status, METH_VARARGS, boinc_upload_status__doc__},
{"boinc_send_trickle_up", bindings_boinc_send_trickle_up, METH_VARARGS, boinc_send_trickle_up__doc__},
{"boinc_receive_trickle_down", bindings_boinc_receive_trickle_down, METH_VARARGS, boinc_receive_trickle_down__doc__},
{"boinc_get_status", bindings_boinc_get_status, METH_VARARGS, boinc_get_status__doc__},
{"boinc_report_app_status", bindings_boinc_report_app_status, METH_VARARGS, boinc_report_app_status__doc__},
{NULL,NULL,0,NULL}};


using namespace std;


/* Initialises BOINC module; obligatory for python extension modules. */
extern "C" PyMODINIT_FUNC initboinc(void)
{
	PyObject *m;

	m  = Py_InitModule3("boinc",BoincMethods,boinc__doc__);

	char chr_BoincError[] = "boinc.error";

	/* Directly inherits from Exception.
	 * This error should be used for problems which we can blame
	 * on the BOINC API. */
	BoincError = PyErr_NewException(chr_BoincError, NULL, NULL);

	Py_INCREF(BoincError);
	PyModule_AddObject(m,"error",BoincError);
}


/* Most of the functions in the "Basic API" documentation are implemented here. That's enough to run any basic BOINC application. Anything more 
sophisticated probably deserves to be rewritten in C++. */
static PyObject *bindings_boinc_init(PyObject *self, PyObject *args)
{

	int retval;

	if (!PyArg_ParseTuple(args, ""))
		return NULL;


	retval = boinc_init();

	/* The errors possible from boinc_init() are many and varied
	   so we will just check that retval is nonzero. */
	if(retval)
	{
		PyErr_SetString(BoincError, "call to boinc_init() failed");
		return NULL;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject *bindings_boinc_init_options(PyObject *self, PyObject *args)
{
  
	int retval;
        BOINC_OPTIONS options;
        memset(&options, 0, sizeof(options));
       
	if (!PyArg_ParseTuple(args, "iiiiii", &options.main_program, &options.check_heartbeat, 
                                   &options.handle_process_control, &options.send_status_msgs,
                                   &options.handle_trickle_ups, &options.handle_trickle_downs))
		return Py_BuildValue("i", 0);

       if (!diagnostics_is_initialized()) {
            retval = boinc_init_diagnostics(BOINC_DIAG_DEFAULTS);
            if (retval) return Py_BuildValue("i", retval);
        }

        retval = boinc_init_options_general(options);
        if (retval) return Py_BuildValue("i", retval);
  
        retval = start_timer_thread();
        if (retval) return Py_BuildValue("i", retval); 

        /*retval = boinc_init_options(&options); */
        retval = 0;	
	return Py_BuildValue("i", retval);
}

static PyObject *bindings_boinc_finish(PyObject *self, PyObject *args)
{

	int retval;
	int exitVal = 0;

	/* This should probably be an error when it fails,
	but it would be an internal python problem. Ditto elsewhere. */
	if (!PyArg_ParseTuple(args, "|i", &exitVal))
		return NULL;

	retval = boinc_finish(exitVal);

	if(retval)
	{
		PyErr_SetString(BoincError, "call to boinc_finish() failed");
		return NULL;
	}

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bindings_boinc_resolve_filename(PyObject *self, PyObject *args)
{
	char *name;

	if (!PyArg_ParseTuple(args, "s", &name))
		return NULL;

	string resolved_name;

	int retval;

	retval = boinc_resolve_filename_s(name, resolved_name);

	if(retval == ERR_NULL)
	{
		PyErr_SetString(BoincError, "call to boinc_resolve_filename() failed, returned ERR_NULL");
		return NULL;
	}


/* If we get here the worst that could happen is the file doesn't exist,
 * but that doesn't really concern us... */

	return Py_BuildValue("s", resolved_name.c_str()); 
}


static PyObject *bindings_boinc_fopen(PyObject *self, PyObject *args)
{

	char *name;
	char *mode;


	if (!PyArg_ParseTuple(args, "ss", &name, &mode))
		return NULL;

	FILE *fp;
	PyObject *object;

	fp = boinc_fopen(name, mode);

	// tighten up error handling

	object = PyFile_FromFile(fp, name, mode, fclose);
	Py_INCREF(object);

	return object;
}


static PyObject *bindings_boinc_checkpoint_completed(PyObject *self, PyObject *args)
{

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	boinc_checkpoint_completed();

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bindings_boinc_time_to_checkpoint(PyObject *self, PyObject *args)
{

	int isItTime;

	if (!PyArg_ParseTuple(args, ""))
		return NULL;


	isItTime = boinc_time_to_checkpoint();

	return Py_BuildValue("i", isItTime);
}


static PyObject *bindings_boinc_begin_critical_section(PyObject *self, PyObject *args)
{

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	boinc_begin_critical_section();

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bindings_boinc_end_critical_section(PyObject *self, PyObject *args)
{
	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	boinc_end_critical_section();

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bindings_boinc_fraction_done(PyObject *self, PyObject *args)
{

	double fractDone;

	if (!PyArg_ParseTuple(args, "d", &fractDone))
		return NULL;
	
	boinc_fraction_done(fractDone);

	Py_INCREF(Py_None);
	return Py_None;
}



static PyObject *bindings_boinc_get_fraction_done(PyObject *self, PyObject *args)
{

	double fractDone;

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	fractDone = boinc_get_fraction_done();

	return Py_BuildValue("d", fractDone);
}


static PyObject *bindings_boinc_is_standalone(PyObject *self, PyObject *args)
{

	int isItStandalone;

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	isItStandalone = boinc_is_standalone();

	return Py_BuildValue("i", isItStandalone);

}


static PyObject *bindings_boinc_need_network(PyObject *self, PyObject *args)
{

	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	boinc_need_network();

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bindings_boinc_network_poll(PyObject *self, PyObject *args)
{

	int haveNetwork;

	if (!PyArg_ParseTuple(args, ""))
		return NULL;


	haveNetwork = boinc_network_poll();

	return Py_BuildValue("i", haveNetwork);

}


static PyObject *bindings_boinc_network_done(PyObject *self, PyObject *args)
{

	if (!PyArg_ParseTuple(args, ""))
		return NULL;


	boinc_network_done();

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *bindings_boinc_ops_per_cpu_sec(PyObject *self, PyObject *args)
{

	double floating_point_ops, integer_ops;

	if (!PyArg_ParseTuple(args, "dd", &floating_point_ops,&integer_ops))
		return NULL;

	
	boinc_ops_per_cpu_sec(floating_point_ops, integer_ops);

	Py_INCREF(Py_None);
	return Py_None;	

}


static PyObject *bindings_boinc_ops_cumulative(PyObject *self, PyObject *args)
{

	double floating_point_ops = 0.0;
	double integer_ops = 0.0;

	if (!PyArg_ParseTuple(args, "d|d", &floating_point_ops, &integer_ops))
		return NULL;

	
	boinc_ops_cumulative(floating_point_ops, integer_ops);

	Py_INCREF(Py_None);
	return Py_None;	

}


static PyObject *bindings_boinc_upload_file(PyObject *self, PyObject *args)
{


	char *name;

	if (!PyArg_ParseTuple(args, "s", &name))
		return NULL;

	string str_name(name);

	int retval;

	retval = boinc_upload_file(str_name);

	if(retval == ERR_FOPEN) {
		PyErr_SetString(PyExc_IOError, "call to boinc_fopen() in boinc_upload_file() failed, opening the file failed");
		return NULL;
	} else if (retval == ERR_NULL) {
		PyErr_SetString(BoincError, "call to boinc_resolve_filename() in boinc_upload_file() failed, returned ERR_NULL");
		return NULL;
	}	

	Py_INCREF(Py_None);
	return Py_None;	

}


static PyObject *bindings_boinc_upload_status(PyObject *self, PyObject *args)
{


	char *name;

	if (!PyArg_ParseTuple(args, "s", &name))
		return NULL;

	string str_name(name);

	int retval;

	retval = boinc_upload_status(str_name);

	if(retval == ERR_NOT_FOUND) {
		PyErr_SetString(PyExc_ValueError, "call to boinc_upload_status() failed because filename didn\'t match one previously given");
		return NULL;
	}

	return Py_BuildValue("i", retval);

}

/**************************************************************
A few notes on the trickle message API implementation...

The 'documentation' at:
http://boinc.berkeley.edu/trac/wiki/TrickleApi
seems to me to be inadequate (more inadequate than most BOINC api documentation),
and I had to study the source code for a while to figure out what to do.

Hidden somewhere in the changelogs was the following:


" ...
    - Completed (more or less) the implementation of trickle messages.
        Some changes:
        - Trickle-up messages now have a "variety",
            specified by the application.
            Typically it's the name of the application.
            The trickle-up handler (on the server side) specifies what
            variety of message it wants to handle.
        - boinc_receive_trickle_down() no longer returns the message itself;
            instead, it returns the name of the file.
            The app must open, read and delete the file.
... "


From this, we infer:
- boinc_receive_trickle_down() returns a filename.
- there is no limit on the length of the filename
- it is up to the client to open, read and delete the file!

And we decide:
- as the trickle message might be quite big (who knows,
  it might even contain base64 blobs...), we do not
  try and handle the open/read/delete logic for the application

But we must ask:
- what happens if the server tries to send multiple trickle messages?

*********************************************************************/

static PyObject *bindings_boinc_send_trickle_up(PyObject *self, PyObject *args)
{
	char *variety;
	char *text;

	int variety_len;

	if (!PyArg_ParseTuple(args, "ss", &variety, &text))
		return NULL;


	variety_len = strlen(variety);

	if(variety_len > 256) {
		PyErr_SetString(PyExc_ValueError, "variety argument was too long; must be maximum of 256 characters");
		return NULL;
	}

	int retval;

	retval = boinc_send_trickle_up(variety,text);



	if(retval == ERR_FOPEN) {
		PyErr_SetString(PyExc_IOError, "error opening trickle file");
		return NULL;		
	} else if (retval == ERR_NO_OPTION) {
		PyErr_SetString(BoincError, "option handle_trickle_ups not set");
		return NULL;
	} else if (retval == ERR_WRITE) {
		PyErr_SetString(PyExc_IOError, "error writing trickle up message to trickle file");
		return NULL;
	}


	cout << "retval=" << retval << endl;

	Py_INCREF(Py_None);
	return Py_None;	
	
}

static PyObject *bindings_boinc_receive_trickle_down(PyObject *self, PyObject *args)
{

	/* Hopefully this will be long enough to store the filename
	(it's copied with strncpy(3) so anything extra will fall off the end) */
	char buf[1024];
	int len = 1024;

	int retval;

	if (!PyArg_ParseTuple(args, ""))
		return NULL;


	retval = boinc_receive_trickle_down(buf,len);

	/* Cannot destinguish between no message and options not set
	-- retval will be false either way! */
	if(retval) {
		Py_INCREF(Py_None);
		return Py_None;	
	}


	return Py_BuildValue("s", buf); 


}


static PyObject *bindings_boinc_get_status(PyObject *self, PyObject *args)
{
	BOINC_STATUS current_status;


	if (!PyArg_ParseTuple(args, ""))
		return NULL;

	boinc_get_status(&current_status);

	return Py_BuildValue("{s:i,s:i,s:i,s:i,s:i,s:d,s:d}", \
		"no_heartbeat", current_status.no_heartbeat, \
		"suspended", current_status.suspended, \
		"quit_request", current_status.quit_request, \
		"reread_init_data_file", current_status.reread_init_data_file, \
		"abort_request", current_status.abort_request, \
		"working_set_size", current_status.working_set_size, \
		"max_working_set_size", current_status.max_working_set_size);
}

static PyObject *bindings_boinc_report_app_status(PyObject *self, PyObject *args)
{
	double cpu_time;
	double checkpoint_cpu_time;
	double fraction_done;

	if (!PyArg_ParseTuple(args, "ddd", &cpu_time, &checkpoint_cpu_time, &fraction_done))
		return NULL;

	// always returns zero, don't capture return value
	boinc_report_app_status(cpu_time, checkpoint_cpu_time, fraction_done);

	Py_INCREF(Py_None);
	return Py_None;	


}




// TODO! Implement this, not done yet.

// static PyObject *bindings_boinc_init_diagnostics(PyObject *self, PyObject *args)
// {
//
// }
