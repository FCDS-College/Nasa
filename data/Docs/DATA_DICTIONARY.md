# Flame in Freefall — Day 1 Canonical Data Dictionary

## Source-level fields

| Field | Type | Meaning | Required | Example |
|---|---|---|---|---|
| `source_id` | string | Internal immutable source identifier | yes | `FF-PSI-25` |
| `title` | string | Canonical investigation/source title | yes | `Burning and Suppression of Solids-II` |
| `provider` | string | Owning/maintaining organization | yes | `NASA Glenn Research Center` |
| `repository` | enum | Canonical repository family | yes | `NASA PSI` |
| `psi_id` | string/null | NASA PSI investigation ID | no | `PSI-25` |
| `persistent_identifier` | string/null | DOI or other durable ID | no | `doi:10.60555/4qc4-de67` |
| `source_type` | enum | Investigation, report, publication corpus, etc. | yes | `investigation_dataset` |
| `data_modalities` | array | Available machine-readable/media formats | no | `video`, `CSV`, `images` |
| `key_variables` | array | Measured/input conditions | no | `O2 concentration`, `flow velocity` |
| `key_outputs` | array | Primary observations/outcomes | no | `spread rate`, `extinction` |
| `license` | string/null | Source license | no | `CC0-1.0` |
| `access_status` | enum | Acquisition readiness | yes | `confirmed_public` |
| `access_url` | URI | Human-facing canonical page | yes | NASA PSI landing page |
| `data_access_url` | URI/null | Direct download endpoint if known | no | bucket/object URL |
| `version` | string/null | Repository release/version | no | `Version 4` |
| `last_verified_utc` | datetime | Last external verification | yes | `2026-10-03T12:00:00Z` |
| `priority` | enum | MVP delivery priority | yes | `P0` |

## File-level fields

```text
file_id
source_id
remote_object_key
original_filename
content_type
size_bytes
sha256
retrieved_at_utc
source_version
is_original
parent_file_id
```

## Experiment/test-level fields

```text
test_id
source_id
sample_id
gravity_regime
gravity_value_g
fuel_or_material
fuel_family
sample_geometry
sample_dimensions
o2_fraction
inert_gas
pressure
ambient_temperature
flow_velocity
flow_direction
droplet_diameter_initial
flame_state_start
flame_state_end
ignition_method
extinction_event
spread_rate
burning_rate
flame_length
flame_temperature
radiation
soot_indicator
co2
notes
```

### Null policy

`null` means **not present or not established**. Do not use zero to mean missing. Unknown units are represented in metadata and block numerical comparison until resolved.

### Units policy

Store SI-normalized fields alongside original units:

```text
flow_velocity_value
flow_velocity_unit_original
flow_velocity_m_per_s
```

Never overwrite an original measurement merely to normalize units.

## Evidence-level fields

```text
evidence_id
source_id
file_id
test_id
measurement_or_claim_type
value_numeric
value_text
unit
location_type
location_pointer
transformation_id
review_status
```

`review_status` should support at least: `raw`, `machine_extracted`, `human_verified`, `rejected`.
