const API_BASE = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

export async function apiFetch(path: string, options: RequestInit = {}) {
  const response = await fetch(`${API_BASE}/${path.replace(/^\//, '')}`, { ...options, credentials: 'include' });
  if (response.status === 401 && path !== '/login' && path !== '/session') window.dispatchEvent(new Event('rh:session-expired'));
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = typeof data.detail === 'string' ? data.detail : data.erro || data.mensagem || `Não foi possível concluir a operação (${response.status}). Confira os dados e tente novamente.`;
    throw new Error(message);
  }
  return response;
}

export interface RegistroIndicador { id: string; nome: string; setor: string; data: string }
export interface SyncStatus { status: 'idle' | 'running' | 'success' | 'error'; ultima_atualizacao: string | null; tem_dados: boolean; erro: string | null }
