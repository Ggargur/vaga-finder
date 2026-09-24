from vaga_finder.slop_lint import verificar


def mensagens(texto, **kw):
    return [a.mensagem for a in verificar(texto, **kw)]


def test_texto_limpo():
    assert mensagens("Olá, equipe da Acme. Vi a vaga de Dev Python no Gupy e desenvolvi APIs em Django por 4 anos.") == []


def test_travessao_e_cliches_pt():
    m = mensagens("Sou apaixonado por tecnologia — e quero agregar valor ao time.")
    assert any("Travessão" in x for x in m)
    assert any("sou apaixonado por" in x for x in m)
    assert any("agregar valor" in x for x in m)


def test_frases_em_ingles_e_contraste():
    m = mensagens("Here's the thing: I really want this role. It's not about money, it's about growth.")
    assert any("Here's the thing" in x for x in m)
    assert any("really" in x for x in m)
    assert any("Not X, it's Y" in x for x in m)


def test_sem_falso_positivo_para_period():
    assert mensagens("I finished the probation period in 2021.") == []


def test_tamanho():
    assert any("curto" in x for x in mensagens("Oi.", palavras_min=120, palavras_max=180))
