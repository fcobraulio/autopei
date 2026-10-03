"""Respostas fictícias (mas realistas) usadas para popular o banco de desenvolvimento.

Cada perfil de NEE (coluna ``perfil_nee`` de dev/estudantes.csv) tem respostas para a
Psicopedagogia, a ETEP e os docentes. ``NADA`` marca a resposta como “Nada a declarar”.
Nos textos, {nome} é o primeiro nome do(a) estudante e {disc} o nome da disciplina.
TODOS OS DADOS SÃO FICTÍCIOS.
"""
from __future__ import annotations

NADA = object()

TEA = "Transtorno do Espectro Autista (TEA)"
TDAH = "Transtorno de Déficit de Atenção e Hiperatividade (TDAH)"
TAG = "Transtorno de Ansiedade Generalizada (TAG)"

PERFIS: dict[str, dict] = {
    "tea": dict(
        psico={
            "Necessidades educacionais": [TEA],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Laudo neurológico (CID 11: 6A02.0) emitido em 2023 por neuropediatra do CER "
                           "de Currais Novos; relatório de terapia ocupacional de 2025.",
            "Acompanhamentos especializados": ["Psicologia", "Terapia ocupacional"],
            "Aspectos cognitivos": "{nome} tem bom raciocínio lógico e memória para detalhes. Compreende melhor "
                                   "instruções objetivas e por escrito; enunciados longos ou com linguagem figurada "
                                   "geram dúvidas. Precisa de mais tempo para organizar a escrita de textos abertos.",
            "Aspectos emocionais": "Mudanças repentinas de rotina (troca de sala, aula vaga, avaliação surpresa) "
                                   "geram ansiedade e retraimento. Responde bem a antecipação das atividades.",
            "Comunicação e interação": "Interage com um grupo pequeno de colegas. Evita trabalhos em grupos grandes "
                                       "e tem dificuldade em interpretar ironias. Comunica-se melhor por escrito.",
            "Aspectos sensoriais": "Sensibilidade a ruídos intensos (sinal sonoro, conversas paralelas). "
                                   "Usa abafador de ruído em alguns momentos.",
            "Recomendações psicopedagógicas": "Antecipar a rotina e as mudanças; fornecer instruções por escrito e "
                                              "em etapas; permitir pausas curtas fora da sala; avaliar em ambiente "
                                              "mais silencioso quando possível; mediar a formação de grupos.",
        },
        etep={
            "Histórico escolar": "Ingressou com PEI do ensino fundamental. Foi acompanhado(a) pelo NAPNE desde a "
                                 "matrícula, com reunião com a família no início do período.",
            "Conhecimentos, habilidades": "Interesse por tecnologia, jogos e programação. Organizado(a) com "
                                          "materiais e prazos quando as tarefas são bem definidas.",
            "Dificuldades apresentadas": "Interpretação de enunciados longos, produção de textos dissertativos e "
                                         "trabalhos em grupo sem papéis definidos.",
            "Apoios e recursos": ["Tempo adicional em avaliações", "Avaliação em ambiente separado",
                                  "Material impresso"],
            "Participação da família": "Participativa",
            "Estratégias pedagógicas": "Disponibilizar o roteiro da aula no início; dividir tarefas em etapas; "
                                       "definir papéis nos trabalhos em grupo; avisar com antecedência sobre "
                                       "avaliações e mudanças.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Roteiro da aula disponibilizado no início; exercícios divididos em etapas com "
                            "checagem individual. Em atividades em grupo, {nome} recebe papel definido.",
            recursos_adapt="Listas e enunciados impressos, com instruções objetivas.",
            avaliacao_adapt="Tempo adicional de 30 minutos e possibilidade de realizar a prova em sala separada. "
                            "Enunciados reescritos sem linguagem figurada.",
            relacao="Boa",
            comportamento="Participa quando solicitado(a) diretamente; prefere sentar-se nas primeiras fileiras, "
                          "longe da porta. Fica desconfortável com barulho excessivo.",
            parecer="{nome} acompanha bem os conteúdos de {disc}, com bom desempenho nas atividades práticas. "
                    "As adaptações nas avaliações e a antecipação da rotina têm sido suficientes.",
        ),
    ),
    "tea_ah": dict(
        psico={
            "Necessidades educacionais": [TEA, "Altas habilidades / Superdotação"],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Laudo de neuropsicologia (2024) indicando TEA nível 1 e altas habilidades na área "
                           "lógico-matemática (avaliação com WISC-IV).",
            "Acompanhamentos especializados": ["Psicologia", "Neurologia"],
            "Aspectos cognitivos": "{nome} resolve problemas lógicos e matemáticos muito acima do esperado para a "
                                   "idade e aprende rapidamente de forma autônoma. Desinteressa-se por atividades "
                                   "repetitivas.",
            "Aspectos emocionais": "Frustra-se quando precisa repetir exercícios que já domina; pode se isolar.",
            "Comunicação e interação": "Conversa com facilidade sobre seus temas de interesse, mas tem dificuldade "
                                       "de manter diálogo sobre outros assuntos e de trabalhar em grupo.",
            "Aspectos sensoriais": NADA,
            "Recomendações psicopedagógicas": "Oferecer atividades de aprofundamento e desafios (olimpíadas, "
                                              "projetos); evitar repetição de exercícios já dominados; mediar "
                                              "interação em grupos pequenos.",
        },
        etep={
            "Histórico escolar": "Medalhista na OBMEP no ensino fundamental. Acompanhado(a) pelo NAPNE desde 2026.1.",
            "Conhecimentos, habilidades": "Programação, matemática, xadrez e robótica.",
            "Dificuldades apresentadas": "Produção de textos em Língua Portuguesa e trabalhos em grupo.",
            "Apoios e recursos": ["Atendimento individualizado (Centro de Aprendizagem)", "Monitoria"],
            "Participação da família": "Participativa",
            "Estratégias pedagógicas": "Enriquecimento curricular com atividades desafiadoras; possibilidade de "
                                       "atuar como monitor(a) em programação; definir papéis em atividades em grupo.",
            "Observações gerais": "Indicado(a) para o programa de olimpíadas científicas do campus.",
        },
        docente=dict(
            adapta_obj=True,
            objetivos_adapt="Inclusão de objetivos de aprofundamento em {disc}, com desafios adicionais.",
            conteudo="Conteúdos complementares de aprofundamento (problemas de olimpíada e desafios de "
                     "programação).",
            metodologia_esp="Listas de desafios extras e atuação como monitor(a) em atividades práticas.",
            recursos_adapt=NADA,
            avaliacao_adapt=NADA,
            relacao="Boa",
            comportamento="Muito participativo(a) nas aulas práticas; dispersa-se em exercícios repetitivos.",
            parecer="{nome} apresenta desempenho excelente em {disc}. O enriquecimento curricular tem mantido "
                    "o interesse e a participação.",
        ),
    ),
    "tdah": dict(
        psico={
            "Necessidades educacionais": [TDAH],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Relatório psiquiátrico (2025), CID 11: 6A05.2, com indicação de acompanhamento "
                           "psicológico.",
            "Acompanhamentos especializados": ["Psiquiatria", "Psicologia"],
            "Aspectos cognitivos": "{nome} compreende bem os conteúdos, mas perde o foco em explicações longas e "
                                   "comete erros por desatenção. Esquece prazos sem lembretes.",
            "Aspectos emocionais": "Inquietação motora e impulsividade; frustra-se com notas baixas por erros "
                                   "de atenção.",
            "Comunicação e interação": NADA,
            "Aspectos sensoriais": NADA,
            "Recomendações psicopedagógicas": "Sentar próximo ao professor e longe de janelas; dividir atividades "
                                              "em blocos curtos; usar agenda/lembretes; permitir pequenas pausas.",
        },
        etep={
            "Histórico escolar": "Acompanhado(a) pelo NAPNE desde o ingresso. Em 2026.1 teve dificuldades com a "
                                 "entrega de atividades no prazo.",
            "Conhecimentos, habilidades": "Gosta de atividades práticas, esportes e desenho.",
            "Dificuldades apresentadas": "Organização dos estudos, cumprimento de prazos e atenção em aulas expositivas.",
            "Apoios e recursos": ["Tempo adicional em avaliações", "Monitoria"],
            "Participação da família": "Parcialmente participativa",
            "Estratégias pedagógicas": "Atividades curtas e variadas; prazos lembrados no ambiente virtual; "
                                       "checagem do caderno ao fim da aula.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Explicações em blocos curtos intercalados com exercícios; lembretes de prazos no "
                            "ambiente virtual.",
            recursos_adapt=NADA,
            avaliacao_adapt="Tempo adicional de 30 minutos e prova dividida em duas partes, com pausa.",
            relacao="Boa",
            comportamento="Participativo(a), mas se dispersa com facilidade; melhora quando senta na frente.",
            parecer="{nome} tem bom entendimento de {disc}, mas perde pontos por desatenção. Os lembretes e a "
                    "divisão das atividades têm ajudado.",
        ),
    ),
    "tag_tdah": dict(
        psico={
            "Necessidades educacionais": [TAG, TDAH],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Laudo psiquiátrico (2025): CID 11: 6B00 e 6A05.0.",
            "Acompanhamentos especializados": ["Psicologia", "Psiquiatria"],
            "Aspectos cognitivos": "Bom potencial de aprendizagem. A ansiedade em avaliações prejudica o desempenho; "
                                   "esquece o que estudou durante as provas.",
            "Aspectos emocionais": "Crises de ansiedade em períodos de avaliação, com choro e pedidos para sair da "
                                   "sala. Autocobrança elevada.",
            "Comunicação e interação": "Tímido(a) para apresentações orais; interage bem em duplas.",
            "Aspectos sensoriais": NADA,
            "Recomendações psicopedagógicas": "Calendário de avaliações divulgado com antecedência; possibilidade de "
                                              "sair da sala por alguns minutos; substituir apresentação oral para a "
                                              "turma por apresentação ao professor, quando necessário.",
        },
        etep={
            "Histórico escolar": "Teve PEI em 2026.1. Encaminhado(a) ao serviço de Psicologia do campus.",
            "Conhecimentos, habilidades": "Desenho digital e leitura; muito caprichoso(a) nos trabalhos escritos.",
            "Dificuldades apresentadas": "Avaliações com tempo restrito e apresentações orais.",
            "Apoios e recursos": ["Tempo adicional em avaliações", "Avaliação em ambiente separado",
                                  "Atendimento individualizado (Centro de Aprendizagem)"],
            "Participação da família": "Participativa",
            "Estratégias pedagógicas": "Antecipar o calendário de avaliações; dividir a nota em mais instrumentos; "
                                       "permitir apresentação em dupla ou só para o professor.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Atendimento individualizado semanal para revisão antes das avaliações.",
            recursos_adapt=NADA,
            avaliacao_adapt="Avaliação em sala separada, com tempo adicional; nota dividida em mais instrumentos.",
            relacao="Boa",
            comportamento="Dedicado(a) e atento(a); fica muito ansioso(a) em semanas de prova.",
            parecer="{nome} domina os conteúdos de {disc} nas atividades práticas. O desempenho nas provas melhorou "
                    "com a avaliação em sala separada.",
        ),
    ),
    "dislexia": dict(
        psico={
            "Necessidades educacionais": ["Dislexia"],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Avaliação fonoaudiológica e neuropsicológica (2024), CID 11: 6A03.0.",
            "Acompanhamentos especializados": ["Fonoaudiologia", "Psicopedagogia clínica"],
            "Aspectos cognitivos": "Leitura lenta e com trocas de letras; compreensão melhora muito quando o texto é "
                                   "lido em voz alta. Raciocínio e oralidade preservados.",
            "Aspectos emocionais": "Constrangimento em ler em voz alta para a turma.",
            "Comunicação e interação": NADA,
            "Aspectos sensoriais": NADA,
            "Recomendações psicopedagógicas": "Não solicitar leitura em voz alta para a turma; fonte ampliada e sem "
                                              "serifa; ledor em avaliações; valorizar respostas orais.",
        },
        etep={
            "Histórico escolar": "Ingressou em 2025 com laudo; acompanhada(o) pelo NAPNE desde então.",
            "Conhecimentos, habilidades": "Ótima oralidade e participação em debates; interesse por culinária.",
            "Dificuldades apresentadas": "Leitura de textos longos e escrita sob pressão de tempo.",
            "Apoios e recursos": ["Ledor / Transcritor", "Tempo adicional em avaliações", "Material ampliado"],
            "Participação da família": "Participativa",
            "Estratégias pedagógicas": "Materiais com fonte ampliada (Arial 14); textos curtos; avaliações com ledor "
                                       "e tempo adicional; considerar a oralidade na avaliação.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Leitura compartilhada dos textos-base e resumos esquemáticos.",
            recursos_adapt="Material com fonte ampliada e sem serifa.",
            avaliacao_adapt="Prova com ledor e 30 minutos adicionais; erros ortográficos não penalizados.",
            relacao="Boa",
            comportamento="Participativa(o) nas discussões orais; evita ler em voz alta.",
            parecer="{nome} demonstra compreensão dos conteúdos de {disc} quando as questões são lidas. "
                    "O ledor nas avaliações tem sido fundamental.",
        ),
    ),
    "baixa_visao": dict(
        psico={
            "Necessidades educacionais": ["Deficiência visual (baixa visão)"],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Laudo oftalmológico (2024): baixa visão bilateral, CID 11: 9D44; acuidade 20/200 "
                           "no melhor olho com correção.",
            "Acompanhamentos especializados": ["Nenhum"],
            "Aspectos cognitivos": NADA,
            "Aspectos emocionais": NADA,
            "Comunicação e interação": NADA,
            "Aspectos sensoriais": "Necessita de ampliação de textos e telas (fonte mínima 24) e de alto contraste. "
                                   "Não enxerga o quadro a partir da terceira fileira.",
            "Recomendações psicopedagógicas": "Material ampliado; ampliador de tela e alto contraste nos computadores; "
                                              "sentar na primeira fileira; descrever verbalmente o que é escrito no quadro.",
        },
        etep={
            "Histórico escolar": "Estudante do superior, ingressou em 2024 pelo sistema de cotas para PcD.",
            "Conhecimentos, habilidades": "Muito bom(boa) em lógica e programação back-end.",
            "Dificuldades apresentadas": "Leitura de diagramas pequenos, slides projetados e material impresso padrão.",
            "Apoios e recursos": ["Material ampliado", "Tecnologia assistiva", "Tempo adicional em avaliações"],
            "Participação da família": "Não se aplica (estudante maior de idade)",
            "Estratégias pedagógicas": "Enviar slides com antecedência; usar ampliador de tela (lupa do sistema); "
                                       "provas ampliadas ou digitais com alto contraste.",
            "Observações gerais": "Solicitado monitor de 27 polegadas ao setor de TI do campus.",
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Slides e códigos enviados com antecedência; descrição verbal do que é escrito no quadro.",
            recursos_adapt="Computador com ampliador de tela e tema de alto contraste.",
            avaliacao_adapt="Prova digital com fonte ampliada e 30 minutos adicionais.",
            relacao="Boa",
            comportamento="Muito participativo(a); senta na primeira fileira.",
            parecer="{nome} acompanha {disc} com bom desempenho, desde que o material esteja ampliado e "
                    "disponibilizado antes da aula.",
        ),
    ),
    "auditiva": dict(
        psico={
            "Necessidades educacionais": ["Deficiência auditiva / Surdez"],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Audiometria (2025): perda auditiva neurossensorial moderada bilateral, CID 11: AB51. "
                           "Usuário(a) de AASI (aparelho auditivo) bilateral.",
            "Acompanhamentos especializados": ["Fonoaudiologia"],
            "Aspectos cognitivos": NADA,
            "Aspectos emocionais": "Retrai-se quando não compreende e evita pedir que repitam.",
            "Comunicação e interação": "Oralizado(a) e faz leitura labial; não usa Libras fluentemente.",
            "Aspectos sensoriais": "Dificuldade de compreensão em ambientes ruidosos e quando o professor fala de costas.",
            "Recomendações psicopedagógicas": "Falar de frente para a turma; sentar na primeira fileira; vídeos com "
                                              "legenda; avisos importantes também por escrito.",
        },
        etep={
            "Histórico escolar": "Acompanhado(a) pelo NAPNE desde 2025.",
            "Conhecimentos, habilidades": "Atividades de laboratório e desenho.",
            "Dificuldades apresentadas": "Compreensão de explicações orais longas e de aulas em ambientes ruidosos.",
            "Apoios e recursos": ["Material impresso", "Tecnologia assistiva"],
            "Participação da família": "Participativa",
            "Estratégias pedagógicas": "Falar de frente; usar legendas; registrar instruções no quadro e no "
                                       "ambiente virtual.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Instruções registradas no quadro e no ambiente virtual; explicações de frente para a turma.",
            recursos_adapt="Vídeos com legenda.",
            avaliacao_adapt="Instruções da prova por escrito.",
            relacao="Boa",
            comportamento="Atento(a) e participativo(a) quando está na primeira fileira.",
            parecer="{nome} tem bom desempenho em {disc} com as instruções por escrito.",
        ),
    ),
    "di": dict(
        psico={
            "Necessidades educacionais": ["Deficiência intelectual"],
            "Situação da documentação": "Possui laudo",
            "Laudos, CID": "Laudo neurológico (2022): deficiência intelectual leve, CID 11: 6A00.0.",
            "Acompanhamentos especializados": ["Psicopedagogia clínica", "Terapia ocupacional"],
            "Aspectos cognitivos": "{nome} aprende melhor com exemplos concretos e repetição. Tem dificuldade com "
                                   "conceitos abstratos, cálculos com várias etapas e textos longos.",
            "Aspectos emocionais": "Desmotiva-se quando não acompanha a turma; responde bem a elogios e metas curtas.",
            "Comunicação e interação": "Boa interação com os colegas; pede ajuda com facilidade a quem conhece.",
            "Aspectos sensoriais": NADA,
            "Recomendações psicopedagógicas": "Flexibilizar objetivos e conteúdos, priorizando os essenciais; "
                                              "atividades com exemplos concretos; avaliações adaptadas e mais curtas.",
        },
        etep={
            "Histórico escolar": "Ingressou em 2025 com PEI da escola anterior. Ficou em dependência em Matemática I.",
            "Conhecimentos, habilidades": "Atividades práticas de laboratório e cozinha experimental.",
            "Dificuldades apresentadas": "Cálculos, leitura de textos técnicos e conceitos abstratos.",
            "Apoios e recursos": ["Atendimento individualizado (Centro de Aprendizagem)", "Monitoria",
                                  "Tempo adicional em avaliações"],
            "Participação da família": "Participativa",
            "Estratégias pedagógicas": "Priorizar conteúdos essenciais; usar exemplos concretos e práticos; "
                                       "avaliações curtas e frequentes.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=True,
            objetivos_adapt="Objetivos de {disc} flexibilizados, priorizando os conceitos essenciais e a aplicação prática.",
            conteudo="Conteúdos essenciais priorizados, com menos itens por unidade.",
            metodologia_esp="Atividades práticas com exemplos concretos e atendimento individualizado semanal.",
            recursos_adapt="Roteiros de estudo com imagens e passo a passo.",
            avaliacao_adapt="Avaliações mais curtas, com questões objetivas e consulta a roteiro; tempo adicional.",
            relacao="Boa",
            comportamento="Esforçado(a) e participativo(a) nas práticas; precisa de retomadas frequentes.",
            parecer="{nome} evoluiu em {disc} com os objetivos flexibilizados e o atendimento individualizado.",
        ),
    ),
    "discalculia": dict(
        psico={
            "Necessidades educacionais": ["Discalculia"],
            "Situação da documentação": "Em investigação diagnóstica",
            "Laudos, CID": NADA,
            "Acompanhamentos especializados": ["Psicopedagogia clínica"],
            "Aspectos cognitivos": "Dificuldade persistente com operações, frações e manipulação de números; "
                                   "leitura e escrita adequadas.",
            "Aspectos emocionais": "Ansiedade diante de atividades com cálculo.",
            "Comunicação e interação": NADA,
            "Aspectos sensoriais": NADA,
            "Recomendações psicopedagógicas": "Permitir calculadora; foco no raciocínio e não no cálculo mecânico; "
                                              "formulários de apoio nas avaliações.",
        },
        etep={
            "Histórico escolar": "Encaminhada(o) ao NAPNE em 2025.2 pela coordenação do curso.",
            "Conhecimentos, habilidades": "Design de interfaces e escrita.",
            "Dificuldades apresentadas": "Disciplinas com cálculo e lógica numérica.",
            "Apoios e recursos": ["Tempo adicional em avaliações", "Monitoria"],
            "Participação da família": "Não se aplica (estudante maior de idade)",
            "Estratégias pedagógicas": "Uso de calculadora; formulário de apoio; exemplos visuais.",
            "Observações gerais": NADA,
        },
        docente=dict(
            adapta_obj=False,
            conteudo=NADA,
            metodologia_esp="Exemplos visuais e uso de planilhas para os cálculos.",
            recursos_adapt="Calculadora e formulário de apoio permitidos.",
            avaliacao_adapt="Calculadora permitida e 20 minutos adicionais.",
            relacao="Boa",
            comportamento="Participativa(o) e organizada(o).",
            parecer="{nome} acompanha {disc} com bom desempenho com o uso de calculadora e formulário de apoio.",
        ),
    ),
}

METODOLOGIAS = ["Aulas expositivas dialogadas", "Exercícios práticos", "Aulas em laboratório"]
RECURSOS = ["Quadro branco", "Computador", "Projetor multimídia", "Ambiente virtual (Moodle/Classroom)"]
AVALIACOES = ["Prova escrita", "Listas de exercícios", "Projetos"]

REGISTRO_GESTAO = ("Reunião de acompanhamento com a família e o(a) estudante no início do período; "
                   "os docentes foram orientados sobre as adaptações recomendadas.")
PARECER_GESTAO = ("A equipe multiprofissional ratifica as adaptações registradas e recomenda a continuidade do "
                  "acompanhamento pelo NAPNE no próximo período.")


def valor_psico_etep(perfil: str, etapa: str, enunciado: str, nome: str):
    for chave, v in PERFIS[perfil]["psico" if etapa == "psicopedagogia" else etapa].items():
        if enunciado.startswith(chave):
            return v.format(nome=nome) if isinstance(v, str) else v
    return NADA


def valor_docente(perfil: str, enunciado: str, nome: str, disc: str, objetivos: str, conteudos: str):
    d = PERFIS[perfil]["docente"]

    def f(v):
        return v.format(nome=nome, disc=disc) if isinstance(v, str) else v

    mapa = {
        "Objetivos do componente": objetivos,
        "Os objetivos precisaram": "Sim" if d["adapta_obj"] else "Não",
        "Adaptações realizadas nos objetivos": f(d.get("objetivos_adapt", NADA)),
        "Conteúdos programáticos": conteudos,
        "Adaptações realizadas nos conteúdos": f(d["conteudo"]),
        "Estratégias metodológicas": METODOLOGIAS,
        "Metodologias específicas": f(d["metodologia_esp"]),
        "Recursos didáticos comumente": RECURSOS,
        "Adaptações nos recursos": f(d["recursos_adapt"]),
        "Instrumentos de avaliação": AVALIACOES,
        "Adaptações nas avaliações": f(d["avaliacao_adapt"]),
        "Relação com colegas": d["relacao"],
        "Comportamento, participação": f(d["comportamento"]),
        "Parecer: trajetória": f(d["parecer"]),
        "Situação atual": "Em andamento",
    }
    for chave, v in mapa.items():
        if enunciado.startswith(chave):
            return v
    return NADA
