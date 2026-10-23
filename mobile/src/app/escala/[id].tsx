import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Linking } from 'react-native';

import { periodo } from '../../lib/datas';
import { situacaoDaEscala } from '../../lib/escala-ui';
import { useTema } from '../../lib/tema';
import { useAcaoDeEscala, useAgenda, useEscala } from '../../lib/hooks';
import { Botao, Campo, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

export default function DetalheDaEscala() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useEscala(id);
  const acao = useAcaoDeEscala(id);
  const [informandoMotivo, setInformandoMotivo] = useState(false);
  const [motivo, setMotivo] = useState('');
  const escala = consulta.data;
  const { cores } = useTema();
  const agenda = useAgenda();

  const iniciou = escala ? new Date(escala.evento.data_inicio) <= new Date() : false;
  const encerrou = escala ? new Date(escala.evento.data_fim) < new Date() : false;

  function pedirTroca() {
    Alert.alert('Pedir troca', 'A liderança vai receber seu pedido para deixar esta escala. Continuar?', [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Pedir troca', onPress: () => acao.mutate({ tipo: 'pedir-troca' }) },
    ]);
  }

  function adicionarAgenda() {
    if (!agenda.data) return;
    // O sistema abre o .ics desta escala e oferece adicionar ao calendário.
    Linking.openURL(`${agenda.data.https}?escala=${id}`).catch(() =>
      Alert.alert('Agenda', 'Não foi possível abrir o calendário neste aparelho.'),
    );
  }

  return (
    <Tela atualizando={consulta.isRefetching} aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={consulta} />
      {escala && (
        <>
          <Cartao>
            <Etiqueta {...situacaoDaEscala(escala, cores)} />
            <Subtitulo>{escala.evento.nome}</Subtitulo>
            <Texto>{periodo(escala.evento.data_inicio, escala.evento.data_fim)}</Texto>
            <Suave>
              {escala.funcao} · {escala.equipe}
            </Suave>
            {!!escala.evento.observacao && <Texto>{escala.evento.observacao}</Texto>}
          </Cartao>

          <Erro erro={acao.error} />

          {!escala.confirmada && !encerrou && (
            <Botao
              titulo="Confirmar presença"
              carregando={acao.isPending && acao.variables?.tipo === 'confirmar'}
              aoTocar={() => acao.mutate({ tipo: 'confirmar' })}
            />
          )}

          {escala.tem_impedimento ? (
            <Suave>Você sinalizou um impedimento. Aguarde a liderança liberar a vaga.</Suave>
          ) : informandoMotivo ? (
            <Cartao>
              <Campo
                rotulo="Por que você não poderá servir?"
                value={motivo}
                onChangeText={setMotivo}
                multiline
                style={{ minHeight: 96, textAlignVertical: 'top', paddingTop: 12 }}
              />
              <Botao
                titulo="Enviar impedimento"
                variante="perigo"
                desabilitado={!motivo.trim()}
                carregando={acao.isPending}
                aoTocar={() =>
                  acao.mutate(
                    { tipo: 'impedimento', motivo: motivo.trim() },
                    { onSuccess: () => setInformandoMotivo(false) },
                  )
                }
              />
              <Botao titulo="Cancelar" variante="secundario" aoTocar={() => setInformandoMotivo(false)} />
            </Cartao>
          ) : (
            !iniciou && (
              <Botao titulo="Sinalizar impedimento" variante="perigo" aoTocar={() => setInformandoMotivo(true)} />
            )
          )}

          {escala.troca_pendente ? (
            <Botao
              titulo="Cancelar pedido de troca"
              variante="secundario"
              carregando={acao.isPending && acao.variables?.tipo === 'cancelar-troca'}
              aoTocar={() => acao.mutate({ tipo: 'cancelar-troca' })}
            />
          ) : (
            !iniciou && <Botao titulo="Pedir troca" variante="secundario" aoTocar={pedirTroca} />
          )}

          {!encerrou && agenda.data && (
            <Botao titulo="Adicionar à agenda" variante="secundario" aoTocar={adicionarAgenda} />
          )}
        </>
      )}
    </Tela>
  );
}
