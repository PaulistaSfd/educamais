export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const { id } = req.query;

    if (!id) {
      return res.status(400).json({ status: 400, erro: 'Transaction ID não informado' });
    }

    const LUMEAPAG_API_KEY = process.env.LUMEAPAG_API_KEY;

    if (!LUMEAPAG_API_KEY) {
      return res.status(500).json({ status: 500, erro: 'LUMEAPAG_API_KEY não configurada' });
    }

    const lumeapagUrl = `https://lumeapag.com/api/gateway/transactions/${id}`;

    const lumeapagResponse = await fetch(lumeapagUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Api-Key': LUMEAPAG_API_KEY,
        'User-Agent': 'EducacaoBR/1.0'
      }
    });

    const lumeapagData = await lumeapagResponse.json();

    if (lumeapagResponse.ok) {
      return res.status(200).json(lumeapagData);
    } else {
      return res.status(lumeapagResponse.status || 404).json({
        status: lumeapagResponse.status || 404,
        erro: lumeapagData.error || 'Transação não encontrada',
        data: lumeapagData
      });
    }

  } catch (error) {
    console.error('[consultar-transacao] Erro:', error);
    return res.status(500).json({ status: 500, erro: 'Erro interno do servidor', detalhes: error.message });
  }
}
