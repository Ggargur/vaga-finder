import httpx
import respx

from vaga_finder.fontes.gupy import URL as URL_GUPY
from vaga_finder.fontes.gupy import Gupy, empresa_da_url
from vaga_finder.fontes.remotive import URL as URL_REMOTIVE
from vaga_finder.fontes.remotive import Remotive

from .conftest import carregar_fixture


@respx.mock
def test_remotive():
    respx.get(URL_REMOTIVE).mock(return_value=httpx.Response(200, json=carregar_fixture("remotive.json")))
    vagas = Remotive().buscar(["python"], 10)
    assert len(vagas) == 3
    v = vagas[1]
    assert v.fonte == "remotive" and v.titulo == "Frontend Web Application Developer"
    assert v.empresa and v.url.startswith("https://remotive.com/")
    assert v.remoto is True
    assert "<" not in v.descricao[:200]


@respx.mock
def test_remotive_dedup_entre_termos():
    respx.get(URL_REMOTIVE).mock(return_value=httpx.Response(200, json=carregar_fixture("remotive.json")))
    assert len(Remotive().buscar(["python", "django"], 10)) == 3


@respx.mock
def test_gupy_pagina_e_converte():
    dados = carregar_fixture("gupy.json")
    dados["pagination"]["total"] = 2
    rota = respx.get(URL_GUPY).mock(return_value=httpx.Response(200, json=dados))
    vagas = Gupy().buscar(["python"], 50)
    assert rota.call_count == 1
    assert len(vagas) == 2
    v = vagas[0]
    assert v.fonte == "gupy" and v.id_fonte == "12587229"
    assert v.empresa == "Fcamara"
    assert v.local == "Belo Horizonte, Minas Gerais" and v.remoto is False


def test_empresa_da_url():
    assert empresa_da_url("https://minha-empresa.gupy.io/job/abc") == "Minha Empresa"
    assert empresa_da_url("https://exemplo.com/x") == ""
