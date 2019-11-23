import multiprocessing
from multiprocessing import Process, Value, Array
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

TIMEOUT = 10  # its in seconds
INITIAL_LATENCY_VAL = 0



def roundRobin(count):
    selected_port = config.ACTIVE_SERVERS[count]
    count = (count + 1) % len(config.ACTIVE_SERVERS)
    return count, selected_port


def leastConnections(active_connections):
    min_connections = sys.maxsize
    selected_port = None

    # fill up latency times
    for port in config.ACTIVE_SERVERS:
        print("port: {0}; number of activeconnections: {1}".format(port, active_connections[port].value))
        if active_connections[port].value < min_connections:
            min_connections = active_connections[port].value
            selected_port = port
    return selected_port


def leastTime(active_connections, average_latency):
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
        print("port: {0}; number of active connections: {1}".format(port, active_connections[port].value))
        scores[port] = active_connections[port].value * active_conn_coeff

    # fill up latency times
    for port in config.ACTIVE_SERVERS:
        print("port: {0}; average latency: {1}".format(port, average_latency[port].value))
        scores[port] += average_latency[port].value * latency_coeff

    # find min value
    min_value = sys.maxsize
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


def worker(client, selected_port, timeout_val, active_connections, average_latency):
    """
    Wraps the sending of request and receiving of responses to measure number of active 
    connections for each server, and also measure latency timings for each server
    """

    time_start = time.time()  # placed before getting lock to take obtaining lock into account for latency
    with active_connections.get_lock():
        active_connections.value += 1

    # actual sending of request and receiving response
    try:
        response = requests.get('http://localhost:{}'.format(selected_port), timeout = timeout_val)
        print("response at port: {0} is {1}".format(selected_port, response))
        client.send(response.text.encode('utf-8'))
        client.shutdown(socket.SHUT_RDWR)
        client.close()
    except requests.exceptions.Timeout:
        pass

    with active_connections.get_lock():
        active_connections.value -= 1
    time_end = time.time()
    new_average_latency = _get_new_average_latency(time_end-time_start, average_latency.value)

    with average_latency.get_lock():
        average_latency.value = new_average_latency


def _get_new_average_latency(diff, average_latency):
    """
    average_latency = ratio*average_latency + (1-ratio)*(diff-average_latency)
    """
    ratio = 0.75
    if average_latency == INITIAL_LATENCY_VAL:
        return diff
    else:
        return ratio*average_latency + (1-ratio)*(diff-average_latency)


if __name__ == '__main__':
    count = 0
    ports = config.ACTIVE_SERVERS
    active_connections = {}
    average_latency = {}

    # initialize values that will be shared between the load balancer thread and each server individually
    for i in ports:
        active_connections[i] = Value("i", 0)
        average_latency[i] = Value("f", INITIAL_LATENCY_VAL)

    # Basic socket setup
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Disables TIME_WAIT state of connected sockets
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind(('', 9093))  # Change port to main server port
    serversocket.listen(5)

    while True:
        try:
            client, address = serversocket.accept()

            # count, selected_port = roundRobin(count)
            # selected_port = leastConnections(active_connections)
            selected_port = leastTime(active_connections, average_latency)

            print("served at port: {0}".format(selected_port))

            p = Process(args=(client, selected_port, TIMEOUT, active_connections[selected_port], average_latency[selected_port]), target=worker)
            p.daemon = True  # This kills all subprocesses when the script ends
            p.start()
        except Exception as e:
            print(e)
            serversocket.shutdown(socket.SHUT_RDWR)
            serversocket.close()
            break
