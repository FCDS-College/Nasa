# Flame in Freefall — Day 1 P0 Data Candidates

**Date of verification:** 2026-10-03

## Day-1 decision

The MVP source backbone should be **NASA Physical Sciences Informatics (PSI)**. NASA states that PSI publishes physical-science experiment data from reduced-gravity environments and related ground studies, and its current public AWS registry exposes the `nasa-psi` S3 bucket without requiring an AWS account. The PSI system provides raw/processed data and supporting resources such as models, images, documentation, and publications. citeturn620724search11turn595254search1

For the first vertical slice, ingest the following four **verified P0 datasets**:

1. **BASS-II (PSI-25)** — solid-fuel flame growth, spread, and extinction. NASA PSI reports CC0 licensing, ISS flight data, Version 4, and 694 files added; the landing page exposes raw MP4 examples and supporting engineering/science files. citeturn311459search1
2. **FLEX (PSI-69)** — liquid-droplet burning, flammability limits, extinction, and gaseous suppressants. NASA PSI reports CC0 licensing and a persistent DOI; the experiment varies pressure, oxygen, droplet size, fuel and suppressant conditions. citeturn311459search0
3. **SAFFIRE-I (PSI-98)** — large-scale spacecraft-fire behavior with flame imaging plus temperature, radiation, pressure, CO2/O2 and airflow measurements. NASA PSI reports CC0 licensing and 74 files added in Version 4. citeturn373787search0
4. **SPICE (PSI-107)** — microgravity co-flow flame/smoke-point behavior, with a public CC0 PSI dataset reported at 6.47 GB. citeturn373787search1

Two additional candidates remain **P0 scope candidates but not ingestion-unblocked** until their canonical PSI dataset identifiers/file manifests are verified:

- **ACME CLD Flame** — NASA describes quantitative measurements of flame size, structure, temperature, soot and stability in gaseous methane/ethylene co-flow flames, including near-extinction and highly sooting regimes. citeturn888466search0
- **FLEX-2** — NASA GRC describes droplet combustion under controlled environments, including sub-buoyant convective flow, droplet arrays, and practical/surrogate fuels. citeturn888466search10turn458684search43

## Bucket check (2026-10-03)

A full recursive listing of the public `s3://nasa-psi/` bucket (388,602 objects, ~30 TB) contains **only three investigations: `DSI/` (directional solidification), `OASIS/` (smectic liquid crystals) and `pk4/` (complex plasma)**. None of the P0 combustion investigations above (BASS-II, FLEX, SAFFIRE-I, SPICE, ACME/CLD, FLEX-2) are in the bucket; their files must be obtained through the PSI web portal instead. Keyword hits for "droplet" (OASIS liquid-crystal droplets) and "burning" (PK-4 plasma logs) are not combustion data.

`FF-PSI-DSI` has been added to the registry as a P2, non-combustion reference source; its docs and one sample run (`Data/S1 activity 4.zip`) are mirrored under `data/raw/nasa_psi/DSI/`.

## Why these sources belong in P0

They span the core fire-safety dimensions needed by the MVP: **solid-material flammability, liquid-droplet combustion, large-scale spacecraft fire behavior, and soot/smoke behavior**. NASA's own combustion-program inventory identifies BASS-II, FLEX, SPICE, SAFFIRE-I/II/III, ACME experiments, CFI, and related investigations as complete/publicly catalogued combustion investigations. citeturn697647search0

This does **not** mean the four P0 datasets are the only important NASA sources. They are the smallest source set that can demonstrate a useful cross-experiment evidence flow without requiring the team to ingest the full combustion archive on Day 1.

## First ingestion unit

Use a two-level model:

```text
Source Registry
  └── Investigation Source
       ├── File Manifest
       │    ├── raw video/image
       │    ├── tabular / experimental table
       │    ├── metadata package
       │    └── supporting document
       └── Evidence Records
            ├── measurement/event
            ├── condition
            ├── derived metric
            └── provenance pointer
```

The first runnable vertical slice should be **BASS-II + FLEX**, because these two sources expose complementary solid-vs-liquid combustion behavior and contain directly useful measurable outcomes. SAFFIRE-I and SPICE should enter the same schema immediately after the common ingestion contract is proven.

## Important boundary

Do not fabricate a universal “risk score” during ingestion. Store the measured facts and experimental conditions first: fuel/material, oxygen, pressure, flow, geometry, time, gravity regime, flame state, spread/extinction outcome, and source provenance. Derived fire-safety recommendations belong to a later evidence/analysis layer.
