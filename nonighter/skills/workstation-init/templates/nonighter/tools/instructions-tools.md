# instructions-tools.md

> How this instance reaches anything outside the filesystem, and the rules that govern every such call. Read on demand before batch tool work, or when deciding how to reach a connected system. What is reachable and how is in `index-tools.md`.

## 1. Execution routes

**One item, or a handful: call the tool.** More than about five similar operations: write a script, run it once, and print what it did. A loop of tool calls over fifty items costs fifty round trips and fails halfway with no record of where.

**A script prepares and prints; it never sends.** Any outbound step — send, publish, push, post — goes through the confirm-first tool after the user has seen what the script produced.

**Verify the effect, not the return value.** A connector that reports success has reported its own opinion. Check the mailbox, the folder, the row.

## 2. Registering a system

A system earns a row in `index-tools.md` **the first time it is actually reached**, not when someone believes it is available. Record four things: what it is, what it can reach, the route to it, and the trap that cost time. A row with an empty trap column is a row that has not been used yet.

**Authorization is not reachability.** A connector may be installed and still unauthorized, and the two are separate for skills and connector tools even when they ship together. Record the state that was observed, dated — "authorization pending" is a useful row; "available" without evidence is not.

**Re-check before depending on it.** Where authorization is per session, a row that held yesterday says nothing about today. The row states that it must be re-checked; it does not promise it holds.

## 3. What does not belong here

Credentials, tokens and keys — never, in any form, not even truncated. The route says *where* to authenticate, never *with what*.

A system nobody has reached. Speculative rows read as capability and send a session down a path that does not exist.

The mechanics of one particular task. Those live with the task; this file is the index and the rules.
