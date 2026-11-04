import { useLocalSearchParams } from 'expo-router';

import { periodo } from '../../lib/datas';
import { LinhaDeColega } from '../../lib/escala-ui';
import { useEscalaDoEvento } from '../../lib/hooks';
import { Cartao, Estado, Grupo, Suave, Subtitulo, Tela, Texto } from '../../lib/ui';

/** Escala de um evento do calendário: quem serviu (evento passado) ou quem vai servir, por equipe. */
export default function EscalaDoEvento() {
  const id = Number(useLocalSearchParams<{ id: string }>().id);
  const consulta = useEscalaDoEvento(id);
  const dados = consulta.data;
  const pessoas = dados?.equipes.flatMap((e) => e.pessoas) ?? [];
  const escalados = pessoas.filter((p) => p.nome).length;
  const vagas = pessoas.length - escalados;

  return (
    <Tela aoAtualizar={() => consulta.refetch()}>
      <Estado consulta={consulta} />
      {dados && (
        <>
          <Cartao>
            <Subtitulo>{dados.evento.nome}</Subtitulo>
            <Texto>{periodo(dados.evento.data_inicio, dados.evento.data_fim)}</Texto>
            {!!dados.evento.equipe && <Suave>Evento da equipe {dados.evento.equipe}</Suave>}
            {pessoas.length > 0 && (
              <Suave>
                {escalados}{' '}
                {dados.passado
                  ? escalados === 1
                    ? 'pessoa serviu'
                    : 'pessoas serviram'
                  : escalados === 1
                    ? 'pessoa escalada'
                    : 'pessoas escaladas'}
                {vagas
                  ? ` · ${vagas} ${dados.passado ? (vagas === 1 ? 'função ficou vaga' : 'funções ficaram vagas') : vagas === 1 ? 'vaga' : 'vagas'}`
                  : ''}
              </Suave>
            )}
          </Cartao>

          {dados.equipes.length === 0 && <Suave style={{ textAlign: 'center' }}>Este evento não teve escala.</Suave>}
          {dados.equipes.map((equipe) => (
            <Grupo key={equipe.equipe} titulo={equipe.equipe}>
              {equipe.pessoas.map((pessoa, i) => (
                <LinhaDeColega key={i} colega={pessoa} passado={dados.passado} eu={pessoa.eu} />
              ))}
            </Grupo>
          ))}
        </>
      )}
    </Tela>
  );
}
