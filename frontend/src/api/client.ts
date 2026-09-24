import type {
  Config,
  Envio,
  Estado,
  Perfil,
  RascunhoCompleto,
  Tarefa,
  VagaDetalhe,
  VagaListada,
} from './tipos'

export class ErroApi extends Error {
  status: number

  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.status = status
  }
}

function mensagemDeErro(corpo: any, status: number): string {
  const detalhe = corpo?.detail
  if (typeof detalhe === 'string') return detalhe
  if (Array.isArray(detalhe)) return detalhe.map((d) => d.msg).join('; ')
  return `Erro ${status}`
}

async function req<T>(metodo: string, caminho: string, corpo?: unknown): Promise<T> {
  const init: RequestInit = { method: metodo, headers: {} }
  if (corpo instanceof FormData) {
    init.body = corpo
  } else if (corpo !== undefined) {
    init.body = JSON.stringify(corpo)
    ;(init.headers as Record<string, string>)['Content-Type'] = 'application/json'
  }
  const resp = await fetch(`/api${caminho}`, init)
  const texto = await resp.text()
  const dados = texto ? JSON.parse(texto) : null
  if (!resp.ok) throw new ErroApi(resp.status, mensagemDeErro(dados, resp.status))
  return dados as T
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  estado: () => req<Estado>('GET', '/estado'),

  vagas: (filtros: {
    status?: string
    fonte?: string
    nota_min?: number | null
    com_email?: boolean | null
    busca?: string
    limite?: number
  }) => req<VagaListada[]>('GET', `/vagas${query(filtros)}`),
  vaga: (id: number) => req<VagaDetalhe>('GET', `/vagas/${id}`),
  marcarAplicada: (id: number) => req<Envio>('POST', `/vagas/${id}/aplicada`),
  descartarVaga: (id: number) => req<{ ok: boolean }>('POST', `/vagas/${id}/descartar`),
  criarRascunho: (id: number, destinatario?: string) =>
    req<RascunhoCompleto>('POST', `/vagas/${id}/rascunho`, destinatario ? { destinatario } : {}),

  rascunhos: (status?: string) => req<RascunhoCompleto[]>('GET', `/rascunhos${query({ status })}`),
  rascunho: (id: number) => req<RascunhoCompleto>('GET', `/rascunhos/${id}`),
  editarRascunho: (id: number, dados: { assunto: string; corpo: string; destinatario: string }) =>
    req<RascunhoCompleto>('PUT', `/rascunhos/${id}`, dados),
  regerarRascunho: (id: number, instrucao?: string) =>
    req<RascunhoCompleto>('POST', `/rascunhos/${id}/regerar`, { instrucao: instrucao || null }),
  aprovarRascunho: (id: number) => req<RascunhoCompleto>('POST', `/rascunhos/${id}/aprovar`),
  cancelarRascunho: (id: number) => req<RascunhoCompleto>('POST', `/rascunhos/${id}/cancelar`),
  rejeitarRascunho: (id: number) => req<RascunhoCompleto>('POST', `/rascunhos/${id}/rejeitar`),

  envios: (busca?: string, origem?: string) => req<Envio[]>('GET', `/envios${query({ busca, origem })}`),
  enviarTeste: () => req<{ enviado_para: string }>('POST', '/envios/teste'),

  iniciarTarefa: (tipo: 'buscar' | 'avaliar' | 'rodar' | 'sincronizar') => req<Tarefa>('POST', `/tarefas/${tipo}`),
  tarefa: (id: number) => req<Tarefa>('GET', `/tarefas/${id}`),
  tarefas: () => req<Tarefa[]>('GET', '/tarefas'),

  perfil: () => req<Perfil | null>('GET', '/perfil'),
  salvarPerfil: (p: Perfil) => req<Perfil>('PUT', '/perfil', p),
  enviarCurriculo: (arquivo: File) => {
    const form = new FormData()
    form.append('arquivo', arquivo)
    return req<Perfil>('POST', '/perfil/curriculo', form)
  },
  regerarPerfil: () => req<Perfil>('POST', '/perfil/regerar'),

  config: () => req<Config>('GET', '/config'),
  salvarConfig: (c: Config) => req<Config>('PUT', '/config', c),
}
