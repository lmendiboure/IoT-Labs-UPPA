# Lab 3 — Secure the AC-1 MQTT installation

## The situation

> "Quality control received a cure record named `CR-301`. It says `PASS`, but the AC-1 team
> cannot find the corresponding cure cycle. We also received a temperature of 999 °C.
> Find out how these messages entered our system. Then secure the installation without
> stopping legitimate production data."
>
> — Nora Elissalde, quality manager, Adour Composites

You are back at the same fictional factory as in Labs 1 and 2.

- **Lab 1:** you followed industrial data from devices to MQTT applications.
- **Lab 2:** you investigated a duplicate cure record (`CR-250`) after a network problem.
- **Lab 3:** you will investigate **new, false messages**, then protect the installation.

You will work with a real MQTT broker, real MQTT clients, access-control rules and TLS.
The autoclave and its measurements are simulated. Your task is to make the communication
system more secure **and keep it working**.

Answer **Q1–Q15**. The four **Going deeper** exercises are optional. Use the commands
in this lab only on the supplied classroom installation.

---

## Preparation

### 1. Start Lab 3 on the Ubuntu VM

If Lab 2 is still running, stop it **on the VM host**, from the `lab2/` directory:

```bash
docker compose down
```

Both labs use port 8080, so do not run them at the same time.

Go to `lab3/` **on the VM host**. Start the services and select the initial, insecure broker profile:

```bash
docker compose up -d --build
./switch.sh open
```

The word `open` means that the broker initially permits anonymous MQTT connections.
You will change this setting during the lab.

### 2. Open two workstation terminals

Run this command **twice on the VM host**, from `lab3/`:

```bash
docker compose exec workstation bash
```

Keep both terminals open:

| Terminal | Use |
|---|---|
| **Workstation A** | Run `quality_monitor.py` and leave it running. |
| **Workstation B** | Run MQTT clients, tests and other Python commands. |
| **VM host** | Edit broker and sensor configuration files. Run `./switch.sh` and `docker compose`. |

Unless a step says **VM host**, type its Python and MQTT commands in a workstation
terminal. The workstation starts in `/work`.

### 3. Open the two observation screens

Open these addresses in your **laptop browser**:

| Screen | Address | What it shows |
|---|---|---|
| MQTT viewer | `http://localhost:8080` | MQTT traffic passing through the teaching plaintext relay |
| Quality console | `http://localhost:8081` | Messages received by the quality application |

If you use a remote VM, forward ports **8080 and 8081** to your laptop.
The common [setup guide](../docs/setup.md) explains SSH port forwarding.

The two screens show different things:

- In the **MQTT viewer**, search for a `record_id` to find its `PUBLISH` packet.
  Clear the filter to find `PUBACK` or `SUBACK` packets. Those acknowledgements
  do not contain the record ID.
- In the **quality console**, search the event log for `CR-301` or another
  record ID. The console shows what the application received.

**Important:** the viewer only shows traffic through the plaintext relay.
Later, direct TLS connections will not appear there. Use the client terminal and
quality console to observe those tests.

The AC-1 simulator produces a temperature roughly every three seconds. It also
sends a completed-cure record named `CR-SIM-...` roughly every twelve seconds.
These are accelerated classroom events, **not real twelve-second cure cycles**.

Lab 3 starts with a fresh simulation. The `CR-250` event from Lab 2 is only a
previous case for comparison. It is not stored in this lab.

---

## Part 1 — Investigate the incident

Your first goal is to understand what the quality application receives.
Do not change the broker configuration yet.

### Step 1 — Observe an ordinary cure record

In **workstation A**, start the quality application:

```bash
python quality_monitor.py
```

**Leave this command running.** It provides the quality console on port 8081.

In your browser:

1. Wait for a cure record beginning with `CR-SIM-`.
2. Copy its exact `record_id` from the quality console.
3. Filter the MQTT viewer using that ID. Find the `PUBLISH` events
   and check their direction arrows (↑ and ↓) and client names.
4. Inspect the JSON payload and the console event for that ID.

### Q1 — What does a normal record tell us?

For **the same `CR-SIM-...` record**, find these two MQTT packets:

- The `PUBLISH` going **up** (client → broker): note the client and topic.
- The `PUBLISH` going **down** (broker → client): note the client and topic.

Also record the quality console's verdict and the JSON `device_id`.

**Question:** if you had observed only the **up** packet, could you conclude
that the quality application received the record? Which **additional observation**
in this experiment shows that the application actually received it?
Answer in two short sentences.

### Step 2 — Publish a fictitious record

In **workstation B**, run:

```bash
python attack.py --anonymous --record-id CR-301 --result PASS
python attack.py --anonymous --value 999
```

`attack.py` is a supplied MQTT publisher for the classroom exercise.
Here it sends messages **without a username or password**. It does not
modify the background AC-1 simulator.

Check three places:

1. The command output: look for `CONNACK` and `PUBACK`.
2. The quality console: search for `CR-301`.
3. The MQTT viewer: find the `PUBLISH` containing `CR-301`.

### Q2 — Did the fictitious record reach quality control?

Copy the `CONNACK`, `PUBACK` and quality-console result for `CR-301`.

Compare this incident with `CR-250` in Lab 2. Was `CR-250` a repeated delivery
of an existing record, or the creation of a new fictitious one? Which happened
with `CR-301`? Give one sentence for each case.

### Step 3 — Read production data anonymously

In **workstation B**, run:

```bash
python subscribe_probe.py --anonymous --topic 'plant/autoclave/AC-1/#'
mosquitto_sub -h relay -p 1884 -V mqttv5 -i lab3-guest-read \
  -t 'plant/autoclave/AC-1/#' -C 3 -v
```

The first command checks the MQTT subscription acknowledgement (`SUBACK`).
The second waits until it **receives three messages** and prints their topics and payloads.

### Q3 — What could the anonymous client read?

Copy the `SUBACK` result and one topic with its temperature value.

**Question:** what is the difference between reading this temperature and
publishing the fictitious `CR-301` in Q2?

### Step 4 — Check that legitimate production works

In **workstation B**, run:

```bash
python verify_service.py --seconds 25
```

This program connects as the `quality` user. It waits for two **new messages**
from the AC-1 simulator: one temperature and one `CR-SIM-...` cure record.
It does not count the forged records sent with `attack.py`.

### Q4 — What is our initial working-service result?

Copy these three output lines:

- `RECEIVED temperature: ... seq: ...`
- `RECEIVED cure record: ...`
- The final `PASS` or `FAIL` line.

Record the **temperature sequence number** and **cure-record ID**.
You will use this check again after changing the security settings.
Why is receiving both messages stronger evidence of working production
than seeing only an MQTT connection succeed? Answer in one sentence.

If it fails, inspect the sensor logs **on the VM host**:

```bash
docker compose logs --tail=30 sensor
```

<details><summary><strong>◆ Going deeper A — Client ID or authenticated identity?</strong></summary>

Open `attack.py` in the workstation files. Find the MQTT Client ID set by the program.

1. Change only that Client ID.
2. Repeat one of the publications from Step 2.
3. Check its `CONNACK` and `PUBACK`.
4. Restore the original Client ID.

Did changing the Client ID change the account's permissions?
Explain the difference between the MQTT Client ID, the authenticated username
and the `device_id` field inside the JSON message.

</details>

---

## Part 2 — Control MQTT access

The broker currently allows anonymous access. You will add two protections:

1. **Authentication:** who is allowed to connect?
2. **ACLs (access-control lists):** which topics can each account read or publish?

A valid password does not automatically give a client permission to use every topic.

### Step 5 — Require a password

On the **VM host**, from `lab3/`, activate authentication:

```bash
./switch.sh auth
```

The broker restarts. Wait for the command to finish.

In **workstation B**, try an anonymous publication and a wrong password:

```bash
python attack.py --anonymous --value 998
python attack.py --user visitor --wrong-password --value 998
```

### Q5 — Where were the connections refused?

For **each command**, record:

- The `CONNACK` result.
- Whether the program attempted a `PUBLISH`.

A connection error or timeout is not the same as an authentication refusal.
If you see a timeout, examine the broker logs on the VM host:

```bash
docker compose logs --tail=30 broker
```

### Step 6 — Try an authenticated visitor

Keep the `auth` profile active. In **workstation B**, run:

```bash
python attack.py --user visitor --record-id CR-302 --result PASS
```

This time the client uses valid demonstration credentials for `visitor`.
Find `CR-302` in the quality console. Also check its `CONNACK` and `PUBACK`.

### Q6 — Is a valid password enough?

Complete these three observations for the `visitor` publication:

| Observation | Result |
|---|---|
| MQTT connection (`CONNACK`) | |
| Cure-record publication (`PUBACK`) | |
| `CR-302` in the quality console | |

**Compare Q5 and Q6:** the anonymous client was refused, but `visitor` could
publish `CR-302`. Which operation did authentication stop in Q5? Which operation
was still allowed in Q6? Name the **exact cure-record topic** on which `visitor`
should not have write permission. Answer in two short sentences.

### Step 7 — Create the access-control policy

The factory has four accounts. These are the **permissions they need**:

| Account | Role |
|---|---|
| `ac1` | Publish AC-1 temperatures, cure records and `public/site/status` |
| `quality` | Read AC-1 temperatures and cure records only |
| `visitor` | Read `public/#` only |
| `maintenance` | Read AC-1 temperatures and publish diagnostics under `plant/autoclave/AC-1/maintenance/#` |

No account should have additional topic permissions.

On the **VM host**, from `lab3/`, open `broker/policy.acl`.
The file contains the four users and some missing rules marked `TODO`.

Mosquitto uses these forms:

```text
user <username>
topic read <topic-or-filter>
topic write <topic-or-filter>
```

The wildcard `#` matches a topic subtree. You used it in Lab 1.

### Q7 — Configure the ACL

**Do the following in order:**

1. Fill in this table using the four roles from Step 7.
2. Write the missing `topic read` and `topic write` rules in `broker/policy.acl`.
   The starter file already contains the visitor's `public/#` rule.
3. Activate your ACL from the **VM host**:

```bash
./switch.sh acl
docker compose logs --tail=30 broker
```

| Username | Topics it may read | Topics it may publish |
|---|---|---|
| `ac1` | | |
| `quality` | | |
| `visitor` | `public/#` | none |
| `maintenance` | | |

Do not use `readwrite #`. If the broker does not start, correct the ACL file
before proceeding. The following experiments will test your rules.

### Step 8 — Test three forbidden operations

In **workstation B**, run:

```bash
python attack.py --user visitor --record-id CR-303 --result PASS
python subscribe_probe.py --user visitor --topic 'plant/autoclave/AC-1/temperature' --listen-seconds 12
python attack.py --user maintenance --value 995
```

Check the output of **each** command.

- For publications, examine `CONNACK` and `PUBACK`.
- For the subscription, examine `SUBACK` **and** `DELIVERED_COUNT`.
- In the quality console, search for `CR-303`.
- While the subscription test runs, check that normal AC-1 temperatures
  still appear in the quality console.

**MQTT detail:** Mosquitto can acknowledge a subscription and still block
messages on forbidden topics. A successful `SUBACK` alone does **not** prove
that reading is authorized.

### Q8 — Did the ACL block the forbidden operations?

Complete the table using the results you just observed:

| Attempt | Connection result | MQTT acknowledgement or count | Application observation |
|---|---|---|---|
| `visitor` publishes `CR-303` | | `PUBACK`: | `CR-303` received: yes/no |
| `visitor` reads AC-1 temperature | | `SUBACK` and `DELIVERED_COUNT`: | New simulated AC-1 temperatures still arriving: yes/no |
| `maintenance` publishes a temperature | | `PUBACK`: | Topic printed by `attack.py`: |

If an operation is wrongly allowed, edit `broker/policy.acl` on the VM host.
Run `./switch.sh acl` again and repeat the failed test.

### Step 9 — Test four authorized operations

**First**, check that the visitor can receive a public site-status message.
In workstation B:

```bash
mosquitto_sub -h relay -p 1884 -V mqttv5 \
  -u visitor -P visitor-demo -i lab3-visitor-public \
  -t 'public/site/status' -C 1 -W 20 -v
```

AC-1 emits this non-sensitive public message about every twelve seconds.
The command stops after receiving one message.

**Next**, run the other tests in workstation B:

```bash
python attack.py --user ac1 --value 181
python subscribe_probe.py --user quality --topic 'quality/autoclave/AC-1/cure-records'
mosquitto_pub -h relay -p 1884 -V mqttv5 -u maintenance -P maintenance-demo \
  -i lab3-maintenance -q 1 -d \
  -t 'plant/autoclave/AC-1/maintenance/status' \
  -m '{"device_id":"AC-1","diagnostic":"fan_vibration","severity":"warning"}'
python verify_service.py --seconds 25
```

The maintenance message is **not** displayed in the quality console.
Read its `PUBACK` in the terminal instead. The `quality` subscription check is
an additional diagnostic. It does not replace `verify_service.py`.

### Q9 — Does the legitimate installation still work?

Report these **four results**:

1. Did `visitor` receive a `public/site/status` message?
2. Was the `ac1` temperature publication accepted?
3. Was the `maintenance/status` publication accepted?
4. Did `verify_service.py` report `PASS` for **both** AC-1 data streams?

For the fourth test, write only `PASS` or `FAIL`. You already recorded
sample messages in Q4. If the result is `FAIL`, identify which stream is missing.

**Troubleshooting case:** suppose the `visitor` and `maintenance` tests pass,
but `verify_service.py` reports `FAIL`: it receives temperatures but **no cure
record**. Which **two ACL permissions** would you check first? For each, name
the account, the action (`read` or `write`) and the exact cure-record topic.
Use your rules from Q7.

If the service check fails, inspect these logs **on the VM host**:

```bash
docker compose logs --tail=40 sensor broker
```

Check which component cannot connect, publish or subscribe. Correct the ACL
and repeat the failed test before moving on.

<details><summary><strong>◆ Going deeper B — What happens with an overly broad ACL?</strong></summary>

This extension deliberately introduces one bad permission.

1. Save a copy of your working `broker/policy.acl` on the VM host.
2. Add one extra permission for `visitor` that allows an operation from Q8.
3. Activate the new policy with `./switch.sh acl`.
4. Repeat that forbidden test from Q8. What changed?
5. Restore the original ACL. Activate it and repeat the test.
6. Run `python verify_service.py --seconds 25` in workstation B.

Which extra rule caused the security problem? Did removing it affect
legitimate production?

</details>

---

## Part 3 — Add TLS without breaking production

The ACL controls MQTT permissions. It does **not** encrypt messages sent
through the plaintext relay.

Now you will secure the connection between MQTT clients and the broker.
You will use a classroom certificate issued for the Docker hostname `broker`.
The trusted CA certificate is available in the workstation as `/work/ca.crt`.

**Migration plan:** enable TLS, test TLS, migrate the clients, check production,
then disable plaintext. Each broker profile change causes a brief restart.
This exercise does not promise a zero-downtime migration.

The demonstration broker key is included in the isolated training files.
Real production private keys must be handled much more securely.

### Step 10 — Check what the plaintext relay can see

Keep the `acl` profile active.

In **workstation B**, publish an authorized temperature:

```bash
python attack.py --user ac1 --value 182.5
```

In the **MQTT viewer**, find this publication and a recent `CR-SIM-...` cure record.
Open the JSON payload of the cure record.

### Q10 — Are business fields visible on plaintext MQTT?

From the cure-record `PUBLISH`, copy:

- Its MQTT topic.
- The JSON value of `result`.
- The JSON value of `batch`.

**Question:** did the ACL stop the plaintext relay from reading these fields?
What protection does TLS add that the ACL does not provide?

### Step 11 — Enable and inspect TLS

On the **VM host**, activate the profile that supports **both** plaintext and TLS:

```bash
./switch.sh tls
```

In **workstation B**, inspect the broker certificate:

```bash
openssl s_client -connect broker:8883 -CAfile /work/ca.crt \
  -verify_hostname broker -verify_return_error -brief </dev/null
```

Then run the same command with a different expected hostname:

```bash
openssl s_client -connect broker:8883 -CAfile /work/ca.crt \
  -verify_hostname not-broker -verify_return_error -brief </dev/null
```

These commands inspect TLS. They do **not** publish MQTT messages.
Do not disable certificate verification to make the second test succeed.

### Q11 — What does hostname verification change?

Copy the certificate-verification result for **both commands**.

Which hostname matched the broker certificate? Why is a successful TCP
connection insufficient to establish the identity of the server?

### Step 12 — Test both MQTT transports

In **workstation A**, stop the old quality monitor with `Ctrl+C`.
Restart it using TLS:

```bash
python quality_monitor.py --tls
```

Leave it running. Refresh the quality console in your browser.

In **workstation B**, publish one measurement over TLS and another over plaintext:

```bash
python attack.py --user ac1 --tls --value 183.5
python attack.py --user ac1 --value 184.5
```

Check the `PUBACK` of each command. Then look for both temperatures in the
quality console. Check which publication appears in the **plaintext viewer**.

### Q12 — Can clients still use plaintext?

Record these observations:

| Test | `PUBACK` | Visible in quality console? | Visible in plaintext viewer? |
|---|---|---|---|
| TLS publication `183.5` | | | |
| Plaintext publication `184.5` | | | |

**Question:** is the old plaintext path still available?

On the **VM host**, open `sensor/sensor.env` and copy the current `MQTT_HOST`.
Why would disabling plaintext now interrupt the AC-1 simulator?

### Step 13 — Migrate the AC-1 producer

So far, your test client and quality application use TLS. The AC-1 simulator
still uses the plaintext relay. You must migrate it as well.

On the **VM host**:

1. Open `sensor/sensor.env` (from the `lab3/` directory).
2. Change `MQTT_TRANSPORT`, `MQTT_HOST` and `MQTT_PORT` to the TLS
   transport and broker endpoint you tested in Steps 11–12.
3. Keep `MQTT_CA_PATH` unchanged.
4. Recreate the sensor container so Docker loads the new values:

```bash
docker compose up -d --no-deps --force-recreate sensor
docker compose logs --tail=35 sensor
```

A simple `docker compose restart sensor` would **not** reload the edited `env_file`.

In **workstation B**, check the background AC-1 simulator, not just your test publisher:

```bash
python verify_service.py --tls
```

The check needs a **new temperature and a new `CR-SIM-...` cure record**.

### Q13 — Did the AC-1 simulator migrate successfully?

Copy:

1. The three modified lines in `sensor/sensor.env`.
2. The `AC-1 CONNECTED ...` line from the sensor logs.
3. `PASS` or `FAIL` from `verify_service.py --tls`. Do not copy all
   the received messages again.

**Question:** which result proves that the **background producer** uses TLS?
Which result shows that the **quality application** still receives both streams?

If the test fails, inspect `docker compose logs --tail=40 sensor broker`
**on the VM host**. Resolve the connection or publication problem before Step 14.

### Step 14 — Disable plaintext

**Only after Q13 succeeds**, activate TLS-only mode on the VM host:

```bash
./switch.sh tls-only
docker compose logs --tail=35 broker sensor
```

In **workstation B**, run these four tests:

```bash
python attack.py --user ac1 --value 185.5
python attack.py --user ac1 --tls --value 185.5
python attack.py --user visitor --tls --value 996
python verify_service.py --tls
```

The first command still uses the old plaintext relay. It may produce a
connection error or timeout. That is **not** an MQTT ACL refusal.

### Q14 — Is plaintext blocked while production still works?

Complete the table with the actual results:

| Test | Observed result | Explanation |
|---|---|---|
| `ac1` publication through plaintext | | |
| `ac1` publication through TLS | | |
| `visitor` publication through TLS | | |
| New AC-1 temperature **and** cure record through TLS | | |

The final row must be supported by `verify_service.py --tls`.
A TLS connection alone does not prove that the application still works.

Which failed test was blocked at the transport level? Which reached
the broker over TLS but was refused by the ACL?

<details><summary><strong>◆ Going deeper C — Investigate a broken TLS migration</strong></summary>

On the **VM host**:

1. Save the working `sensor/sensor.env` file.
2. Set an incorrect `MQTT_HOST`.
3. Recreate the sensor with `docker compose up -d --no-deps --force-recreate sensor`.
4. Inspect its logs. What failed?
5. Compare this failure with the wrong-hostname certificate check in Q11.
6. Restore the correct `sensor/sensor.env` and recreate the sensor again.

In workstation B, finish with a successful `python verify_service.py --tls`.

</details>

---

## Part 4 — Can we trust a valid MQTT message?

You have protected MQTT access and transport. But a client using valid `ac1`
credentials can still send an invented measurement. TLS does not prove that
the physical autoclave produced the value.

### Step 15 — Send a false measurement with valid credentials

Keep the broker in `tls-only` mode. Keep the TLS quality monitor running
in **workstation A**.

In **workstation B**, run:

```bash
python attack.py --user ac1 --tls --value 999
```

Inspect the `PUBACK` and the corresponding event in the quality console.

Now you will add a basic **application-level plausibility check**.
For this **classroom simulation only**, accept a temperature when:

- The JSON payload is an object with `device_id` equal to `AC-1`.
- `temperature_c` is a finite number (not `True`, `False` or infinity).
- The temperature is between **160 and 200 °C**, inclusive.

These numbers are **not industrial safety limits**. They are test values chosen
for this exercise. Malformed or incomplete data must be rejected without
crashing the monitor.

### Step 16 — Complete and test the validation function

In the workstation files, open `validate_student.py`.
Complete the TODO inside `assess(data)`.
It receives an already-decoded JSON value. It returns a pair
`(accepted, reason)`. The first value is `True` or `False`. The second is a
short explanatory string.

Hint: `math.isfinite()` can check for infinity and `NaN`. In Python,
`True` also passes `isinstance(True, int)`, so handle booleans separately.

Run the supplied tests in **workstation B**:

```bash
python test_validation.py
```

Make corrections until the program reports **8/8**.

### Step 17 — Observe the result in the quality console

In **workstation A**, stop the quality monitor (`Ctrl+C`). Restart it with
the validation function enabled:

```bash
python quality_monitor.py --tls --validate
```

Leave it running. In **workstation B**, send three messages:

```bash
python attack.py --user ac1 --tls --value 180
python attack.py --user ac1 --tls --value 999
python attack.py --user ac1 --tls --record-id CR-399 --result PASS
```

Use the quality console's event search to find `CR-399`. Also inspect the
latest **accepted** temperature. A rejected measurement is still recorded
in the event log, but should not replace the latest accepted temperature.

**Important:** `assess(data)` checks **temperature messages only**.
Cure records still appear as `UNVERIFIED`. This means the application has
not verified the physical cure event. It is not an MQTT authentication error.

### Q15 — What can the application verify?

First, show the result **8/8** from `test_validation.py`.
Complete the table using the quality console:

| Input sent over TLS by `ac1` | Console result | What this result tells you |
|---|---|---|
| Temperature `180` | | |
| Temperature `999` | | |
| Cure record `CR-399` with `PASS` | | |

Check whether the rejected `999` replaced the latest accepted temperature.

**Two questions:**

1. Why does accepting `180` **not** prove that the sensor measured 180 °C?
2. Why does the temperature filter **not** establish that the cure cycle
   claimed by `CR-399` actually happened?

<details><summary><strong>◆ Going deeper D — Can two cure records contradict each other?</strong></summary>

In Lab 2, you investigated **duplicate delivery**. Here the question is
whether two business records with the **same ID** can claim different results.
Keep the TLS-only broker, your ACL and the quality monitor from Q15 running.

### D1 — Observe an identical record twice

On the **VM host**, from `lab3/`, open a **third workstation terminal**:

```bash
docker compose exec workstation bash
```

In that terminal, start a separate audit subscriber:

```bash
python record_audit.py --tls
```

Wait for `READY`. This tool compares the contents of cure records with the
same `record_id`. It does not change the main quality application.

In **workstation B**, inspect `replay_cr399.json`. Then run this command
**twice**:

```bash
mosquitto_pub -h broker -p 8883 --cafile /work/ca.crt \
  -u ac1 -P ac1-demo -V mqttv5 -q 1 -d \
  -t 'quality/autoclave/AC-1/cure-records' -f replay_cr399.json
```

In the audit terminal, find the two lines for `CR-399`. Record their labels.
Check that both commands received a `PUBACK`. The quality console should also
show two receptions of this record.

### D2 — Submit a contradictory result

The file `conflict_cr399.json` contains **the same `record_id`** and cure data,
but a different `result`. Compare it with `replay_cr399.json`.

In **workstation B**, publish the conflicting file:

```bash
mosquitto_pub -h broker -p 8883 --cafile /work/ca.crt \
  -u ac1 -P ac1-demo -V mqttv5 -q 1 -d \
  -t 'quality/autoclave/AC-1/cure-records' -f conflict_cr399.json
```

Read the new audit line. Find the corresponding `CR-399` event in the quality
console. Does either application independently know which claimed result is true?

### D3 — Invent a new record ID

In **workstation B**, run:

```bash
python attack.py --user ac1 --tls --record-id CR-400 --result PASS
```

Read the audit line for `CR-400`. The test publisher used valid `ac1`
credentials, but it did not operate a physical autoclave.

**Answer these three short questions:**

1. What distinguishes the second publication in D1 from the publication in D2?
2. Which discrepancy can the audit detect? Does that establish whether the
   actual cure result was `PASS` or `FAIL`?
3. Why does the audit accept `CR-400` as a new ID even though no real cycle
   was observed? What additional evidence would a production quality system need?

The audit keeps its first-seen records **in memory only**. It is an investigation
tool, not a durable quality database or proof of physical provenance.

</details>

---

## Handover — What have we secured?

Your final installation should have:

- A broker that accepts **TLS only**.
- An AC-1 simulator and a quality consumer using TLS.
- ACL rules that block unauthorized operations but allow legitimate production.
- A temperature check that rejects invalid data without claiming physical proof.

Keep the evidence you collected in Q1–Q15. No separate report format is needed.

The next lab will focus on architecture. One question remains open:
**how can the factory establish that a cure record represents a real, complete
and unique production event?**

---

## If you need to start the lab again

Changing the broker profile back to `open` does **not** restore your edits to
`broker/policy.acl` or `sensor/sensor.env`.

**Only if you want to discard these edits**, save your work and run the following
commands **on the VM host, from `lab3/`**:

```bash
cp broker/policy.acl.starter broker/policy.acl
cp sensor/sensor.env.starter sensor/sensor.env
./switch.sh open
docker compose up -d --no-deps --force-recreate sensor
```

This overwrites your ACL and sensor connection settings.
If the quality monitor was stopped, start it again in workstation A.
Its event history is kept in the running application, not in a permanent database.
