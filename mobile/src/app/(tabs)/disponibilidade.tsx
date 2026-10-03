import { router } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { periodo } from '../../lib/datas';
import { useMudarPeriodos, usePeriodos } from '../../lib/hooks';
import { textosDoPeriodo } from '../../lib/periodo-ui';
import { cores } from '../../lib/tema';
import { Periodo, TipoPeriodo } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

const TIPOS: TipoPeriodo[] = ['disponibilidades', 'indisponibilidades'];

export default function Disponibilidade() {
  const [tipo, setTipo] = useState<TipoPeriodo>('disponibilidades');
  const periodos = usePeriodos(tipo);
  const mudar = useMudarPeriodos(tipo);
  const textos = textosDoPeriodo[tipo];

  function excluir(item: Periodo) {
    Alert.alert(`Excluir ${textos.singular}`, periodo(item.data_inicio, item.data_fim), [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Excluir', style: 'destructive', onPress: () => mudar.mutate({ acao: 'excluir', id: item.id }) },
    ]);
  }

  return (
    <Tela atualizando={periodos.isRefetching} aoAtualizar={() => periodos.refetch()}>
      <View style={estilos.seletor}>
        {TIPOS.map((t) => (
          <Pressable key={t} onPress={() => setTipo(t)} style={[estilos.opcao, t === tipo && estilos.opcaoAtiva]}>
            <Text style={[estilos.opcaoTexto, t === tipo && { color: cores.sobrePrimaria }]}>
              {t === 'disponibilidades' ? 'Posso servir' : 'Não posso'}
            </Text>
          </Pressable>
        ))}
      </View>

      <Botao
        titulo="Escolher pelos eventos"
        aoTocar={() => router.push({ pathname: '/periodo/por-evento', params: { tipo } })}
      />
      <Botao
        titulo="Informar dia e horário"
        variante="secundario"
        aoTocar={() => router.push({ pathname: '/periodo/novo', params: { tipo } })}
      />

      <Subtitulo>{textos.plural}</Subtitulo>
      <Erro erro={mudar.error} />
      <Estado consulta={periodos} vazio={periodos.data?.length === 0 && textos.vazio} />
      {periodos.data?.map((item) => (
        <Cartao key={item.id}>
          {!!item.evento && <Subtitulo>{item.evento}</Subtitulo>}
          <Texto>{periodo(item.data_inicio, item.data_fim)}</Texto>
          <Pressable onPress={() => excluir(item)} hitSlop={8}>
            <Suave>Excluir</Suave>
          </Pressable>
        </Cartao>
      ))}
    </Tela>
  );
}

const estilos = StyleSheet.create({
  seletor: {
    flexDirection: 'row',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.cartao,
    overflow: 'hidden',
  },
  opcao: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  opcaoAtiva: { backgroundColor: cores.primaria },
  opcaoTexto: { fontSize: 15, fontWeight: '600', color: cores.texto },
});
