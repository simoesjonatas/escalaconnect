import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useEffect } from 'react';
import { Pressable, Text, View } from 'react-native';

import { useAvisos, useMarcarAvisosLidos } from '../lib/hooks';
import { abrir, sincronizarIcone } from '../lib/push';
import { useTema } from '../lib/tema';
import { Aviso } from '../lib/types';
import { Estado, Subtitulo, Tela } from '../lib/ui';

/**
 * Caixa de avisos: as notificações recebidas. Abrir a tela marca tudo como lido,
 * zera o número no ícone do app e limpa a central de notificações. Os que eram
 * novos continuam destacados enquanto a tela estiver aberta.
 */
export default function Avisos() {
  const consulta = useAvisos();
  const { mutate: marcarLidos } = useMarcarAvisosLidos();
  const naoLidos = consulta.data?.nao_lidos ?? 0;

  useEffect(() => {
    if (!naoLidos) return;
    marcarLidos();
    void sincronizarIcone(0);
  }, [naoLidos, marcarLidos]);

  const avisos = consulta.data?.avisos ?? [];
  const novos = avisos.filter((a) => !a.lido);
  const anteriores = avisos.filter((a) => a.lido);

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={consulta} vazio={avisos.length === 0 && 'Nenhum aviso por aqui ainda.'} />
      {novos.length > 0 && <Subtitulo>Novos</Subtitulo>}
      {novos.map((aviso) => (
        <ItemDeAviso key={aviso.id} aviso={aviso} novo />
      ))}
      {anteriores.length > 0 && novos.length > 0 && <Subtitulo style={{ marginTop: 8 }}>Anteriores</Subtitulo>}
      {anteriores.map((aviso) => (
        <ItemDeAviso key={aviso.id} aviso={aviso} />
      ))}
    </Tela>
  );
}

function ItemDeAviso({ aviso, novo }: { aviso: Aviso; novo?: boolean }) {
  const { cores } = useTema();
  const quando = formatDistanceToNow(new Date(aviso.criado_em), { locale: ptBR, addSuffix: true });
  return (
    <Pressable
      onPress={() => abrir({ tipo: aviso.tipo, escala_id: aviso.escala_id })}
      accessibilityRole="button"
      style={({ pressed }) => [
        {
          flexDirection: 'row',
          gap: 10,
          padding: 12,
          borderRadius: 12,
          borderWidth: 1,
          backgroundColor: cores.cartao,
          borderColor: novo ? cores.primaria : cores.borda,
        },
        pressed && { opacity: 0.6 },
      ]}>
      <View
        style={{
          width: 8,
          height: 8,
          borderRadius: 4,
          marginTop: 6,
          backgroundColor: novo ? cores.primaria : 'transparent',
        }}
      />
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={{ color: cores.texto, fontSize: 15, fontWeight: novo ? '700' : '600' }}>{aviso.titulo}</Text>
        <Text style={{ color: cores.texto, fontSize: 14 }}>{aviso.corpo}</Text>
        <Text style={{ color: cores.textoSuave, fontSize: 12 }}>{quando}</Text>
      </View>
    </Pressable>
  );
}
