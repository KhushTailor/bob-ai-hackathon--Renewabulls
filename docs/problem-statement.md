# Problem Statement

## Background

The global electricity grid is undergoing a structural transformation. As renewable generation capacity — solar photovoltaic and wind — expands to meet net-zero targets, grid operators are managing increasingly complex and volatile systems. Unlike conventional thermal generation, renewable output is intermittent and weather-dependent, creating continuous imbalances between supply and demand that must be resolved in near real-time.

Distribution system operators (DSOs) managing microgrids and regional networks in the 50–500 MW range face this challenge most acutely. These operators are responsible for maintaining grid stability — keeping frequency at 50 Hz and voltage within safe bounds — while simultaneously maximising the utilisation of available renewable generation to minimise curtailment and carbon emissions.

## The Problem

Grid operators managing renewable-heavy systems spend a disproportionate amount of their decision time on **data synthesis rather than decision-making**. The core problem is cognitive overload from fragmented telemetry:

- SCADA systems display raw sensor values (frequency, voltage, MW flows) but do not interpret them
- EMS (Energy Management Systems) provide alarms but do not rank them by urgency or suggest balancing actions
- Demand forecasts, when available, are produced by separate tools on different refresh cycles
- Renewable performance monitoring is manual — operators must compare actual to expected generation in their heads
- When multiple anomalies occur simultaneously, operators must mentally prioritise and select a balancing action without a structured evaluation framework

The result: in a typical frequency deviation event, an operator may spend 8–12 minutes correlating data across 4–6 different screens before initiating a balancing action. During that window, the grid is at risk of cascading under-frequency load shedding.

## Who is Affected

**Primary persona:** Distribution system operators at utilities, independent power producers, or microgrid operators managing renewable-heavy networks in the 50–500 MW range. These operators typically work 12-hour shifts, monitor 2–6 grid zones simultaneously, and are expected to respond to anomalies within minutes.

**Secondary persona:** Grid control room supervisors who need a rapid situational overview at shift handover or during major incidents.

## Why It Matters

- **Renewable curtailment** is a direct financial and environmental loss. In 2023, curtailment of solar and wind energy across major markets exceeded 50 TWh globally — representing clean energy wasted due to grid management limitations.
- **Under-frequency load shedding** (deliberate blackouts to protect grid stability) affects industrial and residential customers and costs utilities significant penalties under regulatory frameworks.
- **Operator error under cognitive load** is a documented contributor to grid incidents. Providing a structured, AI-synthesised view of the current situation reduces the decision burden and the window of risk.

## Why Existing Solutions Fall Short

Current SCADA and EMS tooling was designed for conventional, dispatchable generation. These systems excel at data collection and alarm triggering but have three fundamental gaps that GridPulse addresses:

1. **No synthesis layer:** Raw telemetry is displayed but not interpreted. Operators still must perform the mental work of correlating frequency, demand, renewable output, and battery state into a coherent situational picture.
2. **No forward-looking context:** Existing tools show the current state; they do not show where the grid is heading over the next 72 hours, which is critical for proactive rather than reactive operation.
3. **No ranked action recommendations:** When a balancing action is needed, operators must draw on experience to evaluate options. No standard tool evaluates battery dispatch vs. load shifting vs. grid import in real time and recommends the best option with an explanation.
