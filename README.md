# MyBench

MyBench is a [Smart Tool](https://github.com/microsoft/amplifier-smart-tools) aimed at creating a personal benchmark for yourself so you know how well a model will work for you. 
A *benchmark* consists of *tasks* which have *evaluations* that measure a model's capability.
The goal is to benchmark the capability at the *model* level as much as possible (irrespective of harness). 
So the harness is always fixed, and usually this means tasks that are not necessarily long-running agents, but specific tasks or analysis.
It currently uses OpenCode as the common harness due to its support for many providers and relative simplicity in how it operates out of the box.

## Installation

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv tool install git+https://github.com/DavidKoleczek/mybench-smart-tool
```

To upgrade to the latest:

```bash
uv tool upgrade mybench
```

To run it once without installing:

```bash
uvx --from git+https://github.com/DavidKoleczek/mybench-smart-tool mybench --help
```

## Interface

```bash
# Proposes ideas for tasks
mybench inspire-me --guidance "guidance"

# Create a new task in your benchmark. You can provide an idea, context, or both
mybench create --idea "<pick one>" --context "<pick one"

# Runs your benchmark
mybench run --model

# Opens a UX where you can see historical benchmark results
mybench dashboard
```

## Configuration

TBD

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up your development environment.

