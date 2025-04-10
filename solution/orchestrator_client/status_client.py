#!/usr/bin/env python
# ===================================================================================
# Copyright (C) 2021 Fraunhofer Gesellschaft, Peter Schueller. All rights reserved.
# ===================================================================================
# This Acumos software file is distributed by Fraunhofer Gesellschaft
# under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============LICENSE_END========================================================

# generic parallel orchestrator status client
# arguments:
# --ip/-i <ip> --port/-p <port> --endpoint/-e <ip>:<port>
# functionality:
# get status from orchestrator

import os
import sys
import logging
import argparse
import subprocess
import grpc

SRCDIR = os.path.dirname(os.path.abspath(__file__))

try:
    import orchestrator_pb2
    import orchestrator_pb2_grpc
except:
    # recompile orchestrator client protobuf file if import fails
    logging.warning("exception importing orchestrator_pb2 and orchestrator_pb2_grpc - recompiling!")
    import_dir = os.path.join(SRCDIR, '..', 'protobuf')
    subprocess.check_call(
        "python -m grpc_tools.protoc --python_out=%s --grpc_python_out=%s --proto_path=%s %s" % (
            SRCDIR, SRCDIR, import_dir, os.path.join(import_dir, 'orchestrator.proto')
        ),
        stderr=sys.stderr, shell=True)
    import orchestrator_pb2
    import orchestrator_pb2_grpc
    logging.info("successfully imported orchestrator_pb2  and orchestrator_pb2_grpc after compiling!")


def get_status_string(status):
    return f'message: {status.message} - active_threads: {status.active_threads} - success: {status.success} - code: {status.code}'

def main():
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '-H', '--host', type=str, required=False, metavar='HOST', action='store',
        dest='host', help='The host name or IP address of the orchestrator.')
    ap.add_argument(
        '-p', '--port', type=int, required=False, metavar='PORT', action='store',
        dest='port', help='The network port of the orchestrator.')
    ap.add_argument(
        '-e', '--endpoint', type=str, required=False, metavar='IP:PORT', action='store',
        dest='endpoint', help='The endpoint (combination of host and port) of the orchestrator.')
    args = ap.parse_args()

    endpoint = args.endpoint
    if endpoint is None and args.host is not None and args.port is not None:
        endpoint = '%s:%d' % (args.host, args.port)

    if endpoint is None:
        ap.print_help()
        return -1

    logging.info("connecting to orchestrator")
    channel = grpc.insecure_channel(endpoint)
    stub = orchestrator_pb2_grpc.OrchestratorStub(channel)
    logging.info("calling get_status")
    status = stub.get_status(orchestrator_pb2.RunLabel(label="test"))
    logging.info("status: "+get_status_string(status))

if __name__ == '__main__':
    main()