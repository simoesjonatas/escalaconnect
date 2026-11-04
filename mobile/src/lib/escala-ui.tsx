import Ionicons from '@expo/vector-icons/Ionicons';
import { router } from 'expo-router';
import { Pressable, Text, View } from 'react-native';

import { periodo } from './datas';
import { Cores, useTema } from './tema';
import { Colega, Escala } from './types';
import { Avatar, Cartao, Etiqueta, Suave, Subtitulo, Texto } from './ui';

export function situacaoDaEscala(escala: Escala, cores: Cores): { texto: string; cor: string } {
  if (escala.tem_impedimento) return { texto: 'Impedimento sinalizado', cor: cores.perigo };
  if (escala.troca_pendente) return { texto: 'Troca solicitada', cor: cores.neutra };
  if (escala.confirmada) return { texto: 'Confirmada', cor: cores.confirmada };
  return { texto: 'A confirmar', cor: cores.pendente };
}

/** Cartão de uma escala; tocar abre o detalhe. */
export function CartaoDeEscala({ escala }: { escala: Escala }) {
  const situacao = situacaoDaEscala(escala, useTema().cores);
  return (
    <Pressable onPress={() => router.push({ pathname: '/escala/[id]', params: { id: escala.id } })}>
      <Cartao>
        <Etiqueta {...situacao} />
        <Subtitulo>{escala.evento.nome}</Subtitulo>
        <Texto>{periodo(escala.evento.data_inicio, escala.evento.data_fim)}</Texto>
        <Suave>
          {escala.funcao} · {escala.equipe}
        </Suave>
      </Cartao>
    </Pressable>
  );
}

/** Uma pessoa (ou vaga) da escala. Em evento passado não mostra a confirmação, só quem serviu. */
export function LinhaDeColega({ colega, passado, eu }: { colega: Colega; passado?: boolean; eu?: boolean }) {
  const { cores } = useTema();
  const situacao = !colega.nome
    ? { icone: 'alert-circle-outline' as const, texto: passado ? 'Ficou vaga' : 'Vaga', cor: cores.pendente }
    : passado
      ? null
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
        <Avatar nome={colega.nome} destaque={eu} />
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
          {colega.nome ? `${colega.nome}${eu ? ' (você)' : ''}` : 'Ninguém escalado'}
        </Text>
        <Text numberOfLines={1} style={{ fontSize: 13, color: cores.textoSuave }}>
          {colega.funcao}
        </Text>
      </View>
      {situacao && (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
          <Ionicons name={situacao.icone} size={16} color={situacao.cor} />
          <Text style={{ fontSize: 13, fontWeight: '600', color: situacao.cor }}>{situacao.texto}</Text>
        </View>
      )}
    </View>
  );
}
