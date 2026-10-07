# Working environment

The labs can run either on the **UPPA virtual machine** provided for the course or on a personal machine with Docker and Docker Compose. The lab itself is identical in both cases.

## If you use the UPPA VM

Connect with the address and login provided for the course. The university network uses the following HTTP proxy for external access:

```bash
export http_proxy=http://cache.univ-pau.fr:3128 https_proxy=http://cache.univ-pau.fr:3128
```

The proxy variables are normally already available in the VM environment. If `git clone`, `git pull`, or a Docker build cannot reach the Internet, run the command above in the shell before continuing. The lab's Compose file automatically forwards these variables to image builds; no proxy is stored in the Docker images.

Clone the repository once, then enter the directory of the session you are working on:

```bash
git clone <this repository's URL> ~/IoT-Labs-UPPA
cd ~/iot-labs/lab1        # or lab2 for the second session, or labx for the xth 
```

### Open the viewer from your own computer

The viewer listens only on the VM's loopback interface. From a **terminal on your own computer**, open an SSH tunnel and keep it running:

```bash
ssh -L 8080:127.0.0.1:8080 <login>@<your-vm>
```

Then open <http://localhost:8080> in the browser on your own computer.

If you use **VS Code Remote – SSH**, connect to the VM, open the repository, and forward port `8080` from the *Ports* tab instead.

## If you run the labs locally

You need Git, Docker, and Docker Compose. Clone the repository and enter the directory of the session you are working on:

```bash
git clone <this repository's URL> ~/IoT-Labs-UPPA
cd ~/iot-labs/lab1        # or lab2 for the second session
```

No SSH tunnel is needed. Once the lab is running, open <http://localhost:8080> directly.

The Compose file uses proxy variables only when they exist in the host environment, so the same repository works on a normal Internet connection without any proxy configuration.

## Start the lab

From the current lab directory (`lab1/`, `lab2/`, ... ) on the host machine:

```bash
docker compose up -d --build
docker compose ps --services --status running
```

After a `git pull`, start again with `--build` so that changes to the lab tools are included.

The exercises themselves run in the **workstation container**, which already contains Python, Paho MQTT, and the Mosquitto command-line clients. Open a shell with:

```bash
docker compose exec workstation bash
```

The shell starts in `/work`. This is the same `work/` directory inside the current lab on the host. You may edit files with your usual host editor, or directly inside the container with `nano` or `vim`. Open additional workstation shells when publishers and subscribers must run concurrently.

To stop the lab:

```bash
docker compose down
```

Files under the current lab's `work/` directory are stored on the host and are not removed by `docker compose down`.

## Viewer

The viewer shows MQTT traffic passing through the lab relay — **not all traffic on the simulated network**. The **Packets** tab shows direction (↑ to the broker, ↓ from it), packet type, topic, payload and sizes; click a payload to expand it, and use the filter box to isolate traffic. `PINGREQ`/`PINGRESP` are hidden by default. The **Topics** tab aggregates activity by topic, and **Clients** shows observed MQTT connections. Additional protocol fields and the **Freeze** control stay hidden until **show protocol details** is enabled later in Lab 1.

## When something goes wrong

| You see | It usually means | Try |
|---|---|---|
| `no configuration file provided` | you are not in a lab directory | `cd ~/iot-labs/lab1` or the directory of the current session |
| `git` or the build cannot reach the Internet on an UPPA VM | the proxy is not present in the current shell | check `env | grep -i proxy`, then export the UPPA proxy shown above |
| `failed to fetch anonymous token` / `auth.docker.io` | Docker itself cannot reach Docker Hub | retry once; if it persists, report the VM rather than changing the lab files |
| a service is missing | it stopped or failed | `docker compose logs <service>`, then `docker compose up -d` |
| the viewer does not open from an UPPA VM | the SSH tunnel/port forwarding is missing | open `ssh -L 8080:127.0.0.1:8080 ...` on your computer, or forward port 8080 in VS Code |
| the viewer does not open locally | the relay may not be running | `docker compose ps` and `docker compose logs relay` |
| your MQTT client works but the viewer does not show it | you connected to the broker directly | use host `relay`, port `1884` |
| `mosquitto_sub` prints nothing | the topic/filter may not match, the simulated source may publish periodically, or another live client may be reusing the same Client ID | wait for one source period (10 s for `hygrolab`), check the quoted filter, and use a distinct `-i` for simultaneously running clients |
| `is not valid JSON` | a missing comma or quote | the message gives line and column |
| a program receives nothing | it subscribed before being connected | subscribe in `on_connect` |
| the autoclave says `IDLE`, the router `OFF` | night or weekend at the plant | normal: note the time |
| several services are in an inconsistent state | — | `docker compose down`, then `docker compose up -d`; `work/` is preserved |
