"""Create a new Port binding for an existing container.

..admonition: WARNING!

    This will REPLACE any existing port binding of the given port and replace
    it with a binding to the given ports.

"""
import json
import argparse
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument('Container Hash')
parser.add_argument('host')
parser.add_argument('container')
parser.add_argument('type', '--type', choices=['tcp', 'udp'], default='tcp')

args = parser.parse_args()

config_path = pathlib.Path(f'/var/lib/docker/containers/{args.container_hash}/config.v2.json')
with config_path.open('r') as fp:
    config = json.load(fp)

host_port_and_type = f'{args.host}/{args.type}'
container_port_and_type = f'{args.container}/{args.type}'
config['ExposedPorts'][host_port_and_type] = {}

ports = config['NetworkSettings']['Ports']

ports[args.container] = [{'HostIP': '', 'HostPort': args.host}]
config['NetworkSettings']['Ports'] = ports

with config_path.open('w+') as fp:
    json.dump(config, fp)

host_config_path = pathlib.Path(f'/var/lib/docker/containers/{args.container_hash}/hostconfig.json')
with host_config_path.open('r') as fp:
    host_config = json.load(fp)

host_config['PortBindings'][container_port_and_type] = {'HostIP': '', 'HostPort': args.host}
with host_config_path.open('w+') as fp:
    json.dump(host_config, fp)
