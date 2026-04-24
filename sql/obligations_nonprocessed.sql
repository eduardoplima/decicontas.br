SELECT DISTINCT
    o.IdNerObrigacao as id_ner_obrigacao,
    o.IdNerDecisao as id_ner_decisao,
    o.Ordem as ordem_obrigacao,
    o.DescricaoObrigacao as descricao_obrigacao,

    nd.IdProcesso as id_processo,
    CONCAT(p.Numero_Processo, '/', p.Ano_Processo) AS processo,

    org.Nome        AS orgao_responsavel,
    org.IdOrgao     AS id_orgao_responsavel,
    gp.Nome         AS nome_responsavel,
    gp.Documento    AS documento_responsavel,
    gp.TipoPessoa   AS tipo_responsavel,
    gp.IdPessoa     AS id_pessoa,

    d.monocratica,
    d.codigo_tipo_processo,
    d.descricao,
    d.TipoVoto              AS tipo_voto,
    d.VotoEscolhido         AS voto_escolhido,
    d.IdComposicaoPauta     AS id_composicao_pauta,
    d.numero_sessao,
    d.ano_sessao,
    d.DataSessao            AS data_sessao,
    d.DataEncerramentoSessao AS data_encerramento_sessao,
    d.numeroResultado       AS numero_resultado,
    d.anoResultado          AS ano_resultado,
    d.resultadoTipo         AS resultado_tipo,
    d.idVotoPauta           AS id_voto_pauta,
    d.idVotoDecisao         AS id_voto_decisao,
    d.ementa,
    d.assunto,
    d.NumeroProcesso        AS numero_processo,
    d.AnoProcesso           AS ano_processo,
    d.IdProcesso            AS id_processo_voto,
    d.interessado,
    d.OrgaoOrigem           AS orgao_origem,
    d.isVotoDivergente      AS is_voto_divergente,
    d.IdVotoConcordado      AS id_voto_concordado,
    d.Relatorio             AS relatorio,
    d.FundamentacaoVoto     AS fundamentacao_voto,
    d.Conclusao             AS conclusao,
    d.texto_acordao,
    d.SetorVoto             AS setor_voto

FROM BdDIP.dbo.NERObrigacao o
INNER JOIN BdDIP.dbo.NERDecisao nd 
    ON nd.IdNerDecisao = o.IdNerDecisao
INNER JOIN processo.dbo.Processos p
    ON p.IdProcesso = nd.IdProcesso
INNER JOIN processo.dbo.vw_ia_votos_acordaos_decisoes d
    ON nd.IdProcesso = p.IdProcesso
    AND nd.IdComposicaoPauta = d.IdComposicaoPauta
    AND nd.IdVotoPauta = d.IdVotoPauta
INNER JOIN processo.dbo.Orgaos org 
    ON p.IdOrgaoEnvolvido = org.IdOrgao 
INNER JOIN processo.dbo.Pro_ProcessosResponsavelDespesa pprd 
    ON pprd.IdProcesso = p.IdProcesso 
INNER JOIN processo.dbo.GenPessoa gp 
    ON gp.IdPessoa = pprd.IdPessoa 
WHERE NOT EXISTS (
        SELECT 1
        FROM BdDIP.dbo.ObrigacaoProcessada op
        WHERE op.IdNerObrigacao = o.IdNerObrigacao
    )
  AND NOT EXISTS (
        SELECT 1
        FROM BdDIP.dbo.ObrigacaoStaging os
        WHERE os.IdProcesso         = nd.IdProcesso
          AND os.IdComposicaoPauta  = nd.IdComposicaoPauta
          AND os.IdVotoPauta        = nd.IdVotoPauta
          AND os.DescricaoObrigacao = o.DescricaoObrigacao
          AND os.status IN ('pending', 'approved')
    )
