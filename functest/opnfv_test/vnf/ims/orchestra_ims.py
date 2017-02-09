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
        # self.case_dir = os.path.join(CONST.functest_test, 'vnf/ims/')
        # self.data_dir = CONST.dir_vIMS_data
        # self.test_dir = CONST.dir_repo_vims_test
        self.ob_projectid = ""
        self.ob_nsr_id = ""
        self.main_agent = None
        # vIMS Data directory creation
        # if not os.path.exists(self.data_dir):
        #     os.makedirs(self.data_dir)

    def deploy_orchestrator(self, **kwargs):
        # TODO
        # put your code here to deploy openbaton
        # from the functest docker located on the jumphost
        # you have admin rights on OpenStack SUT
        # you can cretae a VM, spawn docker on the jumphost
        # spawn docker on a VM in the SUT, ..up to you
        #
        # note: this step can be ignored
        # if OpenBaton is part of the installer

        nova_client = os_utils.get_nova_client()
        neutron_client = os_utils.get_neutron_client()
        glance_client = os_utils.get_glance_client()

        bootstrap = ft_utils.get_functest_config("vnf.orchestra_ims.openbaton.bootstrap")
        bootstrap = "sh ./bootstrap release -configFile=./config_file"

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
        userdata += "apt-get install curl\n"
        userdata += "echo \"rabbitmq_broker_ip=%s\" > ./config_file\n" % floatip
        userdata += "echo \"mysql=no\" >> ./config_file\n"
        userdata += "echo \"ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDE993NSp+dMEDXeHzmSX+2GfMV81KjVtqcnq1aRz4+Lsgfdb824N+XFDusXYuCeMa2zb/7eZSMAkwL93XCD39wYmO+gpD6vtPTCVkFLBI3unSrjkVyoBRCsAzSHbYKwpc5dm92NfvKEBbEStvLZ7l4uAaNCAdzdGU6MRJkozQV24NdTUJ4N4OTLICsdD/Cg8q64zr3kphxn6zVXVrcR05TJLx/r2GxrO9/UDiE6Vv/PPWQed/dQIsgZReXGGSwVq7EthQYVvtwJuN0BW0XEmqHOtHzlgBYRp/f4rF6Yt1p3eaCsHUf2V1gg2uLncs7DstPIV+8/zJKtMKSKVWEUpNx openbaton@openbaton-dc-7.openbaton-dc-7domain.com\" >> /home/ubuntu/.ssh/authorized_keys\n"
        userdata += "cat ./config_file\n"
        userdata += "curl -s http://get.openbaton.org/bootstrap > ./bootstrap\n"
        userdata += bootstrap

        self.logger.info("Userdata is:\n%s" % userdata)

        imagename = ft_utils.get_functest_config("vnf.orchestra_ims.openbaton.imagename")

        sg_id = os_utils.create_security_group_full(neutron_client,
                                                    "orchestra-sec-group",
                                                    "allowall")

        os_utils.create_secgroup_rule(neutron_client, sg_id, "ingress", "tcp", 1, 65535)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "ingress", "udp", 1, 65535)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "engress", "tcp", 1, 65535)
        os_utils.create_secgroup_rule(neutron_client, sg_id, "engress", "udp", 1, 65535)

        instance = os_utils.create_instance_and_wait_for_active("m1.medium",
                                                                os_utils.get_image_id(glance_client, imagename),
                                                                network_id,
                                                                "orchestra-openbaton",
                                                                config_drive=False,
                                                                userdata=userdata)

        self.ob_instance_id = instance.id

        self.logger.info("Associating floating ip: '%s' to VM '%s' " % (floatip, "orchestra-openbaton"))

        if not os_utils.add_floating_ip(nova_client, instance.id, floatip):
            self.logger.error("Cannot associate floating IP to VM.")
            self.step_failure("Cannot associate floating IP to VM.")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        x = 0
        result = 1
        while x < 100:
            result = sock.connect_ex((floatip, 8080))
            if servertest(floatip, "8080"):
                break
            else:
                self.logger.info("openbaton is not started yet")
                time.sleep(5)
                x += 1

        if result == 1:
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

        self.ob_ip = "192.168.161.165"

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

        self.logger.info("project id: %s" % self.ob_projectid)
        print os_utils.get_credentials()
        vim_json = {
            "name": "vim-instance",
            "authUrl": os_utils.get_credentials().get("auth_url"),
            "tenant": os_utils.get_credentials().get("tenant_name"),
            "username": os_utils.get_credentials().get("username"),
            "password": os_utils.get_credentials().get("password"),
            "keyPair":"stack",
            "securityGroups": [
                "default"
            ],
            "type": "openstack",
            "location": {
                "name": "opnfv",
                "latitude": "52.525876",
                "longitude": "13.314400"
            }
        }

        self.logger.info("vim: %s" % vim_json)

        self.main_agent.get_agent("vim", project_id=self.ob_projectid).create(entity=json.dumps(vim_json))

        market_agent = self.main_agent.get_agent("market", project_id=self.ob_projectid)

        market_link = "http://marketplace.openbaton.org:8082/api/v1/nsds/80a5cd0e-53cf-431f-9215-b43e5c33592d/json/"

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
        while nsr.get("status") != 'ACTIVE':
            i += 1
            if i == 100:
                self.step_failure("After %s sec the nsr did not go to active..." % i * 100)
            self.logger.info("waiting NSR to go to active")
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
        script = "source {0}venv_cloudify/bin/activate; "
        script += "cd {0}; "
        script += "cfy status | grep -Eo \"([0-9]{{1,3}}\.){{3}}[0-9]{{1,3}}\""
        cmd = "/bin/bash -c '" + script.format(self.data_dir) + "'"

        try:
            self.logger.debug("Trying to get clearwater manager IP ... ")
            mgr_ip = os.popen(cmd).read()
            mgr_ip = mgr_ip.splitlines()[0]
        except:
            self.step_failure("Unable to retrieve the IP of the "
                              "cloudify manager server !")

        api_url = "http://" + mgr_ip + "/api/v2"
        dep_outputs = requests.get(api_url + "/deployments/" +
                                   self.vnf.deployment_name + "/outputs")
        dns_ip = dep_outputs.json()['outputs']['dns_ip']
        ellis_ip = dep_outputs.json()['outputs']['ellis_ip']

        ellis_url = "http://" + ellis_ip + "/"
        url = ellis_url + "accounts"

        params = {"password": "functest",
                  "full_name": "opnfv functest user",
                  "email": "functest@opnfv.fr",
                  "signup_code": "secret"}

        rq = requests.post(url, data=params)
        i = 20
        while rq.status_code != 201 and i > 0:
            rq = requests.post(url, data=params)
            i = i - 1
            time.sleep(10)

        if rq.status_code == 201:
            url = ellis_url + "session"
            rq = requests.post(url, data=params)
            cookies = rq.cookies

        url = ellis_url + "accounts/" + params['email'] + "/numbers"
        if cookies != "":
            rq = requests.post(url, cookies=cookies)
            i = 24
            while rq.status_code != 200 and i > 0:
                rq = requests.post(url, cookies=cookies)
                i = i - 1
                time.sleep(25)

        if rq.status_code != 200:
            self.step_failure("Unable to create a number: %s"
                              % rq.json()['reason'])

        nameservers = ft_utils.get_resolvconf_ns()
        resolvconf = ""
        for ns in nameservers:
            resolvconf += "\nnameserver " + ns

        if dns_ip != "":
            script = ('echo -e "nameserver ' + dns_ip + resolvconf +
                      '" > /etc/resolv.conf; ')
            script += 'source /etc/profile.d/rvm.sh; '
            script += 'cd {0}; '
            script += ('rake test[{1}] SIGNUP_CODE="secret"')

            cmd = ("/bin/bash -c '" +
                   script.format(self.data_dir, self.inputs["public_domain"]) +
                   "'")
            output_file = "output.txt"
            f = open(output_file, 'w+')
            subprocess.call(cmd, shell=True, stdout=f,
                            stderr=subprocess.STDOUT)
            f.close()

            f = open(output_file, 'r')
            result = f.read()
            if result != "":
                self.logger.debug(result)

            vims_test_result = ""
            tempFile = os.path.join(self.test_dir, "temp.json")
            try:
                self.logger.debug("Trying to load test results")
                with open(tempFile) as f:
                    vims_test_result = json.load(f)
                f.close()
            except:
                self.logger.error("Unable to retrieve test results")

            try:
                os.remove(tempFile)
            except:
                self.logger.error("Deleting file failed")

            if vims_test_result != '':
                return {'status': 'PASS', 'result': vims_test_result}
            else:
                return {'status': 'FAIL', 'result': ''}

    def clean(self):
        super(ImsVnf, self).clean()
        self.main_agent.get_agent("nsr", project_id=self.ob_projectid).delete(self.ob_nsr_id)
        time.sleep(5)
        os_utils.delete_instance(nova_client=os_utils.get_nova_client(), instance_id=self.ob_instance_id)


if __name__ == '__main__':
    test = ImsVnf()
    # test.deploy_orchestrator()
    test.deploy_vnf()
    test.clean()
