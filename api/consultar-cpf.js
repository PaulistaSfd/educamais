export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { cpf } = req.query;

    if (!cpf) {
      return res.status(400).json({ status: 400, erro: 'CPF não informado' });
    }

    const cpfClean = cpf.replace(/\D/g, '');

    if (!cpfClean || cpfClean.length !== 11) {
      return res.status(400).json({ status: 400, erro: 'CPF não informado ou inválido' });
    }

    const APELA_USER = process.env.APELA_API_USER || 'seu_token_aqui';

    // Call APELA API
    const apelaUrl = `https://api-apela.online/?user=${encodeURIComponent(APELA_USER)}&cpf=${encodeURIComponent(cpfClean)}`;

    console.log('[DEBUG] Chamando APELA:', apelaUrl);

    const apelaResponse = await fetch(apelaUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; EducacaoBR/1.0)'
      }
    });

    const apelaData = await apelaResponse.json();
    console.log('[DEBUG] Resposta APELA:', apelaData);

    if (apelaData.status !== 200) {
      return res.status(404).json({
        status: 404,
        erro: apelaData.erro || 'CPF não encontrado'
      });
    }

    if (!apelaData.nome || apelaData.nome.trim() === '') {
      return res.status(404).json({
        status: 404,
        erro: 'CPF não encontrado'
      });
    }

    return res.status(200).json({
      status: 200,
      nome: apelaData.nome || '',
      cpf: cpfClean,
      nascimento: apelaData.nascimento || '',
      mae: apelaData.mae || '',
      sexo: apelaData.sexo || ''
    });

  } catch (error) {
    console.error('[consultar-cpf] Erro:', error);
    return res.status(500).json({
      status: 500,
      erro: 'Erro interno do servidor'
    });
  }
}
