import os
import re
import glob
import yaml
import json
import subprocess
import argparse
from kubernetes import client, config
import base64
from pathlib import Path
from urllib.parse import urlparse


class DockerInfo:
    def __init__(self):
        print("")

    def update_node_port(self, ports_mapping, filename):
        print("Start updating the docker info Json : ")
        with open(filename, "r") as jsonFile:
            data = json.load(jsonFile)

        for x in range(len(data["docker_info_list"])):
            container_name = (data["docker_info_list"][x]["container_name"]).lower()
            data["docker_info_list"][x]["port"] = ports_mapping[container_name]

            ###  Updates the container names
            data["docker_info_list"][x]["container_name"] = container_name

            ### Update the ip_address
            ip_address = (data["docker_info_list"][x]["ip_address"]).lower()
            data["docker_info_list"][x]["ip_address"] = ip_address

        print("update_node_port: %s" % data["docker_info_list"])

        with open(filename, "w") as jsonFile:
            json.dump(data, jsonFile)

        print("\n Docker info file is successfully updated  ")


class Deployment:
    def __init__(self, namespace, start_port=30000, end_port=32767, base_path="", image_env=[]):
        self.namespace = namespace
        self.base_path = base_path
        self.start_port = start_port
        self.end_port = end_port
        self.port_mapping = dict()
        self.port = None
        self.image_env=image_env

        if not self.is_valid_namespace():
            raise("deployment is invalid")
        if not os.path.isdir(self.get_deployment_dir()):
            print(base_path)
            print(self.get_deployment_dir())
            raise("Path to the target directory is invalid :  ")

    def get_deployment_dir(self):
        return os.path.join(self.base_path,"deployments")

    def get_next_free_port(self):
        if(self.port is None):
            self.port = 8061
        else: 
            self.port = self.port + 1
        return self.port

    def get_current_dir(self):
        return os.getcwd()

    def is_service(self, file_name):
        with open(file_name) as f:
            doc = yaml.safe_load(f)
        return doc['kind'] == "Service"

    def set_image_pull_policy(self, deployment_file_name, new_policy):
        with open(deployment_file_name) as f:
            doc = yaml.safe_load(f)

        try:
            containers = doc['spec']['template']['spec']['containers']
            for container in containers:
                old_policy = container.get('imagePullPolicy', None)
                if old_policy is not None and old_policy != new_policy:
                    print("set_image_pull_policy changing imagePullPolicy from", old_policy, "to", new_policy)
                elif old_policy is None:
                    print("set_image_pull_policy setting imagePullPolicy to", new_policy)
                container['imagePullPolicy'] = new_policy

            with open(deployment_file_name, "w") as f:
                yaml.dump(doc, f)
        except Exception:
            # if we process a file that is not a deployment - warn
            print("WARNING: set_image_pull_policy encountered incompatible input file", deployment_file_name)

    def set_image_env(self, deployment_file_name):
        with open(deployment_file_name) as f:
            doc = yaml.safe_load(f)

        try:
            containers = doc['spec']['template']['spec']['containers']
            for container in containers:
                image = container.get('image')
                for env_entry in self.image_env:
                    p=re.compile(env_entry['docker_image_pattern'])
                    if(p.match(image)):
                        print(f"set env {env_entry['name']} on image {image}")
                        if container['env'] is None:
                            container['env']=[]
                        container['env'].append({'name': env_entry['name'], 'value': env_entry['value']})

            with open(deployment_file_name, "w") as f:
                yaml.dump(doc, f)
        except Exception as e:
            # if we process a file that is not a deployment - warn
            print("WARNING: set_image_env encountered incompatible input file", deployment_file_name)
            print(e)


    def set_port(self, file_name, port):
        print("set_port in", file_name, "to", port)
        with open(file_name) as f:
            doc = yaml.safe_load(f)

        doc['spec']['ports'][0]['port'] = port

        name = doc['metadata']['name']
        self.port_mapping[name] = port

        with open(file_name, "w") as f:
            yaml.dump(doc, f)

    def get_node_port(self, service):
        process = subprocess.run([
            'kubectl', '-n', self.namespace, 'get', 'svc', service, '-o',
            'go-template={{range .spec.ports}}{{if .nodePort}}{{.nodePort}}{{end}}{{end}}'],
            check=True, stdout=subprocess.PIPE, universal_newlines=True)

        return int(process.stdout)

    def update_yaml_ports(self, file_name):
        with open(file_name) as f:
            doc = yaml.safe_load(f)

        service_name = doc['metadata']['name']
        node_port = self.get_node_port(service_name)
        
        print("set_node_port in", file_name, "to", node_port)
        doc['spec']['ports'][0]['nodePort'] = node_port
        doc['spec']['ports'][0]['port'] = node_port

        self.port_mapping[service_name] = node_port

        with open(file_name, "w") as f:
            yaml.dump(doc, f)

    def apply_yaml_process(self, file_name):
        process = subprocess.run(['kubectl', '-n', self.namespace, 'apply', '-f', file_name], check=True,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)
        return process
    
    def apply_yaml(self, file_name, image_pull_policy):
        print("apply_yaml:", file_name)

        if self.is_service(file_name):
            port = self.get_next_free_port()
            self.set_port(file_name, port)
        else:
            self.set_image_pull_policy(file_name, image_pull_policy)
            self.set_image_env(file_name)

        process = self.apply_yaml_process(file_name)

        if self.is_service(file_name):
            self.update_yaml_ports(file_name=file_name)
            process = self.apply_yaml_process(file_name)

        output = process.stdout
        name = output.split(" ")
        print("  apply got %s" % name)
        return name[0]

    def delete_deployment_services(self, names):
        for name in names:
            process = subprocess.run(['kubectl', '-n', self.namespace, 'delete', str(name)], check=True,
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True)
        output = process.stdout
        print("delete_deployment_services output %s" % output)

    def create_web_ui_service_yaml(self, file_service):
        print("file_name of service yaml =", file_service)        
        with open(file_service) as f:
            doc = yaml.safe_load(f)

        port_name = "webui"
        target_port = 8062
        name = (doc['metadata']['name']) + "webui"
        doc['metadata']['name'] = name
            
        doc['spec']['ports'][0]['name'] = port_name
        doc['spec']['ports'][0]['targetPort'] = target_port

        assert file_service.endswith('.yaml')
        file_service_web_ui = file_service[:-5] + '_webui.yaml'
        with open(file_service_web_ui, "w") as f:
            yaml.dump(doc, f)

        return file_service_web_ui

    def get_namespaces(self):
        process = subprocess.run(['kubectl', 'get', 'namespaces'], check=True,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)
        namespaces = process.stdout
        return namespaces

    def get_service_ip_address(self, namespce, service_name):
        process = subprocess.run(['kubectl', '-n', namespce, 'get', service_name], check=True, stdout=subprocess.PIPE,
                                 universal_newlines=True)
        # print(process.type())
        output = process.stdout
        name = output.split(" ")
        name1 = [x for x in name if x]
        return name1[7]

    def get_node_ip_address(self):
        with open(Path.home() / ".kube" / "config") as f:
            lines = f.readlines()
        server_line=[line.strip() for line in lines if line.strip().startswith("server:") ][0]
        server_url=server_line.split(':',1)[1].strip()
        return urlparse(server_url).hostname

    def is_valid_namespace(self):
        existing_namespaces = [x for x in (re.split('[  \n]', self.get_namespaces())) if x]
        if existing_namespaces.__contains__(self.namespace):
            index = existing_namespaces.index(self.namespace)
            if existing_namespaces[index + 1] == 'Active':
                print("Given namespace is active ")
                return True
            else:
                print("Given namespace is inactive ")
                return False
        else:
            print("Name of your given namespace is invalid")
            print("Existing namespaces are: ", existing_namespaces)
            return False

    def is_orchestrator_present(self, path):
        orchestrator_client = "orchestrator_client.py"
        for root, dirs, files in os.walk(path):
            if orchestrator_client in files:
                return True

class KubernetesSecret:
    def __init__(self, namespace):
        config.load_kube_config()
        self.api_instance = client.CoreV1Api()
        self.namespace = namespace
    def _get_secret_data(self, path_docker_config):
        with open(path_docker_config) as docker_config_file:
            docker_config_json = docker_config_file.read()
        secret_data = {
            ".dockerconfigjson": base64.b64encode(docker_config_json.encode()).decode()
        }
        
        return secret_data

    def _get_secret_metadata(self, name_secret):
        metadata = client.V1ObjectMeta(
            name=name_secret
        )
        return metadata

    def _configure_secret(self, metadata, secret_data):
        secret = client.V1Secret(
            api_version="v1",
            kind="Secret",
            data=secret_data,
            metadata=metadata,
            type="kubernetes.io/dockerconfigjson"
        )
        return secret

    def _get_secret(self, path_docker_config, name_secret):
        metadata = self._get_secret_metadata(name_secret)
        secret_data = self._get_secret_data(path_docker_config)
        return self._configure_secret(metadata, secret_data)
        
        

    def _create_secret(self, secret):
        # api_instance = client.CoreV1Api()

        api_response = self.api_instance.create_namespaced_secret(
            namespace=self.namespace,
            body=secret,
        )
        print(f"Secret {api_response.metadata.name} created in the namespace {api_response.metadata.namespace}")

    def create_secret(self, path_docker_config, name_secret="my-secret"):
        secret = self._get_secret(path_docker_config, name_secret)


        self._create_secret(secret)





def apply_yamls(image_pull_policy, deployment):
    yaml_files = glob.glob(deployment.get_deployment_dir() + "/*.yaml")
    for yaml_file in yaml_files:
        if yaml_file.endswith('webui.yaml'):
            continue
        if deployment.is_service(yaml_file):
            yaml_file_web_ui = deployment.create_web_ui_service_yaml(yaml_file)
            deployment.apply_yaml(file_name=yaml_file_web_ui, image_pull_policy=image_pull_policy)

        deployment.apply_yaml(file_name=yaml_file, image_pull_policy=image_pull_policy)
    print(deployment.port_mapping)

def create_dockerinfo(base_path, deployment):
    dockerInfo = DockerInfo()
    dockerfilename = os.path.join(base_path,"dockerinfo.json")
    if os.path.exists(dockerfilename):
        dockerInfo.update_node_port(deployment.port_mapping, dockerfilename)

def create_secret(namespace, path_docker_config, name_secret):
    kubernetesSecret = KubernetesSecret(namespace=namespace)
    kubernetesSecret.create_secret(path_docker_config=path_docker_config, name_secret=name_secret)

def read_image_environment(args):
    image_env=[]
    try:
        with open(args.config_file, "r") as jsonFile:
            data = json.load(jsonFile)
            image_env=data['environment_variables']
            #print(f'environment: {image_env}')
    except Exception as e:
        print(f"error reading config file: {e}")
    return image_env


def run_client(args):
    namespace = args.namespace
    print(f"namespace = {namespace}")
    image_pull_policy=args.image_pull_policy
    print(f"image_pull_policy = {image_pull_policy}")
    base_path=args.base_path
    print(f"base_path = {base_path}")
    image_environments=read_image_environment(args)

    deployment = Deployment(namespace=namespace, base_path=base_path, image_env=image_environments)


    apply_yamls(image_pull_policy, deployment)

    create_dockerinfo(base_path, deployment)

    if args.path_docker_secret and args.secret_name:
        create_secret(namespace=namespace, path_docker_config=args.path_docker_secret, name_secret=args.secret_name)

    if deployment.is_orchestrator_present(base_path):
        print("Node IP-address : " + deployment.get_node_ip_address())
        print("Orchestrator Port is : " + str(deployment.port_mapping.get('orchestrator')))
        print("Please run python orchestrator_client/orchestrator_client.py --endpoint=%s:%d --basepath=./" % (deployment.get_node_ip_address(), deployment.port_mapping.get('orchestrator')))


def main():
    my_parser = argparse.ArgumentParser()
    my_parser.add_argument('--namespace', '-n', action='store', type=str, required=True,
                           help='name of namespace is required ')
    my_parser.add_argument('--image_pull_policy', '-ipp', action='store', type=str, required=False, default="Always",
                           help='imagepullpolicy for kubernetes deployment ')
    my_parser.add_argument('--base_path'         , '-bp',  action='store', type=str, required=False, default=os.getcwd(),
                           help='basepath of solution')
    my_parser.add_argument('--path_docker_secret'         , '-ps',  action='store', type=str, required=False,
                           help='path of docker secret')
    my_parser.add_argument('--secret_name'         , '-sn',  action='store', type=str, required=False,
                           help='name of docker secret')
    my_parser.add_argument('--config-file'         , '-cf',  action='store', type=str, required=False, default='/home/ai4eu/playground-app/config.json',
                           help='absolute path to playground-app config.json')

    args = my_parser.parse_args()


    run_client(args)



if __name__ == '__main__':
    main()