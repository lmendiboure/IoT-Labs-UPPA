# The course map

The labs apply the material developed in *IoT Systems Design*. The map below positions each session within the end-to-end system and indicates the corresponding lecture material.

## One chain, from the sensor to its use

The sessions progressively cover different parts of the same end-to-end chain.

```mermaid
flowchart LR
    D["Device<br/>sense · compute · power"] --> N["Network<br/>connect · backhaul"]
    N --> E["Gateway and edge<br/>protocols change here"]
    E --> P["Platform<br/>broker, storage, management"]
    P --> A["Use<br/>dashboards, records, alarms"]
```

| Lab | Where in the chain | Lectures |
|---|---|---|
| 1 | The whole chain and MQTT observations | L1; L3 (communications and data) |
| 2 | Broker, application, delivery guarantees and CoAP | L3 (protocols and transport) |
| 3 | MQTT trust boundaries: publisher, broker, reader and channel | L3 (communication services and architecture) |
| 4 (planned) | End-to-end design: field, gateway, edge, cloud and services | L1, L2, L3 |

**L1** *What a connected system is made of* — the six blocks, the five lines, who answers.
**L2** *The radio link* — link budget, range and rate, technologies.
**L3** *Communication protocols and system architectures* — layers, sharing, addressing, transport,
application, data, placement, edge, engineering models, method.

## Protocol families you will meet

These technologies sit at different places in the chain and expose different interaction models. The
labs will make you compare their consequences rather than treat this table as a recipe.

| Technology | Interaction model | Typical transport here | Main role in this course | Lab |
|---|---|---|---|---|
| **MQTT** | publish / subscribe through a broker | TCP or TLS over TCP | data exchanges, reliability and applied security | 1, 2, 3 |
| **LoRaWAN** | device uplinks through gateways to a network server | LoRa radio, sub-GHz | low-rate, long-range IoT connectivity | 1 |
| **Modbus TCP** | request / response over registers | TCP | industrial protocol (context, not a standalone lab) | Architecture |
| **OPC UA** | client / server; also PubSub | UA TCP and other mappings | industrial data models (context, not a standalone lab) | Architecture |
| **CoAP** | request / response; confirmable and non-confirmable messages | UDP | constrained request/response and reliability contrast | 2 |
| **LwM2M** | device management with a standard object model | CoAP | fleet management (background) | Lecture |
| **HTTP** | request / response | TCP in these labs | application service interfaces | Architecture |

## Engineering principles used throughout the course

The labs repeatedly use three principles: distinguish the interaction model from the protocol that implements it; quantify communication costs rather than reasoning only from protocol names; and justify architectural decisions in terms of a constraint, a retained option, an alternative and the rationale for the choice.
