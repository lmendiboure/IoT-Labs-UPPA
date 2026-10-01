# IoT Labs — Adour Composites

You are the new IoT engineers of **Adour Composites**, a plant in Tarnos that makes carbon-fibre parts
for aircraft. Its machines and sensors already send data, each in its own way, and nobody uses them
together. In three weeks an aerospace customer audits the plant; the electricity bill went up by a
third; and the plant manager wants *"one system, not nine"*.

Over ten labs, you build that system, one question at a time.

| Lab | The plant's question | What you learn |
|---|---|---|
| [1](lab1/) | **How do our data travel today, and can we trust them?** | reading an IoT architecture; MQTT; a LoRaWAN frame taken apart; a topic namespace; knowing a device is alive |
| 2 | Can we lose a cure record if the network fails? | MQTT delivery guarantees, sessions |
| 3 | Can we read the machines directly? | Modbus, OPC UA |
| 4 | How do we reach a sensor inside a freezer? | LoRaWAN: range, airtime, energy |
| 5 | How do sensors last years on a battery? | CoAP, LwM2M, energy budget |
| 6 | How do all our devices speak one language? | units, time, identity, data models |
| 7 | What must be decided on site, without waiting for the cloud? | edge processing, alarms |
| 8 | Where does our energy go? | time series, dashboards, KPIs |
| 9 | Who can read and write our data? | TLS, authentication, access control |
| 10 | Is our architecture right? | you defend it |

Each lab is **three hours, on your own**, on a virtual machine that runs the simulated plant. The
data are simulated, but they behave like the real thing: shifts, cure cycles, a freezer door opened a
dozen times a day, devices that crash.

## Start

```bash
git clone <this repository's URL> ~/iot-labs      # once; later: cd ~/iot-labs && git pull
cd ~/iot-labs/lab1 && docker compose up -d
```

Then open the lab's page ([Lab 1](lab1/)): it tells you everything else. If you have never used SSH,
Docker or VS Code Remote, read [Working on your VM](docs/setup.md) first (ten minutes).

## How a lab works

- **The lab's page is the subject.** Read it in order: each part starts with *why* it matters.
- **You do** things in a terminal and in a viewer that shows every message on the network.
  `check` tells you whether an exercise works; `hint` helps you when you are stuck.
- **You think**: the questions go in `work/answers.txt`. They are graded — the checker is not.
- **You hand in** one text file, written by `check report`.
- **One record for the whole course**, `record/site-architecture.md`: each lab adds the decisions you
  took. In Lab 10, you defend it.

*For the link between the labs and the lectures, see [the course map](docs/course.md). Adour
Composites, its people and its data are fictional; the protocols, standards and orders of magnitude
are real.*
