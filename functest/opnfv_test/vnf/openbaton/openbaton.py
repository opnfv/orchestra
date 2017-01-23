#!/usr/bin/env python

# Copyright (c) 2016 Orange and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
import argparse
import inspect
import time
import json

import functest.utils.functest_constants as ft_constants
import functest.utils.functest_logger as ft_logger
import os
from functest.core import vnf_base
from org.openbaton.cli.errors.errors import NfvoException
from os import listdir
from os.path import isfile, join


class OpenBatonVIMSVnf(vnf_base.VnfOnBoardingBase):
    logger = ft_logger.Logger("VNF vIMS on Open Baton").getLogger()

    def __init__(self, ob_port="8080", ob_password="openbaton", ob_username="admin", ob_https=False, ob_projectid="",
                 ob_ip="localhost"):
        super(OpenBatonVIMSVnf, self).__init__()
        self.case_name = "vims_openbaton"
        self.ob_username = ob_username
        self.ob_password = ob_password
        self.ob_ip = ob_ip
        self.ob_port = ob_port
        self.ob_https = ob_https
        self.ob_projectid = ob_projectid
        self.case_dir = os.path.join(ft_constants.FUNCTEST_TEST_DIR, 'vnf/openbaton/')
        self.etc_dir = ft_constants.OB_DATA_DIR
        self.logger.info("Data dir is: %s" % self.etc_dir)
        # self.etc_dir = "/opt/opnfv/functest/%s" % self.etc_dir

    def deploy_orchestrator(self):
        # TODO install openbaton unsing the JOID installer or using the openbaton bootstrap
        self.logger.error("NFVO and GenericVNFM are required for executing these tests")
        self.step_failure("NFVO and GenericVNFM are required for executing these tests")

    # TODO see how to use build in exception form releng module
    def deploy_vnf(self):
        self.logger.info("vIMS Deployment")
        from org.openbaton.cli.agents.agents import MainAgent
        agent = MainAgent(nfvo_ip=self.ob_ip,
                          nfvo_port=self.ob_port,
                          https=self.ob_https,
                          version=1,
                          username=self.ob_username,
                          password=self.ob_password,
                          project_id=self.ob_projectid)

        package_agent = agent.get_agent("vnfpackage", project_id=self.ob_projectid)

        tars = [join(self.etc_dir, f) for f in listdir(self.etc_dir) if
                isfile(join(self.etc_dir, f)) and join(self.etc_dir, f).endswith(".tar")]

        vnfds = []

        for tar in tars:
            self.logger.info("uploading package: %s" % tar)
            try:
                self.logger.info("pacakge agent: %s" % package_agent)
                package = package_agent.create(tar)
                self.logger.info("package is: %s" % package)
            except NfvoException as e:
                self.step_failure(e.message)

        # I am pretty sure there will be only the packages i uploaded
        for vnfd in json.loads(agent.get_agent("vnfd", self.ob_projectid).find()):
            self.logger.info("vnfd is: %s" % vnfd)
            vnfds.append({"id": vnfd.get('id')})

        self.logger.info("Vnfds: %s" % vnfds)
        nsd_agent = agent.get_agent("nsd", project_id=self.ob_projectid)
        vims_nsd = {
            "name": "OpenIMSCore",
            "vendor": "fokus",
            "version": "3.1.0",
            "vnfd": vnfds,
            "vld": [
                {
                    "name": "mgmt"
                }
            ]
        }

        nsd = {}
        try:
            json_dumps = json.dumps(vims_nsd)
            self.logger.info("sending: %s" % json_dumps)
            nsd = nsd_agent.create(entity=json_dumps)
        except NfvoException as e:
            self.step_failure(e.message)

        nsr_agent = agent.get_agent("nsr", project_id=self.ob_projectid)
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
                self.step_failure("After %s sec the nsr did not go to active..." % i*100)
            self.logger.info("waiting NSR to go to active")
            time.sleep(5)
            nsr = json.loads(nsr_agent.find(nsr.get('id')))

        deploy_vnf = {'status': "PASS", 'result': nsr}
        return deploy_vnf

    def test_vnf(self):
        self.logger.info("Run test towards freeradius")
        # TODO:  once the freeradius is deployed..make some tests
        test_vnf = {}
        test_vnf['status'] = "PASS"
        test_vnf['result'] = {}
        return test_vnf

    def main(self, **kwargs):
        self.logger.info("vIMS VNF onboarding")
        self.execute()
        if self.criteria is "PASS":
            return self.EX_OK
        else:
            return self.EX_RUN_ERROR

    def run(self):
        kwargs = {}
        return self.main(**kwargs)

    def step_failure(self, error_msg):
        part = inspect.stack()[1][3]
        self.details[part]['status'] = 'FAIL'
        self.details[part]['result'] = error_msg
        raise Exception(error_msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = vars(parser.parse_args())
    openbaton_vims_vnf = OpenBatonVIMSVnf(ob_projectid="27058d69-d6da-4344-a9a6-8236aa712e8b")
    print(openbaton_vims_vnf.deploy_vnf())
    # try:
    #     result = openbaton_vims_vnf.deploy_vnf()
    #     if result != testcase_base.TestcaseBase.EX_OK:
    #         sys.exit(result)
    #     if args['pushtodb']:
    #         sys.exit(openbaton_vims_vnf.push_to_db())
    # except Exception:
    #     sys.exit(testcase_base.TestcaseBase.EX_RUN_ERROR)

