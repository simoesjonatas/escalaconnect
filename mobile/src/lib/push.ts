import { useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, Linking, Platform } from 'react-native';

import { api } from './api';

// Com o app aberto, a notificação também aparece (por padrão ela seria silenciosa).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

let tokenRegistrado: string | null = null;

/** No Android 13+ o pedido de permissão só aparece depois que existe um canal. */
async function prepararCanal() {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync('default', {
    name: 'Escalas',
    importance: Notifications.AndroidImportance.HIGH,
  });
}

/**
 * Pede permissão, obtém o token de push da Expo e registra o aparelho na API.
 * Não faz nada em emulador sem Google Play, sem permissão ou antes do `eas init`
 * (sem projectId não há token).
 */
export async function registrarAparelho(): Promise<void> {
  const projectId: string | undefined = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!Device.isDevice || !projectId) return;

  await prepararCanal();
  let { status } = await Notifications.getPermissionsAsync();
  if (status !== 'granted') ({ status } = await Notifications.requestPermissionsAsync());
  if (status !== 'granted') return;

  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  await api('POST', '/devices/', {
    expo_token: token,
    plataforma: Platform.OS,
    nome_aparelho: Device.modelName ?? '',
    app_versao: Constants.expoConfig?.version ?? '',
  });
  tokenRegistrado = token;
}

type Permissao = Notifications.NotificationPermissionsStatus;

function permitidas(permissao: Permissao) {
  return permissao.granted || permissao.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL;
}

/**
 * Se as notificações estão permitidas neste aparelho. Relê ao voltar para o app (por exemplo, depois de
 * ativar nos ajustes do celular) e, quando passam a ser permitidas, registra o aparelho para receber push.
 */
export function useNotificacoes() {
  const [permissao, setPermissao] = useState<Permissao | null>(null);

  const ler = useCallback(async () => {
    const atual = await Notifications.getPermissionsAsync().catch(() => null);
    setPermissao(atual);
    if (atual && permitidas(atual) && !tokenRegistrado) void registrarAparelho().catch(() => {});
  }, []);

  useEffect(() => {
    void ler();
    const inscricao = AppState.addEventListener('change', (estado) => {
      if (estado === 'active') void ler();
    });
    return () => inscricao.remove();
  }, [ler]);

  // Depois de uma recusa o sistema não mostra mais o pedido: só dá para ativar nos ajustes do celular.
  const precisaDosAjustes = permissao?.canAskAgain === false;

  async function ativar() {
    if (precisaDosAjustes) {
      await Linking.openSettings();
      return;
    }
    await prepararCanal();
    const nova = await Notifications.requestPermissionsAsync();
    setPermissao(nova);
    if (permitidas(nova)) void registrarAparelho().catch(() => {});
  }

  return {
    carregando: !permissao,
    ativadas: !!permissao && permitidas(permissao),
    precisaDosAjustes,
    ativar,
    abrirAjustes: () => void Linking.openSettings(),
  };
}

/** Antes do logout: este aparelho deixa de receber push da conta. */
export async function removerAparelho(): Promise<void> {
  if (!tokenRegistrado) return;
  await api('DELETE', `/devices/${encodeURIComponent(tokenRegistrado)}/`).catch(() => {});
  tokenRegistrado = null;
}

type DadosDoPush = { tipo?: string; escala_id?: number | null; evento_id?: number | null };

/**
 * Tela que cada tipo de push abre ao toque (os tipos vêm do backend, ver escalaconnect/push.py).
 * Também usada ao tocar num aviso da caixa de avisos.
 */
export function abrir({ tipo, escala_id, evento_id }: DadosDoPush) {
  if ((tipo === 'escalado' || tipo === 'confirmar_escala' || tipo === 'pedido_recusado') && escala_id) {
    router.push({ pathname: '/escala/[id]', params: { id: escala_id } });
  } else if (tipo === 'saiu_da_escala' || tipo === 'escala_fixa' || tipo === 'escalado') router.navigate('/escalas');
  else if (tipo === 'disponibilidade') router.navigate('/disponibilidade');
  else if (tipo === 'membro_aprovado') router.push('/equipes');
  // `t` muda a cada toque, para a aba Liderança voltar para Pendências mesmo se já estiver aberta.
  else if (tipo === 'pendencia_lider')
    router.navigate({ pathname: '/lideranca', params: { aba: 'pendencias', t: Date.now() } });
  else if (tipo === 'oferta_recusada') router.push('/vagas');
  // Ofertas para o líder: o culto, com quem se ofereceu e quem está disponível em cada vaga.
  else if (tipo === 'oferta_lider') {
    if (evento_id) router.push({ pathname: '/lider/culto/[id]', params: { id: evento_id } });
    else router.navigate({ pathname: '/lideranca', params: { aba: 'pendencias', t: Date.now() } });
  }
}

/** Usado dentro da área logada: abre a tela do push tocado e atualiza os dados quando chega um push. */
export function usePush() {
  const queryClient = useQueryClient();
  const resposta = Notifications.useLastNotificationResponse();
  const tratada = useRef<string | null>(null);

  useEffect(() => {
    const id = resposta?.notification.request.identifier;
    if (!resposta || !id || tratada.current === id) return;
    tratada.current = id;
    abrir(resposta.notification.request.content.data as DadosDoPush);
  }, [resposta]);

  useEffect(() => {
    const inscricao = Notifications.addNotificationReceivedListener(() => void queryClient.invalidateQueries());
    return () => inscricao.remove();
  }, [queryClient]);
}

/** Número no ícone do app = avisos não lidos; zero também limpa as notificações da central. */
export async function sincronizarIcone(naoLidos: number): Promise<void> {
  await Notifications.setBadgeCountAsync(naoLidos).catch(() => false);
  if (naoLidos === 0) await Notifications.dismissAllNotificationsAsync().catch(() => {});
}
