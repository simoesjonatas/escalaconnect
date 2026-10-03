import * as SecureStore from 'expo-secure-store';

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'https://connect.pibvp.org.br').replace(/\/$/, '');

const CHAVE_TOKEN = 'token';

/** Erro devolvido pela API: {code, detail, errors?}. O `code` diz ao app o que fazer. */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    detail: string,
    public errors?: Record<string, string[]>,
  ) {
    super(detail);
  }

  /** Mensagem para mostrar ao usuário: os erros de campo, se houver, ou o detalhe. */
  get mensagem(): string {
    const deCampos = Object.values(this.errors ?? {}).flat();
    return deCampos.length ? deCampos.join('\n') : this.message;
  }
}

export function mensagemDeErro(erro: unknown): string {
  if (erro instanceof ApiError) return erro.mensagem;
  return 'Não foi possível falar com o servidor. Verifique sua conexão.';
}

let token: string | null = null;
let aoPerderSessao: () => void = () => {};
let aoFicarPendente: () => void = () => {};

/** O AuthProvider registra aqui o que fazer com 401 (sessão caiu) e 403 de conta pendente. */
export function registrarEventosDeSessao(eventos: { perdeuSessao: () => void; ficouPendente: () => void }) {
  aoPerderSessao = eventos.perdeuSessao;
  aoFicarPendente = eventos.ficouPendente;
}

export async function carregarToken(): Promise<string | null> {
  token = await SecureStore.getItemAsync(CHAVE_TOKEN);
  return token;
}

export async function guardarToken(novo: string | null) {
  token = novo;
  if (novo) await SecureStore.setItemAsync(CHAVE_TOKEN, novo);
  else await SecureStore.deleteItemAsync(CHAVE_TOKEN);
}

type Metodo = 'GET' | 'POST' | 'PATCH' | 'DELETE';

export async function api<T = unknown>(metodo: Metodo, rota: string, corpo?: unknown): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${API_URL}/api/v1${rota}`, {
      method: metodo,
      headers: {
        Accept: 'application/json',
        ...(corpo !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Token ${token}` } : {}),
      },
      body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    throw new ApiError(0, 'sem_conexao', 'Não foi possível falar com o servidor. Verifique sua conexão.');
  }

  if (resposta.status === 204) return undefined as T;
  const dados = await resposta.json().catch(() => null);
  if (resposta.ok) return dados as T;

  const erro = new ApiError(
    resposta.status,
    dados?.code ?? 'erro',
    dados?.detail ?? 'Algo deu errado. Tente de novo.',
    dados?.errors,
  );
  if (resposta.status === 401 && token) aoPerderSessao();
  if (erro.code === 'senha_pendente' || erro.code === 'termo_pendente') aoFicarPendente();
  throw erro;
}
