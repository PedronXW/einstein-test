# Features spec-anchored

Cada feature vive em `F-XXX-<slug>/`. Dentro dela:

- `spec.md` — spec LEGÍVEL: histórias `U-###`, critérios `AC-###` (refs),
  suposições `A-###` e perguntas `Q-###`.
- `plan.md` — plano: tarefas `T-###`, deps, paralelismo.
- `criteria.reg` — máquina: `AC-id	U-id	descricao	T-id`.
- `assumptions.reg` — máquina: `id	tipo(A|Q)	status	texto`.
- `trace.tsv` — máquina: `AC-id	comando-teste	T-id	status	sha`.
- `state.tsv` — máquina: `T-id	status	branch	sha`.
- `tasks/T-XXX.md` — janela de execução por tarefa.

Todo critério tem DONO de tarefa. Toda tarefa tem janela (worktree+branch)
própria quando executada em paralelo. "Pronto" = veredito da máquina (`specs proof`).
