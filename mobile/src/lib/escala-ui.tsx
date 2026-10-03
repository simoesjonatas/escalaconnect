import { router } from 'expo-router';
import { Pressable } from 'react-native';

import { periodo } from './datas';
import { cores } from './tema';
import { Escala } from './types';
import { Cartao, Etiqueta, Suave, Subtitulo, Texto } from './ui';

export function situacaoDaEscala(escala: Escala): { texto: string; cor: string } {
  if (escala.tem_impedimento) return { texto: 'Impedimento sinalizado', cor: cores.perigo };
  if (escala.troca_pendente) return { texto: 'Troca solicitada', cor: cores.neutra };
  if (escala.confirmada) return { texto: 'Confirmada', cor: cores.confirmada };
  return { texto: 'A confirmar', cor: cores.pendente };
}

/** Cartão de uma escala; tocar abre o detalhe. */
export function CartaoDeEscala({ escala }: { escala: Escala }) {
  const situacao = situacaoDaEscala(escala);
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
