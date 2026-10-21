import Ionicons from '@expo/vector-icons/Ionicons';
import * as Updates from 'expo-updates';
import { useEffect, useRef } from 'react';
import { Alert, AppState, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useTema } from './tema';

/** Intervalo mínimo entre verificações automáticas ao voltar para o app. */
const INTERVALO_MS = 5 * 60 * 1000;

/** Procura uma atualização publicada pelo `eas update` e, se houver, baixa. Devolve se baixou. */
async function baixarSeHouver(): Promise<boolean> {
  const verificacao = await Updates.checkForUpdateAsync();
  if (!verificacao.isAvailable) return false;
  const download = await Updates.fetchUpdateAsync();
  return download.isNew;
}

/**
 * Verifica atualizações ao abrir o app e ao voltar para ele (no máximo a cada 5 min),
 * baixando em segundo plano. A faixa de aviso aparece quando o download termina.
 * Desligado no desenvolvimento (Expo Go / dev client), onde não há atualizações.
 */
export function useVerificarAtualizacoes() {
  const ultimaVerificacao = useRef(0);

  useEffect(() => {
    if (!Updates.isEnabled) return;

    const verificar = () => {
      if (Date.now() - ultimaVerificacao.current < INTERVALO_MS) return;
      ultimaVerificacao.current = Date.now();
      baixarSeHouver().catch(() => {}); // sem internet: tenta de novo na próxima volta ao app
    };

    verificar();
    const inscricao = AppState.addEventListener('change', (estado) => {
      if (estado === 'active') verificar();
    });
    return () => inscricao.remove();
  }, []);
}

/** Faixa no topo quando há uma versão baixada esperando: um toque recarrega o app com ela. */
export function FaixaDeAtualizacao() {
  const { isUpdatePending } = Updates.useUpdates();
  const { cores } = useTema();
  const { top } = useSafeAreaInsets();
  if (!isUpdatePending) return null;

  return (
    <View pointerEvents="box-none" style={[estilos.posicao, { top: top + 8 }]}>
      <Pressable
        onPress={() => void Updates.reloadAsync()}
        accessibilityRole="button"
        accessibilityLabel="Nova versão disponível. Toque para atualizar."
        style={({ pressed }) => [estilos.faixa, { backgroundColor: cores.primaria }, pressed && { opacity: 0.85 }]}>
        <Ionicons name="sparkles" size={18} color={cores.sobrePrimaria} />
        <Text style={[estilos.texto, { color: cores.sobrePrimaria }]}>Nova versão disponível</Text>
        <Text style={[estilos.acao, { color: cores.sobrePrimaria }]}>Atualizar</Text>
      </Pressable>
    </View>
  );
}

/** Botão "Verificar atualização" do Perfil: procura, baixa e oferece recarregar na hora. */
export async function verificarAtualizacaoAgora(): Promise<void> {
  if (!Updates.isEnabled) {
    Alert.alert('Atualizações', 'Este modo do app não recebe atualizações pelo ar.');
    return;
  }
  try {
    const baixou = await baixarSeHouver();
    if (baixou) {
      Alert.alert('Atualização baixada', 'O app vai reiniciar para usar a versão nova.', [
        { text: 'Depois', style: 'cancel' },
        { text: 'Atualizar agora', onPress: () => void Updates.reloadAsync() },
      ]);
    } else {
      Alert.alert('Tudo certo', 'Você já está com a versão mais recente.');
    }
  } catch {
    Alert.alert('Atualizações', 'Não foi possível verificar agora. Confira sua conexão e tente de novo.');
  }
}

const estilos = StyleSheet.create({
  posicao: { position: 'absolute', left: 12, right: 12, zIndex: 100 },
  faixa: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 6,
  },
  texto: { flex: 1, fontSize: 15, fontWeight: '600' },
  acao: { fontSize: 15, fontWeight: '800', textDecorationLine: 'underline' },
});
