# Site architecture record — Adour Composites, Tarnos

Team: *(your names)*

This file follows you from lab to lab. Each lab asks you to write or revise one section, and to add
the decisions you took to the log at the end. In Lab 10, you defend it: it should let a newcomer
understand how the plant's data travel, and why they travel that way.

Keep it short and precise: a diagram, a table, a sentence per decision. A section written in Lab 1
may be wrong by Lab 5 — revise it, and say so in the log. Every decision is written the way the
lectures ask: the constraint, the option retained, the option rejected, and the reason.

## 1. Context and needs *(Lab 1, at home before Lab 2)*

Three uses of the plant's data, each in the five lines of L1:

| | Freezer compliance | Cure record | Energy bill |
|---|---|---|---|
| Family of use | | | |
| Deciding constraint | | | |
| Tolerates a lost message? | | | |
| Whose network | | | |
| Who is still there in ten years | | | |

## 2. Architecture overview *(Lab 1, at home before Lab 2; revised in every lab)*

A diagram of the site's data path, layer by layer: devices, networks, gateways, broker, platform,
applications. A Mermaid diagram (GitHub draws it) or an image in this folder.

## 3. Topic organisation *(Lab 1, at home before Lab 2)*

The structure of the plant's topic tree, with two or three examples, what queries it makes easy, and one limitation you observed.

## 4. Device status and liveness *(Lab 1, at home before Lab 2)*

How the site observes MQTT-client liveness: topics, payloads, retain flags and keepalive — and what this does not prove about sensors behind a gateway.

## 5. Delivery guarantees per flow *(Lab 2)*

## 6. Field integration: Modbus and OPC UA *(Lab 3)*

## 7. Long-range wireless *(Lab 4)*

## 8. Constrained devices and their energy *(Lab 5)*

## 9. Data model *(Lab 6)*

## 10. Edge processing *(Lab 7)*

## 11. Platform *(Lab 8)*

## 12. Security *(Lab 9)*

## Decision log

| Lab | Constraint | Option retained | Option rejected | Reason |
|---|---|---|---|---|
| 1 | | | | |
