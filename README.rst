Overview
========

The *of_flow_manager* NApp exports a REST API to add, remove,
list flows from OpenFlow switches, for versions 1.0 and 1.3.
It can be used by other applications to manage flows with the supported fields.

This application creates an abstraction layer to other applications:
it is only necessary to know the endpoints. The application handles
the requests and return the information already formatted.

Installing
==========

All of the Kytos Network Applications are located in the NApps online repository.
To install this NApp, run:

.. code:: shell

   $ kytos napps install kytos/of_flow_manager

Rest API
========

You can find a list of the available endpoints and example input/output in the
'REST API' tab in this NApp's webpage in the `Kytos NApps Server
<https://napps.kytos.io/kytos/of_flow_manager>`_.
