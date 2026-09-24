<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api/client'
import type { VagaDetalhe, VagaListada } from '../api/tipos'
import EstadoVazio from '../components/EstadoVazio.vue'
import ListaAvisos from '../components/ListaAvisos.vue'
import Modal from '../components/Modal.vue'
import NotaBadge from '../components/NotaBadge.vue'
import StatusTag from '../components/StatusTag.vue'
import { tentar } from '../composables/toast'
import { formatarData, nomeFonte } from '../formato'
import { useApp } from '../stores/app'

const app = useApp()
const router = useRouter()

const filtros = reactive({
  busca: '',
  status: '',
  fonte: '',
  nota_min: null as number | null,
  com_email: '' as '' | 'sim' | 'nao',
})
const vagas = ref<VagaListada[]>([])
const carregando = ref(false)
const detalhe = ref<VagaDetalhe | null>(null)
const modalAberto = ref(false)
const destinatarioManual = ref('')
const gerando = ref(false)

async function carregar() {
  carregando.value = true
  vagas.value =
    (await tentar(() =>
      api.vagas({
        busca: filtros.busca,
        status: filtros.status,
        fonte: filtros.fonte,
        nota_min: filtros.nota_min,
        com_email: filtros.com_email === '' ? null : filtros.com_email === 'sim',
        limite: 300,
      }),
    )) ?? []
  carregando.value = false
}

let atraso: number | undefined
watch(filtros, () => {
  clearTimeout(atraso)
  atraso = window.setTimeout(carregar, 250)
})
watch(() => app.versao, carregar)
onMounted(carregar)

async function abrir(id: number) {
  const d = await tentar(() => api.vaga(id))
  if (!d) return
  detalhe.value = d
  destinatarioManual.value = ''
  modalAberto.value = true
}

async function gerarRascunho() {
  if (!detalhe.value) return
  gerando.value = true
  const r = await tentar(
    () => api.criarRascunho(detalhe.value!.id, destinatarioManual.value || undefined),
    'Rascunho criado.',
  )
  gerando.value = false
  if (r) {
    modalAberto.value = false
    app.mudou()
    router.push('/revisao')
  }
}

async function marcarAplicada() {
  if (!detalhe.value) return
  if (await tentar(() => api.marcarAplicada(detalhe.value!.id), 'Registrado no histórico.')) {
    modalAberto.value = false
    app.mudou()
  }
}

async function descartar() {
  if (!detalhe.value) return
  if (await tentar(() => api.descartarVaga(detalhe.value!.id))) {
    modalAberto.value = false
    app.mudou()
  }
}
</script>

<template>
  <header>
    <h1 class="text-2xl font-semibold tracking-tight">Vagas</h1>
    <p class="text-sm text-texto-2">Tudo o que foi coletado, da maior para a menor nota.</p>
  </header>

  <div class="cartao grid grid-cols-2 gap-3 p-4 md:grid-cols-5">
    <label class="col-span-2">
      <span class="rotulo">Buscar</span>
      <input v-model="filtros.busca" class="campo" placeholder="Título ou empresa" type="search" />
    </label>
    <label>
      <span class="rotulo">Status</span>
      <select v-model="filtros.status" class="campo">
        <option value="">Todos</option>
        <option value="nova">Novas</option>
        <option value="avaliada">Avaliadas</option>
        <option value="aplicada">Aplicadas</option>
        <option value="filtrada">Filtradas</option>
      </select>
    </label>
    <label>
      <span class="rotulo">Fonte</span>
      <select v-model="filtros.fonte" class="campo">
        <option value="">Todas</option>
        <option v-for="(_, f) in app.estado?.vagas_por_fonte" :key="f" :value="f">{{ nomeFonte(String(f)) }}</option>
      </select>
    </label>
    <div class="grid grid-cols-2 gap-3 max-md:col-span-2">
      <label>
        <span class="rotulo">Nota ≥</span>
        <input v-model.number="filtros.nota_min" type="number" min="0" max="100" class="campo" />
      </label>
      <label>
        <span class="rotulo">Email</span>
        <select v-model="filtros.com_email" class="campo">
          <option value="">Todas</option>
          <option value="sim">Com</option>
          <option value="nao">Sem</option>
        </select>
      </label>
    </div>
  </div>

  <EstadoVazio
    v-if="!carregando && !vagas.length"
    titulo="Nenhuma vaga encontrada"
    texto="Ajuste os filtros ou rode uma busca no Painel."
  />

  <div v-else class="cartao overflow-x-auto">
    <table class="w-full min-w-[720px] text-sm">
      <thead class="border-b border-borda text-left text-xs text-texto-2 uppercase">
        <tr>
          <th class="w-16 px-4 py-3 font-medium">Nota</th>
          <th class="px-4 py-3 font-medium">Vaga</th>
          <th class="px-4 py-3 font-medium">Fonte</th>
          <th class="px-4 py-3 font-medium">Local</th>
          <th class="px-4 py-3 font-medium">Contato</th>
          <th class="px-4 py-3 font-medium">Status</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-borda">
        <tr
          v-for="v in vagas"
          :key="v.id"
          class="cursor-pointer hover:bg-superficie-2"
          tabindex="0"
          @click="abrir(v.id)"
          @keydown.enter="abrir(v.id)"
        >
          <td class="px-4 py-3"><NotaBadge :nota="v.avaliacao?.nota" /></td>
          <td class="max-w-md px-4 py-3">
            <p class="truncate font-medium">{{ v.titulo }}</p>
            <p class="truncate text-xs text-texto-2">
              {{ v.empresa }}<template v-if="v.avaliacao"> · {{ v.avaliacao.motivo }}</template>
              <template v-else-if="v.motivo_filtro"> · {{ v.motivo_filtro }}</template>
            </p>
          </td>
          <td class="px-4 py-3 whitespace-nowrap text-texto-2">{{ nomeFonte(v.fonte) }}</td>
          <td class="max-w-40 truncate px-4 py-3 text-texto-2">{{ v.remoto ? 'Remoto' : v.local }}</td>
          <td class="px-4 py-3">
            <span v-if="v.emails.length" class="text-xs text-ok">✉ email</span>
            <span v-else class="text-xs text-texto-2">link</span>
          </td>
          <td class="px-4 py-3">
            <StatusTag :status="v.enviado_em ? 'aplicada' : v.rascunho_status ?? v.status" />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="vagas.length >= 300" class="border-t border-borda px-4 py-2 text-xs text-texto-2">
      Mostrando as 300 primeiras. Use os filtros para refinar.
    </p>
  </div>

  <Modal v-model:aberto="modalAberto" largo>
    <template #titulo>
      <span v-if="detalhe">{{ detalhe.titulo }}</span>
    </template>
    <div v-if="detalhe" class="grid gap-5 text-sm md:grid-cols-[1fr_280px]">
      <div class="space-y-4">
        <p class="text-texto-2">
          {{ detalhe.empresa }} · {{ nomeFonte(detalhe.fonte) }} · {{ detalhe.remoto ? 'Remoto' : detalhe.local }}
          <template v-if="detalhe.publicada_em"> · publicada {{ formatarData(detalhe.publicada_em) }}</template>
        </p>
        <ListaAvisos :avisos="detalhe.historico.avisos" />
        <div v-if="detalhe.avaliacao" class="flex gap-3 rounded-lg bg-superficie-2 p-3">
          <NotaBadge :nota="detalhe.avaliacao.nota" />
          <div class="space-y-2">
            <p>{{ detalhe.avaliacao.motivo }}</p>
            <p v-if="detalhe.avaliacao.pontos_fortes.length" class="text-ok">
              + {{ detalhe.avaliacao.pontos_fortes.join(' · ') }}
            </p>
            <p v-if="detalhe.avaliacao.lacunas.length" class="text-atencao">
              − {{ detalhe.avaliacao.lacunas.join(' · ') }}
            </p>
          </div>
        </div>
        <p class="max-h-[45vh] overflow-y-auto text-[13px] leading-relaxed whitespace-pre-line text-texto-2">
          {{ detalhe.descricao || 'Sem descrição.' }}
        </p>
      </div>

      <div class="space-y-4">
        <a :href="detalhe.url" target="_blank" rel="noopener" class="botao w-full">Abrir vaga ↗</a>
        <div>
          <p class="rotulo">Contato publicado</p>
          <p v-if="detalhe.emails.length" class="break-all">{{ detalhe.emails.join(', ') }}</p>
          <p v-else class="text-texto-2">A vaga não publica email. Candidate-se pelo link.</p>
        </div>

        <template v-if="!detalhe.historico.bloqueado && !detalhe.rascunhos.some((r) => ['pendente', 'aprovado'].includes(r.status))">
          <label v-if="!detalhe.emails.length" class="block">
            <span class="rotulo">Tem um email de contato?</span>
            <input v-model="destinatarioManual" type="email" class="campo" placeholder="recrutamento@empresa.com" />
            <span class="mt-1 block text-xs text-texto-2">Só use um endereço que você viu publicado ou recebeu.</span>
          </label>
          <button
            class="botao primario w-full"
            :disabled="gerando || (!detalhe.emails.length && !destinatarioManual)"
            @click="gerarRascunho"
          >
            {{ gerando ? 'Redigindo (~40s)…' : 'Redigir email com o Claude' }}
          </button>
        </template>
        <p v-else-if="detalhe.rascunhos.length" class="text-texto-2">
          Esta vaga já tem rascunho: <StatusTag :status="detalhe.rascunhos.at(-1)!.status" />
        </p>

        <div v-if="detalhe.envios.length" class="space-y-1">
          <p class="rotulo">Candidaturas</p>
          <p v-for="e in detalhe.envios" :key="e.id ?? e.enviado_em" class="text-texto-2">
            {{ formatarData(e.enviado_em) }} · {{ e.destinatario ?? 'pelo link' }}
          </p>
        </div>

        <div class="flex flex-col gap-2 border-t border-borda pt-4">
          <button v-if="detalhe.status !== 'aplicada'" class="botao" @click="marcarAplicada">
            Marquei como aplicada
          </button>
          <button v-if="detalhe.status !== 'filtrada'" class="botao perigo" @click="descartar">Descartar vaga</button>
        </div>
      </div>
    </div>
  </Modal>
</template>
