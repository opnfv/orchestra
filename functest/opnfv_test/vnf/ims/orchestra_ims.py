#!/usr/bin/env python

# Copyright (c) 2016 Orange and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0

import json
import socket
import subprocess
import time

import functest.core.vnf_base as vnf_base
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import functest.utils.openstack_utils as os_utils
import os
import requests
from functest.utils.constants import CONST

from org.openbaton.cli.agents.agents import MainAgent
from org.openbaton.cli.errors.errors import NfvoException


def servertest(host, port):
    args = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    for family, socktype, proto, canonname, sockaddr in args:
        s = socket.socket(family, socktype, proto)
        try:
            s.connect(sockaddr)
        except socket.error:
            return False
        else:
            s.close()
            return True


class ImsVnf(vnf_base.VnfOnBoardingBase):
    def __init__(self, project='functest', case='orchestra_ims',
                 repo='', cmd=''):
        super(ImsVnf, self).__init__(project, case, repo, cmd)
        self.ob_password = "openbaton"
        self.ob_username = "admin"
        self.ob_https = False
        self.ob_port = "8080"
        self.ob_ip = "localhost"
        self.ob_instance_id = ""
        self.logger = ft_logger.Logger("vIMS").getLogger()
        self.case_dir = os.path.join(CONST.functest_test, 'vnf/ims/')
        self.data_dir = CONST.dir_vIMS_data
        self.test_dir = CONST.dir_repo_vims_test
        self.ob_projectid = ""
        self.keystone_client = os_utils.get_keystone_client()
        self.ob_nsr_id = ""
        self.main_agent = None
        # vIMS Data directory creation
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def deploy_orchestrator(self, **kwargs):
        nova_client = os_utils.get_nova_client()
        neutron_client = os_utils.get_neutron_client()
        glance_client = os_utils.get_glance_client()

        network_dic = os_utils.create_network_full(neutron_client,
                                                   "openbaton_mgmt",
                                                   "openbaton_mgmt_subnet",
                                                   "openbaton_router",
                                                   "192.168.100.0/24")
        if not network_dic:
            self.logger.error("There has been a problem when creating the neutron network")

        network_id = network_dic["net_id"]

        self.logger.info("Creating floating IP for VM in advance...")
        floatip_dic = os_utils.create_floating_ip(neutron_client)
        floatip = floatip_dic['fip_addr']

        if floatip is None:
            self.logger.error("Cannot create floating IP.")

        userdata = "#!/bin/bash\n"
        userdata += "set -x\n"
        userdata += "set -e\n"
        userdata += "echo \"nameserver   8.8.8.8\" >> /etc/resolv.conf\n"
        userdata += "apt-get install curl\n"
        userdata += "echo \"rabbitmq_broker_ip=%s\" > ./config_file\n" % floatip
        userdata += "echo \"mysql=no\" >> ./config_file\n"
        userdata += "echo \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCuPXrV3geeHc6QUdyUr/1Z+yQiqLcOskiEGBiXr4z76MK4abiFmDZ18OMQlcfl0p3kS0WynVgyaOHwZkgy/DIoIplONVr2CKBKHtPK+Qcme2PVnCtvEqItl/FcD+1h5XSQGoa+A1TSGgCod/DPo+pes0piLVXP8Ph6QS1k7Sic7JDeRQ4oT1bXYpJ2eWBDMfxIWKZqcZRiGPgMIbJ1iEkxbpeaAd9O4MiM9nGCPESmed+p54uYFjwEDlAJZShcAZziiZYAvMZhvAhe6USljc7YAdalAnyD/jwCHuwIrUw/lxo7UdNCmaUxeobEYyyFA1YVXzpNFZyaXPGAAYIJwEq/ openbaton@opnfv\" >> /home/ubuntu/.ssh/authorized_keys\n"
        userdata += "cat ./config_file\n"
        userdata += "curl -s http://get.openbaton.org/bootstrap > ./bootstrap\n"
        userdata += "export OPENBATON_COMPONENT_AUTOSTART=false\n"
        bootstrap = "sh ./bootstrap release -configFile=./config_file"
        userdata += bootstrap + "\n"

        userdata += "echo \"nfvo.plugin.timeout=300000\" >> /etc/openbaton/openbaton-nfvo.properties\n"
        userdata += "service openbaton-nfvo restart\n"
        userdata += "service openbaton-vnfm-generic restart\n"

        self.logger.debug("Userdata is:\n%s" % userdata)

        imagename = ft_utils.get_functest_config("vnf.orchestra_ims.openbaton.imagename")

        sg_id = os_utils.create_security_group_full(neutron_client,
                                                    "orchestra-sec-group",
                                                    "allowall")

        os_utils.create_secgroup_rule(neutron_client, sg_id, "ingress", "icmp", 0, 255)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "egress", "icmp", 0, 255)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "ingress", "tcp", 1, 65535)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "ingress", "udp", 1, 65535)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "egress", "tcp", 1, 65535)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "egress", "udp", 1, 65535)

        instance = os_utils.create_instance_and_wait_for_active("m1.medium",
                                                                os_utils.get_image_id(glance_client, imagename),
                                                                network_id,
                                                                "orchestra-openbaton",
                                                                config_drive=False,
                                                                userdata=userdata)

        self.ob_instance_id = instance.id

        self.logger.info("Adding sec group to orchestra instance")
        os_utils.add_secgroup_to_instance(nova_client, self.ob_instance_id, sg_id)

        self.logger.info("Associating floating ip: '%s' to VM '%s' " % (floatip, "orchestra-openbaton"))
        if not os_utils.add_floating_ip(nova_client, instance.id, floatip):
            self.logger.error("Cannot associate floating IP to VM.")
            self.step_failure("Cannot associate floating IP to VM.")

        self.logger.info("Waiting for nfvo to be up and running...")
        x = 0
        while x < 100:
            if servertest(floatip, "8080"):
                break
            else:
                self.logger.debug("openbaton is not started yet")
                time.sleep(5)
                x += 1

        if x == 100:
            self.logger.error("Openbaton is not started correctly")
            self.step_failure("Openbaton is not started correctly")

        self.ob_ip = floatip
        self.ob_password = "openbaton"
        self.ob_username = "admin"
        self.ob_https = False
        self.ob_port = "8080"

        self.logger.info("Deploy orchestrator: OK")

    def deploy_vnf(self):
        self.logger.info("vIMS Deployment")

        self.main_agent = MainAgent(nfvo_ip=self.ob_ip,
                                    nfvo_port=self.ob_port,
                                    https=self.ob_https,
                                    version=1,
                                    username=self.ob_username,
                                    password=self.ob_password)

        project_agent = self.main_agent.get_agent("project", self.ob_projectid)
        for p in json.loads(project_agent.find()):
            if p.get("name") == "default":
                self.ob_projectid = p.get("id")
                break

        self.logger.debug("project id: %s" % self.ob_projectid)
        if self.ob_projectid == "":
            self.logger.error("Default project id was not found!")
            self.step_failure("Default project id was not found!")

        vim_json = {
            "name": "vim-instance",
            "authUrl": os_utils.get_credentials().get("auth_url"),
            "tenant": os_utils.get_credentials().get("tenant_name"),
            "username": os_utils.get_credentials().get("username"),
            "password": os_utils.get_credentials().get("password"),
            "keyPair": "opnfv", # TODO change the keypair to correct value or upload a correct one or remove it
            "securityGroups": [
                "default","orchestra-sec-group"
            ],
            "type": "openstack",
            "location": {
                "name": "opnfv",
                "latitude": "52.525876",
                "longitude": "13.314400"
            }
        }

        self.logger.debug("vim: %s" % vim_json)

        self.main_agent.get_agent("vim", project_id=self.ob_projectid).create(entity=json.dumps(vim_json))

        market_agent = self.main_agent.get_agent("market", project_id=self.ob_projectid)

        market_link = ft_utils.get_functest_config("vnf.orchestra_ims.openbaton.marketplace_link")

        nsd = {}
        try:
            self.logger.info("sending: %s" % market_link)
            nsd = market_agent.create(entity=market_link)
            self.logger.info("Onboarded nsd: " + nsd.get("name"))
        except NfvoException as e:
            self.step_failure(e.message)

        nsr_agent = self.main_agent.get_agent("nsr", project_id=self.ob_projectid)
        nsd_id = nsd.get('id')
        if nsd_id is None:
            self.step_failure("NSD not onboarded correctly")

        nsr = None
        try:
            nsr = nsr_agent.create(nsd_id)
        except NfvoException as e:
            self.step_failure(e.message)

        if nsr is None:
            self.step_failure("NSR not deployed correctly")

        i = 0
        self.logger.info("waiting NSR to go to active...")
        while nsr.get("status") != 'ACTIVE':
            i += 1
            if i == 100:
                self.step_failure("After %s sec the nsr did not go to active..." % 5 * 100)
            time.sleep(5)
            nsr = json.loads(nsr_agent.find(nsr.get('id')))

        deploy_vnf = {'status': "PASS", 'result': nsr}
        self.ob_nsr_id = nsr.get("id")
        self.logger.info("Deploy VNF: OK")
        return deploy_vnf

    def test_vnf(self):
        # Adaptations probably needed
        # code used for cloudify_ims
        # ruby client on jumphost calling the vIMS on the SUT
        return

    def clean(self):
        self.main_agent.get_agent("nsr", project_id=self.ob_projectid).delete(self.ob_nsr_id)
        time.sleep(5)
        os_utils.delete_instance(nova_client=os_utils.get_nova_client(), instance_id=self.ob_instance_id)
        # TODO question is the clean removing also the VM? i think so since is goinf to remove the tenant...
        super(ImsVnf, self).clean()


if __name__ == '__main__':
    test = ImsVnf()
    test.deploy_orchestrator()
    test.deploy_vnf()
    test.clean()
