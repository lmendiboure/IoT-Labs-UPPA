# IoT Labs — Adour Composites

You are the new IoT engineers of **Adour Composites**, a plant in Tarnos that makes carbon-fibre parts
for aircraft. Its machines and sensors already send data, each in its own way, and nobody uses them
together. In three weeks an aerospace customer audits the plant; the electricity bill went up by a
third; and the plant manager wants *"one system, not nine"*.

Over ten labs, you build that system, one question at a time.

| Lab | The plant's question | What you learn |
|---|---|---|
| [1](lab1/) | **How do our data travel today, and can we trust them?** | MQTT publish/subscribe; tracing data end to end; first normalization decisions; client liveness |
| 2 | Can we lose a cure record if the network fails? | MQTT delivery guarantees, sessions |
| 3 | Can we read the machines directly? | Modbus, OPC UA |
| 4 | How do we reach a sensor inside a freezer? | LoRaWAN: range, airtime, energy |
| 5 | How do sensors last years on a battery? | CoAP, LwM2M, energy budget |
| 6 | How do all our devices speak one language? | units, time, identity, data models |
| 7 | What must be decided on site, without waiting for the cloud? | edge processing, alarms |
| 8 | Where does our energy go? | time series, dashboards, KPIs |
| 9 | Who can read and write our data? | TLS, authentication, access control |
| 10 | Is our architecture right? | you defend it |

Each lab is designed for a full three-hour session, with optional extensions beyond the core work. The simulated plant runs on a virtual machine and reproduces the kinds of events needed throughout the course: shifts, cure cycles, door openings, changing measurements and device failures.

## Start

```bash
git clone <this repository's URL> ~/iot-labs      # once; for a new lab later: cd ~/iot-labs && git pull
cd ~/iot-labs/lab1 && docker compose up -d --build
```

Then open the lab page ([Lab 1](lab1/)). [Working on your VM](docs/setup.md) contains the common VM, SSH, Docker and viewer setup.

## Across the ten labs

The numbered questions form the core work and are recorded in `work/answers.txt`; ◆ extensions provide additional problems based on the same material. Implementation exercises can be checked locally with `check`, while `check report` generates the submission file.

The ten labs progressively build a single architecture. Each session adds or revises decisions in `record/site-architecture.md`, with the constraint, retained option, rejected option and rationale. Lab 10 uses this record as the basis for the final defence.

*For the link between the labs and the lectures, see [the course map](docs/course.md). Adour
Composites, its people and its data are fictional; the protocols, standards and orders of magnitude
are real.*
