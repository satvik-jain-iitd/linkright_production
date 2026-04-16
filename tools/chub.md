# chub (Context Hub)
> github.com/andrewyng/context-hub

Fetches curated, versioned API docs for any library. Prevents coding from stale training data.

## When to use
- Before writing any code that calls an external library → `chub get <library>`
- When an API call fails unexpectedly → `chub get <library>` before debugging
- When unsure what a library supports → `chub search <keyword>`
- Never write API call code from training data alone

## Commands
```
chub get <id>                   # get full docs for a library
chub get <id> --lang py|js      # language-specific variant
chub get <id> --full            # include all reference files
chub search <query>             # discover available docs
chub annotate <id> "note"       # save local note to docs
chub annotate --list            # view saved annotations
chub feedback <id> up|down      # rate doc quality
```

## Input/Output
- Input: library name or keyword
- Output: markdown docs with usage examples, method signatures, current API shape

## Install
```
npm install -g @aisuite/chub
```
