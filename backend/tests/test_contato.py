from vaga_finder.contato import extrair_emails


def test_extrai_email_publicado():
    assert extrair_emails("Envie o CV para vagas@acme.com.br até sexta.") == ["vagas@acme.com.br"]


def test_ignora_noreply_privacidade_e_imagens():
    texto = "no-reply@acme.com privacidade@acme.com logo@2x.png dpo@acme.com contato@example.com"
    assert extrair_emails(texto) == []


def test_email_ofuscado():
    assert extrair_emails("Contato: joao [at] acme [dot] io") == ["joao@acme.io"]


def test_recrutamento_vem_primeiro_e_sem_duplicatas():
    texto = "Dúvidas: joao@acme.com. Currículos: RH@acme.com ou rh@acme.com."
    assert extrair_emails(texto) == ["rh@acme.com", "joao@acme.com"]


def test_sem_email():
    assert extrair_emails("Aplique pelo formulário.") == []
    assert extrair_emails("") == []


def test_email_colado_na_proxima_frase():
    texto = "pelo e-mail: recrutamento@cardway.com.brNosso compromisso"
    assert extrair_emails(texto) == ["recrutamento@cardway.com.br"]
    assert extrair_emails("vagas@acme.comEnvie até sexta") == ["vagas@acme.com"]
