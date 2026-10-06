# Assumptions and Boundaries

## 1. Current Data Availability

The actual NASA competition dataset is not available during the current development stage.

The data will be provided or made available during the competition.

Therefore, the current RAG design must not depend on a specific NASA dataset structure.

---

## 2. Schema Assumptions

No specific NASA columns or metadata fields are assumed at this stage.

Fields such as:

* fuel
* oxidizer
* gravity condition
* mission
* experiment

must not be treated as confirmed dataset fields unless they are actually present in the provided data.

---

## 3. Architecture Assumptions

The RAG system is designed to support scientific documents and/or structured scientific data that can be represented as retrievable evidence.

The actual ingestion and mapping process will depend on the format supplied during the competition.

---

## 4. Retrieval Assumptions

The architecture supports:

* semantic retrieval
* keyword retrieval
* metadata filtering
* hybrid retrieval
* reranking

The final retrieval strategy and ranking weights will be determined after inspecting the actual corpus.

---

## 5. Evaluation Assumptions

Retrieval evaluation requires a representative evaluation corpus.

Because the real NASA corpus is not currently available, final retrieval metrics cannot be meaningfully established before the competition data is received.

---

## 6. Mock/Test Data

If testing is required before the competition, synthetic or public test documents may be used only to verify pipeline functionality.

Such data must be clearly labeled as test data.

Test data must not be presented as NASA competition data.

---

## 7. Scientific Grounding Boundary

The system must distinguish between:

* authoritative retrieved evidence
* memory
* cached results
* model pretrained knowledge

Only appropriate authoritative source evidence should be used as the basis for project-specific scientific claims.

---

## 8. Future Adaptation

When the competition data becomes available, the following steps will be performed:

1. inspect the data format
2. identify documents/records
3. identify available metadata
4. map the data to the document/chunk schema
5. define chunking strategy
6. generate embeddings
7. configure retrieval
8. configure reranking
9. build evaluation queries
10. evaluate retrieval quality
11. revise the schema or retrieval configuration if necessary

---

## 9. Out of Scope for This Day

The following are not assumed to be part of the current Day 1 implementation:

* final NASA data preprocessing
* final NASA dataset analysis
* production dashboard implementation
* final model selection
* final retrieval hyperparameters
* final retrieval metrics
* production deployment

These can be addressed when the relevant project components and competition data are available.
