# Working on your VM

This page contains the setup shared by all labs.

## Connect

Use the VM address and login provided for the course.

- **VS Code Remote – SSH**: connect to the VM and open `~/iot-labs`. Web services exposed by the VM can be forwarded from the *Ports* tab.
- **Terminal**: `ssh -L 8080:localhost:8080 <login>@<your-vm>`. The tunnel exposes the lab viewer on the local machine.

## Start a lab, and work in it

On the VM:

```bash
cd ~/iot-labs/lab1
docker compose up -d --build                       # starts the lab; the first time takes a few minutes
docker compose ps --services --status running      # what is running
docker compose exec workstation bash               # opens a terminal in your workstation
```

After `git pull` (a new lab, or a fix), start again with `--build`, so that the lab's tools are rebuilt.

The exercises are executed **inside the workstation container**, which contains Python, the MQTT clients, `check` and `hint`. The directory `~/iot-labs/lab1/work` on the VM is mounted as `/work` in that container; `~/iot-labs/record` is mounted as `/record`. Multiple workstation shells can be opened when an exercise requires concurrent publishers and subscribers.

## The tools

| Tool | What it does |
|---|---|
| the **viewer**, http://localhost:8080 on your laptop (`relay:8080` inside the lab) | every MQTT packet that passes through the lab relay, live — **not all traffic on the simulated network**. *Packets*: each observed MQTT packet, its direction (↑ to the broker, ↓ from it), type, topic, payload and sizes; click a payload to see it whole; the **filter** box keeps only packets that mention what you type; `PINGREQ`/`PINGRESP` are hidden unless you untick the box; the top line counts the last minute. *Topics*: per topic, over 5 minutes. *Clients*: every observed MQTT connection, its settings, how it ended, and a **Freeze** button |
| `check` | validates the implementation exercises; `check 3` runs only the checks associated with exercise 3 |
| `hint 3` | displays progressive diagnostic hints for exercise 3 |
| `check report` | generates `work/report-lab1.txt`, including the recorded validation state of the exercises |

## When something goes wrong

| You see | It usually means | Try |
|---|---|---|
| `check: command not found` | you are on the VM, not in the workstation | `docker compose exec workstation bash` |
| `no configuration file provided` | you are not in the lab's folder | `cd ~/iot-labs/lab1` |
| a service is missing | it stopped or failed | `docker compose logs <service>`, then `docker compose up -d` |
| the viewer does not open | no SSH tunnel | `ssh -L 8080:localhost:8080 ...`, or VS Code's *Ports* tab |
| your client works but the viewer does not show it | you connected to the broker directly | host `relay`, port `1884` |
| `mosquitto_sub` prints nothing | a wrong topic, or a `#` the shell swallowed | quote it: `-t 'hygrolab/#'` |
| `is not valid JSON` | a missing comma or quote | the message gives line and column |
| a program receives nothing | it subscribed before being connected | subscribe in `on_connect` |
| the autoclave says `IDLE`, the router `OFF` | night or weekend at the plant | normal: note the time |
| several services are in an inconsistent state | — | `docker compose down`, then `docker compose up -d`; `work/` is preserved |
