import multiprocessing
import os
import socket
import sys
import signal
import time
import threading
import requests
import random
import config
import copy
import queue

# Necessary for multiprocessing library to work on linux
multiprocessing.set_start_method('spawn', True)
# update_conn_table_lock = threading.Lock()


# All the actual work happens in the worker function


def worker(socket, worker_num, queue):
    conns = {i: 0 for i in config.ACTIVE_SERVERS}

    while True:
        client, address = socket.accept()
        print("{u} connected to {w}".format(u=address, w=worker_num))
        buffer = client.recv(4096)
        buffer_string = buffer.decode('utf-8')
        curl_request = buffer_string.split("\r")[0]
        print("Curl Request: ", curl_request)

        # port = random.choice(config.ACTIVE_SERVERS) # Selects a random server from the config file. Can be changed to round robin, weighted, etc
        # port = roundRobin(queue)
        port = leastConnections()

        # Queries the respective server, currently only handles GET requests, but can be further configured to handle more if necessary
        response = requests.get('http://localhost:{}'.format(port))

        client.send(response.text.encode('utf-8'))
        print("Port used: ", port)

        time.sleep(1)
        client.close()


def roundRobin(queue):
    count = queue.get()
    selected_port = config.ACTIVE_SERVERS[count]
    count = (count + 1) % len(config.ACTIVE_SERVERS)
    queue.put(count)
    print(count)
    return selected_port


def leastLatency():
    selected_port = 0
    min_timing = sys.maxsize
    for port in config.ACTIVE_SERVERS:
        os.system("nmap -p " + str(port) + " localhost > response.txt")
        with open("response.txt") as response_file:
            response = response_file.read()
        timing = float(response.split("Host is up (")[1].split("s latency")[0])
        print("port: {0}, timing: {1}".format(port, timing))
        if timing < min_timing:
            selected_port = port
            min_timing = timing

    print("selected port: {0}".format(selected_port))
    return selected_port


def leastConnections(conn_count):
    min_connections = sys.maxsize
    selected_port = None
    for port in config.ACTIVE_SERVERS:
        if conn_count[port] < min_connections:
            least_connected = port
            selected_port = least_connected
    return selected_port

def leastTime(conn_count):
    """
    Cost function for each port is
    active_conn_coeff*(number of active connections) + latency_coeff*(latency timing in seconds)
    port with min cost function is returned
    """
    active_conn_coeff = 1
    latency_coeff = 1

    scores = {}

    # fill up active connections
    for port in config.ACTIVE_SERVERS:
        print("type(conn_count[port])".format(type(conn_count[port])))
        scores[port] = conn_count[port] * active_conn_coeff

    # fill up latency times
    for port in config.ACTIVE_SERVERS:
        os.system("nmap -p " + str(port) + " localhost > response.txt")
        with open("response.txt") as response_file:
            response = response_file.read()
        scores[port] += float(response.split("Host is up (")[1].split("s latency")[0]) * latency_coeff

    # find min value
    min_value = sys.maxSize
    selected_port = None
    for port in scores.keys():
        if scores[port] < min_value:
            min_value = scores[port]
            selected_port = port
    print("all scores: {0}".format(scores))
    print("selected_port: {0}".format(selected_port))
    return selected_port


def randomAssignment():
    return random.choice(config.ACTIVE_SERVERS)


if __name__ == '__main__':
    ports = config.ACTIVE_SERVERS
    temp_list = [0] * len(ports)
    active_conn = multiprocessing.Array("i", temp_list)

    # Basic socket setup
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Disables TIME_WAIT state of connected sockets
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind(('', 9093))  # Change port to main server port
    serversocket.listen(5)
    q = multiprocessing.Queue()
    q.put(0)
    # Start multiple worker processes in parallel
    workers = [multiprocessing.Process(target=worker, args=(
        serversocket, i, q)) for i in range(config.WORKER_NUM)]

    for p in workers:
        p.daemon = True  # This kills all subprocesses when the script ends
        p.start()

    # Keep the program running
    while True:
        try:
            time.sleep(10)
        except:
            serversocket.shutdown(socket.SHUT_RDWR)
            serversocket.close()
