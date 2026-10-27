import { useState } from 'react';
import { Alert } from 'react-native';

import { periodo } from '../lib/datas';
import { useOferta, useVagasAbertas } from '../lib/hooks';
import { useTema } from '../lib/tema';
import { VagaAberta } from '../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Opcoes, Suave, Subtitulo, Tela, Texto } from '../lib/ui';

/** Vagas em aberto das equipes do voluntário: ele se oferece e a liderança decide. */
export default function VagasAbertas() {
  const vagas = useVagasAbertas();
  const oferta = useOferta();
  const { cores } = useTema();

  const [equipe, setEquipe] = useState('todas');

  const ocupada = (vaga: VagaAberta) => oferta.isPending && oferta.variables?.vagaId === vaga.id;

  // Filtro por equipe: só equipes que têm vaga, e só aparece se houver mais de uma.
  const todas = vagas.data ?? [];
  const equipes = [...new Map(todas.map((v) => [String(v.equipe_id), v.equipe])).entries()].sort((a, b) =>
    a[1].localeCompare(b[1]),
  );
  const filtro = equipes.some(([id]) => id === equipe) ? equipe : 'todas';
  const lista = filtro === 'todas' ? todas : todas.filter((v) => String(v.equipe_id) === filtro);

  function oferecer(vaga: VagaAberta) {
    Alert.alert('Quero servir', `A liderança da equipe ${vaga.equipe} vai receber sua oferta para esta vaga.`, [
      { text: 'Voltar', style: 'cancel' },
      { text: 'Me oferecer', onPress: () => oferta.mutate({ vagaId: vaga.id }) },
    ]);
  }

  return (
    <Tela aoAtualizar={() => vagas.refetch()}>
      <Texto>Estas funções ainda estão sem ninguém escalado. Se você puder servir, ofereça-se e a liderança confirma.</Texto>
      <Erro erro={oferta.error} />
      <Estado consulta={vagas} vazio={vagas.data?.length === 0 && 'Nenhuma vaga em aberto na sua equipe agora.'} />
      {equipes.length > 1 && (
        <Opcoes
          opcoes={[{ valor: 'todas', rotulo: 'Todas' }, ...equipes.map(([valor, rotulo]) => ({ valor, rotulo }))]}
          valor={filtro}
          aoEscolher={setEquipe}
        />
      )}
      {lista.map((vaga) => (
        <Cartao key={vaga.id}>
          {vaga.me_ofereci && <Etiqueta texto="Você se ofereceu" cor={cores.neutra} />}
          <Subtitulo>{vaga.evento.nome}</Subtitulo>
          <Texto>{periodo(vaga.evento.data_inicio, vaga.evento.data_fim)}</Texto>
          <Suave>
            {vaga.funcao} · {vaga.equipe}
          </Suave>
          {vaga.me_ofereci ? (
            <>
              <Suave>Aguardando a liderança. Você recebe um aviso quando ela decidir.</Suave>
              <Botao
                titulo="Desistir da oferta"
                variante="secundario"
                carregando={ocupada(vaga)}
                aoTocar={() => oferta.mutate({ vagaId: vaga.id, desistir: true })}
              />
            </>
          ) : (
            <Botao titulo="Quero servir" carregando={ocupada(vaga)} aoTocar={() => oferecer(vaga)} />
          )}
        </Cartao>
      ))}
    </Tela>
  );
}
