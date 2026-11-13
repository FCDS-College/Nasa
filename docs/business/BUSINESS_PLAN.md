# Flame in Freefall: business plan (commercial space)

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas) | Draft for team review | 0.1.0 | 2026-11-13 | — | — |

**Decision recorded 2026-11-13:** the first paying customer is **commercial space**: teams designing crewed station and habitat cabins, and the suppliers who qualify materials for them. Everything below is a plan and a set of hypotheses to test. No customer has been contacted yet.

## 1. Problem

- **Cabin atmospheres are being designed now, for conditions nobody has flown much.**
  - Commercial LEO stations, lunar landers and surface habitats are choosing them today.
  - NASA's own exploration vehicles plan up to 30–34 % O₂ at reduced pressure (NASA/TM-2008-215260 p. 5), more oxygen than the ISS.
  - Materials burn more readily there.
- **The flight evidence is public but scattered.** It sits across four NASA PSI investigations (840 tests) and decades of NTRS reports, in tables with different variables, units and gaps.
- **Finding which tests speak to a given atmosphere takes an expert days.** Seeing where *no* test exists is harder still, and that is where risk hides.
- **The cost of guessing is known.** Apollo 1 (1967) put flight materials in a 100 % O₂ atmosphere in which they had never been tested (FF-NTRS-20070021223 p. 2).

## 2. Product

An **evidence workspace for spacecraft fire safety.** You enter a cabin atmosphere (O₂, pressure, gravity) and it shows:

1. **The coverage verdict:** covered, partial or none, with the nearest real flight test and the size of the gap;
2. **NASA investigations ranked** by how directly their data speaks to that atmosphere;
3. **Cited findings**, every number linked to its NASA table cell or report page;
4. **A validated outcome estimate** (FLEX droplets) that **refuses** outside its flight envelope;
5. **A cited history:** incidents and design changes that bear on the atmosphere;
6. **A grounded Q&A** over the corpus, which answers only from cited passages.

**The differentiator is not prediction, it is calibrated refusal plus traceability.** For a safety-critical buyer, "we will not estimate this, and here is the nearest data" is the feature.

## 3. Customers (target segments, in order)

| Segment | Who | Job to be done | Why now |
|---|---|---|---|
| 1. Commercial station and habitat developers | Cabin, ECLSS and safety engineers at commercial LEO-station and lunar-habitat programmes | Choose and justify a cabin atmosphere; find the flight evidence and its gaps; prepare safety reviews | Station and habitat design reviews are happening in this decade |
| 2. Materials and component suppliers | Teams qualifying textiles, foams, polymers and avionics enclosures for crewed vehicles | Show which flight and test data covers their material's environment; plan tests at worst-case conditions | Flammability testing at worst-case conditions has been the rule since Apollo 1 (FF-NTRS-20070021223 p. 2) |
| 3. Agencies and research labs | Microgravity combustion groups; safety offices | One cited view of PSI results; coverage gaps that argue for the next flight experiment | Reuses NASA's open data; supports proposals |

## 4. Business model (hypotheses to test)

| Offer | What | Price hypothesis |
|---|---|---|
| Team workspace (SaaS) | Hosted dashboard, scenario library, cited exports for design reviews | per team per year; to be set after 5 design-partner interviews |
| API | The 0.7.0 contract (coverage, ranking, insights, history) for in-house tools | usage tiers |
| Evidence reports | A signed, cited coverage report for one atmosphere or material, for a review board | per report |
| Private corpus add-on | The customer's own test data, kept private, next to NASA's | annual |

**Entry route:**
- NASA SBIR/STTR and ESA Business Incubation (BIC) pilots, to fund the first design-partner deployments and validate value;
- then paid design-partner contracts;
- then self-serve SaaS.

## 5. Why us (moat)

- A curated, **checksum-verified, licence-checked corpus**:
  - 840 flight tests and 27 NTRS reports, each with provenance;
  - the gates are code (`fetch_ntrs.py`), so the corpus can be audited.
- A **refusal engine** with explicit rules:
  - the model's applicability domain;
  - the scenario coverage verdict;
  - gravity regimes;
  - all tested and documented (ADR-011, ADR-013).
- **Evidence-first answers.** Every number cites a cell or page, and CI checks that historical quotes are verbatim.

**Competitors and alternatives:** in-house literature reviews, test-lab consulting, general AI assistants. The last are the risk we position against: they answer confidently outside the data.

## 6. Go-to-market plan

| Phase | Goal | Exit criterion |
|---|---|---|
| 0. Pitch (now) | Space Apps demo; the Apollo 1 scenario shows the value | Demo journey passes end to end (`npm run smoke`) |
| 1. Discovery | 10 interviews: cabin and ECLSS engineers, materials qualifiers | 5 confirm the coverage verdict saves review time; 3 agree to a pilot |
| 2. Pilot (SBIR/BIC-funded) | Single-tenant hosted deployment for 2–3 design partners | Used in one real design review |
| 3. Product | Multi-tenant SaaS, private corpus, exports | First paid contract |

## 7. Measures of success

- Time to answer "what flight data covers atmosphere X?": days → minutes (measure in pilots).
- Share of answers with full citations: 100 %, a release gate.
- Refusal correctness on out-of-envelope questions: 100 %, a release gate (EV-10).
- Pilot retention, and the number of design reviews that cite a Flame report.

## 8. Risks

| Risk | Mitigation |
|---|---|
| The market is small and concentrated | Start with grants. Segment 2 (suppliers) broadens it. The refusal engine can carry over to other oxygen-enriched domains later, which needs their own data |
| Users read "covered" as "safe" | Wording rules in the product (ADR-013); the coverage verdict is never a risk score (ADR-011) |
| The data is thin: droplets only, no partial gravity | Say so in every result. Add SAME, ACME and FLEX-2, then partner flight data |
| Export control or third-party content | Only `PUBLIC` NTRS records with permitted copyright and no third-party material are accepted (`fetch_ntrs.py`) |
| Code licence undecided (today "proprietary, team internal") | Team decision before the first pilot: open core vs proprietary |

## 9. From the current system to production

The current release is **pitch/demo-grade** (decision 2026-11-13). These gaps are documented and must close before a paying pilot:

- **Operations:**
  - redeploy to Railway from this branch;
  - run the Compose stack end to end;
  - schedule backups;
  - deploy alerting.
- **Security:**
  - an identity provider (SSO) for real user identities;
  - remove the deprecated write token;
  - an external security review.
- **Product:**
  - multi-tenancy;
  - a private-corpus store;
  - billing.
- **Evaluation:**
  - real-LLM evaluation numbers (EV-06/EV-10);
  - a human-reviewed gold set.

Each is tracked in `FINAL_PROJECT_STATUS.md`.

## Known limitations
- No customer has been interviewed. Prices are placeholders by design.
- Segment names are categories, not named accounts. Naming target companies needs a separate, permissioned outreach plan.

## Changelog
- 0.1.0 (2026-11-13): first draft, with the customer decision (commercial space) and the production-scope decision (pitch/demo-grade).
