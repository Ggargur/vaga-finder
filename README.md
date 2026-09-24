# vaga-finder

Busca vagas parecidas com o seu currículo, dá uma nota para cada uma com o Claude e, quando a vaga publica um email de contato, escreve um email de candidatura para você revisar e enviar pelo Gmail.

Nada é enviado sem a sua aprovação. O sistema também bloqueia reenvios: mesma vaga (mesmo em outra fonte), mesmo contato dentro de N dias e contatos que já aparecem na sua pasta Enviados do Gmail.

## Como funciona

1. Você envia o PDF do currículo. O Claude extrai um perfil (skills, senioridade, cargos-alvo), que você pode editar.
2. As fontes são consultadas: Gupy, Remotive, RemoteOK, Himalayas, sites de vagas de games (Hitmarker, Remote Game Jobs, Work With Indies, InGame Job, GamesIndustry.biz), Greenhouse, Lever e Ashby (por empresa), páginas de carreira que você listar e, se você ligar, LinkedIn.
3. Um filtro por palavras-chave descarta o que não tem relação. O Claude dá nota de 0 a 100 ao resto.
4. Vagas acima da nota mínima e com email publicado ganham um rascunho. O Claude escreve e depois revisa o texto com as regras do [stop-slop](https://hvpandya.com) para tirar os vícios de texto de IA.
5. Na tela de revisão você edita, pede outra versão, rejeita ou aprova. Aprovou, sai pelo seu Gmail com o CV anexo.
6. Vagas boas sem email vão para a lista "Aplicar pelo link".

## Requisitos

- Python 3.12+ e [uv](https://docs.astral.sh/uv/)
- Node 20+
- [Claude Code](https://claude.com/claude-code) logado (`claude` no PATH). O projeto usa `claude -p`, que consome a cota da sua assinatura. Não precisa de chave da API.
- Uma conta Gmail com verificação em 2 etapas e uma [senha de app](https://myaccount.google.com/apppasswords)

## Instalação

```bash
cd backend
uv sync
cp .env.example .env    # preencha GMAIL_USER, GMAIL_APP_PASSWORD, REMETENTE_NOME

cd ../frontend
npm install
npm run build           # gera frontend/dist, servido pelo backend
```

## Primeiro uso

1. Suba o servidor e abra http://127.0.0.1:8000.
2. Em **Perfil**, envie o PDF do currículo. Confira e ajuste o que o Claude extraiu, principalmente as palavras-chave.
3. Em **Config**, ajuste os termos de busca e clique em **Enviar email de teste para mim**.
4. Opcional: **Sincronizar Enviados** para importar candidaturas antigas do Gmail.
5. No **Painel**, clique em **Buscar e avaliar**. Quando terminar, revise os emails em **Revisão**.

## Uso

```bash
cd backend
uv run vaga-finder serve        # abre em http://127.0.0.1:8000
```

Para desenvolver o front com hot reload, rode `uv run vaga-finder serve --reload` e, em outro terminal, `cd frontend && npm run dev` (http://localhost:5173, com proxy de `/api`).

Linha de comando (útil para cron):

```bash
uv run vaga-finder buscar       # coleta vagas das fontes ligadas
uv run vaga-finder avaliar      # dá nota e gera rascunhos
uv run vaga-finder rodar        # buscar + avaliar
uv run vaga-finder sincronizar  # importa a pasta Enviados do Gmail para o histórico
```

Configuração em `backend/config.yaml` (também editável na tela Config).

## Sobre as fontes

- **Sites de games**: Hitmarker (pelo sitemap), Remote Game Jobs (pelo RSS), Work With Indies (pela listagem), InGame Job e GamesIndustry.biz (pela busca do site). Cada site é lido com a pausa que o robots.txt dele pede, então o GamesIndustry.biz é lento (10s por página). Games Jobs Direct ficou de fora porque o robots.txt proíbe robôs, e o Gamejobs.co bloqueia o acesso. Use termos em inglês.
- **Estúdios de games**: o botão "Adicionar estúdios de games" em Config inclui Riot, Epic, Wildlife, Roblox, Scopely, Bungie, Insomniac, Naughty Dog, Kabam, Jam City, Supercell, Voodoo e Believer.
- **Greenhouse, Lever e Ashby** são os sistemas de recrutamento de muitas empresas de tecnologia. Informe o slug da empresa em Config (o trecho depois de `boards.greenhouse.io/`, `jobs.lever.co/` ou `jobs.ashbyhq.com/`).
- **Páginas de carreira**: se a página linka para Greenhouse, Lever ou Ashby, o vaga-finder usa a API deles. Senão, lê os dados estruturados (JSON-LD) ou segue os links cujo texto bate com os seus termos de busca. Páginas montadas só com JavaScript não funcionam.
- A maioria das vagas não publica email de contato. Essas vão para "Aplicar pelo link"; o sistema nunca inventa endereços.
- **LinkedIn** vem desligado. Os termos de uso do LinkedIn proíbem scraping, e a conta ou o IP podem ser bloqueados. Se ligar, o coletor usa só a busca pública (sem login) e poucas páginas por rodada.
- **Indeed** não é suportado: o Cloudflare bloqueia requisições automatizadas.

## Dados

`backend/data/` guarda o CV, o perfil e o banco SQLite. A pasta está no `.gitignore`.

## Créditos

As regras de escrita em `backend/prompts/stop_slop/` vêm do skill *stop-slop* de [Hardik Pandya](https://hvpandya.com), com uma lista de frases em português adicionada.
