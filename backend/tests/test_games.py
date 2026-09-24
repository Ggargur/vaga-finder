from datetime import datetime, timezone

import httpx
import respx

from vaga_finder.fontes.games import ESTUDIOS, QUADROS, SiteGames
from vaga_finder.fontes.pagina_generica import vagas_jsonld

AGORA = datetime(2026, 9, 24, tzinfo=timezone.utc)

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Studio A is hiring Unity Developer</title><link>https://remotegamejobs.com/jobs/a-unity-dev</link>
<description>Build gameplay in C#</description></item>
<item><title>Studio B is hiring Concept Artist</title><link>https://remotegamejobs.com/jobs/b-artist</link>
<description>Paint things</description></item>
<item><title>Unity outro site</title><link>https://outro.com/jobs/x</link><description>unity</description></item>
</channel></rss>"""

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://hitmarker.net/jobs/playrix-senior-unity-engineer-1</loc><lastmod>2026-09-20T10:00:00+01:00</lastmod></url>
<url><loc>https://hitmarker.net/jobs/old-studio-unity-developer-2</loc><lastmod>2026-06-01T10:00:00+01:00</lastmod></url>
<url><loc>https://hitmarker.net/jobs/riot-community-lead-3</loc><lastmod>2026-09-22T10:00:00+01:00</lastmod></url>
</urlset>"""

JOBPOSTING = """<html><head><script type="application/ld+json">
{"@context":"http://schema.org","@type":"JobPosting","title":"Senior Unity &amp; C# Engineer",
"hiringOrganization":"CI Games","jobLocation":{"@type":"Place","address":"Anywhere"},
"jobLocationType":"TELECOMMUTE","description":"<p>Ship games.\tApply at jobs@cigames.com</p>"}
</script></head><body><footer>contato: hello@remotegamejobs.com</footer></body></html>"""


def test_jsonld_com_campos_em_texto_e_caracteres_de_controle():
    [v] = vagas_jsonld(JOBPOSTING, "https://remotegamejobs.com/jobs/a-unity-dev", "remotegamejobs")
    assert v.titulo == "Senior Unity & C# Engineer" and v.empresa == "CI Games"
    assert v.local == "Anywhere" and v.remoto is True and v.emails == ["jobs@cigames.com"]


def test_rss_filtra_por_termo_e_dominio():
    s = SiteGames("remotegamejobs", pausa_s=0)
    assert s.candidatos_rss(RSS, ["unity"]) == ["https://remotegamejobs.com/jobs/a-unity-dev"]


def test_sitemap_filtra_por_slug_e_idade():
    s = SiteGames("hitmarker", pausa_s=0, agora=AGORA)
    assert s.candidatos_sitemap(SITEMAP, ["unity"]) == ["https://hitmarker.net/jobs/playrix-senior-unity-engineer-1"]


def test_links_de_busca_e_listagem():
    html = """<a href="/en/job/unity-dev?ref=1">Unity Dev</a><a href="/en/job/unity-dev">dup</a>
    <a href="/en/company/acme">Acme</a><a href="https://ingamejob.com/en/job/artist">Artist</a>"""
    s = SiteGames("ingamejob", pausa_s=0)
    base = "https://ingamejob.com/en/jobs?q=unity"
    assert s.candidatos_html(html, base, None) == ["https://ingamejob.com/en/job/unity-dev", "https://ingamejob.com/en/job/artist"]
    assert s.candidatos_html(html, base, ["unity"]) == ["https://ingamejob.com/en/job/unity-dev"]


@respx.mock
def test_buscar_rss_completo_descarta_email_do_site():
    respx.get("https://remotegamejobs.com/feed.rss").mock(return_value=httpx.Response(200, text=RSS))
    respx.get("https://remotegamejobs.com/jobs/a-unity-dev").mock(return_value=httpx.Response(200, text=JOBPOSTING))
    [v] = SiteGames("remotegamejobs", pausa_s=0).buscar(["unity"], 10)
    assert v.fonte == "remotegamejobs" and v.id_fonte == v.url == "https://remotegamejobs.com/jobs/a-unity-dev"
    assert v.emails == ["jobs@cigames.com"]


@respx.mock
def test_buscar_sem_jsonld_usa_h1_e_seletor_de_empresa():
    respx.get(url__startswith="https://ingamejob.com/en/jobs").mock(
        return_value=httpx.Response(200, text='<a href="/en/job/unity-dev">Unity Dev</a>')
    )
    respx.get("https://ingamejob.com/en/job/unity-dev").mock(return_value=httpx.Response(200, text="""
        <html><body><main><h1>Senior Unity Developer</h1><a href="/en/company/hypervr">HyperVR Games</a>
        <p>Requisitos: Unity. Dúvidas: info@ingamejob.com</p></main></body></html>"""))
    [v] = SiteGames("ingamejob", pausa_s=0).buscar(["unity"], 10)
    assert v.titulo == "Senior Unity Developer" and v.empresa == "HyperVR Games" and v.emails == []


@respx.mock
def test_respeita_pausa_entre_requisicoes(monkeypatch):
    pausas = []
    monkeypatch.setattr("vaga_finder.fontes.games.time.sleep", pausas.append)
    respx.get("https://remotegamejobs.com/feed.rss").mock(return_value=httpx.Response(200, text=RSS))
    respx.get("https://remotegamejobs.com/jobs/a-unity-dev").mock(return_value=httpx.Response(200, text=JOBPOSTING))
    assert SiteGames("gamesindustry").pausa_s == 10.0
    SiteGames("remotegamejobs").buscar(["unity"], 10)
    assert pausas == [QUADROS["remotegamejobs"].pausa_s]


def test_estudios_tem_slugs():
    assert "wildlifestudios" in ESTUDIOS["greenhouse"] and ESTUDIOS["ashby"]
