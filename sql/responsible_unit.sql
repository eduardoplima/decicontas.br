SELECT DISTINCT resp.Nome,
        respuni.Cargo,
        respuni.DataInicioGestao,
        respuni.DataTerminoGestao
    FROM [BdSIAI].[dbo].[Anexo42_Responsavel] resp
    INNER JOIN [BdSIAI].[dbo].[Anexo42_ResponsavelUnidade] respuni ON resp.IdResponsavel = respuni.IdResponsavel
    INNER JOIN [BdSIAI].[dbo].[Anexo42_UnidadeJurisdicionada] uni ON uni.IdUnidadeJurisdicionada = respuni.IdUnidadeJurisdicionada 
        WHERE uni.IdUnidadeJurisdicionada = {id_unit}
        AND (respuni.DataTerminoGestao IS NULL OR respuni.DataTerminoGestao >= '{session_date}')
        AND respuni.DataInicioGestao <= '{session_date}'