import { useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import * as Notifications from 'expo-notifications';
import { router } from 'expo-router';
import { useEffect, useRef } from 'react';
import { Platform } from 'react-native';

import { api } from './api';

// Com o app aberto, a notificação também aparece (por padrão ela seria silenciosa).
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let tokenRegistrado: string | null = null;

/**
 * Pede permissão, obtém o token de push da Expo e registra o aparelho na API.
 * Não faz nada em emulador sem Google Play, sem permissão ou antes do `eas init`
 * (sem projectId não há token).
 */
export async function registrarAparelho(): Promise<void> {
  const projectId: string | undefined = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId;
  if (!Device.isDevice || !projectId) return;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Escalas',
      importance: Notifications.AndroidImportance.HIGH,
    });
  }
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

/** Antes do logout: este aparelho deixa de receber push da conta. */
export async function removerAparelho(): Promise<void> {
  if (!tokenRegistrado) return;
  await api('DELETE', `/devices/${encodeURIComponent(tokenRegistrado)}/`).catch(() => {});
  tokenRegistrado = null;
}

type DadosDoPush = { tipo?: string; escala_id?: number | null };

/** Tela que cada tipo de push abre ao toque (os tipos vêm do backend, ver escalaconnect/push.py). */
function abrir({ tipo, escala_id }: DadosDoPush) {
  if ((tipo === 'escalado' || tipo === 'confirmar_escala') && escala_id) {
    router.push({ pathname: '/escala/[id]', params: { id: escala_id } });
  } else if (tipo === 'saiu_da_escala') router.navigate('/escalas');
  else if (tipo === 'disponibilidade') router.navigate('/disponibilidade');
  else if (tipo === 'membro_aprovado') router.push('/equipes');
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
