export type StatusVaga = 'nova' | 'filtrada' | 'avaliada' | 'aplicada'
export type StatusRascunho = 'pendente' | 'aprovado' | 'rejeitado' | 'enviado' | 'erro'
export type OrigemEnvio = 'ferramenta' | 'gmail' | 'manual'

export interface Avaliacao {
  nota: number
  motivo: string
  pontos_fortes: string[]
  lacunas: string[]
}

export interface Aviso {
  tipo: 'slop' | 'historico' | 'contato'
  mensagem: string
  trecho: string | null
}

export interface Vaga {
  id: number
  fonte: string
  id_fonte: string
  titulo: string
  empresa: string
  local: string
  remoto: boolean | null
  url: string
  descricao: string
  emails: string[]
  publicada_em: string | null
  coletada_em: string
  status: StatusVaga
  motivo_filtro: string | null
}

export interface VagaListada extends Vaga {
  avaliacao: Avaliacao | null
  rascunho_status: StatusRascunho | null
  enviado_em: string | null
}

export interface Envio {
  id: number | null
  vaga_id: number | null
  destinatario: string | null
  empresa: string
  titulo: string
  assunto: string
  corpo: string
  url: string | null
  enviado_em: string
  origem: OrigemEnvio
}

export interface VagaDetalhe extends Vaga {
  avaliacao: Avaliacao | null
  rascunhos: Rascunho[]
  envios: Envio[]
  historico: { bloqueado: boolean; avisos: Aviso[] }
}

export interface Rascunho {
  id: number
  vaga_id: number
  destinatario: string
  assunto: string
  corpo: string
  idioma: string
  status: StatusRascunho
  avisos: Aviso[]
  erro: string | null
  criado_em: string
  atualizado_em: string
}

export interface RascunhoCompleto extends Rascunho {
  bloqueado: boolean
  palavras: number
  vaga: Pick<Vaga, 'id' | 'titulo' | 'empresa' | 'url' | 'fonte' | 'local' | 'remoto' | 'descricao' | 'emails'>
  avaliacao: Avaliacao | null
}

export interface Tarefa {
  id: number
  tipo: string
  status: 'rodando' | 'concluida' | 'erro'
  progresso: number
  total: number
  mensagem: string
  resultado: Record<string, any>
  criada_em: string
  terminada_em: string | null
}

export interface Estado {
  vagas_por_status: Partial<Record<StatusVaga, number>>
  vagas_por_fonte: Record<string, number>
  rascunhos_pendentes: number
  enviados_hoje: number
  enviados_total: number
  limite_diario: number
  nota_minima: number
  tem_perfil: boolean
  tem_curriculo: boolean
  gmail_configurado: boolean
  gmail_user: string
  tarefa_rodando: Tarefa | null
  fila: { aprovados: number; proximo_envio_em_s: number }
}

export interface Perfil {
  nome: string
  email: string
  telefone: string
  localizacao: string
  links: string[]
  resumo: string
  senioridade: string
  anos_experiencia: number
  cargos_alvo: string[]
  palavras_chave: string[]
  skills: string[]
  idiomas: { idioma: string; nivel: string }[]
  experiencias: { cargo: string; empresa: string; periodo: string; destaques: string[] }[]
  formacao: string[]
  preferencias: { remoto: boolean; locais: string[] }
}

export interface Config {
  busca: { termos: string[]; exclusoes: string[]; palavras_chave: string[]; limite_por_fonte: number }
  fontes: {
    gupy: boolean
    remotive: boolean
    remoteok: boolean
    himalayas: boolean
    greenhouse: string[]
    lever: string[]
    paginas: string[]
    linkedin: boolean
    linkedin_local: string
  }
  avaliacao: { nota_minima: number; modelo: string; lote: number }
  redacao: { modelo: string; palavras_min: number; palavras_max: number; assinatura: string }
  envio: {
    limite_diario: number
    dias_entre_contatos: number
    pausa_min_s: number
    pausa_max_s: number
    anexar_curriculo: boolean
  }
}
