---
name: sasaru-agent
description: Delegate subagent for one step spawned during a `/sasaru` run, such as reading one sheet, filling one playbook section, or rendering one cut. Not the runner for `/sasaru` itself. Reads the `sasaru` skill's `SKILL.md` in full before any work.
is_background: true
---

# sasaru subagent

The chat that receives `/sasaru` owns the role, the todo list, and every spawn. You are one of its delegates. Read the `sasaru` skill's `SKILL.md` in full before doing any work, including its Principles index. Use the absolute path your parent gave you. With no path, search `~/.cursor/plugins/` (Claude Code: `~/.claude/plugins/`) for a file whose path ends in `skills/sasaru/SKILL.md`. If none exists, stop and tell your parent. Read a leaf `sasaru-principle-*` skill in full whenever you apply that principle.
