import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { addHours, startOfHour } from 'date-fns';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Platform, Pressable, View } from 'react-native';

import { diaPorExtenso, hora } from '../../lib/datas';
import { useMudarPeriodos } from '../../lib/hooks';
import { textosDoPeriodo, tipoDoParametro } from '../../lib/periodo-ui';
import { Botao, Cartao, Erro, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

/** Data e hora: no Android abre os diálogos nativos (data, depois hora); no iOS o seletor fica na tela. */
function CampoDataHora({ rotulo, valor, aoMudar }: { rotulo: string; valor: Date; aoMudar: (d: Date) => void }) {
  function abrirNoAndroid() {
    DateTimePickerAndroid.open({
      value: valor,
      mode: 'date',
      onValueChange: (_, data) =>
        DateTimePickerAndroid.open({ value: data, mode: 'time', is24Hour: true, onValueChange: (_, d) => aoMudar(d) }),
    });
  }

  return (
    <Cartao>
      <Suave>{rotulo}</Suave>
      {Platform.OS === 'android' ? (
        <Pressable onPress={abrirNoAndroid}>
          <Subtitulo>
            {diaPorExtenso(valor)} · {hora(valor)}
          </Subtitulo>
          <Suave>Toque para alterar</Suave>
        </Pressable>
      ) : (
        <View style={{ alignItems: 'flex-start' }}>
          <DateTimePicker value={valor} mode="datetime" locale="pt-BR" onValueChange={(_, d) => aoMudar(d)} />
        </View>
      )}
    </Cartao>
  );
}

export default function NovoPeriodo() {
  const tipo = tipoDoParametro(useLocalSearchParams<{ tipo?: string }>().tipo);
  const mudar = useMudarPeriodos(tipo);
  const [inicio, setInicio] = useState(() => addHours(startOfHour(new Date()), 1));
  const [fim, setFim] = useState(() => addHours(startOfHour(new Date()), 3));

  function mudarInicio(novo: Date) {
    setInicio(novo);
    if (fim <= novo) setFim(addHours(novo, 2)); // mantém o fim depois do início
  }

  return (
    <Tela>
      <Texto>
        {tipo === 'disponibilidades'
          ? 'Informe um período em que você pode servir.'
          : 'Informe um período em que você não pode servir.'}
      </Texto>
      <CampoDataHora rotulo="Início" valor={inicio} aoMudar={mudarInicio} />
      <CampoDataHora rotulo="Fim" valor={fim} aoMudar={setFim} />
      <Erro erro={mudar.error} />
      <Botao
        titulo={`Salvar ${textosDoPeriodo[tipo].singular}`}
        carregando={mudar.isPending}
        aoTocar={() =>
          mudar.mutate(
            { acao: 'criar', data_inicio: inicio.toISOString(), data_fim: fim.toISOString() },
            { onSuccess: () => router.back() },
          )
        }
      />
    </Tela>
  );
}
