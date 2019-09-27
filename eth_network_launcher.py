"""Simple script to launch private ethereum networks using Geth."""
import json
import multiprocessing as mp
import pathlib
import subprocess
import time
from typing import List, Optional, Iterable

import requests
import structlog

from eth_utils.address import to_checksum_address
from eth_utils.typing import ChecksumAddress

log = structlog.getLogger()


DEFAULT_BALANCE = 100_000_000_000_000_000_000_000
DEFAULT_GAS_LIMIT = 200_000_000
#: Placeholder Ethereum Address to send mining rewards to.
DEFAULT_ETHERBASE = to_checksum_address("6d11a7c346bee25df0845163f0cbe3ebdb7e3114")


class EthClient:
    def __init__(self, index: int, genesis_file: pathlib.Path, base_port: int = 8000, data_path: pathlib.Path = pathlib.Path()):
        log.debug("Instantiating EthClient Instance", index=index, genesis_file=str(genesis_file), base_port=base_port, data_path=str(data_path))
        self.index = index
        self._base_port = base_port
        self.process = None
        self._genesis_file = genesis_file
        self.network_config = json.loads(genesis_file.read_text())
        self.data_path = data_path.joinpath(f"{self.network_id}_node{index}")
        self.data_path.mkdir(exist_ok=True)
        self._nonce = 1
        self._enode = None

    def rpc_call(self, method, params=None):
        payload = {"method": method, "params": params, "jsonrpc": "2.0", "id": self.nonce}
        payload = {k:v for k,v in payload.items() if v}
        log.debug("Requesting RPC Call", method=method, params=params or [], curl=f"REQUEST: curl -XPOST {self.address} --data '{json.dumps(payload)}' --headers 'content-type:application/json' -vvv")
        resp = requests.post(self.address, json=payload)
        data = resp.json()
        log.debug("RPC Call Response Received", response=resp, json=data)
        return data

    @property
    def nonce(self):
        nonce = self._nonce
        self._nonce += 1
        return nonce

    def __str__(self):
        return self.name

    @property
    def name(self):
        return f"GethNode<{self.index}>@{self.address}/{self.network_id}"

    @property
    def network_id(self):
        return self.network_config["config"]["chainId"]

    @property
    def log_file(self) -> pathlib.Path:
        path = self.data_path.joinpath(f"GethNode_{self.index}.log")
        path.touch()
        return path

    @property
    def port(self) -> int:
        return  self._base_port + self.index

    @property
    def address(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def enode(self) -> str:
        if not self._enode:
            data = self.rpc_call("admin_nodeInfo", [])
            self._enode = data["result"]["enode"]
        return self._enode

    def init(self):
        command_tuple = ("geth", "--datadir", str(self.data_path), "init", str(self._genesis_file))

        log.debug("Initializing Ethereum client with genesis file", network_config=self.network_config, name=self.name, command=" ".join(command_tuple))
        result = subprocess.run(command_tuple, capture_output=True)
        if result.returncode > 0:
            log.error("Could not initialize client", node=self.name, stderr=result.stderr, stdout=result.stdout)
            exit()

    def start(self, mine=False):
        command_tuple = (
            "geth",
            "--port", str(30303 + self.index),
            "--datadir", str(self.data_path),
            "--networkid", str(self.network_id),
            "--rpc",
            "--rpcport", str(self.port),
            "--rpcapi", "admin,eth,net,web3,miner,debug,personal,rpc",
        )
        if mine:
            command_tuple = (
                *command_tuple,
                "--mine",
                "--miner.threads", "1",
                "--miner.etherbase", DEFAULT_ETHERBASE,
            )

        log.debug("Starting Ethereum Client", name=self.name, command=" ".join(command_tuple))

        def run_client():
            with self.log_file.open(mode="w+") as f:
                subprocess.run(command_tuple, text=True, stderr=f, stdout=f)

        self.process = mp.Process(target=run_client, name=self.name)
        self.process.start()
        log.debug("Ethereum Client started", pid=self.process.pid)

    def stop(self, timeout=5):
        log.debug("Joining Ethereum client process", name=self.name, pid=self.process.pid, timeout=timeout)
        if not self.process or not self.process.is_alive():
            log.debug("Ethereum client process not started or dead!", name=self.name)
            return
        self.process.join(timeout=timeout)
        if not self.process.exitcode:
            log.debug("Could not join process, killing it", pid=self.process.pid, name=self.name)
            self.process.kill()

    def connect_peers(self, peers: Iterable["EthClient"]):
        log.debug("Connecting peers to Ethereum Client", name=self.name, peers=peers)
        if not self.process.is_alive():
            log.debug("Could not connect peers, client is dead", name=self.name, pid=self.process.pid, exitcode=self.process.exitcode)
        for peer in peers:
            log.debug("Connecting peer to client", name=self.name, target=peer, enode=peer.enode)
            print(self.rpc_call("admin_addPeer", params=[peer.enode]))


def create_genesis_file(
        data_dir: pathlib.Path,
        chain_id: int,
        difficulty: int = 1,
        gas_limit: int = DEFAULT_GAS_LIMIT,
        default_balance: int = DEFAULT_BALANCE,
        addresses: Optional[List[ChecksumAddress]] = None,
) -> pathlib.Path:
    config = {
        "config":{
            "chainId": chain_id,
            "homesteadBlock": 0,
            "eip155Block": 0,
            "eip158Block": 0,
            "byzantiumBlock ": 0,
        },
        "difficulty": f"{difficulty}",
        "gasLimit": f"{gas_limit}",
        "alloc": {
            address: {"balance": default_balance}
            for address in (addresses or [])
        },
    }
    fpath = data_dir.joinpath("genesis.json")
    with fpath.open("w+") as f:
        json.dump(config, f)
    return fpath


def launch_network(data_path, genesis_file: pathlib.Path = None, node_count: int = 5):
    base_port = 8545

    # Init clients with genesis file and start them up.
    nodes = [EthClient(i, genesis_file=genesis_file, data_path=data_path, base_port=base_port) for i in range(node_count)]
    for i, node in enumerate(nodes):
        node.init()
        node.start(mine=(i == len(nodes)-1))
    log.info("Nodes Initialized and started", nodes=nodes)

    time.sleep(3)

    for node in nodes:
        peers = tuple(set(nodes) - {node})
        counter = len(nodes)
        connected = False
        while counter > 0:
            try:
                node.connect_peers(peers)
            except requests.ConnectionError:
                log.error(f"Could not connect to node!", node=node, retries_left=counter)
                time.sleep(1)
                counter -= 1
                continue
            else:
                log.info("Peers connected", node=node)
                connected = True
                break
        if not connected:
            log.error("Could not connect peers!", node=node)
            raise ConnectionRefusedError

    return nodes


if __name__ == '__main__':
    import sys
    data_dir = pathlib.Path(sys.argv[-1])
    gen_file = create_genesis_file(data_dir, 66)
    nodes = launch_network(data_dir, gen_file)
    while True:
        time.sleep(5)
        for node in nodes:
            node.rpc_call("eth_blockNumber")
