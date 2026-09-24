<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '../api/client'
import type { RascunhoCompleto } from '../api/tipos'
import EstadoVazio from '../components/EstadoVazio.vue'
import ListaAvisos from '../components/ListaAvisos.vue'
import NotaBadge from '../components/NotaBadge.vue'
import StatusTag from '../components/StatusTag.vue'
import { avisar, tentar } from '../composables/toast'
import { nomeFonte, relativo } from '../formato'
import { useApp } from '../stores/app'

const app = useApp()
const lista = ref<RascunhoCompleto[]>([])
const selecionadoId = ref<number | null>(null)
const form = reactive({ assunto: '', corpo: '', destinatario: '' })
const instrucao = ref('')
const ocupado = ref<'' | 'salvar' | 'aprovar' | 'regerar' | 'rejeitar'>('')
const carregando = ref(true)
const verDescricao = ref(false)

const ORDEM: Record<string, number> = { erro: 0, pendente: 1, aprovado: 2 }

async function carregar() {
  const [pendentes, erros, aprovados] = await Promise.all([
    api.rascunhos('pendente'),
    api.rascunhos('erro'),
    api.rascunhos('aprovado'),
  ]).catch(() => [[], [], []] as RascunhoCompleto[][])
  lista.value = [...erros, ...pendentes, ...aprovados].sort(
    (a, b) => ORDEM[a.status]! - ORDEM[b.status]! || (b.avaliacao?.nota ?? 0) - (a.avaliacao?.nota ?? 0),
  )
  carregando.value = false
  if (!lista.value.some((r) => r.id === selecionadoId.value)) selecionar(proximoEditavel())
}

onMounted(carregar)
watch(() => app.versao, carregar)

const atual = computed(() => lista.value.find((r) => r.id === selecionadoId.value) ?? null)
const editavel = computed(() => atual.value && ['pendente', 'erro'].includes(atual.value.status))
const sujo = computed(
  () =>
    !!atual.value &&
    (form.assunto !== atual.value.assunto ||
      form.corpo !== atual.value.corpo ||
      form.destinatario !== atual.value.destinatario),
)
const palavras = computed(() => (form.corpo.match(/[\p{L}\p{N}_]+/gu) ?? []).length)
const bloqueado = computed(() => atual.value?.bloqueado ?? false)
const naFila = computed(() => lista.value.filter((r) => r.status === 'aprovado').length)

function proximoEditavel(excluir?: number): number | null {
  return lista.value.find((r) => r.id !== excluir && r.status !== 'aprovado')?.id ?? lista.value[0]?.id ?? null
}

function selecionar(id: number | null) {
  if (sujo.value && !confirm('Descartar as alterações não salvas?')) return
  selecionadoId.value = id
  const r = lista.value.find((x) => x.id === id)
  form.assunto = r?.assunto ?? ''
  form.corpo = r?.corpo ?? ''
  form.destinatario = r?.destinatario ?? ''
  instrucao.value = ''
  verDescricao.value = false
}

function substituir(r: RascunhoCompleto) {
  const i = lista.value.findIndex((x) => x.id === r.id)
  if (i >= 0) lista.value[i] = r
  form.assunto = r.assunto
  form.corpo = r.corpo
  form.destinatario = r.destinatario
}

async function salvar(): Promise<boolean> {
  if (!atual.value) return false
  ocupado.value = 'salvar'
  const r = await tentar(() => api.editarRascunho(atual.value!.id, { ...form }))
  ocupado.value = ''
  if (r) substituir(r)
  return !!r
}

async function aprovar() {
  if (!atual.value) return
  if (sujo.value && !(await salvar())) return
  ocupado.value = 'aprovar'
  const id = atual.value.id
  const r = await tentar(() => api.aprovarRascunho(id))
  ocupado.value = ''
  if (!r) return
  substituir(r)
  const espera = app.estado?.fila.proximo_envio_em_s ?? 0
  avisar(
    espera > 5 ? `Na fila de envio. Sai em cerca de ${Math.ceil(espera / 60)} min.` : 'Na fila de envio. Sai em instantes.',
    'ok',
  )
  selecionar(proximoEditavel(id))
  lista.value.sort((a, b) => ORDEM[a.status]! - ORDEM[b.status]!)
  app.mudou()
}

async function regerar() {
  if (!atual.value) return
  if (sujo.value && !confirm('Gerar de novo descarta suas edições. Continuar?')) return
  ocupado.value = 'regerar'
  const r = await tentar(() => api.regerarRascunho(atual.value!.id, instrucao.value), 'Nova versão pronta.')
  ocupado.value = ''
  if (r) {
    substituir(r)
    instrucao.value = ''
  }
}

async function rejeitar() {
  if (!atual.value) return
  ocupado.value = 'rejeitar'
  const id = atual.value.id
  const r = await tentar(() => api.rejeitarRascunho(id))
  ocupado.value = ''
  if (!r) return
  lista.value = lista.value.filter((x) => x.id !== id)
  form.assunto = form.corpo = form.destinatario = ''
  selecionadoId.value = null
  selecionar(proximoEditavel())
  app.mudou()
}

async function cancelar() {
  if (!atual.value) return
  const r = await tentar(() => api.cancelarRascunho(atual.value!.id), 'Removido da fila.')
  if (r) {
    substituir(r)
    app.mudou()
  }
}
</script>

<template>
  <header class="flex flex-wrap items-end justify-between gap-3">
    <div>
      <h1 class="text-2xl font-semibold tracking-tight">Revisão</h1>
      <p class="text-sm text-texto-2">
        Nada sai sem a sua aprovação. Aprovados entram na fila e saem com uma pausa entre eles.
      </p>
    </div>
    <p v-if="naFila" class="text-sm text-texto-2">{{ naFila }} na fila de envio</p>
  </header>

  <p v-if="carregando" class="text-sm text-texto-2">Carregando…</p>

  <EstadoVazio
    v-else-if="!lista.length"
    titulo="Nenhum email para revisar"
    texto="Os rascunhos aparecem aqui quando o Claude encontra vagas acima da nota mínima com email de contato publicado."
  >
    <button class="botao primario" :disabled="app.tarefa?.status === 'rodando'" @click="app.iniciar('rodar')">
      Buscar e avaliar agora
    </button>
    <RouterLink to="/aplicar" class="botao">Ver vagas sem email</RouterLink>
  </EstadoVazio>

  <div v-else class="grid gap-4 lg:grid-cols-[280px_1fr]">
    <!-- lista -->
    <nav class="cartao max-h-[40vh] overflow-y-auto lg:max-h-[calc(100vh-10rem)]" aria-label="Rascunhos">
      <button
        v-for="r in lista"
        :key="r.id"
        class="flex w-full items-start gap-3 border-b border-borda px-4 py-3 text-left last:border-0 hover:bg-superficie-2"
        :class="r.id === selecionadoId ? 'bg-marca-suave' : ''"
        @click="selecionar(r.id)"
      >
        <NotaBadge :nota="r.avaliacao?.nota" />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-medium">{{ r.vaga.titulo }}</span>
          <span class="block truncate text-xs text-texto-2">{{ r.vaga.empresa || nomeFonte(r.vaga.fonte) }}</span>
          <span class="mt-1 flex gap-1">
            <StatusTag v-if="r.status !== 'pendente'" :status="r.status" />
            <span v-if="r.bloqueado" class="text-xs text-erro">já enviado</span>
          </span>
        </span>
      </button>
    </nav>

    <!-- editor -->
    <section v-if="atual" class="grid gap-4 xl:grid-cols-[1fr_340px]">
      <div class="cartao space-y-4 p-5">
        <div class="flex flex-wrap items-center gap-2">
          <StatusTag :status="atual.status" />
          <span class="text-xs text-texto-2">
            criado {{ relativo(atual.criado_em) }} · idioma {{ atual.idioma.toUpperCase() }}
          </span>
        </div>

        <p v-if="atual.erro" class="rounded-lg bg-erro-suave px-3 py-2 text-sm text-erro">{{ atual.erro }}</p>

        <label class="block">
          <span class="rotulo">Para</span>
          <input v-model="form.destinatario" type="email" class="campo" :disabled="!editavel" />
          <span v-if="atual.vaga.emails.length > 1" class="mt-1 block text-xs text-texto-2">
            Outros emails na vaga: {{ atual.vaga.emails.filter((x) => x !== form.destinatario).join(', ') }}
          </span>
        </label>

        <label class="block">
          <span class="rotulo">Assunto</span>
          <input v-model="form.assunto" class="campo" :disabled="!editavel" />
        </label>

        <label class="block">
          <span class="flex items-baseline justify-between">
            <span class="rotulo">Mensagem</span>
            <span class="text-xs text-texto-2 tabular-nums">{{ palavras }} palavras</span>
          </span>
          <textarea v-model="form.corpo" rows="16" class="campo leading-relaxed" :disabled="!editavel" />
          <span class="mt-1 block text-xs text-texto-2">O currículo em PDF vai anexado.</span>
        </label>

        <ListaAvisos :avisos="atual.avisos" />

        <div v-if="editavel" class="rounded-lg border border-borda bg-superficie-2 p-3">
          <label class="rotulo" for="instrucao">Pedir outra versão ao Claude</label>
          <div class="flex flex-col gap-2 sm:flex-row">
            <input
              id="instrucao"
              v-model="instrucao"
              class="campo"
              placeholder="Opcional: mais curto, destaque o projeto X, tom mais formal…"
              @keydown.enter="regerar"
            />
            <button class="botao shrink-0" :disabled="!!ocupado" @click="regerar">
              {{ ocupado === 'regerar' ? 'Gerando…' : 'Gerar de novo' }}
            </button>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 border-t border-borda pt-4">
          <template v-if="editavel">
            <button class="botao perigo" :disabled="!!ocupado" @click="rejeitar">Rejeitar</button>
            <span class="flex-1" />
            <button class="botao" :disabled="!!ocupado || !sujo" @click="salvar">
              {{ ocupado === 'salvar' ? 'Salvando…' : 'Salvar edição' }}
            </button>
            <button class="botao primario" :disabled="!!ocupado || bloqueado" @click="aprovar">
              {{ ocupado === 'aprovar' ? 'Aprovando…' : 'Aprovar e enviar' }}
            </button>
          </template>
          <template v-else-if="atual.status === 'aprovado'">
            <span class="flex-1 text-sm text-texto-2">
              Na fila de envio<template v-if="app.estado?.fila.proximo_envio_em_s">
                · próximo envio em {{ Math.ceil(app.estado.fila.proximo_envio_em_s / 60) }} min</template
              >
            </span>
            <button class="botao" @click="cancelar">Tirar da fila</button>
          </template>
        </div>
      </div>

      <!-- vaga -->
      <aside class="cartao h-fit space-y-4 p-5 text-sm">
        <div>
          <p class="text-xs text-texto-2">{{ nomeFonte(atual.vaga.fonte) }} · {{ atual.vaga.local || 'local não informado' }}</p>
          <h2 class="mt-1 text-base font-semibold">{{ atual.vaga.titulo }}</h2>
          <p class="text-texto-2">{{ atual.vaga.empresa }}</p>
          <a :href="atual.vaga.url" target="_blank" rel="noopener" class="link mt-1 inline-block">Abrir vaga ↗</a>
        </div>
        <div v-if="atual.avaliacao" class="space-y-3 border-t border-borda pt-4">
          <div class="flex items-center gap-3">
            <NotaBadge :nota="atual.avaliacao.nota" />
            <p class="text-texto-2">{{ atual.avaliacao.motivo }}</p>
          </div>
          <div v-if="atual.avaliacao.pontos_fortes.length">
            <p class="rotulo">Pontos fortes</p>
            <ul class="list-disc space-y-0.5 pl-5">
              <li v-for="p in atual.avaliacao.pontos_fortes" :key="p">{{ p }}</li>
            </ul>
          </div>
          <div v-if="atual.avaliacao.lacunas.length">
            <p class="rotulo">Lacunas</p>
            <ul class="list-disc space-y-0.5 pl-5 text-texto-2">
              <li v-for="p in atual.avaliacao.lacunas" :key="p">{{ p }}</li>
            </ul>
          </div>
        </div>
        <div class="border-t border-borda pt-4">
          <button class="link text-sm" @click="verDescricao = !verDescricao">
            {{ verDescricao ? 'Esconder descrição' : 'Ver descrição da vaga' }}
          </button>
          <p v-if="verDescricao" class="mt-2 max-h-96 overflow-y-auto text-xs leading-relaxed whitespace-pre-line text-texto-2">
            {{ atual.vaga.descricao }}
          </p>
        </div>
      </aside>
    </section>
  </div>
</template>
