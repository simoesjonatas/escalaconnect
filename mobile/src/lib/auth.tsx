import { useQueryClient } from '@tanstack/react-query';
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { api, ApiError, carregarToken, guardarToken, registrarEventosDeSessao } from './api';
import { registrarAparelho, removerAparelho } from './push';
import { Usuario } from './types';

/** Em que parte do app o usuário pode estar (ver os guards em src/app/_layout.tsx). */
export type EstadoDaSessao = 'carregando' | 'anonimo' | 'senha' | 'termo' | 'liberado';

type Auth = {
  estado: EstadoDaSessao;
  usuario: Usuario | null;
  entrar: (username: string, password: string) => Promise<void>;
  sair: () => Promise<void>;
  /** Atualiza o usuário com o que a API devolveu (ou busca de novo em /me/). */
  atualizarUsuario: (usuario?: Usuario) => Promise<void>;
};

const AuthContext = createContext<Auth | null>(null);

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth fora do AuthProvider');
  return auth;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [carregando, setCarregando] = useState(true);
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  const limparSessao = useCallback(async () => {
    await guardarToken(null);
    setUsuario(null);
    queryClient.clear();
  }, [queryClient]);

  const atualizarUsuario = useCallback(async (novo?: Usuario) => {
    setUsuario(novo ?? (await api<Usuario>('GET', '/me/')));
  }, []);

  useEffect(() => {
    registrarEventosDeSessao({
      perdeuSessao: () => void limparSessao(),
      // O líder pode redefinir a senha com o app aberto: recarrega para cair na tela certa.
      ficouPendente: () => void atualizarUsuario().catch(() => {}),
    });
  }, [limparSessao, atualizarUsuario]);

  // Ao abrir o app: se há token guardado, confirma que ainda vale buscando o usuário.
  useEffect(() => {
    (async () => {
      try {
        if (await carregarToken()) await atualizarUsuario();
      } catch (erro) {
        // Sem internet o token continua guardado; só descarta se a API o recusou.
        if (erro instanceof ApiError && erro.status === 401) await limparSessao();
      } finally {
        setCarregando(false);
      }
    })();
  }, [atualizarUsuario, limparSessao]);

  const entrar = useCallback(async (username: string, password: string) => {
    const resposta = await api<{ token: string; usuario: Usuario }>('POST', '/auth/login/', { username, password });
    await guardarToken(resposta.token);
    setUsuario(resposta.usuario);
  }, []);

  // Com usuário na sessão, registra o aparelho para push (falhar aqui não atrapalha o uso).
  const usuarioId = usuario?.id;
  useEffect(() => {
    if (usuarioId) void registrarAparelho().catch(() => {});
  }, [usuarioId]);

  const sair = useCallback(async () => {
    await removerAparelho();
    await api('POST', '/auth/logout/').catch(() => {}); // sem internet, sai assim mesmo
    await limparSessao();
  }, [limparSessao]);

  const estado: EstadoDaSessao = carregando
    ? 'carregando'
    : !usuario
      ? 'anonimo'
      : usuario.precisa_definir_senha
        ? 'senha'
        : usuario.precisa_aceitar_termo
          ? 'termo'
          : 'liberado';

  const valor = useMemo(
    () => ({ estado, usuario, entrar, sair, atualizarUsuario }),
    [estado, usuario, entrar, sair, atualizarUsuario],
  );
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
