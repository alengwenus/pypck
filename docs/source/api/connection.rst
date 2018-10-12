:mod:`pypck.connection`
-----------------------

.. automodule:: pypck.connection
	
.. autoclass:: PchkConnection
	:members:
		connect,
		close,
		send_command,
		send_command_async,
		process_input
		
.. autoclass:: PchkConnectionManager
	:members:
		connect,
		get_lcn_connected,
		is_ready,
		get_module_conn
