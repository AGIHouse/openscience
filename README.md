## Open Science Mission
Create an open-source datastore of research data built to back research powered Generative AI applications. Our first datasource will be Arxiv / Bioarxiv. We will power clean research datastore creation and access, AI augmented research processes and fully autonomous generative research.

## Tiers:
1. Cleaned Dataset (dataset; ETL tool) with papers standardized in JSON.
LLM Training.
2. Research exploration & retrieval (tool)
Search for relevant research.
3. AI Augmented Research Process (product)
Research Paper Writing (http://arxivgen.com)
From prompt.
From data.
Automated research reviews & criticism
Paper Reviews.
Proposal Reviews.
Automating the evaluation of ‘new’ knowledge.
Experiment writeups.
Evaluation of scientific claims.
Research creativity.
Generating novel methods.
Generating novel hypotheses.
Generating novel explanations for results.
Generating novel evaluation methodology.
4. Generative Research (product)
Knowledge generating agents & algorithms.

## Deliverables (Output):
1. Open Source Github Repo with tools to scrape/parse sources of scientific data.
2. Repositories (S3?) of data which are legally easy to host.
3. It should allow contributing developers to easily add research functionality, especially ETL functionality.
We’ll enable researchers to upload embeddings and search methods for new sources of data.

## Unified JSON Schema & API
We will publish a new, code friendly JSON representation of all papers in OpenScience. This will make it simple to access all paper text and metadata through an easy-to-use API, and will ensure that all data formats are standardized.

### Data to collect & harmonize:
- The full text of all arxiv papers.
- Passage embeddings for the full text of all arxiv papers.
- Paper author metadata.
- Paper title data.
- Paper citation data.
- Publication date.

## Modular Open Source Toolkit
While pursuing a unified JSON representation, we will make a modular, reusable toolkit which we will open source for broader use.

### Toolkit Components:
1. Scraping scripts
This pulls raw data into a mount or folder.
2. Parsing scripts
Likely dataset conditional parsers that turn raw data into passages and additional metadata.
Missing metadata will be handled in the database.
Varying segmentation strategies / rules are allowed.
Ex., token count with overlap, sentence by sentence with overlap, passage by passage.
Latex -> json.gz
Write a schema with important paper metadata in the json files.
3. Database: Space for similar metadata across data sources.
Full Text
Passages
Typed based on their segmentation strategy.
Authors
Title
Citations (Of other papers)
Human readable
Unique ID within this database
Citation String
Passage Embeddings (Including various types: all-mpnet-base, ada-002, MiniLM)
Paper Tags (ex., Arxiv categories like Information Retrieval or Biomolecules)
Source
4. Database API
Retrieval functions for paper data
5. Embedding Service
Likely Fargate / Lambda auto-scaling service.
6. Retrieval Service
Approximate Nearest Neighbors Index w/ API
## Data Sources

### First Stage Data Sources
We will collect:
Arxiv
Bioarxiv

### Second Stage Data Sources
In our second stage, we would like to collect:
chemarxiv
Pubmed
JStor
Nature
Science
Springer
ScienceDirect
Academic Torrents
Other datasets

## Existing Relevant Tools and Companies
Semantic Scholar
Elicit
OpenSyllabus
sCite
Kaggle
Galactica
Metaphor
Alexandria Embeddings
Connected Papers
### Examples of knowledge generation:
Deep Learning Guided Discovery of an antibiotic targeting Acinetobacter baumannii
Discovering New Interpretable Conservation Laws as Sparse Invariants

### Resources:
Alexandria Embeddings (https://huggingface.co/datasets/macrocosm/arxiv_abstracts)
Arxiv sanity lite (https://arxiv-sanity-lite.com/)
ArxivGen (http://arxivgen.com/)
TXYZ (https://txyz.ai/)

## Legal Disclaimers

On Research Data IP:
We do not store the exact text of research data. We store code that allows users to download and transform data in to a useful format. We store only embeddings of research data, and processes for using those embeddings for search.
