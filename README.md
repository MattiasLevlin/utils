# code-comments-remove

## Description

* This repository contains a script that removes comments from a codebase
* Currently, it supports comment removal in HTML, CSS, JS

## Why

* Increasingly, LLM interaction is becoming prevalent in programming
* Several LLMs have a tendency to liberally comment the code
* Upon further iterations with the LLM, any LLM-added comments will consume tokens
* Thus, the primary uses of this repository is to:
    * Reduce amount of LLM tokens in any conversation/call to an LLM
    * Direct the LLM to focus on the code, not comments
    * Reduce noise in the LLM interaction

## Who

This script IS recommended for:

* Hobbyist projects
* "Vibe coding"
* Codebases that contain non-critical functionality
* Codebases that are heavily integrated into LLM workflows

This script is NOT recommended for:

* Enterprise projects
* Traditional coding
* Codebases that contain any kind of critical functionality 
* Codebases that are 100% under human supervision

```bash
# python
curl -sSL https://raw.githubusercontent.com/MattiasLevlin/utils/master/run.py | python

# python3
curl -sSL https://raw.githubusercontent.com/MattiasLevlin/utils/master/run.py | python3
```

## Other recommended (local) commands

```bash
npx prettier --write .
npx standard --fix
```