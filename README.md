SpaceCraft
==========

An AI space fighting playground.

You can use fabric to do pretty much anything there is to do currently:

To run the tests
----------------

$ fab test


To start a server
-----------------

    $ fab run_server

Extra arguments can be passed into this command in two different (ugly) ways:

    $ fab run_server:--xsize,1234

or:

    $ fab "run_server:--xsize 1234"


To start a client
-----------------

    $ fab run_client

You can start more than one client at a time


To start a monitor
------------------

    $ fab run_monitor

Like with clients, you can start more than one monitor at a time.


TODO
----

- everything
- wraparound
- bullets
- energy
- game logic

