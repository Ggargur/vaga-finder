import httpx
import respx

from vaga_finder.config import Config
from vaga_finder.fontes import fontes_ativas
from vaga_finder.fontes.ashby import URL as URL_ASHBY
from vaga_finder.fontes.ashby import Ashby
from vaga_finder.fontes.base import casa_termos
from vaga_finder.fontes.greenhouse import URL as URL_GH
from vaga_finder.fontes.greenhouse import Greenhouse
from vaga_finder.fontes.himalayas import URL as URL_HIM
from vaga_finder.fontes.himalayas import Himalayas
from vaga_finder.fontes.lever import URL as URL_LEVER
from vaga_finder.fontes.lever import Lever
from vaga_finder.fontes.linkedin import DETALHE, LISTA, LinkedIn, cartoes
from vaga_finder.fontes.pagina_generica import PaginaGenerica, ats_citados, links_de_vagas, vagas_jsonld
from vaga_finder.fontes.remoteok import URL as URL_ROK
from vaga_finder.fontes.remoteok import RemoteOK
from vaga_finder.models import Vaga

from .conftest import FIXTURES, carregar_fixture


def _html(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def test_casa_termos_exige_todas_as_palavras():
    v = Vaga(fonte="t", id_fonte="1", titulo="Backend Developer", url="x", descricao="We use Python and Go")
    assert casa_termos(v, ["python"])
    assert casa_termos(v, ["backend developer"])
    assert not casa_termos(v, ["desenvolvedor backend"])
    assert casa_termos(v, [])


@respx.mock
def test_remoteok_ignora_aviso_legal_e_filtra_termos():
    respx.get(URL_ROK).mock(return_value=httpx.Response(200, json=carregar_fixture("remoteok.json")))
    vagas = RemoteOK().buscar(["python"], 10)
    assert [v.titulo for v in vagas] == ["Sr Solutions Architect", "DESARROLLADOR FULL STACK"]
    assert all(v.remoto and v.fonte == "remoteok" for v in vagas)
    assert "â€" not in vagas[0].descricao and "â\x80" not in vagas[0].descricao


@respx.mock
def test_himalayas_pagina_ate_acabar():
    dados = carregar_fixture("himalayas.json")
    rota = respx.get(URL_HIM).mock(
        side_effect=[httpx.Response(200, json=dados), httpx.Response(200, json={"jobs": []})]
    )
    vagas = Himalayas().buscar(["python"], 50)
    assert rota.call_count == 2 and len(vagas) == 2
    assert vagas[0].empresa == "lemon.io" and vagas[0].url.startswith("https://himalayas.app/")


@respx.mock
def test_greenhouse_lever_ashby():
    respx.get(URL_GH.format(slug="gitlab")).mock(return_value=httpx.Response(200, json=carregar_fixture("greenhouse.json")))
    respx.get(URL_GH.format(slug="nao-existe")).mock(return_value=httpx.Response(404))
    respx.get(URL_LEVER.format(slug="spotify")).mock(return_value=httpx.Response(200, json=carregar_fixture("lever.json")))
    respx.get(URL_ASHBY.format(slug="nubank")).mock(return_value=httpx.Response(200, json=carregar_fixture("ashby.json")))

    gh = Greenhouse(["nao-existe", "gitlab"]).buscar(["engineer"], 10)
    assert [v.titulo for v in gh] == ["AI Engineer"] and gh[0].empresa == "GitLab" and gh[0].id_fonte.startswith("gitlab:")

    lv = Lever(["spotify"]).buscar(["engineer"], 10)
    assert [v.titulo for v in lv] == ["Android Engineer - Experience"] and lv[0].empresa == "Spotify"

    ab = Ashby(["nubank"]).buscar(["security"], 10)
    assert [v.titulo for v in ab] == ["Lead Security Engineer (Threat Detection)"] and ab[0].remoto is not None


def test_linkedin_cartoes():
    cs = cartoes(_html("linkedin_lista.html"))
    assert len(cs) == 2
    assert cs[0]["id"].isdigit() and cs[0]["titulo"] and cs[0]["empresa"]
    assert "?" not in cs[0]["url"]


@respx.mock
def test_linkedin_busca_detalhe_e_para_no_bloqueio():
    respx.get(LISTA).mock(side_effect=[httpx.Response(200, text=_html("linkedin_lista.html")), httpx.Response(200, text="")])
    ids = [c["id"] for c in cartoes(_html("linkedin_lista.html"))]
    respx.get(DETALHE.format(id=ids[0])).mock(return_value=httpx.Response(200, text=_html("linkedin_vaga.html")))
    respx.get(DETALHE.format(id=ids[1])).mock(return_value=httpx.Response(429))
    vagas = LinkedIn(pausa=(0, 0)).buscar(["python"], 20)
    assert len(vagas) == 2
    assert len(vagas[0].descricao) > 200 and vagas[1].descricao == ""


JSONLD = """<html><head><meta property="og:site_name" content="Acme"><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[{"@type":"JobPosting","title":"Dev Python","datePosted":"2026-09-01",
"description":"<p>Envie para vagas@acme.com</p>","hiringOrganization":{"@type":"Organization","name":"Acme SA"},
"jobLocation":{"@type":"Place","address":{"addressLocality":"Recife"}},"url":"https://acme.com/vagas/1"}]}
</script></head><body></body></html>"""

LISTAGEM = """<html><body><nav><a href="/sobre">Sobre</a></nav>
<a href="/vagas/dev-python">Desenvolvedor Python Sênior</a>
<a href="https://outra.com/vagas/java">Desenvolvedor Java</a>
<a href="/vagas/dev-python">Desenvolvedor Python Sênior</a></body></html>"""


def test_pagina_jsonld():
    [v] = vagas_jsonld(JSONLD, "https://acme.com/carreiras")
    assert v.titulo == "Dev Python" and v.empresa == "Acme SA" and v.local == "Recife"
    assert v.emails == ["vagas@acme.com"] and v.url == "https://acme.com/vagas/1"


def test_pagina_links_e_ats():
    links = links_de_vagas(LISTAGEM, "https://acme.com/carreiras", ["python"])
    assert links == [("https://acme.com/vagas/dev-python", "Desenvolvedor Python Sênior")]
    html = '<a href="https://jobs.ashbyhq.com/nubank">Vagas</a><a href="https://job-boards.greenhouse.io/gitlab/jobs/1">x</a>'
    assert ats_citados(html, "https://nubank.com.br") == {"ashby": ["nubank"], "greenhouse": ["gitlab"]}
    assert ats_citados("", "https://jobs.lever.co/spotify") == {"lever": ["spotify"]}


@respx.mock
def test_pagina_segue_links():
    respx.get("https://acme.com/carreiras").mock(return_value=httpx.Response(200, text=LISTAGEM))
    respx.get("https://acme.com/vagas/dev-python").mock(
        return_value=httpx.Response(200, text="<html><body><header>menu</header><main><h1>Dev Python Sr</h1><p>Requisitos: Django.</p></main></body></html>")
    )
    [v] = PaginaGenerica(["https://acme.com/carreiras"], pausa_s=0).buscar(["python"], 10)
    assert v.titulo == "Dev Python Sr" and "Django" in v.descricao and "menu" not in v.descricao
    assert v.empresa == "Acme" and v.fonte == "pagina"


def test_fontes_ativas_respeitam_config():
    cfg = Config()
    assert [f.nome for f in fontes_ativas(cfg)] == ["gupy", "remotive", "remoteok", "himalayas"]
    cfg.fontes.gupy = False
    cfg.fontes.greenhouse = ["gitlab"]
    cfg.fontes.ashby = ["nubank"]
    cfg.fontes.linkedin = True
    assert [f.nome for f in fontes_ativas(cfg)] == ["remotive", "remoteok", "himalayas", "greenhouse", "ashby", "linkedin"]


@respx.mock
def test_linkedin_bloqueio_na_listagem_nao_busca_detalhes():
    respx.get(LISTA).mock(side_effect=[httpx.Response(200, text=_html("linkedin_lista.html")), httpx.Response(429)])
    detalhe = respx.get(url__startswith="https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/")
    vagas = LinkedIn(pausa=(0, 0)).buscar(["python"], 20)
    assert len(vagas) == 2 and detalhe.call_count == 0
