.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. SPDX-License-Identifier: CC-BY-4.0
.. (c) Fraunhofer FOKUS

============================================
OPNFV Euphratest release notes for Orchestra
============================================


Abstract
========

This document describes the release note of the Orchestra project.


Version history
===============

+------------+----------+--------------------+------------------------+
| **Date**   | **Ver.** | **Author**         | **Comment**            |
|            |          |                    |                        |
+------------+----------+--------------------+------------------------+
| 2017-08-25 | 1.0.0    | Giuseppe Carella   | Euphrates.1.0 release  |
|            |          | (Fraunhofer FOKUS) |                        |
+------------+----------+--------------------+------------------------+

Important notes
===============

The OPNFV Orchestra project started with the main objective of integrating
the Open Baton open source framework with OPNFV. The initial main objective was
to allow OPNFV users to get an Open Baton environment up and running using
OPNFV installers.
Furthermore, the Orchestra team collaborates with testing projects in order
to include some scenarios for validating the actual integration between the
Open Baton project and the OPNFV platform.


OPNFV Orchestra Euphrates Release
=================================

During the Euphrates release, the Orchestra team focused mainly in integrating
Orchestra with the JOID installer, and in extending the testing scenarios
developed in the context of the Functest project.

With the JOID installer users can easily get a ready-to-go Open Baton environment
selecting the 'os-nosdn-openbaton-ha' scenario. After the installation,
Open Baton release 4 will be available as part of the OPNFV environment. Users can
refer to the Open Baton documentation in order to get started immediately
on boarding their VNFs and network services.

Using functest users can test the integration of the orchestra project with the OPNFV
platform. In particular, there are two use cases implementing the automated on boarding and
deployment of a classical IMS network service on top of the OPNFV platform:

* `OpenIMSCore <http://openimscore.org/>`
* `Clearwater IMS <http://www.projectclearwater.org/>`



Useful links
============

 - wiki project page: https://wiki.opnfv.org/display/PROJ/Orchestra

 - Open Baton web site: http://openbaton.github.io/



