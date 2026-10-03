import { router } from 'expo-router';
import { Alert, Pressable } from 'react-native';

import { periodo } from '../../lib/datas';
import { useDisponibilidades, useMudarDisponibilidades } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { Disponibilidade } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

/** Disponibilidades do voluntário, registradas pelos eventos (como no site). */
export default function Disponibilidades() {
  const disponibilidades = useDisponibilidades();
  const mudar = useMudarDisponibilidades();
  const { cores } = useTema();

  function excluir(item: Disponibilidade) {
    Alert.alert('Excluir disponibilidade', item.evento ?? periodo(item.data_inicio, item.data_fim), [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Excluir', style: 'destructive', onPress: () => mudar.mutate({ acao: 'excluir', id: item.id }) },
    ]);
  }

  return (
    <Tela atualizando={disponibilidades.isRefetching} aoAtualizar={() => disponibilidades.refetch()}>
      <Texto>Marque os eventos em que você pode servir. A liderança escala só quem está disponível.</Texto>
      <Botao titulo="Registrar disponibilidade" aoTocar={() => router.push('/periodo/por-evento')} />

      <Subtitulo>Próximas disponibilidades</Subtitulo>
      <Erro erro={mudar.error} />
      <Estado
        consulta={disponibilidades}
        vazio={disponibilidades.data?.length === 0 && 'Você ainda não informou quando pode servir.'}
      />
      {disponibilidades.data?.map((item) => (
        <Cartao key={item.id}>
          {!!item.evento && <Subtitulo>{item.evento}</Subtitulo>}
          <Texto>{periodo(item.data_inicio, item.data_fim)}</Texto>
          <Pressable onPress={() => excluir(item)} hitSlop={8} accessibilityRole="button">
            <Suave style={{ color: cores.perigo }}>Excluir</Suave>
          </Pressable>
        </Cartao>
      ))}
    </Tela>
  );
}
