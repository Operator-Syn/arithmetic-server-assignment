# Arithmetic Server Report Template

Replace every `TODO` with observations and numbers from your own run on hpc1.
Do not submit this Markdown file as-is; convert your completed report to
`report.pdf`.

## Part 3 - Empirical Measurement

### M1. Round-trip time

Command used:

```sh
python3 run_measurements.py --port TODO_PORT
```

| Run | Mean RTT (ms) | Median RTT (ms) |
| --- | ---: | ---: |
| 1 | TODO | TODO |
| 2 | TODO | TODO |
| 3 | TODO | TODO |

Variation comment:

TODO: Compare the three runs and explain whether the spread is small or large.

### M2. Pipelined throughput

| Run | Elapsed seconds | Operations per second |
| --- | ---: | ---: |
| 1 | TODO | TODO |
| 2 | TODO | TODO |
| 3 | TODO | TODO |

Comparison with M1:

TODO: Explain why pipelining was faster or, if it was not faster, what you
investigated.

### M3. Concurrent clients

| Concurrent clients | Mean RTT (ms) | Median RTT (ms) | Notes |
| ---: | ---: | ---: | --- |
| 5 | TODO | TODO | TODO |
| 10 | TODO | TODO | TODO |
| 20 | TODO | TODO | TODO |

Scaling comment:

TODO: Say whether it scales linearly, sub-linearly, or worse. Refer to the
server's thread-per-client design.

## Part 4 - TCP Byte-stream Analysis

### L1. Telnet

Relevant log excerpt:

```text
TODO: paste the L1 recv log excerpt here
```

Observation:

TODO: Count the recv() calls for one `ADD 1 2` command and explain whether
your telnet looked like line mode or character mode.

### L2. Pipelined benchmark client

Relevant log excerpt:

```text
TODO: paste an L2 recv log line that contains multiple ADD commands
```

Maximum complete commands in one recv():

TODO

What this shows:

TODO: Explain the relationship between application messages and TCP reads.

### L3. Drip client

Relevant log excerpt:

```text
TODO: paste the byte-at-a-time recv log excerpt here
```

Code references:

TODO: Cite the line numbers in `arithmetic_server.py` around the per-client
buffer, `buffer.extend(...)`, and `extract_raw_lines(...)`.

Explanation:

TODO: Explain how the receive buffer accumulates bytes until a newline arrives.

## Part 5 - Original Extension

Command name:

TODO: `MOD`

Syntax and semantics:

TODO: Explain `MOD <N1> <N2>`.

Successful interaction:

```text
TODO
```

Error case:

```text
TODO
```

Justification:

TODO: Explain why this is a reasonable addition and which design principle it
respects or violates.

## Part 6 - Design Document

### 1. Command framing and partial buffers

TODO: Walk through `ADD 1`, a 10-second pause, and then ` 2\n`. Cite the
function and line numbers that hold and parse the partial buffer.

### 2. Concurrency model

TODO: State that the server accepts connections with `selectors` and handles
each client in a thread, then explain why and where it scales poorly.

### 3. Slow malicious client

TODO: Explain current behavior for a client that sends one byte every 30
seconds forever. Describe a timeout-based defense.

### 4. Newline ASCII vs length-prefixed binary

TODO: Give one advantage and one disadvantage.

### 5. L3 byte-at-a-time handling

TODO: Refer to the L3 log and exact code lines that made the command succeed.
