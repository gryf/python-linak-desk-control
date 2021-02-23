=========================
python-linak-desk-control
=========================

This is a simple program for controlling LINAK Desk Control Cable in linux with
simple python and `libusb1`_.

It's a Python implementation of `C-Routine of ranma1988`_

Tested on: Gentoo x64 (December 2018). Might work on Windows too.
Tested on model: usb2lin06 with CONTROL BOX CBD6S without safety limit.

Dependencies
------------

This program is using `libusb1`_ which is python wrapper on `libusb` C library.
You can install it by searching for appropriate package in you operating system
(i.e. there is a ``python3-libusb1`` package for Ubuntu), or build by yourself
issuing following command:

.. code:: shell-session

   $ pip install -r requirements.txt

Note, that for build process, you might need to have devel packages for
`libusb`_ C library installed.

Capabilities
------------

* setting height
* retrieve current height

Usage
-----

Just trying out in your shell is easy:

.. code:: shell-session

   $ python3 linak-desk-control.py

It will show you mostly the whole help in order to understand which commands
can be executed. E.g. to get the current height:

.. code:: shell-session

   $ python3 linak-desk-control.py height

And to bring the desk to height 4414:

.. code:: shell-session

   $ python3 linak-desk-control.py move 4414



License
-------

This piece of work is distributed with GNU GPLv3 or later.


.. _libusb1: https://github.com/vpelletier/python-libusb1
.. _C-Routine of ranma1988: https://github.com/ranma1988/usb2lin06-HID-in-linux-for-LINAK-Desk-Control-Cable
.. _libusb: https://libusb.info
