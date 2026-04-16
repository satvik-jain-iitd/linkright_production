# qmd
> github.com/tobi/qmd

Local search engine for markdown files. Indexes specs/, docs/, and notes. BM25 + vector + LLM reranking — all local.

## When to use
- Before writing a new spec → check if one already exists
- Before answering "how does X work in this project?" → search local docs first
- When user references a past decision → find the spec that captured it
- Before building a feature → understand existing patterns in specs/

## Commands
```
qmd "<query>"                           # hybrid search (best quality — use this)
qmd search "<query>"                    # fast keyword search
qmd vsearch "<query>"                   # semantic similarity search
qmd get <file>                          # retrieve specific doc
qmd multi-get <pattern>                 # batch retrieve by glob
qmd status                              # index health + collections
qmd update                              # re-index all collections
qmd collection add <path>               # add directory to index
qmd context add <path> "<description>"  # add metadata to collection
qmd embed                               # generate embeddings
```

## Flags
```
-n <num>            # number of results (default 5)
--full              # include complete document
--json              # structured output for agents
--explain           # show scoring breakdown
-c <collection>     # restrict to specific collection
```

## Setup (one time)
```
qmd collection add ./specs "Feature specs, PRDs, architecture decisions"
qmd embed
```
