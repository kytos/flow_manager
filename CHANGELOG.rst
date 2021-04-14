#########
Changelog
#########
All notable changes to the flow_manager NApp project will be documented in this
file.

[UNRELEASED] - Under development
********************************
Added
=====

Changed
=======

Deprecated
==========

Removed
=======

Security
========


[4.0] - 2021-05-26
******************
Added
=====
 - Added support to handle with OpenFlow error OFPBAC_BAD_OUT_PORT.
 - Added attempt limits to try to recover box from storehouse, avoiding
   a possible thread lock condition.
 - Added consistency mechanism information in README file.
 - Added support for non-strict exclusion in the consistency check.
 - Add support for the list of exceptions in the consistency mechanism.
 - Add validation to data sent by REST endpoints in requests to install flows.
 - Add support for install or remove flows in the switches using Kytos Events.

Changed
=======
 - Update consistency check to use ``DELETE_STRICT`` to remove 'alien' flows in
   switches.
 - Consistency check routine to recreate the flows when the switch reconnects 
   to Kytos.

Fixed
=====
 - New method to cast ``UBInt`` type to int to solve JSON serialization error.
 - Fix the HTTP status code returned when the switch is not found.

 
[3.0] - 2020-12-23
******************
Added
=====
- Added new consistency check to guarantee the consistency of installed flows
  between switches and the controller.
- Added persistence mechanism to save in storehouse all the
  flows installed by ``kytos/flow_manager``.
- Added mechanism to resend stored flows in Kytos bootstrap.
- Include the original command in the list of sent flow mods.

Changed
=======
- Updated flow installation to allow removal of flows from disabled switches.
- Changed setup.py to alert when a test fails on Travis.


[2.3] - 2020-07-07
******************
Added
=====
- Added unit tests, increasing coverage to 97%.
- Added listener to handle OpenFlow errors sent by ``of_core``.
- Added HTTP DELETE method support to REST API on ``/flows``.
- Added the error code of the flow mod message to the content
  of the resulting event.
- Started to use ``FlowFactory`` to check which version of ``Flow`` to use.
- Added ``@tags`` decorator to run tests by type and size.


[2.2.2] - 2019-03-15
********************
Changed
=======
- Continuous integration enabled at scrutinizer.

Fixed
=====
- Improve code organization and fix some linter issues.


[2.2.1] - 2018-12-14
********************

Fixed
=====
 - Fix `flow` being used outside of its scope when installing a flow.


[2.2.0] - 2018-06-15
********************

Changed
=======
- Send flow_mod to only enabled switches.
- Change enabled attributes to use the method is_enabled.


[2.1.0] - 2018-04-20
********************

Changed
=======
- Update kytos.json version form 2.0.0 to 2.1.0.
- Send flow_mod to only enabled switches.
- Return 404 status code when dpid is not found.

Fixed
=====
- Fix actions to have correct type and value pair.
- Fix OpenAPI.yml.
- Some type fixes.


[2.0.0] - 2017-11-30
********************
Added
=====
- Add REST API Version.
- Send app specific events when sending a flow_mod.
- Add documentation for of_flow_manager.
- Implement endpoint for add/delete/list flows.
- Added methods to deal with 1.0/1.3 flows.
- Adding dependencies in kytos.json.

Changed
=======
- Change request body of the rest api.
- Change rest api to return Response with mimetype='application/json'.
- Change list of flows to dictitonary.
- Change actions field from dict to list in bodies.
- Standardize models and examples.
- Change 'Response' to 'Flows'.
- Change HTTP success code for add flows.
- Change Napp name  to `kytos/flow_manager` and tags


[1.1.3] - 2017-06-16
********************
Added
=====
- Added examples of requests/replies to of_flow_manager REST endpoints.
- Added rest api endpoints and JSON input/output.


[0.1.0] - 2016-11-09
********************
Added
=====
- Created application to register REST endpoints to manage flows.
