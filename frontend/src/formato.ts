const dataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
const soData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' })

export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : dataHora.format(d)
}

export function formatarData(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return isNaN(d.getTime()) ? iso : soData.format(d)
}

export function relativo(iso: string | null | undefined): string {
  if (!iso) return ''
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'agora'
  if (s < 3600) return `há ${Math.floor(s / 60)} min`
  if (s < 86400) return `há ${Math.floor(s / 3600)} h`
  const dias = Math.floor(s / 86400)
  return dias === 1 ? 'ontem' : `há ${dias} dias`
}

const FONTES: Record<string, string> = {
  gupy: 'Gupy',
  remotive: 'Remotive',
  remoteok: 'RemoteOK',
  himalayas: 'Himalayas',
  greenhouse: 'Greenhouse',
  lever: 'Lever',
  pagina: 'Página de carreira',
  linkedin: 'LinkedIn',
}

export function nomeFonte(fonte: string): string {
  return FONTES[fonte] ?? fonte
}

export const ROTULO_ORIGEM: Record<string, string> = {
  ferramenta: 'vaga-finder',
  gmail: 'Gmail',
  manual: 'Pelo link',
}
