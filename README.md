(Jin's version)
# Setup
Make sure you have multiple servers running in the background.You can use any kind of server you want, but there is a default Ruby-On-Rails server provided in the folder ROR_Server. In order to start the servers, cd into the folder and run `rails s -p 8001`. Ensure that the -p argument corresponds to the active_servers port numbers in the [config file](https://github.com/JinBean/Load-Balancer-Implementation/blob/master/config.py).

### Troubleshooting ROR
If you get this error message (`A server is already running. Check /tmp/pids/server.pid.`) while running the ROR server, just add a `-P` argument to specify a different PID. `rails s -p 8002 -P 42222`


# cURLing
`curl http://localhost:{portnumber}`



(JD's version)

### Setup

- In three different clis:

  ```
  export FLASK_APP=sampleFlask.py
  python3 -m flask run --port 8001
  ```

  ensure the ports for each cli is 8001, 8002, and 8003 respectively

- Then run the load balancer:
  ```python3 nginx_implementation_junde.py```
### To use

```curl 127.0.0.1:9093```