# Working on your VM

Everything practical, once for all labs. The labs' pages link here when you need it.

## Connect

Your teacher gives you the address of your VM and your login.

- **With VS Code** (recommended): install the *Remote – SSH* extension, *Connect to Host*, then open the
  folder `~/iot-labs`. You get an editor and terminals on the VM; the VM's web pages are forwarded to
  your laptop by themselves (*Ports* tab).
- **With a terminal**: `ssh -L 8080:localhost:8080 <login>@<your-vm>`. The `-L` part carries the
  viewer's page to your laptop.

## Start a lab, and work in it

On the VM:

```bash
cd ~/iot-labs/lab1
docker compose up -d --build                       # starts the lab; the first time takes a few minutes
docker compose ps --services --status running      # what is running
docker compose exec workstation bash               # opens a terminal in your workstation
```

After `git pull` (a new lab, or a fix), start again with `--build`, so that the lab's tools are rebuilt.

You work **in the workstation**, a container with Python, the MQTT tools, `check` and `hint`. Your
prompt there is `root@workstation:/work#`. Open two such terminals: one to listen, one to act.

Your files are in `~/iot-labs/lab1/work` on the VM, which the workstation sees as `/work`: edit them
with VS Code, run them in the workstation. The record is `~/iot-labs/record`, seen as `/record`.

## The tools

| Tool | What it does |
|---|---|
| the **viewer**, http://localhost:8080 on your laptop (`relay:8080` inside the lab) | every MQTT packet of the lab, live. *Packets*: each packet, its direction (↑ to the broker, ↓ from it), type, topic, payload, sizes; click a payload to see it whole; the **filter** box keeps only the packets that mention what you type; `PINGREQ`/`PINGRESP` are hidden unless you untick the box; the top line counts the last minute. *Topics*: per topic, over 5 minutes. *Clients*: every connection, its settings, how it ended, and a **Freeze** button |
| `check` | tells whether each exercise works, and if not, why. `check 3` checks exercise 3 only |
| `hint 3` | the next hint for exercise 3; run it again for the next one. The last hint is close to the answer |
| `check report` | writes the file you hand in, `work/report-lab1.txt`. An exercise counts from the first time `check` confirmed it |

## Python, JSON and the terminal in ten lines

```text
Terminal  cd ~/iot-labs/lab1 · ls · cat file      move, list, print a file;  ↑ recalls a command
          Ctrl+C stops the running program;  nano file edits (Ctrl+O save, Ctrl+X quit) — or VS Code
JSON      {"temperature_c": 20.4, "tags": ["a", "b"]}   double quotes only, no comma after the last item
          python -m json.tool tree.json                  checks a JSON file, says where it is broken
Python    import json;  d = json.loads(text);  text = json.dumps(d)       text <-> dictionary
          d["pressure_psi"] · float("20.65") · round(x, 2) · f"lab/sensors/{name}/env"
          from datetime import datetime, timezone
          datetime.now(timezone.utc).isoformat(timespec="seconds")      now, ISO 8601, in UTC
          datetime.fromtimestamp(1790000000, timezone.utc).isoformat()  seconds since 1970 -> ISO
          import base64, struct;  raw = base64.b64decode(s);  struct.unpack(">BhBBB", raw)  bytes -> numbers
```

In `struct`: `>` big-endian, `B` one unsigned byte, `h` two bytes read as a signed number.

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
| everything is broken | — | `docker compose down`, then `docker compose up -d`: `work/` is kept |
