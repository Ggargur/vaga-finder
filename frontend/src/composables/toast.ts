import { reactive } from 'vue'

export type TipoToast = 'ok' | 'erro' | 'info'

export interface Toast {
  id: number
  tipo: TipoToast
  texto: string
}

let proximo = 1
export const toasts = reactive<Toast[]>([])

export function avisar(texto: string, tipo: TipoToast = 'info', duracaoMs = 5000) {
  const id = proximo++
  toasts.push({ id, tipo, texto })
  setTimeout(() => fechar(id), tipo === 'erro' ? duracaoMs * 2 : duracaoMs)
}

export function fechar(id: number) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i >= 0) toasts.splice(i, 1)
}

/** Executa uma ação da API mostrando o erro como toast. Devolve undefined se falhar. */
export async function tentar<T>(acao: () => Promise<T>, sucesso?: string): Promise<T | undefined> {
  try {
    const r = await acao()
    if (sucesso) avisar(sucesso, 'ok')
    return r
  } catch (e) {
    avisar(e instanceof Error ? e.message : String(e), 'erro')
    return undefined
  }
}
