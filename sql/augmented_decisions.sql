SELECT p.idprocesso as id_processo, NumeroProcesso as numero_processo, AnoProcesso as ano_processo, 
 IdComposicaoPauta as id_composicao_pauta, idVotoPauta as id_voto_pauta, 
numero_sessao, ano_sessao, DataSessao as data_sessao,  
Relatorio, FundamentacaoVoto as fundamentacao_voto, 
Conclusao, texto_acordao, o.nome as orgao_responsavel, o.IdOrgao as id_orgao_responsavel,
gp.Nome as nome_responsavel, gp.Documento as documento_responsavel, gp.TipoPessoa as tipo_responsavel, gp.idpessoa as id_pessoa
FROM processo.dbo.vw_ia_votos_acordaos_decisoes ia 
LEFT JOIN processo.dbo.processos p ON ia.NumeroProcesso = p.numero_processo  AND ia.AnoProcesso = p.ano_processo 
LEFT JOIN processo.dbo.Orgaos o ON o.IdOrgao = p.IdOrgaoEnvolvido
LEFT JOIN processo.dbo.Pro_ProcessosResponsavelDespesa pprd ON p.IdProcesso = pprd.IdProcesso 
LEFT JOIN processo.dbo.GenPessoa gp ON pprd.IdPessoa = gp.IdPessoa 
WHERE ano_sessao >= 2020
AND pprd.TipoResponsavel = 1