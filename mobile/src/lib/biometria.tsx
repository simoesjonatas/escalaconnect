import * as LocalAuthentication from 'expo-local-authentication';
import * as SecureStore from 'expo-secure-store';
import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppState, Platform, View } from 'react-native';

import { EstadoDaSessao, useAuth } from './auth';
import { useTema } from './tema';
import { Botao, Icone, Logo, Suave, Titulo } from './ui';

/**
 * "Entrar com Face ID / digital": opcional, ligado no Perfil e guardado por aparelho. O login
 * continua salvo como sempre (nenhuma senha fica no celular); a biometria só destrava o app ao
 * abrir e ao voltar depois de alguns minutos fora. Se a biometria falhar, o sistema oferece o
 * código do celular, e a tela de bloqueio tem "Sair da conta" para entrar com a senha.
 */

const MINUTOS_FORA = 5;
const chave = (usuarioId: number) => `biometria_${usuarioId}`;

type Biometria = {
  /** O aparelho tem biometria cadastrada. */
  disponivel: boolean;
  /** "Face ID", "Touch ID", "digital" ou "biometria". */
  nome: string;
  icone: Icone;
  ativa: boolean;
  /** Pede a biometria uma vez para confirmar e liga; devolve se ligou. */
  ativar: () => Promise<boolean>;
  desativar: () => Promise<void>;
};

const ContextoDaBiometria = createContext<Biometria | null>(null);

export function useBiometria(): Biometria {
  const biometria = useContext(ContextoDaBiometria);
  if (!biometria) throw new Error('useBiometria fora do BiometriaProvider');
  return biometria;
}

function descrever(tipos: LocalAuthentication.AuthenticationType[]): { nome: string; icone: Icone } {
  if (tipos.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION) && Platform.OS === 'ios') {
    return { nome: 'Face ID', icone: 'scan-outline' };
  }
  if (tipos.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
    return { nome: Platform.OS === 'ios' ? 'Touch ID' : 'digital', icone: 'finger-print-outline' };
  }
  return { nome: 'biometria', icone: 'lock-closed-outline' };
}

async function autenticar(mensagem: string) {
  const resultado = await LocalAuthentication.authenticateAsync({
    promptMessage: mensagem,
    cancelLabel: 'Cancelar',
    fallbackLabel: 'Usar código',
  });
  if (resultado.success) return 'ok' as const;
  // Sem biometria nem código no aparelho não há como travar: libera em vez de prender a pessoa fora.
  const erro = resultado.error;
  return erro === 'not_enrolled' || erro === 'passcode_not_set' || erro === 'not_available'
    ? ('indisponivel' as const)
    : ('falhou' as const);
}

export function BiometriaProvider({ children }: { children: ReactNode }) {
  const { usuario, estado, sair } = useAuth();
  const usuarioId = usuario?.id;
  const [aparelho, setAparelho] = useState({
    disponivel: false,
    nome: 'biometria',
    icone: 'lock-closed-outline' as Icone,
  });
  const [ativa, setAtiva] = useState(false);
  const [bloqueado, setBloqueado] = useState(false);
  const estadoAnterior = useRef<EstadoDaSessao>(estado);
  const saiuEm = useRef<number | null>(null);

  useEffect(() => {
    (async () => {
      const [hardware, cadastrada, tipos] = await Promise.all([
        LocalAuthentication.hasHardwareAsync(),
        LocalAuthentication.isEnrolledAsync(),
        LocalAuthentication.supportedAuthenticationTypesAsync(),
      ]);
      setAparelho({ disponivel: hardware && cadastrada, ...descrever(tipos) });
    })().catch(() => {});
  }, []);

  // Ao abrir o app já logado (e não logo depois de digitar a senha), trava se a opção estiver ligada.
  useEffect(() => {
    const anterior = estadoAnterior.current;
    estadoAnterior.current = estado;
    if (!usuarioId || estado !== 'liberado') {
      setAtiva(false);
      setBloqueado(false);
      return;
    }
    SecureStore.getItemAsync(chave(usuarioId))
      .then((valor) => {
        setAtiva(valor === '1');
        if (valor === '1' && anterior === 'carregando') setBloqueado(true);
      })
      .catch(() => {});
  }, [usuarioId, estado]);

  // Voltou depois de alguns minutos em segundo plano: trava de novo.
  useEffect(() => {
    const inscricao = AppState.addEventListener('change', (agora) => {
      if (agora === 'background') saiuEm.current = Date.now();
      if (agora === 'active' && saiuEm.current && ativa) {
        if (Date.now() - saiuEm.current > MINUTOS_FORA * 60_000) setBloqueado(true);
        saiuEm.current = null;
      }
    });
    return () => inscricao.remove();
  }, [ativa]);

  const destravar = useCallback(async () => {
    const resultado = await autenticar('Desbloquear o Escala Connect');
    if (resultado !== 'falhou') setBloqueado(false);
  }, []);

  // A trava já pede a biometria sozinha ao aparecer.
  useEffect(() => {
    if (bloqueado) void destravar();
  }, [bloqueado, destravar]);

  const ativar = useCallback(async () => {
    if (!usuarioId) return false;
    if ((await autenticar(`Confirme para entrar com ${aparelho.nome}`)) !== 'ok') return false;
    await SecureStore.setItemAsync(chave(usuarioId), '1');
    setAtiva(true);
    return true;
  }, [usuarioId, aparelho.nome]);

  const desativar = useCallback(async () => {
    setAtiva(false);
    if (usuarioId) await SecureStore.deleteItemAsync(chave(usuarioId)).catch(() => {});
  }, [usuarioId]);

  return (
    <ContextoDaBiometria.Provider value={{ ...aparelho, ativa, ativar, desativar }}>
      {children}
      {bloqueado && estado === 'liberado' && (
        <TelaDeBloqueio
          nome={aparelho.nome}
          aoDestravar={destravar}
          aoSair={() => {
            setBloqueado(false);
            void sair();
          }}
        />
      )}
    </ContextoDaBiometria.Provider>
  );
}

function TelaDeBloqueio({ nome, aoDestravar, aoSair }: { nome: string; aoDestravar: () => void; aoSair: () => void }) {
  const { cores } = useTema();
  return (
    <View
      accessibilityViewIsModal
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: cores.fundo,
        justifyContent: 'center',
        padding: 24,
        gap: 12,
      }}>
      <View style={{ alignItems: 'center', gap: 8, marginBottom: 24 }}>
        <Logo tamanho={96} />
        <Titulo>Escala Connect</Titulo>
        <Suave style={{ textAlign: 'center' }}>Desbloqueie para continuar.</Suave>
      </View>
      <Botao titulo={`Desbloquear com ${nome}`} aoTocar={aoDestravar} />
      <Botao titulo="Sair e entrar com a senha" variante="secundario" aoTocar={aoSair} />
    </View>
  );
}
