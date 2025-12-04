SELECT 
    p.IdProcesso,
    CONCAT(p.Numero_Processo, '/', p.Ano_Processo) AS processo,
    o.Nome AS orgao_responsavel, 
    o.IdOrgao AS id_orgao_responsavel,
    gp.Nome AS nome_responsavel,
    gp.Documento AS documento_responsavel,
    gp.TipoPessoa AS tipo_responsavel,
    gp.IdPessoa AS id_pessoa,
    d.[monocratica],
    d.[codigo_tipo_processo],
    d.[descricao],
    d.[TipoVoto] as tipo_voto,
    d.[VotoEscolhido] as voto_escolhido,
    d.[IdComposicaoPauta] as id_composicao_pauta,
    d.[numero_sessao],
    d.[ano_sessao],
    d.[DataSessao] as data_sessao,
    d.[DataEncerramentoSessao] as data_encerramento_sessao,
    d.[numeroResultado] as numero_resultado,
    d.[anoResultado] as ano_resultado,
    d.[resultadoTipo] as resultado_tipo,
    d.[idVotoPauta] as id_voto_pauta,
    d.[idVotoDecisao] as id_voto_decisao,
    d.[ementa],
    d.[assunto],
    d.[NumeroProcesso] as numero_processo,
    d.[AnoProcesso] as ano_processo,
    d.[IdProcesso] as id_processo,
    d.[interessado],
    d.[OrgaoOrigem] as orgao_origem,
    d.[isVotoDivergente] as is_voto_divergente,
    d.[IdVotoConcordado] as id_voto_concordado,
    d.[Relatorio] as relatorio,
    d.[FundamentacaoVoto] as fundamentacao_voto,
    d.[Conclusao] as conclusao,
    d.[texto_acordao],
    d.[SetorVoto] as setor_voto
    FROM processo.dbo.vw_ia_votos_acordaos_decisoes d
    INNER JOIN processo.dbo.Processos p 
        ON d.IdProcesso = p.IdProcesso
    INNER JOIN processo.dbo.Orgaos o 
        ON p.IdOrgaoEnvolvido = o.IdOrgao 
    INNER JOIN processo.dbo.Pro_ProcessosResponsavelDespesa pprd 
        ON pprd.IdProcesso = p.IdProcesso 
    INNER JOIN processo.dbo.GenPessoa gp 
        ON gp.IdPessoa = pprd.IdPessoa 
    WHERE CONCAT(p.Numero_Processo, '/', p.Ano_Processo) IN ({processes})
  AND NOT EXISTS (
        SELECT 1
        FROM BdDIP.dbo.Obrigacao ob
        WHERE d.IdComposicaoPauta = ob.IdComposicaoPauta
          AND d.IdVotoPauta       = ob.IdVotoPauta
    )
  AND NOT EXISTS (
        SELECT 1
        FROM BdDIP.dbo.Recomendacao r
        WHERE d.IdComposicaoPauta = r.IdComposicaoPauta
          AND d.IdVotoPauta       = r.IdVotoPauta
    );
