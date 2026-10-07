# IoT Labs — Adour Composites

You are the new IoT engineers of **Adour Composites**, a plant in Tarnos that makes carbon-fibre parts
for aircraft. Its machines and sensors already send data, each in its own way, and nobody uses them
together. In three weeks an aerospace customer audits the plant; the electricity bill went up by a
third; and the plant manager wants *"one system, not nine"*.

Over ten labs, you build that system, one question at a time.

| Lab | The plant's question | What you learn |
|---|---|---|
| [1](lab1/) | **How do our data travel today, and can we trust them?** | MQTT publish/subscribe; tracing data end to end; first normalization decisions; client liveness |
| [2](lab2/) | **Can we lose a cure record if the network fails?** | MQTT QoS, acknowledgements and persistent sessions; first CoAP request/response and retransmission |
| 3 | Can we read the machines directly? | Modbus, OPC UA |
| 4 | How do we reach a sensor inside a freezer? | LoRaWAN: range, airtime, energy |
| 5 | How do sensors last years on a battery? | CoAP for constrained devices, Observe, LwM2M, energy budget |
| 6 | How do all our devices speak one language? | units, time, identity, data models |
| 7 | What must be decided on site, without waiting for the cloud? | edge processing, alarms |
| 8 | Where does our energy go? | time series, dashboards, KPIs |
| 9 | Who can read and write our data? | TLS, authentication, access control |
| 10 | Is our architecture right? | you defend it |

Each lab contains a core path and optional extensions for groups that progress faster. The simulated plant runs on a virtual machine and reproduces the kinds of events needed throughout the course: shifts, cure cycles, door openings, changing measurements and device failures.

## Start

Clone the repository once, then enter the directory of the session you are working on:

```bash
git clone <this repository's URL> ~/IoT-Labs-UPPA      # once
cd ~/iot-labs/lab1                                  # or lab2
docker compose up -d --build
```

For later sessions, update the repository with `git pull` and enter the corresponding lab directory.
The available lab pages are [Lab 1](lab1/) and [Lab 2](lab2/). [Working environment](docs/setup.md) explains the UPPA VM or local setup, Docker, and access to the viewer.

*For the link between the labs and the lectures, see [the course map](docs/course.md). Adour
Composites, its people and its data are fictional; the protocols, standards and orders of magnitude
are real.*
