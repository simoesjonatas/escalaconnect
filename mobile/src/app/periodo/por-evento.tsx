import Ionicons from '@expo/vector-icons/Ionicons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { periodo } from '../../lib/datas';
import { useEventosElegiveis, useMudarPeriodos } from '../../lib/hooks';
import { tipoDoParametro } from '../../lib/periodo-ui';
import { cores } from '../../lib/tema';
import { Botao, Cartao, Erro, Estado, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

export default function PorEvento() {
  const tipo = tipoDoParametro(useLocalSearchParams<{ tipo?: string }>().tipo);
  const eventos = useEventosElegiveis(tipo);
  const mudar = useMudarPeriodos(tipo);
  const [marcados, setMarcados] = useState<number[]>([]);

  const alternar = (id: number) =>
    setMarcados((atual) => (atual.includes(id) ? atual.filter((i) => i !== id) : [...atual, id]));

  return (
    <Tela atualizando={eventos.isRefetching} aoAtualizar={() => eventos.refetch()}>
      <Texto>
        {tipo === 'disponibilidades'
          ? 'Marque os eventos dos próximos 60 dias em que você pode servir.'
          : 'Marque os eventos dos próximos 60 dias em que você não pode servir.'}
      </Texto>
      <Estado consulta={eventos} vazio={eventos.data?.length === 0 && 'Não há eventos novos para marcar.'} />
      {eventos.data?.map((evento) => {
        const marcado = marcados.includes(evento.id);
        return (
          <Pressable
            key={evento.id}
            onPress={() => alternar(evento.id)}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: marcado }}>
            <Cartao style={marcado ? { borderColor: cores.primaria } : undefined}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                <Ionicons
                  name={marcado ? 'checkbox' : 'square-outline'}
                  size={26}
                  color={marcado ? cores.primaria : cores.textoSuave}
                />
                <View style={{ flex: 1, gap: 2 }}>
                  <Subtitulo>{evento.nome}</Subtitulo>
                  <Suave>{periodo(evento.data_inicio, evento.data_fim)}</Suave>
                </View>
              </View>
            </Cartao>
          </Pressable>
        );
      })}
      <Erro erro={mudar.error} />
      {!!eventos.data?.length && (
        <Botao
          titulo={marcados.length ? `Salvar (${marcados.length})` : 'Salvar'}
          desabilitado={marcados.length === 0}
          carregando={mudar.isPending}
          aoTocar={() =>
            mudar.mutate({ acao: 'por-evento', evento_ids: marcados }, { onSuccess: () => router.back() })
          }
        />
      )}
    </Tela>
  );
}
