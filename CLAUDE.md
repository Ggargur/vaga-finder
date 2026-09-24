# vaga-finder

Coleta vagas, avalia aderência ao currículo com `claude -p`, redige emails de candidatura (regras stop-slop) e envia via Gmail após revisão humana.

- `backend/`: FastAPI + serviços em `src/vaga_finder/` (uv, Python 3.14). Testes: `cd backend && uv run pytest`.
- `frontend/`: Vue 3 + Vite + TS. `cd frontend && npm run dev` / `npm run build`.
- LLM: sempre via `vaga_finder.llm` (usa `claude -p`, assinatura Pro; não há ANTHROPIC_API_KEY).
- `backend/data/` guarda CV, perfil e banco: nunca versionar.

## Commits
- Não adicionar a linha `Co-Authored-By` (nem outra atribuição ao Claude) nas mensagens de commit ou descrições de PR deste repositório.
- Mensagens curtas em português.
