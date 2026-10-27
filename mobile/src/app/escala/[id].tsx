import Ionicons from '@expo/vector-icons/Ionicons';
import { isSameDay } from 'date-fns';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Text, View } from 'react-native';

import { diaEHora, diaPorExtenso, hora } from '../../lib/datas';
import { situacaoDaEscala } from '../../lib/escala-ui';
import { useAcaoDeEscala, useColegas, useEscala } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { Colega } from '../../lib/types';
import {
  Avatar,
  Botao,
  Campo,
  Cartao,
  Erro,
  Estado,
  Etiqueta,
  Grupo,
  Icone,
  ItemDeGrupo,
  Tela,
} from '../../lib/ui';

/** Uma informação do cabeçalho com ícone (data, horário, função, observação). */
function Info({ icone, texto }: { icone: Icone; texto: string }) {
  const { cores } = useTema();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10 }}>
      <Ionicons name={icone} size={18} color={cores.textoSuave} style={{ marginTop: 1 }} />
      <Text style={{ flex: 1, fontSize: 15, lineHeight: 21, color: cores.texto }}>{texto}</Text>
    </View>
  );
}

/** Aviso de algo que a pessoa já pediu e está esperando a liderança. */
function Aviso({ icone, cor, texto }: { icone: Icone; cor: string; texto: string }) {
  const { cores } = useTema();
  return (
    <Cartao style={{ flexDirection: 'row', alignItems: 'center', gap: 10, borderColor: cor }}>
      <Ionicons name={icone} size={20} color={cor} />
      <Text style={{ flex: 1, fontSize: 14, lineHeight: 20, color: cores.texto }}>{texto}</Text>
    </Cartao>
  );
}

function LinhaDeColega({ colega }: { colega: Colega }) {
  const { cores } = useTema();
  const situacao = !colega.nome
    ? { icone: 'alert-circle-outline' as const, texto: 'Vaga', cor: cores.pendente }
    : colega.confirmada
      ? { icone: 'checkmark-circle' as const, texto: 'Confirmou', cor: cores.confirmada }
      : { icone: 'time-outline' as const, texto: 'A confirmar', cor: cores.textoSuave };
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: cores.borda,
      }}>
      {colega.nome ? (
        <Avatar nome={colega.nome} />
      ) : (
        <View
          style={{
            width: 32,
            height: 32,
            borderRadius: 16,
            alignItems: 'center',
            justifyContent: 'center',
            borderWidth: 1,
            borderStyle: 'dashed',
            borderColor: cores.pendente,
          }}>
          <Ionicons name="person-add-outline" size={15} color={cores.pendente} />
        </View>
      )}
      <View style={{ flex: 1, gap: 1 }}>
        <Text numberOfLines={1} style={{ fontSize: 15, fontWeight: '600', color: colega.nome ? cores.texto : cores.textoSuave }}>
          {colega.nome ?? 'Ninguém escalado'}
        </Text>
        <Text numberOfLines={1} style={{ fontSize: 13, color: cores.textoSuave }}>
          {colega.funcao}
        </Text>
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
        <Ionicons name={situacao.icone} size={16} color={situacao.cor} />
        <Text style={{ fontSize: 13, fontWeight: '600', color: situacao.cor }}>{situacao.texto}</Text>
      </View>
    </View>
  );
}

export default function DetalheDaEscala() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useEscala(id);
  const acao = useAcaoDeEscala(id);
  const colegas = useColegas(id);
  const [informandoMotivo, setInformandoMotivo] = useState(false);
  const [motivo, setMotivo] = useState('');
  const escala = consulta.data;
  const { cores } = useTema();

  const iniciou = escala ? new Date(escala.evento.data_inicio) <= new Date() : false;
  const encerrou = escala ? new Date(escala.evento.data_fim) < new Date() : false;

  function pedirTroca() {
    Alert.alert('Pedir troca', 'A liderança vai receber seu pedido para deixar esta escala. Continuar?', [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Pedir troca', onPress: () => acao.mutate({ tipo: 'pedir-troca' }) },
    ]);
  }

  if (!escala) {
    return (
      <Tela aoAtualizar={() => consulta.refetch()}>
        <Estado consulta={consulta} />
      </Tela>
    );
  }

  const { data_inicio, data_fim } = escala.evento;
  const dia = diaPorExtenso(data_inicio);
  const horario = `${hora(data_inicio)} – ${isSameDay(new Date(data_inicio), new Date(data_fim)) ? hora(data_fim) : diaEHora(data_fim)}`;
  const podeTrocar = escala.troca_pendente || !iniciou;
  const podeSinalizar = !escala.tem_impedimento && !iniciou;

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Cartao style={{ gap: 10 }}>
        <Etiqueta {...situacaoDaEscala(escala, cores)} />
        <Text style={{ fontSize: 20, fontWeight: '700', color: cores.texto }}>{escala.evento.nome}</Text>
        <View style={{ gap: 8 }}>
          <Info icone="calendar-outline" texto={dia.charAt(0).toUpperCase() + dia.slice(1)} />
          <Info icone="time-outline" texto={horario} />
          <Info icone="person-outline" texto={`${escala.funcao} · ${escala.equipe}`} />
          {!!escala.evento.observacao && <Info icone="information-circle-outline" texto={escala.evento.observacao} />}
        </View>
      </Cartao>

      {escala.tem_impedimento && (
        <Aviso
          icone="alert-circle-outline"
          cor={cores.perigo}
          texto="Você sinalizou um impedimento. Aguarde a liderança liberar a vaga."
        />
      )}
      {escala.troca_pendente && (
        <Aviso icone="swap-horizontal-outline" cor={cores.neutra} texto="Você pediu troca. A liderança vai avaliar o pedido." />
      )}

      <Erro erro={acao.error} />

      {!escala.confirmada && !encerrou && (
        <Botao
          titulo="Confirmar presença"
          carregando={acao.isPending && acao.variables?.tipo === 'confirmar'}
          aoTocar={() => acao.mutate({ tipo: 'confirmar' })}
        />
      )}

      {informandoMotivo ? (
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
              acao.mutate({ tipo: 'impedimento', motivo: motivo.trim() }, { onSuccess: () => setInformandoMotivo(false) })
            }
          />
          <Botao titulo="Cancelar" variante="secundario" aoTocar={() => setInformandoMotivo(false)} />
        </Cartao>
      ) : (
        (podeTrocar || podeSinalizar) && (
          <Grupo titulo="Não vai poder servir?">
            {escala.troca_pendente ? (
              <ItemDeGrupo
                icone="close-circle-outline"
                titulo="Cancelar pedido de troca"
                carregando={acao.isPending && acao.variables?.tipo === 'cancelar-troca'}
                aoTocar={() => acao.mutate({ tipo: 'cancelar-troca' })}
              />
            ) : (
              podeTrocar && (
                <ItemDeGrupo
                  icone="swap-horizontal-outline"
                  titulo="Pedir troca"
                  carregando={acao.isPending && acao.variables?.tipo === 'pedir-troca'}
                  aoTocar={pedirTroca}
                />
              )
            )}
            {podeSinalizar && (
              <ItemDeGrupo
                icone="alert-circle-outline"
                titulo="Sinalizar impedimento"
                perigo
                aoTocar={() => setInformandoMotivo(true)}
              />
            )}
          </Grupo>
        )
      )}

      {!!colegas.data?.length && (
        <Grupo titulo="Quem serve com você">
          {colegas.data.map((colega, i) => (
            <LinhaDeColega key={i} colega={colega} />
          ))}
        </Grupo>
      )}
    </Tela>
  );
}
