# Concepts

## Benchmark

Your entire personal collection of tasks. 
Running the benchmark executes every task against a model and produces a scored result set.

## Task

One specific, bounded piece of work given to a model. 
A task carries the instructions, any input material the model needs, and its evaluations. 
See [Task Format](03-task-format.md).

## Evaluation

A measure attached to a task that scores a model's output for that task. 
A task has zero or more evaluations; one with none is run and viewed, never scored.

## Model

The model is what MyBench measures, whilst everything else is kept as a fixed variable.
The harness is currently fixed to be OpenCode with a fixed version.
