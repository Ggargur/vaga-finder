from vaga_finder.texto import consertar_mojibake, html_para_texto, impressao_vaga, normalizar


def test_normalizar_remove_acentos_e_pontuacao():
    assert normalizar("Desenvolvedor(a) Sênior — Python!") == "desenvolvedor a senior python"


def test_impressao_igual_para_mesma_vaga_em_fontes_diferentes():
    a = impressao_vaga("Acme Ltda.", "Desenvolvedor Python Sênior (Remoto)")
    b = impressao_vaga("ACME", "Desenvolvedor Python Senior - Remote")
    assert a == b


def test_impressao_diferente_para_vagas_diferentes():
    assert impressao_vaga("Acme", "Dev Python") != impressao_vaga("Acme", "Dev Java")
    assert impressao_vaga("Acme", "Dev Python") != impressao_vaga("Outra", "Dev Python")


def test_html_para_texto_quebra_paragrafos_e_remove_tags():
    texto = html_para_texto("<p>Olá</p><ul><li>Python</li><li>SQL</li></ul><script>x()</script>")
    assert "Olá" in texto and "Python\n" in texto and "x()" not in texto and "<" not in texto


def test_html_para_texto_aceita_html_escapado():
    assert html_para_texto("&lt;p&gt;Oi&lt;/p&gt;") == "Oi"


def test_consertar_mojibake():
    assert consertar_mojibake("weâ\x80\x99re") == "we’re"
    assert consertar_mojibake("texto normal çã") == "texto normal çã"
