.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0


Orchestra Installation
======================
Orchestra is the OPNFV name given to the Open Baton integration project. This documentation explains how to install it.
Please notice that the JOID installer already integrates Orchestra as a scenario. Please refer to the JOID installer in case
you want to install Orchestra using it.

.. contents::
   :depth: 3
   :local:



Hardware configuration
----------------------

No special hardware is needed in order to execute Orchestra. We assume that you are performing
the installation on top of a clean installation either of Ubuntu 14.04, Ubuntu 16.04 or Debian Jessy.
In other cases we suggest to install the components one by one.
You can checkout the bootstrap repository and see the installation procedures which are executed by the bootstrap script.

Orchestra can be installed on any kind of environment (physical hosts, virtual machines, containers, etc.).
So, you can decide either to install it on top of virtual machine running on the jump host or somewhere else.
Suggested requirements in terms of CPUs, Memory, and disk space are:

* minimal: > 2GB of RAM, and > 2CPUs, 10GB of disk space
* suggested: > 8GB of RAM, and > 8CPUs, 10GB of disk space

In general, you may be able to get a working environment also with less perfomant hardware, especially tuning the JVM startup options (i.e -Xms and -Xmx).

Orchestra Bootstrap
-------------------
To facilitate the installation procedures we provide a bootstrap script which
will install the desired components and configure them for running a hello world VNF out of the box.
To execute the bootstrap procedure you need to have curl installed (see http://curl.haxx.se/).
This command should work on any Ubuntu system:

.. code-block:: bash

    apt-get install curl

We provide a non-interactive installation using a configuration file.
Specifically, you need to have the configuration file locally available and to pass it
to the bootstrap command as a parameter. You can download this example of configuration file,
modify it accordingly and execute the bootstrap typing the following command:

.. code-block:: bash

    wget http://get.openbaton.org/bootstraps/orchestra/euphrates/bootstrap-config-file # modify any parameters you want
    sh <(curl -s http://get.openbaton.org/bootstraps/orchestra/euphrates/bootstrap) release --config-file=/home/ubuntu/bootstrap-config-file


VERY IMPORTANT NOTE - By default RabbitMQ is installed on the host of the NFVO.
Be aware of the fact that during the installation you will be prompted for entering the RabbitMQ IP and Port.
Please make sure that this IP can be reached by external components (VMs, or host where will run other VNFMs) otherwise you will have runtime issues.
If you are installing Open Baton on a VM running in OpenStack, the best is that you put here the floating IP.

At this point the NFVO dashboard should be reachable via the following URL http://your-ip-here:8080
