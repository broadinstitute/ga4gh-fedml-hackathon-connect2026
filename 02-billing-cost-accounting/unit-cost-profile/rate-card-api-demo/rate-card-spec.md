# Rate Card Specification

Version 0.1.0 (hackathon draft).

## TL;DR

- A rate card is a JSON-LD document published by one TES endpoint, describing the compute offerings available at that endpoint and the unit price of each.
- **Scaffolding is load-bearing**: JSON-LD `@context`, `x_ga4gh:` extension prefix, string-typed prices, schema.org `Offer` / `UnitPriceSpecification` nesting, split `specVersion` / `rateCardVersion`, and open-typed `priceCurrency` (so ACCESS-style credits can attach later). Removing any of these after v0 is a breaking change.
- **Payload is minimal**: one `offers[]` array, each offer carrying hardware, a boolean preemption flag, limits, and a `priceSpecification[]` of per-unit prices. No Modal multipliers, no `preemptMode` enum, no `unit_dictionary`, no `pricingModel` enum, no tiered pricing. Each of those can be added in v0.2 without breaking v0 consumers.
- **Access layer is first-class**: site-level fields for allocation, payer model, data governance, support contact, and authentication hints. These are deal-breakers for academic and hospital sites and are the fields most likely to block federation participation if absent.

## Background concepts

Most of the terminology below is borrowed from external vocabularies. Full write-ups live in `../unit-cost-profile/rate-card-landscape-analysis/`.

- **JSON-LD `@context` and the `x_ga4gh:` prefix.** JSON-LD lets a JSON document declare which vocabulary each key comes from. Our `@context` imports `https://schema.org` so keys like `@type`, `name`, `provider`, `priceCurrency`, and `priceSpecification` carry schema.org semantics. We also declare a GA4GH-specific namespace at `https://ga4gh.org/fedml/rate-card/v0#` aliased as `x_ga4gh`. Any key prefixed `x_ga4gh:` is a field we invent because no existing vocabulary covers it. This prefix matches FOCUS's own vendor-extension convention (`x_*`) and lets generic JSON-LD tooling ingest the card without choking on unknown keys.

- **schema.org `Service`, `Offer`, `UnitPriceSpecification`.** schema.org's pricing vocabulary is the closest formal model to a compute rate card. A `Service` has one or more `Offer`s; each `Offer` may carry one or more `UnitPriceSpecification`s expressing "this many currency units per this unit of consumption."

- **FOCUS (FinOps Open Cost and Usage Specification).** Industry-standard column names for cloud billing exports; AWS, Azure, GCP, and OCI export it. We borrow field *names* (e.g. `SkuId`, `BillingCurrency`, `EffectiveDate`) so downstream FinOps pipelines ingest without adapters.

- **ACCESS credits.** NSF ACCESS (the post-XSEDE national academic compute allocation system) uses an abstract currency: researchers redeem ACCESS Credits at a published exchange rate against any participating Resource Provider. Credits let a federation price compute in a stable common unit. We reserve `priceCurrency: "CREDITS"` (or equivalent opaque pool identifier) for this pattern; sites pricing in dollars ignore it.

- **TES and WES.** GA4GH Task Execution Service sits in front of actual compute (Slurm, k8s, cloud VMs) and runs a single task. Each TES endpoint knows its own hardware and prices, so **it publishes the rate card** — one per TES endpoint. GA4GH Workflow Execution Service orchestrates workflows across TES backends; when planning, it **reads** each backend's rate card and **aggregates** per-task cost estimates. WES never authors a rate card.

## Schema

A rate card is a schema.org `Service` with `x_ga4gh` extensions. All fields not prefixed `x_ga4gh:` are schema.org or JSON-LD keywords.

### Envelope (required)

| Field | Type | Notes |
|---|---|---|
| `@context` | array | `["https://schema.org", {"x_ga4gh": "https://ga4gh.org/fedml/rate-card/v0#"}]` |
| `@type` | string | `"Service"` |
| `@id` | URI | Stable identifier for this rate card |
| `identifier` | string | Site-local id (e.g. `"uva-rivanna"`) |
| `name` | string | Human-readable site name |
| `provider` | Organization | `{"@type": "Organization", "name": "..."}` |
| `x_ga4gh:specVersion` | string | Spec semver; `"0.1.0"` for this revision |
| `x_ga4gh:rateCardVersion` | string | The *site's* versioning of its prices |
| `validFrom` | ISO 8601 | Card-level start of validity |
| `validThrough` | ISO 8601 | Card-level end of validity (may be null) |
| `x_ga4gh:billingCurrency` | string | ISO 4217 code (`"USD"`) or opaque pool id for credits (see Background) |

### Site-level access layer (optional but recommended)

These capture who can actually use the site, and under what governance. Absence means "unspecified" rather than "no restrictions."

| Field | Type | Notes |
|---|---|---|
| `x_ga4gh:requiresAllocation` | bool | Must a user have an account/allocation before jobs run? |
| `x_ga4gh:allocationContact` | string | URL or email to obtain access |
| `x_ga4gh:payerModel` | string | `"user"` \| `"grant"` \| `"institution_subsidized"` \| `"free_at_point_of_use"` |
| `x_ga4gh:dataGovernance` | object | `{"phiAllowed": bool, "exportControlled": bool, "irbGated": bool}` |
| `x_ga4gh:supportContact` | string | URL or email |
| `x_ga4gh:authentication` | string | Free-form hint (e.g. `"CILogon"`, `"InCommon"`, `"OIDC"`) |

### Offerings (required; at least one)

`offers` is a schema.org `Offer` array. One offer per Slurm partition, k8s node pool, cloud instance type, or lab workstation. A single-offering card is degenerate but valid.

| Field | Type | Notes |
|---|---|---|
| `@type` | string | `"Offer"` |
| `identifier` | string | Offer-local id |
| `name` | string | Human-readable |
| `x_ga4gh:skuId` | string | FOCUS `SkuId`; stable across versions |
| `x_ga4gh:allowPreemption` | bool | Whether jobs on this offer can be preempted |
| `x_ga4gh:hardware` | object | `{cpuModel, arch, memoryGiB, gpuModel?, interconnect?}` |
| `x_ga4gh:limits` | object | `{maxWallHours?, maxCpusPerJob?, maxMemoryGiB?}` |
| `priceSpecification` | array | One `UnitPriceSpecification` per priced unit |

### UnitPriceSpecification

Each entry in `priceSpecification[]`:

| Field | Type | Notes |
|---|---|---|
| `@type` | string | `"UnitPriceSpecification"` |
| `price` | **string** | Decimal string to avoid float drift (e.g. `"2.50"`, `"0.0000131"`) |
| `priceCurrency` | string | Matches envelope `x_ga4gh:billingCurrency` unless per-offer override |
| `unitCode` | string | UN/CEFACT Rec 20 code (`"HUR"` hour, `"GB"` gigabyte, `"MIN"` minute, `"C62"` unit) — advisory for generic tooling |
| `unitText` | string | Authoritative key into a future unit dictionary; drives invoice math. Canonical values: `"cpu_hour"`, `"gib_hour"`, `"gpu_hour"`, `"gib_month"`, `"gib_egress"` |
| `validFrom` | ISO 8601 | Optional per-price override of the card-level window |

**On precedence**: when `unitCode` and `unitText` disagree, `unitText` is authoritative for invoice computation. `unitCode` exists so RDF crawlers see something standard.

## Example

See `../unit-cost-profile/node-rate-card-example02.json` for a concrete two-offering Slurm-HPC card following this schema.

## Deferred to v0.2 or later

Each of these can be added as an optional field without breaking v0 consumers, because JSON-LD treats unknown keys as simply unused. They are deferred because no hackathon demo scenario requires them.

- `unit_dictionary` — full mapping of `unitText` tokens to OGF Usage Record fields + metrics. v0 fixes the canonical token set in prose; v0.2 makes it machine-enforced.
- `x_ga4gh:preemptMode` — Slurm enum (`CANCEL` / `REQUEUE` / `SUSPEND` / `GANG` / `OFF`). v0 uses the boolean `allowPreemption`.
- `x_ga4gh:selector` — scheduler dispatch hints (partition, qos, node label). A separate `selectors` companion document is the likely path; the rate card stays pricing-only.
- `x_ga4gh:minBillableSeconds`, `x_ga4gh:nonPreemptibleMultiplier`, `x_ga4gh:idleRateMultiplier`, `x_ga4gh:regionMultiplier` — Modal-style compressions. Add when a site actually needs them.
- Tiered pricing inside `UnitPriceSpecification` — egress or volume tiers (`[{upTo, rate}, ...]`). v0 ships one flat rate per unit.
- Flat / access fees at the site level — monthly federation fees for `api_access`, `model_evaluation`, etc.
- Signed rate cards — JWS over the JSON-LD document. The schema is signing-ready because it is JSON-LD.

## Rejected alternatives

- **Pure OpenCost flat rates** (one `{CPU, RAM, GPU}` vector per site) — loses partition/node-pool/SKU heterogeneity, which is the whole point.
- **Parallel spot-SKU encoding** (OpenCost `CPU`/`spotCPU`) — lets prices drift independently and doubles the schema surface. One offer per price model is cleaner.
- **Numeric `price`** — OpenCost, Stripe, and FOCUS all independently converged on string-typed prices after hitting float-precision bugs on fractional cents. We adopt the convergent answer from day one.
- **Bare `priceCurrency: "CREDITS"`** — two sites using the same literal for different credit pools silently collide. When credits are used, the currency must be an opaque pool id.
- **ODRL** — a W3C rights-policy language, not a pricing language.
- **ISO 19086** — SLOs, not pricing.
- **Full TM Forum SID / TMF620** — most complete formal rate-card model in existence but telco-biased and compute-blind. We keep the three-entity split (Offering / Price / Usage) as a concept; we reject the payload.

## Open questions

- **Trust and signing.** If WES aggregates rate cards from multiple sites to quote a user, how does the user trust those numbers? JWS over JSON-LD is the obvious path; unsolved for v0.
- **Discovery via `service-info`.** Likely: add `rateCardUrl` to the GA4GH `service-info` response. Not yet taken to the TES/WES working group.
- **Credit pool namespace.** When `priceCurrency` is non-ISO, what registry governs the allowed values? Ad-hoc for now; may need a small GA4GH-maintained list.
- **WES aggregation semantics.** Does WES sum list prices, best-case preemptible prices, or expected-value prices weighted by preemption probability? The schema supports all three; the planning policy is out of scope.
- **Per-offering vs per-card validity.** The schema allows both `validFrom`/`validThrough` on the card and per-price overrides. Handover windows (e.g. FY26 → FY27) may need two overlapping cards; semantics are undecided.
- **Storage tier granularity.** A single `gib_month` conflates scratch, project, and archive storage. Deferred to a tier block in v0.2.
