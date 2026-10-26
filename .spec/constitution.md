# Constituição do projeto

Regras inegociáveis do projeto. Cada regra carrega uma verificação executável
(`- scan: <comando>`) que `specs constitution scan` roda contra o repositório.
O comando DEVE ter saída vazia quando a regra é respeitada — qualquer saída é
violação, rastreada até arquivo e linha. **Sem prova, a regra não fecha feature.**

> Os scans usam `grep -r n` (zero dependências). Se o comando do scan não
> existir no ambiente, `specs constitution` responde **NAO-VERIFICADO (exit 1)** —
> nunca um "respeitada" falso.

---

## C-PRIV-001 — Nota de aluno nunca exposta a outro aluno

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.rs' --include='*.go' --include='*.java' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules 'nota[[:space:]]+(do|de|por|para)[[:space:]]+aluno|grade[[:space:]]+(by|of|for)[[:space:]]+student' src/ app/ lib/ 2>/dev/null`

Resultados indicam código expondo a nota de um aluno — possivelmente a outro aluno.

## C-PRIV-002 — Dado pessoal de aluno nunca em log

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.rs' --include='*.go' --include='*.java' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules --exclude='*.test.js' --exclude='*.test.ts' --exclude='*.test.tsx' --exclude='*.test.jsx' --exclude='*.spec.js' --exclude='*.spec.ts' --exclude='*_test.py' --exclude='test_*.py' --exclude='*_test.go' 'logger\.(info|debug|warn|error)|console\.log|print\(' src/ app/ lib/ 2>/dev/null | grep -iE 'cpf|cnpj|email|telefone|documento|matricula|nascimento|rgm|password|senha'`

Aponta log que pode conter dado pessoal (cpf, e-mail, …). Dado pessoal não
entra em log em hipótese alguma.

## C-PRIV-003 — Lista de alunos não vazada em endpoint público

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules 'alunos|listStudents' src/ app/ 2>/dev/null | grep -viE 'test|mock|fake|private|auth|admin|role'`

Sinaliza rota/controller que pode listar alunos sem autorização.

## C-PRIV-004 — Senha/token nunca em texto plano

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.rs' --include='*.go' --include='*.java' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules --exclude-dir=test --exclude-dir=tests '"(senha|password|token|api[_k]?ey|secret)[[:space:]]*[:=][[:space:]]*[^[:space:]]{6,}"' . 2>/dev/null`

Derrame de credencial em texto plano no código. Credenciais vêm de secrets/ambiente.

## C-DATA-001 — Remoção de dado pessoal ao excluir conta

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.sql' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules '(delete|destroy|remove)[[:space:]]+(user|account|aluno|graduation)' src/ app/ 2>/dev/null | grep -viE 'phone|email|tombstone|soft|logical|hard'`

Contração (account/aluno) não pode preservar dado pessoal sem anonimização.

## C-AUDIT-001 — Acesso não-autorizado bloqueado em endpoints de dado pessoal

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules 'app\.(get|post|put|delete)|@(Get|Post|Put|Delete)|@app\.route|@router\.(get|post)|router\.(get|post|put|delete)|def (get|post|put|delete)' src/ app/ 2>/dev/null | grep -iE 'aluno|cpf|matricula|nota' | grep -viE '(auth|jwt|token|role|permission|session|middleware|guard|require)'`

Endpoint que manipula dado pessoal sem nenhuma evidência próxima de controle
de acesso.

## C-OPS-001 — Sem importações secretas/privadas

`scan: grep -rniE --include='*.py' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.rs' --include='*.go' --exclude-dir=.git --exclude-dir=.spec --exclude-dir=node_modules '((from|import|require)[[:space:]]+)(["'"'"'])[^"'"'"']*(/private/|/secret/|/internal/)('"'"'|")' src/ 2>/dev/null`

Não atravessar fronteiras de módulo via caminhos internos/secretos.

---

## Como editar esta constituição

- Nunca **apague** uma regra sem substituí-la por outra — constituição é para ser
  endurecida, não amolecida.
- Ao adicionar regra, adicione também o `scan:` executável (a regra sem prova é
  só opinião).
- `specs constitution` roda todos os scans; o agente reporta o exit code
  (0 = respeito; 1 = violação; 1 = NAO-VERIFICADO se um comando do scan faltar).
  A feature não fecha com constituição violada ou não verificada.