# Curriculum Knowledge Graph

Turns a university program's course-sequence flowchart (a PDF) into a **Neo4j knowledge graph** of courses, categories, specializations and prerequisite chains, using an LLM for the extraction step.

Course flowcharts are drawn for people: boxes, arrows and footnotes rather than tables. Rule-based OCR struggled to recover which arrow points to which course, so the extraction step sends the PDF to Claude with a strict JSON schema, then cleans and validates the result in Python before loading it into the graph.

Built as Project 1 for CSC 3331 (Spring 2026), using a real BSc Computer Science catalog (2023–2025) as the input.

## Pipeline

```text
Course-sequence PDF
      │
      ▼  extract.py: Claude reads the PDF and returns JSON in a fixed schema
      │             (code, title, credits, prerequisites, category)
      ▼  extract.py: clean and validate (normalize codes, numeric credits,
      │             "NONE" for missing values, fixes for known misreads)
      ▼
11 Excel sheets: Mathematics, ComputerScience, ScienceEngineering, GenEd,
      │          Elective, Minor + one per specialization (AI, ACS, BDA, CSys, SE)
      ▼  part2_test/import_test.py
Neo4j graph
```

## Graph model

```text
(:Program {name:'BSCS'})
   └─[:HAS_CATEGORY]→ GenEd · ComputerScience · Mathematics · ScienceEngineering · Electives · Minor
ComputerScience ─[:HAS_GROUP]→ (:CSGroup) Required · Specializations · ComputingElective
Specializations ─[:HAS_SPECIALIZATION]→ (:Specialization) AI · ACS · BDA · CSys · SE
   └─[:HAS_GROUP]→ (:SpecGroup) Required · Optional ─[:HAS_COURSE]→ (:Course)
GenEd ─[:HAS_GROUP]→ (:GenEdGroup) Arabic · French · Humanities · Art · ...
Minor ─[:HAS_MINOR_TYPE]→ (:MinorType)

(:Course {code, title, credits, category})-[:REQUIRES]->(:Course)
```

Prerequisite edges are built by parsing course codes out of each course's prerequisite text, so `"CSC3308 or CSC3309"` produces two `REQUIRES` edges.

## Example queries

Every course you must complete before a given course (the full chain, not just direct prerequisites):

```cypher
MATCH path = (c:Course {code:'CSC4352'})-[:REQUIRES*]->(pre:Course)
RETURN DISTINCT pre.code, pre.title, length(path) AS depth
ORDER BY depth;
```

Required courses of a specialization and their direct prerequisites:

```cypher
MATCH (:Specialization {name:'AI'})-[:HAS_GROUP]->(:SpecGroup {name:'Required'})-[:HAS_COURSE]->(c:Course)
OPTIONAL MATCH (c)-[:REQUIRES]->(p:Course)
RETURN c.code, c.title, collect(p.code) AS prerequisites;
```

Courses with no prerequisites (good first-semester options):

```cypher
MATCH (c:Course) WHERE NOT EXISTS { (c)-[:REQUIRES]->() }
RETURN c.code, c.title ORDER BY c.code;
```

The courses that unlock the most others (bottlenecks in the curriculum):

```cypher
MATCH (c:Course)<-[:REQUIRES]-(next:Course)
RETURN c.code, c.title, count(next) AS unlocks
ORDER BY unlocks DESC LIMIT 10;
```

## Running it

Requires Python 3.10+, an Anthropic API key, and a running Neo4j instance (Neo4j Desktop or AuraDB Free).

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys
```

```bash
python extract.py                     # PDF → Excel sheets in ../output/
cd part2_test
python import_test.py                 # Excel sheets → Neo4j (clears the graph first)
```

`import_test.py` reads the sheets from `DATA_DIR` (default: the current folder, which holds the checked-in sample sheets).

## Project structure

```text
├── extract.py                         # LLM extraction + cleaning → Excel
├── BSCSC_Course-Sequence_Catalog ...  # input PDF
├── part2_test/
│   ├── *_test.xlsx                    # extracted sheets used for the import
│   ├── import_test.py                 # full graph import with prerequisite edges
│   └── import_part2.py                # earlier version of the import
├── requirements.txt
└── .env.example
```

## Limitations

- The extraction prompt is written for this catalog's layout and categories. Using another program's flowchart means editing the prompt and the sheet list in `extract.py`.
- A few prerequisites the model consistently misread are corrected by hand (`HARDCODED_PREREQ_FIXES` in `extract.py`).
- The minor courses are placeholders (`COURSE1`–`COURSE5`), as the assignment specified.

## Team

- **Jihane Erraji**: PDF extraction pipeline (OCR first, then the LLM-based version) and data cleaning
- **Doha**: Neo4j import scripts (`part2_test/`)
