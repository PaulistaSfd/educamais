export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    const LUMEAPAG_API_KEY = process.env.LUMEAPAG_API_KEY;

    if (!LUMEAPAG_API_KEY) {
      return res.status(500).json({ status: 500, erro: 'LUMEAPAG_API_KEY não configurada' });
    }

    const payload = req.body;

    if (!payload.product || !payload.customer || !payload.product.value) {
      return res.status(400).json({
        status: 400,
        erro: 'Campos obrigatórios faltando: product.name, product.value, customer.name, customer.email'
      });
    }

    const idempotencyKey = payload.metadata?.pedido || payload.external_id || `${Date.now()}-${Math.random().toString(36)}`;

    const lumeapagUrl = 'https://lumeapag.com/api/gateway/charges';

    const lumeapagResponse = await fetch(lumeapagUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Api-Key': LUMEAPAG_API_KEY,
        'Idempotency-Key': idempotencyKey,
        'User-Agent': 'EducacaoBR/1.0'
      },
      body: JSON.stringify(payload)
    });

    const lumeapagData = await lumeapagResponse.json();

    if (lumeapagResponse.ok && lumeapagData.success) {
      return res.status(201).json(lumeapagData);
    } else if (lumeapagResponse.status === 409 && lumeapagData.error_code === 'charge_in_progress') {
      return res.status(409).json({ status: 409, erro: 'Cobrança já em processo', data: lumeapagData });
    } else {
      return res.status(lumeapagResponse.status || 400).json({
        status: lumeapagResponse.status || 400,
        erro: lumeapagData.error || 'Falha ao criar cobrança',
        data: lumeapagData
      });
    }

  } catch (error) {
    console.error('[criar-cobranca] Erro:', error);
    return res.status(500).json({ status: 500, erro: 'Erro interno do servidor', detalhes: error.message });
  }
}
