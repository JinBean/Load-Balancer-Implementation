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

multiprocessing.set_start_method('spawn', True) # Necessary for multiprocessing library to work on linux

# All the actual work happens in the worker function
def worker(socket, worker_num, queue):
  while True:
      client, address = socket.accept()
      print("{u} connected to {w}".format(u=address, w=worker_num))
      buffer = client.recv(4096)
      buffer_string = buffer.decode('utf-8')
      curl_request = buffer_string.split("\r")[0]
      print("Curl Request: ", curl_request)
      
      # port = random.choice(config.ACTIVE_SERVERS) # Selects a random server from the config file. Can be changed to round robin, weighted, etc
      port = roundRobin(queue)

      # Queries the respective server, currently only handles GET requests, but can be further configured to handle more if necessary
      response = requests.get('http://localhost:{}'.format(port))

      client.send(response.text.encode('utf-8'))
      print("Port used: ", port)
      time.sleep(1)
      client.close()

def roundRobin(queue):
  count = queue.get()
  selected_port = config.ACTIVE_SERVERS[count]
  count = (count + 1)%len(config.ACTIVE_SERVERS)
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
    print(port, timing)
    if timing < min_timing:
      selected_port = port
      min_timing = timing
  return selected_port

if __name__ == '__main__':
  # Basic socket setup
  serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Disables TIME_WAIT state of connected sockets
  serversocket.bind(('',9093)) # Change port to main server port
  serversocket.listen(5)
  q = multiprocessing.Queue()
  q.put(0)
  # Start multiple worker processes in parallel
  workers = [multiprocessing.Process(target=worker, args=(serversocket, i, q)) for i in range(config.WORKER_NUM)]

  for p in workers:
    p.daemon = True # This kills all subprocesses when the script ends
    p.start()

  # Keep the program running
  while True:
    try:
      time.sleep(10)
    except:
      serversocket.shutdown(socket.SHUT_RDWR)
      serversocket.close()
