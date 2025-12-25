---
title: Facefusion3.1
emoji: 💻
colorFrom: green
colorTo: red
sdk: docker
app_port: 8080
pinned: false
license: mit
short_description: faceswap
startup_duration_timeout: 5m
custom_headers:
  cross-origin-embedder-policy: require-corp
  cross-origin-opener-policy: same-origin
---

FaceFusion
==========

> Industry leading face manipulation platform with dataset training capabilities.

[![Build Status](https://img.shields.io/github/actions/workflow/status/facefusion/facefusion/ci.yml.svg?branch=master)](https://github.com/facefusion/facefusion/actions?query=workflow:ci)
[![Coverage Status](https://img.shields.io/coveralls/facefusion/facefusion.svg)](https://coveralls.io/r/facefusion/facefusion)
![License](https://img.shields.io/badge/license-OpenRAIL--AS-green)

## 🚀 Development Environment (HuggingFace Spaces)

### Quick Start
1. **Launch**: HuggingFace Spaces automatically runs `bash dev_start.sh`
2. **Authenticate**: Run `claude-code auth login` in VS Code terminal
3. **Organization ID**: `7d37921e-6314-4b53-a02d-7ea9040b3afb`
4. **Access VS Code**: Available on port 8080 after startup

### Development Setup Details
- **Environment**: VS Code web server with Claude Code CLI
- **Installation**: Automatic (Node.js, code-server, Claude Code)
- **Session Tracking**: Progress saved in `.claude-session/` directory
- **Primary Documentation**: See `prd.MD` for complete development plan

## 🆕 New Features

### Dataset Training Tab
This Space now includes a dedicated **Training** tab that allows you to:
- Upload and manage training datasets
- Configure training parameters for custom face models
- Monitor training progress (when dependencies are available)
- Learn about InstantID and other advanced face training techniques

**Note**: Full training requires additional dependencies. The training tab provides comprehensive guidance for setting up training in your own environment.
Preview
-------

![Preview](https://raw.githubusercontent.com/facefusion/facefusion/master/.github/preview.png?sanitize=true)


Installation
------------

Be aware, the [installation](https://docs.facefusion.io/installation) needs technical skills and is not recommended for beginners. In case you are not comfortable using a terminal, our [Windows Installer](http://windows-installer.facefusion.io) and [macOS Installer](http://macos-installer.facefusion.io) get you started.


Usage
-----

Run the command:

```
python facefusion.py [commands] [options]

options:
  -h, --help                                      show this help message and exit
  -v, --version                                   show program's version number and exit

commands:
    run                                           run the program
    headless-run                                  run the program in headless mode
    batch-run                                     run the program in batch mode
    force-download                                force automate downloads and exit
    benchmark                                     benchmark the program
    job-list                                      list jobs by status
    job-create                                    create a drafted job
    job-submit                                    submit a drafted job to become a queued job
    job-submit-all                                submit all drafted jobs to become a queued jobs
    job-delete                                    delete a drafted, queued, failed or completed job
    job-delete-all                                delete all drafted, queued, failed and completed jobs
    job-add-step                                  add a step to a drafted job
    job-remix-step                                remix a previous step from a drafted job
    job-insert-step                               insert a step to a drafted job
    job-remove-step                               remove a step from a drafted job
    job-run                                       run a queued job
    job-run-all                                   run all queued jobs
    job-retry                                     retry a failed job
    job-retry-all                                 retry all failed jobs
```


Documentation
-------------

Read the [documentation](https://docs.facefusion.io) for a deep dive.
