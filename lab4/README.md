# Lab 4 — Edge or Cloud? Keep the factory running

## The situation

> "AC-1 sends temperature readings to our central platform. Quality control wants an alert
> when the temperature stays too high. We are considering a small computer on the factory
> site to process the data locally. Does moving the decision to the edge really help?
> What would we lose? I need a recommendation based on tests, not a diagram alone."
>
> — Nora Elissalde, quality manager, Adour Composites

You return to the same fictional factory as in Labs 1–3. You already know how MQTT delivers
measurements, what happens when communication fails, and what authentication and TLS do.
This time, the question is **where processing should run**.

You will operate two real MQTT brokers, two Python processing services and a configurable
site-to-cloud forwarder. You will write a small detection algorithm and compare two
placements using **the same input data**. Then you will disconnect the forwarder.
The autoclave measurements are simulated. The MQTT exchanges and application processing
are real. Both sites run on one Ubuntu VM. The experiment does **not** measure a real WAN
latency or simulate physical equipment failures.

Complete **Q1–Q15**. The four **Going deeper** experiments are optional. The main lab is designed
for a three-hour session. Answer questions with short explanations supported by what you observed.

---

## Preparation

### 1. Start the services (VM host)

On the **VM host**, use these exact commands. Stopping Lab 3 is harmless if it is
already stopped:

```bash
cd ~/iot-labs/lab3
docker compose down
cd ../lab4
docker compose up -d --build
./mode.sh raw
./window.sh 5
docker compose ps
```

`raw` means that the site-to-cloud forwarder sends **every temperature measurement**.
`5` means that the edge produces one summary for every five measurements. You will
change the forwarding mode later. This lab has its **own** Docker environment.
Previous records from Lab 3 are not stored here.

### 2. Open your terminals

From `lab4/` on the **VM host**, open two workstation terminals with:

```bash
docker compose exec workstation bash
```

Run the command twice. Both terminals start in `/work`.

| Terminal | Used for |
|---|---|
| **Workstation A** | Send AC-1 measurements, run Python tests and read reports |
| **Workstation B** | Observe MQTT with `mosquitto_sub` and run diagnostics |
| **VM host** | Edit the lab files and run `./mode.sh`, `./window.sh` and `docker compose` |

Unless a step says **VM host**, run the Python and `mosquitto_sub` commands inside a workstation.
Check that all services are ready for MQTT traffic:

```bash
python check_services.py
```

Wait for `READY: all requested services` before sending data. A container shown as
*running* by Compose may not yet have subscribed to its MQTT topic.

### 3. Open two browser tabs

| Dashboard | Laptop browser | What it shows |
|---|---|---|
| **Edge gateway** | `http://localhost:8080` | Measurements and alerts handled on the factory site |
| **Cloud analytics** | `http://localhost:8081` | Messages actually received and processed in the cloud |

If you use the remote Ubuntu VM, forward **both** ports from your own computer.
For SSH, use `-L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081`.
See [Working environment](../docs/setup.md) for the full instructions.

The diagrams below show the **application data path**. The `workstation` is also connected
to both Docker networks so you can inspect the two dashboards. This is a separate
**teaching/measurement access path**, not a bypass used by production data.

```text
 FACTORY SITE (Docker network: site)              CLOUD (Docker network: cloud)
  AC-1 simulator -> site-broker                    cloud-broker -> cloud analytics
                       |                               ^
                       +-> edge processor             |
                       |     |                        |
                       |     +-> summaries and alerts |
                       |                              |
                       +------> uplink forwarder -----+
                           (raw OR edge mode)
```

The edge processor subscribes to the site broker and publishes its derived topics
back to that same broker. The forwarder chooses which of those topics reach the
cloud broker. The two brokers use real MQTT. The forwarder is a Python **application-level link** between
them. Stopping it is a controlled WAN-uplink failure. It is **not** a complete network
partition or a latency emulator. MQTT broker ports are not exposed to the VM host.

The brokers allow anonymous connections in this isolated classroom lab so that the
experiments isolate **placement** and traffic. A production design would also need
the authentication, ACL and TLS protections investigated in Lab 3.

The deterministic scenario sends 20 temperatures. Two events are important:

- A **single high measurement** near the start.
- A **sequence of high measurements** later in the run.

The classroom alert rule is: **three consecutive measurements strictly above 190 °C**.
This is an illustrative algorithm, **not** an industrial safety limit.

---

## Part 1 — Investigate the cloud-only decision

The initial architecture sends all AC-1 temperatures to the cloud. The cloud already
implements the three-consecutive-measurements rule. The edge service is running, but
its student detection function is not yet implemented.

### Observe the MQTT publications

1. In **workstation B**, subscribe to the cloud broker **before** sending the scenario:

   ```bash
   mosquitto_sub -h cloud-broker -p 1883 -V mqttv5 \
     -t 'plant/autoclave/AC-1/temperature' -C 3 -v
   ```

   This command prints three real MQTT messages and then exits.

2. In **workstation A**, send the fixed 20-measurement scenario:

   ```bash
   python send_scenario.py --run RAW-1
   ```

3. Keep the `RAW-1` run in both dashboards. You can add `?run=RAW-1` to the URL.
   Generate a report:

   ```bash
   python report.py --run RAW-1 --expect-edge 20 --expect-cloud 20
   ```

### Q1 — What did the cloud actually receive?

Copy one complete topic and JSON message from workstation B. Find its `run_id`, `seq`
and `temperature`. In the report, record the number of raw measurements received by
the cloud. Are all 20 measurements visible at the cloud application?

### Find the two high-temperature events

In the **Cloud analytics** dashboard, select `RAW-1`. Use **Readings in this run**
to inspect the temperatures and **Alert events** to find the alert sequence number.
You can also check each value against the `PUBACK` lines in workstation A.

### Q2 — Why did one event trigger an alert but not the other?

Find the isolated reading at `seq=3`. Then inspect `seq=7`, `8` and `9`.
Which sequence produced the alert? Explain why the other high reading did not.

### Measure the initial upstream traffic

The report gives the number of MQTT publications and the total **application-payload bytes**
received by the cloud. This means the bytes inside the MQTT messages. It does not include
MQTT headers, TCP/IP framing, retransmissions or encryption overhead.

### Q3 — What does cloud processing require from the network?

Record the cloud's publication count and payload bytes for `RAW-1`.
The cloud raised an alert at `seq=9`. If it received **only** the temperature at
`seq=9`, could it apply the three-consecutive-readings rule? Name the preceding
readings it needs. Keep the traffic counters for Part 3.

---

## Part 2 — Move the decision to the edge

Now implement the same decision close to AC-1. The edge service already subscribes to
real temperature messages on the **site broker**. It produces summary messages every
five samples, but it cannot produce the required alert until you complete its function.

### Complete the local detector

1. In **workstation A**, run the initial tests **before changing the code**:

   ```bash
   python test_edge.py
   ```

   The incomplete starter fails some tests. Keep the output for Q4.
2. On the **VM host**, open `work/detect_student.py`. Complete its function
   `step(temperature, consecutive)`.
   Return the updated counter and a Boolean indicating whether to raise an alert.
   Raise **one** alert on the third consecutive reading strictly above 190 °C.
   Do not raise another on the fourth high reading. Reset the counter after a
   normal reading.
3. In **workstation A**, run the tests again:

   ```bash
   python test_edge.py
   ```

   Continue when you obtain `RESULT 7/7`.
4. On the **VM host**, restart the edge service so it loads your edited file:

   ```bash
   docker compose restart edge
   ```

5. In **workstation A**, check that its MQTT subscription is ready:

   ```bash
   python check_services.py
   ```

### Q4 — What does the function need to remember?

Choose **two failed cases from your first `test_edge.py` run**. For each,
record the temperature, the previous counter and the expected result.
Why does the detection rule need to remember the counter between readings?

### Test the detector on live MQTT data

The uplink is still in `raw` mode. Send the same temperatures under a new run ID:

```bash
python send_scenario.py --run MATCH-1
python report.py --run MATCH-1 --expect-edge 20 --expect-cloud 20
```

Inspect the **Edge gateway** and **Cloud analytics** dashboards for `MATCH-1`.

### Q5 — Do the edge and cloud decisions agree?

Record the alert sequence numbers from both services. They should describe the
same event. If not, use `python test_edge.py` and `docker compose logs --tail=30 edge`
to find out whether the edge is running your latest code.

### Q6 — Why is the fourth high reading different?

Use the outputs of `test_edge.py` for the third and fourth consecutive high
readings. What would happen if your function emitted another alert for every
subsequent high sample? Explain one consequence for an alarm dashboard.

### Q7 — Is the edge detecting an actual MQTT stream?

Take one `PUBACK` line from the simulator and the edge `raw samples` count
from the `MATCH-1` report. **What does the `PUBACK` prove, and what does the
edge count prove that the `PUBACK` alone does not?** Name the broker that
acknowledged the simulator's publication.

<details><summary><strong>◆ Going deeper A — Is a simple threshold enough?</strong></summary>

Keep `raw` mode. Send a different scenario with isolated high readings:

```bash
python send_scenario.py --run NOISE-1 --profile noisy
python report.py --run NOISE-1 --expect-edge 20 --expect-cloud 20
python inspect_alerts.py --run NOISE-1
```

The last tool compares two rules using **real received measurements**: an alarm for
every individual temperature above 190 °C, versus the three-consecutive-samples
rule you implemented. Record both event counts. Which rule suppresses isolated
spikes? What important drawback could the three-sample rule introduce if the
sampling interval were much longer?

</details>

---

## Part 3 — Reduce site-to-cloud traffic

The local detector now works. We can stop forwarding raw measurements and send only
**summary windows and alerts** to the cloud. We must compare both modes using the
**same 20 temperatures**. Do not restart the brokers. Use a new run ID.

### Activate edge forwarding

On the **VM host**:

```bash
./mode.sh edge
```

In **workstation A**:

```bash
python send_scenario.py --run EDG-1
python report.py --run EDG-1 --expect-edge 20 --expect-cloud 5
```

Open the **Cloud analytics** dashboard with `?run=EDG-1`. Compare it with `RAW-1`.

### Q8 — How many publications crossed the link?

Complete this table using the two reports. Do **not** use the number of messages
published only on the site broker.

| Placement | Cloud MQTT publications | Cloud application-payload bytes | Cloud alerts |
|---|---:|---:|---|
| Raw forwarding, `RAW-1` | | | |
| Edge summaries and alerts, `EDG-1` | | | |

### Q9 — What did the traffic reduction actually save?

Calculate the reduction in cloud publications and in payload bytes, in percent:
`100 × (raw − edge) / raw`. Why can the two percentages differ?

### Q10 — Which information disappeared?

For the first window, find `seq=1–5` and its mean in the cloud summary.
Compare it with the isolated 195 °C sample at `seq=3` from Part 1.
Can the cloud reconstruct that exact high reading from the mean alone? Use these
observations to justify your answer.

### Q11 — Can a richer summary preserve the peak?

You have seen that the mean cannot reveal the isolated peak. Now improve the
application rather than answering only in theory.

1. Open `work/summary_student.py` on the **VM host**. Complete `extra_fields(window)`.
   The input is an ordered list of `(seq, temperature)` pairs. Return the **maximum
   temperature** and the **sequence number of its first occurrence**, using the
   fields `maximum` and `peak_seq`.
2. In **workstation A**, test the function:

   ```bash
   python test_summary.py
   ```

   The starter is incomplete. Continue when you obtain `RESULT 5/5`.
3. On the **VM host**, restart `edge` to load your code:

   ```bash
   docker compose restart edge
   ```

4. In **workstation A**, wait for the service, send a new run and inspect its report:

   ```bash
   python check_services.py
   python send_scenario.py --run EDG-PEAK
   python report.py --run EDG-PEAK --expect-edge 20 --expect-cloud 5
   ```

5. In the cloud dashboard, look at the summary for `seq=1–5` under `EDG-PEAK`.
   Record its `mean`, `maximum` and `peak_seq`. Compare the number of **payload bytes**
   with the old `EDG-1` run. Did preserving this peak make the summary larger?

Can the cloud now reconstruct the **complete five-temperature sequence**?
Explain what information it still lacks.

<details><summary><strong>◆ Going deeper B — Does a larger window always help?</strong></summary>

Keep `edge` mode. Compare three summary sizes. For each **new run**, set the size
on the **VM host**, then send the fixed scenario in **workstation A**:

| VM host command | Workstation A: send | Workstation A: report |
|---|---|---|
| `./window.sh 5` | `python send_scenario.py --run WIN-05` | `python report.py --run WIN-05 --expect-cloud 5` |
| `./window.sh 10` | `python send_scenario.py --run WIN-10` | `python report.py --run WIN-10 --expect-cloud 3` |
| `./window.sh 20` | `python send_scenario.py --run WIN-20` | `python report.py --run WIN-20 --expect-cloud 2` |

Use the same input temperatures each time. Record the number of cloud publications,
payload bytes and summary ranges. Does a larger window reduce the traffic?
What is its effect on **how soon** the cloud learns the mean of recent measurements?
Restore `./window.sh 5` on the VM host afterward.

</details>

---

## Part 4 — Keep local detection during a WAN outage

We will now stop **only the uplink forwarder**. The local broker, edge processor and
cloud service remain running. No messages are queued for later transfer in this
teaching forwarder. This is a placement and visibility experiment, **not** a repeat
of the MQTT QoS and persistent-session exercises from Lab 2.

### Establish a shared starting point

1. On the **VM host**, ensure the configuration is back to:

   ```bash
   ./mode.sh edge
   ./window.sh 5
   ```

2. In **workstation A**, send the first five readings:

   ```bash
   python send_scenario.py --run WAN-1 --segment before
   python report.py --run WAN-1 --expect-edge 5 --expect-cloud 1
   ```

3. On the **VM host**, stop the forwarder:

   ```bash
   docker compose stop uplink
   ```

4. In **workstation A**, check that the **edge and cloud** services are still ready:

   ```bash
   python check_services.py --without-uplink
   ```

5. Still in **workstation A**, send the next ten readings during the outage:

   ```bash
   python send_scenario.py --run WAN-1 --segment outage
   python report.py --run WAN-1 --expect-edge 15 --expect-cloud 1
   ```

### Q12 — What is still running during the outage?

In the `WAN-1` report, compare the number of site measurements with the number of
cloud publications. Which components have definitely continued processing?
Use the **Edge gateway** dashboard to confirm that local readings are still arriving.

### Q13 — Where was the alert generated?

Find the alert sequence number in the edge dashboard for `WAN-1`.
Search for the same `run_id` in the cloud dashboard. Why is this alert missing
from the cloud even though it was produced locally?

### Reconnect without inventing a recovery mechanism

On the **VM host**, start the forwarder again:

```bash
docker compose start uplink
```

In **workstation A**, wait for its MQTT subscriptions, then publish the final five readings:

```bash
python check_services.py
python send_scenario.py --run WAN-1 --segment after
python report.py --run WAN-1 --expect-edge 20 --expect-cloud 2
```

### Q14 — Did reconnection restore the missing history?

From the final report, record the cloud's summary sequence ranges.
Which readings reached the edge but are absent from the cloud history?
Why does the forwarder resuming **new publications** not restore the missing ones?

### Q15 — Where should each function run?

Use your own observations to complete this short architecture decision table.
For each function, choose **edge**, **cloud** or **both**, and cite **one result**
from this lab. The same answer is not required for every function.

| Function | Edge / cloud / both? | Evidence from your experiments |
|---|---|---|
| Immediate temperature alert at the factory | | |
| Historical quality analysis across sites | | |
| Aggregation before the WAN link | | |
| Recovery of measurements missed during a WAN outage | | |

For the final row, state one **additional mechanism** your proposed system would
need. Do not claim that the current forwarder already implements recovery.

<details><summary><strong>◆ Going deeper C — Detect the holes in cloud history</strong></summary>

Extend Q14 with a small program. Open `work/gaps_student.py` on the VM host.
Complete `missing_ranges(local_seqs, cloud_ranges)` to return the intervals
that the edge received but the cloud did not. The cloud may have individual
raw sequences or aggregate ranges. The function must work even when the first
local sequence is not 1.

In **workstation A**:

```bash
python test_gaps.py
python history_check.py --run WAN-1
```

The student starter is incomplete. First obtain `RESULT 5/5`.
Then use the *real* `WAN-1` service observations to identify the missing ranges.
Why can a correct gap detector **report** missing data without being able to
reconstruct it? Name one mechanism that could provide durable recovery.

</details>

<details><summary><strong>◆ Going deeper D — What if the edge itself fails?</strong></summary>

The edge is now a possible point of failure. Test a **manual cloud fallback**.
On the **VM host**:

```bash
./mode.sh raw
docker compose stop edge
```

In **workstation A**:

```bash
python check_services.py --without-edge
python send_scenario.py --run FALL-1
python report.py --run FALL-1 --expect-cloud 20
```

The site broker remains alive, and the forwarder now routes raw measurements
to the cloud. Confirm the cloud alert sequence number. Which local function is
lost while `edge` is stopped? Does this configuration require the WAN to stay
available for detection? Restore the lab on the **VM host**:

```bash
docker compose start edge
./mode.sh edge
```

Then run `python check_services.py` in workstation A.
This experiment demonstrates a **manual** fallback, not an automatic failover.

</details>

---

## Handover — What should Adour Composites deploy?

Your final recommendation must distinguish **where a decision is made** from
**where a record is stored**. The experiments establish that local processing can
continue while the WAN forwarder is down, and that summary-only traffic can save
transmissions at the cost of raw information. They do **not** prove that any
industrial system is fault-tolerant, or that a measurement is physically authentic.

Keep four pieces of evidence with your answers: the cloud-only baseline, your working
edge detector (`7/7`), the raw-versus-edge traffic comparison, your improved summary (`5/5`), and the WAN-outage
result. These are sufficient to justify your architecture in Q15.

### Stop the lab

When finished, on the **VM host**:

```bash
docker compose down
```

Your edits under `lab4/work/` remain on the VM. For another attempt, choose **new
run IDs**. If you want a clean start, use `docker compose down` followed by
`docker compose up -d --build`, then run `./mode.sh raw` and `./window.sh 5`.
