########
Overview
########

.. attention::

    THIS NAPP IS STILL EXPERIMENTAL AND IT'S EVENTS, METHODS AND STRUCTURES MAY
    CHANGE A LOT ON THE NEXT FEW DAYS/WEEKS, USE IT AT YOUR OWN DISCERNEMENT


The *kytos/flow_manager* NApp exports a REST API to add, remove,
list flows from OpenFlow switches, for versions 1.0 and 1.3.
It can be used by other applications to manage flows with the supported fields.

This application creates an abstraction layer to other applications:
it is only necessary to know the endpoints. The application handles
the requests and return the information already formatted.

Supported Fields
****************

This NApp support a subset of the OpenFlow specification fields in the bodies of
the requests when creating and removing flows:

- Flow attributes:

  - priority: Priority of the flow entry when matching packets;
  - idle_timeout: Time before the flow expires when no packet is matched;
  - hard_timeout: Time before the flow expires, not related to matching;
  - cookie: Flow cookie;
  - match:

    - in_port: Port where the packet came from;
    - dl_src: Ethernet frame source MAC address;
    - dl_dst: Ethernet frame destination MAC address;
    - dl_type: EtherType of the upper layer protocol;
    - dl_vlan: 802.1q VLAN ID;
    - dl_vlan_pcp: 802.1q VLAN PCP;
    - nw_src: IPv4 source address of the packet;
    - nw_dst: IPv4 destination address of the packet;
    - nw_proto: Upper layer protocol number;

  - actions:

    - set_vlan: Change the VLAN ID of the packet;
    - output: Send the packet through a port.

.. note::

    For the Output Action port you may use any port number or the string
    "controller". The string will be interpreted and converted to the correct
    controller port number for the datapath protocol version.

.. note::

    For OpenFlow 1.3, the only Instruction supported is InstructionApplyAction.

Other fields are not supported and will generate error messages from the NApp.

##########
Installing
##########

All of the Kytos Network Applications are located in the NApps online repository.
To install this NApp, run:

.. code:: shell

   $ kytos napps install kytos/flow_manager

######
Events
######

Generated
*********

kytos/flow_manager.flow.added
=============================

*buffer*: ``app``

Event reporting that a FlowMod was sent to a Datapath with the ADD command.

Content
-------

.. code-block:: python3

   {
     'datapath': <Switch object>,
     'flow': <Object representing the installed flow>
   }

kytos/flow_manager.flow.removed
===============================

*buffer*: ``app``

Event reporting that a FlowMod was sent to a Datapath with the DELETE command.

Content
-------

.. code-block:: python3

   {
     'datapath': <Switch object>,
     'flow': <Object representing the removed flow>
   }

########
Rest API
########

You can find a list of the available endpoints and example input/output in the
'REST API' tab in this NApp's webpage in the `Kytos NApps Server
<https://napps.kytos.io/kytos/flow_manager>`_.
