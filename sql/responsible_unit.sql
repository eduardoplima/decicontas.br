SELECT DISTINCT resp.Nome,
        uni.IdUnidadeJurisdicionada,
        uni.NomeUnidade,
        respuni.Cargo,
        respuni.DataInclusao,
        respuni.DataInicioGestao,
        respuni.DataTerminoGestao
    FROM [BdSIAI].[dbo].[Anexo42_Responsavel] resp
    INNER JOIN [BdSIAI].[dbo].[Anexo42_ResponsavelUnidade] respuni ON resp.IdResponsavel = respuni.IdResponsavel
    INNER JOIN [BdSIAI].[dbo].[Anexo42_UnidadeJurisdicionada] uni ON uni.IdUnidadeJurisdicionada = respuni.IdUnidadeJurisdicionada 
        WHERE uni.IdUnidadeJurisdicionada = {id_unit}