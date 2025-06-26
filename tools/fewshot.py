import uuid
from typing import Dict, List, Tuple, TypedDict
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from pydantic import BaseModel
from .schema import (
    Decisao,
    MultaFixa,
    MultaPercentual,
    Recomendacao,
    Ressarcimento,
    Obrigacao,
    ObrigacaoMulta
)


exemplo_1 = '''
DECIDEM os Conselheiros do Tribunal de Contas do Estado, à unanimidade, em consonância com a informação do Corpo Técnico e com o parecer do Ministério Público que atua junto a esta Corte de Contas, acolhendo integralmente o voto do Conselheiro Relator, julgar: a) pela DENEGAÇÃO DE REGISTRO ao ato concessivo da aposentadoria e à despesa dele decorrente; b) pela determinação ao IPERN, à vista da Lei Complementar Estadual nº 547/2015, para que, no prazo de 60 (sessenta) dias, após o trânsito em julgado desta decisão, adote as correções necessárias para regularização do ato concessório, do cálculo dos proventos e de sua respectiva implantação; c) no caso de descumprimento da presente decisão, a responsabilização do titular da pasta responsável por seu atendimento, sem prejuízo da multa cominatória desde já fixada no valor de R$ 50,00 (cinquenta reais) por dia que superar o interregno fixado no item `b`, com base no art. 110 da Lei Complementar Estadual nº 464/2012, valor este passível de revisão e limitado ao teto previsto no art. 323, inciso II, alínea `f`, do Regimento Interno, a ser apurado por ocasião de eventual subsistência de mora.
'''
label_1 = Decisao(
    multas_fixas=[],
    multas_percentuais=[],
    ressarcimentos=[],
    obrigacoes=[],
    recomendacoes=[],
    obrigacoes_multa=[
        ObrigacaoMulta(
            descricao_obrigacaomulta="determinação ao IPERN, à vista da Lei Complementar Estadual nº 547/2015, para que, no prazo de 60 (sessenta) dias, após o trânsito em julgado desta decisão, adote as correções necessárias para regularização do ato concessório, do cálculo dos proventos e de sua respectiva implantação; c) no caso de descumprimento da presente decisão, a responsabilização do titular da pasta responsável por seu atendimento, sem prejuízo da multa cominatória desde já fixada no valor de R$ 50,00 (cinquenta reais) por dia que superar o interregno fixado no item `b`, com base no art. 110 da Lei Complementar Estadual nº 464/2012, valor este passível de revisão e limitado ao teto previsto no art. 323, inciso II, alínea `f`, do Regimento Interno, a ser apurado por ocasião de eventual subsistência de mora.",
            valor_obrigacaomulta=50.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="titular da pasta responsável por seu atendimento",
            orgao_responsavel_obrigacaomulta="IPERN"
        )
    ]
)

exemplo_2 = '''
Vistos, relatados e discutidos estes autos da aposentadoria voluntária, por tempo de contribuição, com proventos proporcionais, concedida à servidora Francisca Lima da Silva, no cargo de Auxiliar de Serviços Gerais, do quadro de pessoal do Município de Alexandria,  considerando a manifestação emitida pelo Corpo Técnico e do parecer do Ministério Público junto a esta Corte, ACORDAM os Conselheiros,  nos termos do voto proferido pelo Conselheiro Relator, julgar pela DENEGAÇÃO do registro do ato concessivo de aposentadoria em foco,  nos termos do artigo 53, inciso III, da Constituição Estadual e do artigo 1º, inciso III, da Lei Complementar nº 464/2012, visto que as  irregularidades suscitadas no bojo do processo não foram sanadas; com APLICAÇÃO DE MULTA no valor de R$600,00 (seiscentos reais) ao gestor responsável  pelo Instituto de Previdência do Município de Alexandria - IPAMA, à época dos fatos, o senhor Francisco Marcolino Neto, nos termos do art. 107,  inciso II, alínea f, da Lei Complementar Estadual nº 464/12, pelo descumprimento de determinação do Tribunal (Decisão nº 2849/2012-TC);  pela INTIMAÇÃO da referida autoridade competente, a fim de que tome conhecimento desta Decisão e, se for o caso, apresentem recurso no  prazo regimental; e ainda, pela RENOVAÇÃO DA DETERMINAÇÃO constante na decisão retro, estipulando o prazo de 60 (sessenta) dias, para  que o IPAMA, no seu atual gestor, regularize a situação noticiada nos autos, sob pena de sanção prevista no artigo 101, parágrafo único,   c/c artigo 110, da Lei Complementar Estadual nº 464/2012.
'''
label_2 = Decisao(
    multas_fixas=[
        MultaFixa(
            descricao_multafixa="MULTA no valor de R$600,00 (seiscentos reais) ao gestor responsável pelo Instituto de Previdência do Município de Alexandria - IPAMA, à época dos fatos, o senhor Francisco Marcolino Neto, nos termos do art. 107, inciso II, alínea f, da Lei Complementar Estadual nº 464/12, pelo descumprimento de determinação do Tribunal (Decisão nº 2849/2012-TC);",
            valor_multafixa=600.0,
            nome_responsavel_multafixa="Francisco Marcolino Neto",
        )
    ],
    multas_percentuais=[],
    ressarcimentos=[],
    obrigacoes=[],
    recomendacoes=[],
    obrigacoes_multa=[]
)

exemplo_3 = '''
Vistos, relatados e discutidos estes autos da Representação formulada pela Diretoria de Despesa com Pessoal, solicitando a adoção de medidas cautelares, em desfavor da Câmara Municipal de Monte Alegre/RN, concernente à remuneração de agentes políticos, considerando em parte a manifestação emitida pelo Corpo Técnico e do parecer do Ministério Público junto a esta Corte, ACORDAM os Conselheiros, nos termos do voto proferido pelo Conselheiro Relator, julgar: a)pela perda parcial do Objeto da Representação, em virtude da revogação da norma municipal ofensiva ao art. 29 da CF;)irregularidade da matéria afeta à Gestão do Ex-Presidente da Câmara de Vereadores, Sr. Giodano Bruno de Castro Galvão, na forma do art. 75, II da Lei Complementar n°464/2012; c)aplicação de multa ao Sr. Giodano Bruno de Castro Galvão pelas infrações legais detalhadas na fundamentação, com fulcro no art. 107, II, “b”, da LCE 464/12; c/c art. 323, II, “b” e §4º do mesmo artigo da Res. 009/2012-TCE, com base no valor mínimo de 30% sobre o valor máximo, atualizado pela Portaria 104/2017-GP/TCE, de 14/02/2017, o que importa na quantia de R$4.172,49 (quatro mil, cento e setenta e dois reais e quarenta e nove centavos); e d) expedição de recomendação para a atual Gestão da Câmara Municipal de Monte Alegre para que adote as providências necessárias ao cumprimento das exigências previstas nos arts. 16, 17 e 21 da Lei de Responsabilidade Fiscal, inclusive com o reconhecimento da nulidade do aumento concedido caso se comprove a sua incompatibilidade com as exigências legais e com os limites constitucionais.
'''
label_3 = Decisao(
    multas_fixas=[],
    multas_percentuais=[
        MultaPercentual(
            descricao_multapercentual="multa ao Sr. Giodano Bruno de Castro Galvão pelas infrações legais detalhadas na fundamentação, com fulcro no art. 107, II, “b”, da LCE 464/12; c/c art. 323, II, “b” e §4º do mesmo artigo da Res. 009/2012-TCE, com base no valor mínimo de 30% sobre o valor máximo, atualizado pela Portaria 104/2017-GP/TCE, de 14/02/2017, o que importa na quantia de R$4.172,49 (quatro mil, cento e setenta e dois reais e quarenta e nove centavos)",
            percentual_multapercentual=30.0,
            base_calculo_multapercentual=4172.49,
            nome_responsavel_multapercentual="Giodano Bruno de Castro Galvão",
        )],
    recomendacoes=[
        Recomendacao(
            descricao_recomendacao="recomendação para a atual Gestão da Câmara Municipal de Monte Alegre para que adote as providências necessárias ao cumprimento das exigências previstas nos arts. 16, 17 e 21 da Lei de Responsabilidade Fiscal, inclusive com o reconhecimento da nulidade do aumento concedido caso se comprove a sua incompatibilidade com as exigências legais e com os limites constitucionais.",
            prazo_cumprimento_recomendacao="",
            nome_responsavel_recomendacao="atual Gestão da Câmara Municipal de Monte Alegre",
            orgao_responsavel_recomendacao="Câmara Municipal de Monte Alegre"
        )
    ],
    obrigacoes=[],
    ressarcimentos=[],
    obrigacoes_multa=[]
)

exemplo_4 = '''
Vistos, relatados e discutidos estes autos da análise de documentação e balancetes do FUNDEF referente aos meses de janeiro a dezembro de 1998 da Prefeitura Municipal de Tangará/RN, considerando parcialmente a manifestação emitida pelo Corpo Técnico, (discordando deste com relação ao remanejamento, ante a prescrição) e integralmente o parecer do Ministério Público junto a esta Corte, ACORDAM os Conselheiros, nos termos do voto proferido pelo Conselheiro Relator, julgar: a) pela irregularidade da matéria, nos termos do artigo 78, incisos II e IV da Lei Complementar nº121/94, b) pela condenação do gestor responsável, Senhor Giovannu César Pinheiro e Alves, ao ressarcimento da quantia R$ 6.583,99 (seis mil, quinhentos e oitenta e três reais e noventa e nove centavos) referente ao pagamento de encargos moratórios gerados por juros e multa do FGTS e INSS, c) pelo reconhecimento da prescrição decenária da pretensão punitiva no que tange ao remanejamento e aplicação de multa, como matéria de ordem pública e prejudicial de mérito, nos termos do art. 170, caput, da Lei Complementar nº 464/2012.
'''
label_4 = Decisao(
    multas_fixas=[],
    multas_percentuais=[],
    ressarcimentos=[
        Ressarcimento(
            descricao_ressarcimento="Giovannu César Pinheiro e Alves, ao ressarcimento da quantia R$ 6.583,99 (seis mil, quinhentos e oitenta e três reais e noventa e nove centavos) referente ao pagamento de encargos moratórios gerados por juros e multa do FGTS e INSS",
            valor_dano_ressarcimento=6583.99,
            responsavel_ressarcimento="Giovannu César Pinheiro e Alves"
        )
    ],
    obrigacoes=[],
    recomendacoes=[],
    obrigacoes_multa=[]
)

exemplo_5 = '''
Vistos, relatados e discutidos estes autos do Convênio nº 03/2003 – SIN, firmado entre a Secretaria de Estado da Infraestrutura – SIN, e a Prefeitura Municipal de Tenente Ananias, que teve por objeto o repasse de recursos financeiros destinados à serviços de drenagem e pavimentação de ruas no município. Considerando a manifestação emitida pelo Corpo Técnico e parecer do Ministério Público junto a esta Corte, ACORDAM os Conselheiros, nos termos do voto proferido pelo Conselheiro Relator, julgar pela IRREGULARIDADE das contas do município de Tenente Ananias, relativamente à aplicação dos recursos recebidos através do Convênio nº 003/2003 – SIN, nos termos do art. 75, incisos II e IV, da Lei Complementar nº 464/2012, com aplicação das seguintes obrigações e penalidades à gestora Maria José Jácome da Silva, todas de conformidade com o art. 78, § 3º, alíneas ‘a’ e ‘b’, c/c art. 102, incisos I e II, da Lei Complementar Estadual nº 121/94, norma vigente à época dos fatos; com restituição aos cofres públicos estaduais da quantia de R$ 6.522,30 (seis mil quinhentos e vinte e dois reais e trinta centavos), a serem devidamente atualizados a partir da data do pagamento da despesa e com aplicação dos juros devidos, em solidariedade com a empresa contratada para execução das obras, Horebe Comércio e Serviços Ltda; e multa aos responsáveis solidários no percentual de 30% (trinta por cento), calculada sobre o valor atualizado da restituição; e a gestora responsável no valor de R$ 500,00 (quinhentos reais) cada, no total de 03 (três), totalizando R$ 1.500,00 (mil e quinhentos reais), em função das irregularidades formais praticadas.
'''
label_5 = Decisao(
    multas_fixas=[],
    # MUITO COMPLEXO!!!
    # n 8 no label_studio 
    multas_percentuais=[
        MultaPercentual(
            descricao_multapercentual="multa aos responsáveis solidários no percentual de 30% (trinta por cento), calculada sobre o valor atualizado da restituição; e a gestora responsável no valor de R$ 500,00 (quinhentos reais) cada, no total de 03 (três), totalizando R$ 1.500,00 (mil e quinhentos reais), em função das irregularidades formais praticadas.",
            percentual_multapercentual=30.0,
            base_calculo_multapercentual=500.0,
            e_multa_solidaria_multapercentual=True
        )
    ],
    ressarcimentos=[
        Ressarcimento(
            descricao_ressarcimento="Maria José Jácome da Silva, todas de conformidade com o art. 78, § 3º, alíneas ‘a’ e ‘b’, c/c art. 102, incisos I e II, da Lei Complementar Estadual nº 121/94, norma vigente à época dos fatos; com restituição aos cofres públicos estaduais da quantia de R$ 6.522,30 (seis mil quinhentos e vinte e dois reais e trinta centavos), a serem devidamente atualizados a partir da data do pagamento da despesa e com aplicação dos juros devidos, em solidariedade com a empresa contratada para execução das obras, Horebe Comércio e Serviços Ltda",
            valor_dano_ressarcimento=6522.30,
            responsavel_ressarcimento="Maria José Jácome da Silva"
        )
    ],
    obrigacoes=[],
    recomendacoes=[],
    obrigacoes_multa=[]
)

exemplo_6 = '''
DECIDEM os Conselheiros do Tribunal de Contas do Estado, à unanimidade, em consonância com a informação do Corpo Técnico, e do parecer do Ministério Público que atua junto a esta Corte de Contas, acolhendo integralmente o voto da Conselheira Relatora, julgar com fulcro no art. 312, §4º, do Regimento Interno desta Corte, pelo PREJUÍZO DO EXAME de mérito da aposentadoria, em decorrência do falecimento da servidora, e ainda, pela denegação de registro ao ato de pensão em análise, nos termos do art. 71, III, da Constituição Federal, art. 53, III, da Constituição do Estado e arts. 1º, III e 95, III, da Lei Complementar Estadual nº 464/12, determinando após o trânsito em julgado da decisão, a intimação do IPERN para que, em 60 (sessenta) dias, adote as medidas regularizadoras cabíveis, sob pena de estabelecimento de multa diária em face do gestor responsável, que desde já fixado em R$ 50,00 (cinquenta) reais por cada dia de atraso que exceder ao prazo acima consignado, valor este passível de revisão e limitado ao teto previsto no art. 323, inciso II, alínea `f`, do Regimento Interno, a ser apurado por ocasião de eventual subsistência de mora.
'''
label_6 = Decisao(
    multas_fixas=[],
    obrigacoes=[],
    recomendacoes=[],
    multas_percentuais=[],
    ressarcimentos=[],
    obrigacoes_multa=[
        ObrigacaoMulta(
            descricao_obrigacaomulta="determinando após o trânsito em julgado da decisão, a intimação do IPERN para que, em 60 (sessenta) dias, adote as medidas regularizadoras cabíveis, sob pena de estabelecimento de multa diária em face do gestor responsável, que desde já fixado em R$ 50,00 (cinquenta) reais por cada dia de atraso que exceder ao prazo acima consignado, valor este passível de revisão e limitado ao teto previsto no art. 323, inciso II, alínea `f`, do Regimento Interno, a ser apurado por ocasião de eventual subsistência de mora.",
            valor_obrigacaomulta=50.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="gestor responsável",
            orgao_responsavel_obrigacaomulta="IPERN"
        )
    ]
)

exemplo_7 = '''
Vistos, relatados e discutidos estes autos de Representação apresentada pela Diretoria de Despesa com Pessoal - DDP, Unidade Técnica desta Corte de Contas, em face da Prefeitura Municipal de Mossoró/RN, referente à remuneração dos agentes políticos, notadamente o Prefeito e Vice Prefeito, para o período 2017 a 2020, que teve como base a Lei Municipal n.º 3.439/2016, ACORDAM os Conselheiros, nos termos do voto proposto pelo Conselheiro Relator, julgar:

a) Pela NEGATIVA da aplicação da Lei Municipal nº 3.439/2016, em virtude dos vícios de inconstitucionalidade, com fundamento na Súmula nº 347 do STF, bem como na Lei Orgânica 464/2012 (arts. 142 e seguintes) e no Regimento Interno do TCERN (arts. 403 e seguintes);

b) Pela DETERMINAÇÃO a atual gestora do Município de Mossoró, que continue se abstendo de pagar os subsídios do Prefeito e Vice-Prefeito com base na Lei nº 3.439/2016 daquele Município – cuja aplicação ora se nega, sob pena de multa pessoal de R$ 10.000,00 (dez mil reais) ao Gestor do Executivo do Município de Mossoró por cada mês em que descumprida a presente ordem, devendo os agentes políticos (Prefeito e Vice-Prefeito) continuarem sendo remunerados com base nos subsídios fixados na Lei Municipal anterior;

c) Pela DETERMINAÇÃO à Diretoria de Atos e Execução – DAE deste Tribunal que proceda com a intimação da Prefeita Municipal de Mossoró/RN, Sra. Rosalba Ciarlini Rosado, para ciência e cumprimento desta Decisão, fixando prazo de 15 (quinze) dias a contar de sua intimação, para que comprova a edição de ato formal, em cumprimento da determinação estabelecida na letra “b”, a fim de que continue se abstendo de aplicar a Lei nº 3.439/2016 daquele Município (tal ato formal deve abranger os subsídios tanto do Prefeito como do Vice-Prefeito);

d) Pela abertura de processo de apuração de responsabilidade contra os responsáveis pelo Poder Executivo e Poder legislativo à época da Edição da Lei Municipal nº 3.439/2016; e

e) Pela RECOMENDAÇÃO ao Poder Executivo e Legislativo do Município de Mossoró/RN, nas pessoas de seus representantes legais, para que da edição de nova lei municipal que aborde aumento de despesa com pessoal, que seja precedida de estudo de impacto financeiro e orçamentário e que sejam observados os prazos e mandamentos da Constituição Federal e da LRF.
'''
label_7 = Decisao(
    multas_fixas=[],
    multas_percentuais=[],
    ressarcimentos=[],
    obrigacoes_multa=[
        ObrigacaoMulta(
            descricao_obrigacaomulta="DETERMINAÇÃO a atual gestora do Município de Mossoró, que continue se abstendo de pagar os subsídios do Prefeito e Vice-Prefeito com base na Lei nº 3.439/2016 daquele Município – cuja aplicação ora se nega, sob pena de multa pessoal de R$ 10.000,00 (dez mil reais) ao Gestor do Executivo do Município de Mossoró por cada mês em que descumprida a presente ordem, devendo os agentes políticos (Prefeito e Vice-Prefeito) continuarem sendo remunerados com base nos subsídios fixados na Lei Municipal anterior;",
            valor_obrigacaomulta=10000.0,
            periodo_obrigacaomulta="mensal",
            nome_responsavel_obrigacaomulta="Gestor do Executivo do Município de Mossoró",
            orgao_responsavel_obrigacaomulta="Município de Mossoró"
        )
    ],
    obrigacoes=[
        Obrigacao(
            descricao_obrigacao="Sra. Rosalba Ciarlini Rosado, para ciência e cumprimento desta Decisão, fixando prazo de 15 (quinze) dias a contar de sua intimação, para que comprova a edição de ato formal, em cumprimento da determinação estabelecida na letra “b”, a fim de que continue se abstendo de aplicar a Lei nº 3.439/2016 daquele Município (tal ato formal deve abranger os subsídios tanto do Prefeito como do Vice-Prefeito);",
            prazo_cumprimento_obrigacao="15 dias",
            nome_responsavel_obrigacaomulta="Rosalba Ciarlini Rosado",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Mossoró"
            )
    ],
    recomendacoes=[
        Recomendacao(
            descricao_recomendacao="RECOMENDAÇÃO ao Poder Executivo e Legislativo do Município de Mossoró/RN, nas pessoas de seus representantes legais, para que da edição de nova lei municipal que aborde aumento de despesa com pessoal, que seja precedida de estudo de impacto financeiro e orçamentário e que sejam observados os prazos e mandamentos da Constituição Federal e da LRF.",
            nome_responsavel_recomendacao="Poder Executivo e Legislativo do Município de Mossoró",
            orgao_responsavel_recomendacao="Município de Mossoró"
        )
    ]
)

exemplo_8 = '''
Vistos, relatados e discutidos estes autos, ACORDAM os Conselheiros, nos termos do voto vista proferido pelo Excelentíssimo Conselheiro Carlos Thompson Costa Fernandes, julgar no sentido de:

a) Em relação ao Poder Legislativo do Município de Acari:

i. Pela revogação da medida cautelar arbitrada, para autorizar, especificamente para os cargos relativos à Câmara Municipal, a homologação do concurso público e o seu regular prosseguimento;

ii. Pela imposição de multa ao então presidente da Câmara Municipal, Sr. Leonardo Ferreira de Medeiros, no valor de R$ 4.172,49 (quatro mil, cento e setenta e dois reais e quarenta e nove centavos), fulcrada no art. 107, inciso II, alínea “b”, da Lei Complementar Estadual nº 464/2012, c/c art. 323, inciso II, do Regimento Interno, diante do não envio voluntário do edital do concurso público, exigência prevista no art. 308, do Regimento Interno desta Corte;

iii. Pela obrigação de remeter a este Tribunal de Contas, quando das nomeações, o demonstrativo que certifique a existência de prévia dotação orçamentária suficiente para atender às projeções de despesa com pessoal e aos acréscimos dela decorrentes quando da nomeação dos candidatos aprovados;

iv. Pela obrigação de remeter a este Tribunal de Contas os processos de admissão, com o fito de proceder à análise de sua legalidade, com fins de registro.



b) Em relação ao Poder Executivo do Município de Acari:

i. Reforçar a medida cautelar proferida nestes autos, com fundamento nos arts. 120 e 121, inciso II, da Lei Complementar Estadual nº 464/2012, c/c o disposto nos arts. 345, e 346, inciso II, do Regimento Interno, com o fito de proibir que o Poder Executivo de Acari proceda à homologação do concurso público deflagrado pelo Edital nº 001/2016, especificamente com relação às suas vagas, enquanto não houver decisão de mérito, devendo realizar a publicação do ato em imprensa oficial no prazo de 10 (dez) dias a partir da ciência desta Decisão, sob pena de multa diária no valor de R$ 500,00 (quinhentos reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012 , c/c o disposto no art. 326, do Regimento Interno ;

ii. Fixar o prazo de 60 (sessenta) dias contados a partir da comunicação desta Decisão para que o Poder Executivo Municipal apresente demonstrativo de despesas com pessoal atualizado, hábil a comprovar a compatibilidade entre o quantitativo de servidores, o número de cargos criados por lei e as vagas disponibilizadas para o preenchimento por concurso, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno;

iii. Igualmente em 60 (sessenta) dias, deve o gestor apresentar documentação hábil a demonstrar a existência de prévia dotação orçamentária, suficiente para atender às projeções de despesa com pessoal advindas do concurso e aos acréscimos dela decorrentes, em nos exatos termos do artigo 169, §1º, inciso I da Constituição Federal, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno;

iv. No mesmo prazo de 60 (sessenta) dias, deverá juntar aos autos estimativa do impacto considerando as nomeações advindas do concurso público tanto para o exercício em que tais servidores ingressarem, como para os dois subsequentes, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno;

v. Apresentar, em 60 (sessenta) dias, declaração do ordenador de despesas sobre o aumento de dispêndio com pessoal e a adequação orçamentária e financeira com a LOA, PPA e a LDO, considerando o efetivo dispêndio com as nomeações dos candidatos aprovados, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno;

vi. Determinar que se comprove, também em 60 (sessenta) dias, o atendimento aos ditames do artigo 16, I e II, § 2º, c/c o artigo 17, §§ 1º, 2º, 4º e 5º e com o artigo 21, I, da Lei Complementar Federal nº 101/2000, atestando que a despesa criada ou aumentada com o ingresso aprovados não afeta as metas de resultados fiscais previstas no anexo da LDO, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno;

vii. Comprovar, em até quatro quadrimestres – contados a partir desta Decisão –, sob pena de ser considerado nulo de pleno direito o concurso público, que o Poder Executivo adotou as medidas para eliminar o percentual excedente do limite prudencial de despesas com pessoal – com a adoção das medidas descritas na Constituição Federal e na LRF –, considerando o disposto nos arts. 20, 22, 23, e 66, todos da Lei de Responsabilidade Fiscal, inclusive com a rescisão de todos os contratos temporários;

viii. Regularizar, em 60 (sessenta) dias, as informações prestadas ao SIAI-DP, de modo que haja congruência com os dados constantes no Portal da Transparência do Município de Acari, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno.

ACORDAM, por fim, pela imediata remessa do voto e do Acórdão proferido nestes autos ao Ministério Público Estadual, para ciência e adoção das providências pertinentes no escopo de sua competência.
'''

label_8 = Decisao(
    multas_percentuais=[],
    ressarcimentos=[],
    recomendacoes=[],
    obrigacoes=[
        Obrigacao(descricao_obrigacao="obrigação de remeter a este Tribunal de Contas, quando das nomeações, o demonstrativo que certifique a existência de prévia dotação orçamentária suficiente para atender às projeções de despesa com pessoal e aos acréscimos dela decorrentes quando da nomeação dos candidatos aprovados",
            prazo_cumprimento_obrigacao="",
            nome_responsavel_obrigacao="Poder Legislativo do Município de Acari",
            orgao_responsavel_obrigacao="Câmara Municipal de Acari"
        ),
        Obrigacao(descricao_obrigacao="obrigação de remeter a este Tribunal de Contas os processos de admissão, com o fito de proceder à análise de sua legalidade, com fins de registro",
            prazo_cumprimento_obrigacao="",
            nome_responsavel_obrigacao="Poder Legislativo do Município de Acari",
            orgao_responsavel_obrigacao="Câmara Municipal de Acari"
        ),
        Obrigacao(descricao_obrigacao="Comprovar, em até quatro quadrimestres – contados a partir desta Decisão –, sob pena de ser considerado nulo de pleno direito o concurso público, que o Poder Executivo adotou as medidas para eliminar o percentual excedente do limite prudencial de despesas com pessoal – com a adoção das medidas descritas na Constituição Federal e na LRF –, considerando o disposto nos arts. 20, 22, 23, e 66, todos da Lei de Responsabilidade Fiscal, inclusive com a rescisão de todos os contratos temporários",
            prazo_cumprimento_obrigacao="4 quadrimestres",
            nome_responsavel_obrigacao="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacao="Prefeitura Municipal de Acari"
        ),
    ],
    multas_fixas=[
        MultaFixa(
            descricao_multafixa="multa ao então presidente da Câmara Municipal, Sr. Leonardo Ferreira de Medeiros, no valor de R$ 4.172,49 (quatro mil, cento e setenta e dois reais e quarenta e nove centavos), fulcrada no art. 107, inciso II, alínea “b”, da Lei Complementar Estadual nº 464/2012, c/c art. 323, inciso II, do Regimento Interno, diante do não envio voluntário do edital do concurso público, exigência prevista no art. 308, do Regimento Interno desta Corte;",
            valor_multafixa=4172.49,
            nome_responsavel_multafixa="Leonardo Ferreira de Medeiros",
        )
    ],
    obrigacoes_multa=[
        ObrigacaoMulta(
            descricao_obrigacaomulta="proibir que o Poder Executivo de Acari proceda à homologação do concurso público deflagrado pelo Edital nº 001/2016, especificamente com relação às suas vagas, enquanto não houver decisão de mérito, devendo realizar a publicação do ato em imprensa oficial no prazo de 10 (dez) dias a partir da ciência desta Decisão, sob pena de multa diária no valor de R$ 500,00 (quinhentos reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012 , c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=500.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="10 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        ),
        ObrigacaoMulta(
            descricao_obrigacaomulta="Fixar o prazo de 60 (sessenta) dias contados a partir da comunicação desta Decisão para que o Poder Executivo Municipal apresente demonstrativo de despesas com pessoal atualizado, hábil a comprovar a compatibilidade entre o quantitativo de servidores, o número de cargos criados por lei e as vagas disponibilizadas para o preenchimento por concurso, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=100.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        ),
        ObrigacaoMulta(
            descricao_obrigacaomulta="60 (sessenta) dias, deve o gestor apresentar documentação hábil a demonstrar a existência de prévia dotação orçamentária, suficiente para atender às projeções de despesa com pessoal advindas do concurso e aos acréscimos dela decorrentes, em nos exatos termos do artigo 169, §1º, inciso I da Constituição Federal, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=100.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        ),
        ObrigacaoMulta(
            descricao_obrigacaomulta="prazo de 60 (sessenta) dias, deverá juntar aos autos estimativa do impacto considerando as nomeações advindas do concurso público tanto para o exercício em que tais servidores ingressarem, como para os dois subsequentes, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=100.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        ),
        ObrigacaoMulta(
            descricao_obrigacaomulta="Apresentar, em 60 (sessenta) dias, declaração do ordenador de despesas sobre o aumento de dispêndio com pessoal e a adequação orçamentária e financeira com a LOA, PPA e a LDO, considerando o efetivo dispêndio com as nomeações dos candidatos aprovados, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=100.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        ),
        ObrigacaoMulta(
            descricao_obrigacaomulta="Determinar que se comprove, também em 60 (sessenta) dias, o atendimento aos ditames do artigo 16, I e II, § 2º, c/c o artigo 17, §§ 1º, 2º, 4º e 5º e com o artigo 21, I, da Lei Complementar Federal nº 101/2000, atestando que a despesa criada ou aumentada com o ingresso aprovados não afeta as metas de resultados fiscais previstas no anexo da LDO, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=100.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        ),
        ObrigacaoMulta(
            descricao_obrigacaomulta=" Regularizar, em 60 (sessenta) dias, as informações prestadas ao SIAI-DP, de modo que haja congruência com os dados constantes no Portal da Transparência do Município de Acari, sob pena de multa diária de R$ 100,00 (cem reais), com fundamento no art. 110, da Lei Complementar Estadual nº 464/2012, c/c o disposto no art. 326, do Regimento Interno",
            valor_obrigacaomulta=100.0,
            periodo_obrigacaomulta="diário",
            prazo_obrigacaomulta="60 dias",
            nome_responsavel_obrigacaomulta="Poder Executivo do Município de Acari",
            orgao_responsavel_obrigacaomulta="Prefeitura Municipal de Acari"
        )
    ]    
)

TOOL_USE_EXAMPLES = [
    (exemplo_1, label_1),
    (exemplo_2, label_2),
    (exemplo_3, label_3),
    (exemplo_4, label_4),
    (exemplo_5, label_5),
    (exemplo_6, label_6),
    (exemplo_7, label_7),
    (exemplo_8, label_8),
]

def convert_tool_example_to_messages(text: str, tool_call: BaseModel) -> List:
    tool_call_id = str(uuid.uuid4())
    return [
        HumanMessage(content=text),
        AIMessage(content="", tool_calls=[
            {
                "id": tool_call_id,
                "name": tool_call.__class__.__name__,  # "Decisao"
                "args": tool_call.model_dump()
            }
        ]),
        ToolMessage(content="Você chamou corretamente essa ferramenta.", tool_call_id=tool_call_id)
    ]


def get_fewshot_messages(examples: List[Tuple[str, Decisao]]) -> List[List[BaseMessage]]:
    return [convert_tool_example_to_messages(text, label) for text, label in examples]


fewshot_chats = get_fewshot_messages(TOOL_USE_EXAMPLES)

# Flatten all examples em uma lista de mensagens
fewshot_context = [msg for chat in fewshot_chats for msg in chat]

# Agora adicione sua nova entrada
def build_fewshot_prompt(novo_texto: str) -> List[BaseMessage]:
    return fewshot_context + [HumanMessage(content=novo_texto)]

def get_formatted_messages_from_examples(examples: List[Tuple[str, str]]) -> List[Dict[str, BaseMessage]]:
    """Generate a list of formatted messages from a list of examples.

    Args:
        examples (list[tuple[str, str]]): A list of tuples where each tuple contains
                                          a text input and a corresponding tool call.

    Returns:
        list[BaseMessage]: A list of formatted messages.
    """
    formatted_messages = []

    for text_input, tool_call in examples:
        # Convert each example to a list of messages and extend the formatted_messages list
        formatted_messages.extend(
            convert_tool_example_to_messages(text_input, tool_call)
        )
    
    return formatted_messages