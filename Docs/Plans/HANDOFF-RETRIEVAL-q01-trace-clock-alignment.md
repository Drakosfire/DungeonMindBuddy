# RETRIEVAL · Align Q01 benchmark clocks

Active under the Q01 latency objective. Serial after #4254 merged at
`e3a1d3095dfcae796acbb8dd1bfb0746ca379ed7`. Own the existing Buddy trace
recorder and the ordinary Plan timing assertion.

On a detailed capture, export existing phase intervals and the first Jev
transport entry on the same process-monotonic clock as the sink and host-work
intervals. The detail output is still benchmark-local and opt-in. No model
message, route or persistence semantic changes. Verify the actual ordinary
Plan route retains authorization and dispatch intervals, the same writer
receipt, and no writer provider I/O.
