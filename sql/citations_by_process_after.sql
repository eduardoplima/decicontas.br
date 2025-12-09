SELECT CONCAT([Numero_Citacao], '/', [Ano_citacao]) as citacao
      ,CONCAT([Numero_Processo],'/',[Ano_Processo]) as processo
      ,[Orgao] as orgao
      ,[Nome] as nome
      ,[DataInicioContagem] as data_inicio_contagem
      ,[DataFinalResposta] as data_final_resposta
  FROM [processo].[dbo].[Cit_Citacoes] cit
  WHERE CONCAT(cit.Numero_Processo, '/', cit.Ano_Processo) = '{process}'
  AND cit.DataInicioContagem <= '{session_date}';