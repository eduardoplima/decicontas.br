-- Canonical source of texto_acordao for one decision. Used by the review UI
-- (GET /reviews/{kind}/{id}) and by the stage-2 ETL pipelines when hydrating
-- context for the LLM. Parametric on the identity triple
-- (IdProcesso, IdComposicaoPauta, IdVotoPauta).
--
-- Multiple rows may come back per decision (one per responsible person on
-- Pro_ProcessosResponsavelDespesa); callers aggregate via tools.utils.aggregate_responsaveis.
SELECT
    p.IdProcesso                                   AS id_processo,
    CONCAT(p.Numero_Processo, '/', p.Ano_Processo) AS processo,
    o.Nome                                         AS orgao_responsavel,
    o.IdOrgao                                      AS id_orgao_responsavel,
    gp.Nome                                        AS nome_responsavel,
    gp.Documento                                   AS documento_responsavel,
    gp.TipoPessoa                                  AS tipo_responsavel,
    gp.IdPessoa                                    AS id_pessoa,
    d.IdComposicaoPauta                            AS id_composicao_pauta,
    d.idVotoPauta                                  AS id_voto_pauta,
    d.DataSessao                                   AS data_sessao,
    d.OrgaoOrigem                                  AS orgao_origem,
    d.Relatorio                                    AS relatorio,
    d.FundamentacaoVoto                            AS fundamentacao_voto,
    d.Conclusao                                    AS conclusao,
    d.texto_acordao
FROM processo.dbo.vw_ia_votos_acordaos_decisoes d
INNER JOIN processo.dbo.Processos p
    ON d.IdProcesso = p.IdProcesso
INNER JOIN processo.dbo.Orgaos o
    ON p.IdOrgaoEnvolvido = o.IdOrgao
INNER JOIN processo.dbo.Pro_ProcessosResponsavelDespesa pprd
    ON pprd.IdProcesso = p.IdProcesso
INNER JOIN processo.dbo.GenPessoa gp
    ON gp.IdPessoa = pprd.IdPessoa
WHERE d.IdProcesso        = {id_processo}
  AND d.IdComposicaoPauta = {id_composicao_pauta}
  AND d.idVotoPauta       = {id_voto_pauta};
