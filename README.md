# IoT Labs — Adour Composites

You are part of the engineering team at **Adour Composites**, a fictional carbon-fibre manufacturing site in Tarnos. Across the labs, you return to the same factory, its equipment and its quality-control needs. Each session starts with a new problem in a system you already know.

## The four investigations

| Lab | The problem to solve | What you will investigate |
|---|---|---|
| [Lab 1 — Understand the installation](lab1/) | How do equipment data reach applications, and what can we actually observe? | MQTT publish/subscribe, topics, payloads, gateways, LoRaWAN uplink, client liveness |
| [Lab 2 — Investigate network failures](lab2/) | Can an autoclave cure record be lost, delayed or delivered twice? | MQTT QoS, acknowledgements, sessions, reconnection and a first comparison with CoAP |
| [Lab 3 — Secure the existing system](lab3/) | Can an unauthorized client fabricate a cure record, and can we secure MQTT without interrupting production data? | Message injection, identity, ACL configuration, TLS migration, application checks |
| Lab 4 — Design the architecture (forthcoming) | How should we design the complete IoT system given what we have learned? | Justified choices for devices, gateways, edge/cloud, reliability, security and data handling |

**The connection between sessions matters.** Lab 1 establishes the data path; Lab 2 tests what the communication layer guarantees under failure; Lab 3 asks who is allowed to supply those data and whether the quality application can trust them. The last lab brings these observations together into an architecture.

Each lab runs a **separate, reproducible Docker simulation**. The site, equipment names, MQTT topics and business scenarios are reused where relevant, but a broker session or a record saved in one lab is not automatically transferred to the next. References to earlier incidents are there to help you compare what you observed.

## Preparation and working environment

Use the UPPA teaching VM or a local machine with Docker Compose. See [Working environment](docs/setup.md) for initial setup, proxy settings, SSH access, port forwarding and troubleshooting.

Clone the repository only once. Before a new lab, update your existing copy:

```bash
cd ~/iot-labs
git pull
```

Stop the previous lab from **its own directory** (`docker compose down`) before starting the next one; the labs reuse some host ports. For example, to start Lab 3 after Lab 2:

```bash
cd ~/iot-labs/lab2
docker compose down
cd ../lab3
docker compose up -d --build
docker compose ps
```

Follow the **Preparation** section in the README of the lab you are doing. Unless the instructions say otherwise, the student commands run inside its `workstation` container:

```bash
docker compose exec workstation bash
```

The MQTT viewer is available at `http://localhost:8080` (forward this port when using the VM). Lab 3 also has a quality console at `http://localhost:8081`; its README explains when to start it and how to forward the second port. The viewer and the quality console show **different evidence**: packets seen on the observation path versus data handled by the application.

## How to work through a lab

Read the scenario, follow the experiments in order and use your observations to support answers to the numbered questions. Commands, traces and application output are evidence, not explanations on their own. Some exercises require modifying configurations or Python files and then showing that the resulting service still works. Optional **Going deeper** sections are not prerequisites.

You may keep the reasoning and evidence in a format that suits your group; no universal answer template is imposed. If useful, maintain the [optional architecture decision log](record/site-architecture.md) to carry your findings into Lab 4.

**Safety note:** the deliberately insecure services, sample accounts and training certificates are intended only for the isolated teaching environment. Do not reuse them for a real installation or test the exercises against systems outside the lab.
