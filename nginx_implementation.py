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

multiprocessing.set_start_method('spawn', True)

def worker(socket, worker_num):
  while True:
      client, address = socket.accept()
      print("{u} connected to {w}".format(u=address, w=worker_num))
      buffer = client.recv(4096)
      buffer_string = buffer.decode('utf-8')
      curl_request = buffer_string.split("\r")[0]
      print("Curl Request: ", curl_request)
      
      port = random.choice(config.ACTIVE_SERVERS)
      response = requests.get('http://localhost:{}'.format(port))

      client.send(response.text.encode('utf-8'))
      print("Port used: ", port)
      time.sleep(1)
      client.close()

if __name__ == '__main__':
  serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  serversocket.bind(('',9086))
  serversocket.listen(5)
  workers = [multiprocessing.Process(target=worker, args=(serversocket, i,)) for i in range(config.WORKER_NUM)]

  for p in workers:
    p.daemon = True
    p.start()

  while True:
    try:
      time.sleep(10)
    except:
      serversocket.shutdown(socket.SHUT_RDWR)
      serversocket.close()
