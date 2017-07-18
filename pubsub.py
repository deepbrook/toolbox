# Import Built-Ins
import logging
import socket
import os
from multiprocessing.connection import Listener, Client
from queue import Queue, Empty
from threading import Thread, Event, Timer

# Import Third-Party

# Import Homebrew

# Init Logging Facilities
log = logging.getLogger(__name__)


class Distributor(Thread):
    """Base Class providing a AF_INET, AF_UNIX or AF_PIPE connection to its
    data queue. It offers put() and get() method wrappers, and therefore
    behaves like a Queue as well as a Thread.

    Data from the internal queue is automatically fed to the connecting client.
    """
    def __init__(self, address, max_q_size=None, timeout=None,
                 *thread_args, **thread_kwargs):
        """Initialize class.

        :param sock_name: UDS, TCP socket or pipe name
        :param max_q_size: maximum queue size for self.q, default infinite
        """
        self.address = address
        self.connector = Listener(address)
        max_q_size = max_q_size if max_q_size else 0
        self.q = Queue(maxsize=max_q_size)
        self._running = Event()
        self.connection_timer = Timer(timeout, self.connection_timed_out)
        super(Distributor, self).__init__(*thread_args, **thread_kwargs)

    def connection_timed_out(self):
        """Closes the Listener and shutsdown Distributor if no Client connected.

        We do this by temporarily connecting to ourselves using a Client(),
        and instantly closing the connection.

        :return:
        """
        self._running.clear()
        sentinel_conn = Client(self.address)
        sentinel_conn.close()
        self.connector.close()
        self.join()
        os.remove(self.address)

    def _start_connection_timer(self):
        self.connection_timer.start()

    def start(self):
        self._running.set()
        super(Distributor, self).start()

    def join(self, timeout=None):
        self._running.clear()
        super(Distributor, self).join(timeout=timeout)

    def run(self):
        while self._running.is_set():
            self._start_connection_timer()
            try:
                client = self.connector.accept()
                self.connection_timer.cancel()
                self.feed_data(client)
            except (TimeoutError, socket.timeout, ConnectionError):
                continue
            except Exception as e:
                raise

    def feed_data(self, client):
        try:
            while self._running.is_set():
                try:
                    client.send(self.q.get())
                except Empty:
                    continue
        except EOFError:
            return

    def send(self, data, block=True, timeout=None):
        self.put(data, block, timeout)

    def put(self, item, block=True, timeout=None):
        """put() wrapper around self.q.put()

        :param item:
        :param block:
        :param timeout:
        :return:
        """
        self.q.put(item, block, timeout)

    def get(self, block=True, timeout=None):
        """get() wrapper around self.q.get()

        :param block:
        :param timeout:
        :return:
        """
        self.q.get(block, timeout)


class Publisher:
    """Publisher Class responsible for setting up nodes and their connection.

    Employs basic publish/subscribe model.
    
    Data may be send via any of TCP, UDS or named Windows Pipe.
    """
    def __init__(self, address, max_q_size=None, timeout=None):
        """Initialize Instance.

        :param sock_name:
        :param max_q_size:
        :param timeout:
        """
        self._address = address
        self._subscribers = set()
        self._subscriber_nodes = {}
        self._running = Event()
        self.connection = Listener(address)
        self._node_factory = lambda x: Distributor(x, max_q_size, timeout)

    def attach(self, subscriber):
        """Attach a subscriber to the publisher.

        :param subscriber: string, UDS Path| TCP Address Tuple | Named Pipe
        :return:
        """
        self._subscribers.add(subscriber)
        self._subscriber_nodes[subscriber] = self._node_factory(subscriber)
        self._subscriber_nodes[subscriber].start()

    def detach(self, subscriber):
        """Detaches the given subscriber from the publisher.

        :param subscriber: string, UDS Path| TCP Address Tuple | Named Pipe
        :return:
        """

        self._subscribers.remove(subscriber)
        removed_sub = self._subscriber_nodes.pop(subscriber)
        if removed_sub.is_alive():
            removed_sub.join()

    def publish(self, data):
        """Publish the given data to all current subscribers.

        :param data:
        :return:
        """
        for subscriber in self._subscribers:
            if self._subscriber_nodes[subscriber].is_alive():
                self._subscriber_nodes[subscriber].send(data)
            else:
                self.detach(subscriber)

    def stop(self):
        """Sends shutdown sentinel signal to main loop.
        
        :return: 
        """
        try:
            sentinel_conn = Client(self._address)
            sentinel_conn.send('$$$')
        except (EOFError, ConnectionResetError, ConnectionAbortedError):
            pass
        
    def _shut_down(self):
        self._running.clear()
        for sub in self._subscribers:
            self.detach(sub)
        os.remove(self._address)

    def handle_conns(self):
        while self._running.is_set():
            try:
                client = self.connection.accept()
                sub = client.recv()
                if sub == '$$$':
                    self._shut_down()
                else:
                    self.attach(sub)
                client.send('ok')
                client.close()
            except EOFError:
                continue
            except Exception as e:
                raise


if __name__ == '__main__':
    import time
    n = Distributor('/home/nils/git/spab2/test.uds', timeout=5)
    n.start()
    print("Sleeping")
    time.sleep(10)
    print("manual join")
    if n.is_alive():
        n.join()
    else:
        print("Completed.")

