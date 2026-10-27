import { router } from 'expo-router';
import { Alert, Pressable } from 'react-native';

import { periodo } from '../../lib/datas';
import { AvisoSemEquipe } from '../../lib/equipe-ui';
import { useDisponibilidades, useHome, useMudarDisponibilidades, useOferta, useVagasAbertas } from '../../lib/hooks';
import { useTema } from '../../lib/tema';
import { Disponibilidade, VagaAberta } from '../../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

/** Disponibilidades do voluntário, registradas pelos eventos (como no site). */
export default function Disponibilidades() {
  const disponibilidades = useDisponibilidades();
  const mudar = useMudarDisponibilidades();
  const { cores } = useTema();
  const home = useHome();
  const vagas = useVagasAbertas();
  const oferta = useOferta();
  const semEquipe = home.data?.em_equipe === false;
  // Vagas em que a pessoa se ofereceu e a liderança ainda não decidiu.
  const ofertas = (vagas.data ?? []).filter((v) => v.me_ofereci);

  function desistir(vaga: VagaAberta) {
    Alert.alert('Desistir da oferta', `${vaga.funcao} · ${vaga.evento.nome}`, [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Desistir', style: 'destructive', onPress: () => oferta.mutate({ vagaId: vaga.id, desistir: true }) },
    ]);
  }

  function excluir(item: Disponibilidade) {
    Alert.alert('Excluir disponibilidade', item.evento ?? periodo(item.data_inicio, item.data_fim), [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Excluir', style: 'destructive', onPress: () => mudar.mutate({ acao: 'excluir', id: item.id }) },
    ]);
  }

  return (
    <Tela aoAtualizar={() => Promise.all([disponibilidades.refetch(), home.refetch(), vagas.refetch()])}>
      {semEquipe ? (
        <AvisoSemEquipe />
      ) : (
        <>
          <Texto>Marque os eventos em que você pode servir. A liderança escala só quem está disponível.</Texto>
          <Botao titulo="Registrar disponibilidade" aoTocar={() => router.push('/periodo/por-evento')} />
        </>
      )}

      {ofertas.length > 0 && (
        <>
          <Subtitulo>Vagas em que você se ofereceu</Subtitulo>
          <Erro erro={oferta.error} />
          {ofertas.map((vaga) => (
            <Cartao key={vaga.id}>
              <Etiqueta texto="Aguardando a liderança" cor={cores.neutra} />
              <Subtitulo>{vaga.evento.nome}</Subtitulo>
              <Texto>{periodo(vaga.evento.data_inicio, vaga.evento.data_fim)}</Texto>
              <Suave>
                {vaga.funcao} · {vaga.equipe}
              </Suave>
              <Pressable
                onPress={() => desistir(vaga)}
                disabled={oferta.isPending}
                hitSlop={8}
                accessibilityRole="button">
                <Suave style={{ color: cores.perigo }}>Desistir da oferta</Suave>
              </Pressable>
            </Cartao>
          ))}
        </>
      )}

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
