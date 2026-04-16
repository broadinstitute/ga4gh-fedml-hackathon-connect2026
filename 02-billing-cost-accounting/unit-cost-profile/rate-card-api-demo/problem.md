# Rate Card API: Problem Description

## Abstract

Federated ML across GA4GH participants requires a way for each compute site to advertise what it costs to run a job there. Today there is no GA4GH schema for this, and sites are too heterogeneous — academic HPC, hospital data centers, commercial clouds, and single-lab workstations — to be described by a single flat price list. This document sketches a minimal, TES-aligned "rate card" schema built around the idea of multiple priced *offerings* per site, with preemption as a first-class field.

## The problem

Federated machine learning only works if workloads can move to data. As soon as a workflow planner has more than one eligible site for a task, it needs to reason about cost: is it cheaper to run here or there? How much budget does this training run consume? Can I use a cheaper preemptible queue and tolerate restarts?

In practice, the sites that make up a GA4GH federation look nothing alike:

- An academic HPC cluster with Slurm partitions (`gpu`, `gpu-preempt`, `bigmem`), no dollars, but an allocation / service-unit economy.
- A hospital data center with fixed internal chargeback rates per CPU-hour.
- A commercial cloud backend (AWS Batch, GCP Batch) with on-demand and spot pricing that changes by region and instance type.
- A lab workstation with effectively zero marginal cost but a real opportunity cost when the grad student wants it back.

There is no uniform SKU catalog across these. There is also no existing GA4GH specification that says how a site should expose its prices. Downstream work on cost attribution, chargeback, and budget-aware scheduling is blocked until that schema exists.

## Who owns the rate card?

We argue the rate card belongs at the **TES endpoint**. TES is where tasks actually execute and where the backend-specific resource model is already concrete (CPU, RAM, GPU, disk, runtime). A TES implementation already knows what hardware it has and what queues or node pools it can dispatch to. Asking it to additionally publish a price per offering is a small step.

**WES aggregates.** When a workflow engine plans a multi-step job, it consults the rate cards of all TES backends it can reach and composes a workflow-level cost estimate. WES itself does not need to own prices; it needs to be able to read them.

Discovery is an open question (see below), but a natural path is an extension to the existing GA4GH `service-info` response pointing at a rate card URL.

## Heterogeneity: the offering model

A single `site -> price` mapping is not expressive enough. Every site we have looked at exposes several priced lanes:

- **Slurm** sites define partitions with `TRESBillingWeights` — different CPU/GPU/memory weights per partition, plus QOS tiers.
- **Kubernetes** sites define node pools and `PriorityClass` objects — some pools are on-demand, some are spot/preemptible, with different per-node cost.
- **Clouds** expose on-demand, spot, reserved, and savings-plan pricing for otherwise identical instance types.

The common shape is: a site publishes **N offerings**, each priced independently, each with its own preemption semantics and hardware descriptor. A rate card is therefore a list of offerings, not a list of resource prices.

## Preemption as a first-class field

Academic and institutional sites frequently offer "scavenger" or preemptible queues at large discounts — sometimes free — in exchange for the right to kill jobs. Clouds do the same thing with spot instances. Workflow planners need this signal to decide whether a given task (checkpointable? short? tolerant of restart?) is a good fit for a cheap-but-interruptible offering.

Preemption therefore needs to be explicit on every offering, not inferred from a name like `gpu-preempt`.

## Proposed minimal schema

An offering is roughly:

```json
{
  "offering_id": "uva-rivanna-gpu-preempt",
  "description": "Rivanna GPU partition, preemptible QOS",
  "unit": "gpu-hour",
  "price": 0.40,
  "currency": "USD",
  "pricing_model": "preemptible",
  "allow_preemption": true,
  "tier": "scavenger",
  "hardware": {
    "cpu_model": "AMD EPYC 7763",
    "memory_gb": 256,
    "gpu": "NVIDIA A100 40GB"
  },
  "region": "us-east",
  "effective_date": "2026-04-01"
}
```

Allowed values for `pricing_model`: `on_demand`, `spot`, `preemptible`, `allocation` (for credit-based academic systems). `unit` follows the FOCUS/OpenCost convention (`cpu-hour`, `gpu-hour`, `gb-month`, `gb` for transfer). A full rate card is `{ site_id, offerings: [...] }`, plus a version and an issued-at timestamp.

Field names are chosen to match FOCUS (FinOps Open Cost and Usage Spec) wherever overlap exists, so that cost data flowing out of TES can be consumed by existing FinOps tooling without a translation layer.

## Relationship to existing standards

- **FOCUS (FinOps)** — adopt its vocabulary for billing period, unit, currency, service category.
- **AWS Price List API** — prior art for a queryable per-offering price feed; too vendor-specific to adopt wholesale but informs the query shape.
- **OpenCost** — aligns with its per-resource unit costs (CPU-hour, GB-month); a TES rate card should be trivially convertible to an OpenCost-style model.
- **Slurm `TRESBillingWeights`** — the canonical "one rate per partition, weighted by resource type" model; our offering collapses to this when the backend is Slurm.
- **Kubernetes `PriorityClass` + node pools** — the container-native analog; our offering collapses to this when the backend is k8s.
- **ACCESS (NSF) credits** — introduces a credits-plus-exchange-rate layer for academic federations. Out of scope for the prototype but motivates the `allocation` pricing model and hints at future work on non-monetary units.

## Scope for this prototype

In scope for the hackathon:

- A FastAPI service that serves a rate card for a single site with multiple offerings.
- A JSON schema for offerings with the fields above.
- A reference example for a Slurm-style site and a cloud-style site.
- A simple client that WES could use to fetch and compare rate cards across sites.

Out of scope:

- Authentication and signing of rate cards.
- Actual usage metering, invoicing, chargeback.
- Multi-currency conversion and credit exchange rates.
- Dynamic/real-time pricing (spot price feeds).
- Any attempt to standardize egress pricing beyond a flat per-GB offering.

## Open questions

- **Currency vs credits.** How do we represent academic allocations where the "price" is in SUs, node-hours, or project credits rather than USD? A `currency` field plus an `allocation` pricing model is the current sketch; it is not sufficient for ACCESS-style exchange rates.
- **Authentication.** Are rate cards public, or do they require the same authn as the TES endpoint? Public-by-default is simpler; some hospital sites will not accept that.
- **Trust and signing.** If a WES aggregates rate cards from multiple TES backends to produce a cost estimate for a user, how does the user trust those numbers? Signed rate cards (JWS) are an obvious direction.
- **Discovery.** How does a WES find the rate card for a given TES? A `service-info` extension with a `rateCardUrl` pointer is the lightest-weight option and reuses an existing GA4GH pattern.
- **Versioning.** Prices change. Does a rate card carry a version and effective date range per offering, or is the whole card versioned as a unit? The prototype uses per-offering `effective_date`; a retired-date is likely also needed.
- **Relationship to the unit cost profile.** The sibling `unit-cost-profile/` effort describes per-node cost. The rate card is the site-level, multi-offering view; the unit cost profile may end up being a derived per-node slice of it, or a separate resolution altogether. That boundary needs to be drawn.
