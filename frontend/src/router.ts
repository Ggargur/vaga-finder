import { createRouter, createWebHistory } from 'vue-router'

import AplicarLinkView from './views/AplicarLinkView.vue'
import ConfigView from './views/ConfigView.vue'
import HistoricoView from './views/HistoricoView.vue'
import PainelView from './views/PainelView.vue'
import PerfilView from './views/PerfilView.vue'
import RevisaoView from './views/RevisaoView.vue'
import VagasView from './views/VagasView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'painel', component: PainelView, meta: { titulo: 'Painel' } },
    { path: '/revisao', name: 'revisao', component: RevisaoView, meta: { titulo: 'Revisão' } },
    { path: '/vagas', name: 'vagas', component: VagasView, meta: { titulo: 'Vagas' } },
    { path: '/aplicar', name: 'aplicar', component: AplicarLinkView, meta: { titulo: 'Aplicar pelo link' } },
    { path: '/historico', name: 'historico', component: HistoricoView, meta: { titulo: 'Histórico' } },
    { path: '/perfil', name: 'perfil', component: PerfilView, meta: { titulo: 'Perfil' } },
    { path: '/config', name: 'config', component: ConfigView, meta: { titulo: 'Config' } },
  ],
})

router.afterEach((to) => {
  document.title = to.meta.titulo ? `${to.meta.titulo} · vaga-finder` : 'vaga-finder'
})
