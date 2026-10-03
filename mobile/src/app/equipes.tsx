import { useCandidatura, useEquipes } from '../lib/hooks';
import { useTema } from '../lib/tema';
import { Equipe } from '../lib/types';
import { Botao, Cartao, Erro, Estado, Etiqueta, Suave, Subtitulo, Tela } from '../lib/ui';

export default function Equipes() {
  const equipes = useEquipes();
  const candidatura = useCandidatura();
  const ocupada = (equipe: Equipe) => candidatura.isPending && candidatura.variables?.equipeId === equipe.id;
  const dados = equipes.data;
  const { cores } = useTema();

  return (
    <Tela atualizando={equipes.isRefetching} aoAtualizar={() => equipes.refetch()}>
      <Estado consulta={equipes} />
      <Erro erro={candidatura.error} />
      {dados && (
        <>
          <Subtitulo>Participo</Subtitulo>
          {dados.aprovadas.length === 0 && <Suave>Você ainda não participa de nenhuma equipe.</Suave>}
          {dados.aprovadas.map((equipe) => (
            <Cartao key={equipe.id}>
              <Subtitulo>{equipe.nome}</Subtitulo>
            </Cartao>
          ))}

          {dados.pendentes.length > 0 && <Subtitulo>Aguardando aprovação</Subtitulo>}
          {dados.pendentes.map((equipe) => (
            <Cartao key={equipe.id}>
              <Etiqueta texto="Pedido enviado" cor={cores.pendente} />
              <Subtitulo>{equipe.nome}</Subtitulo>
              <Botao
                titulo="Cancelar pedido"
                variante="secundario"
                carregando={ocupada(equipe)}
                aoTocar={() => candidatura.mutate({ equipeId: equipe.id, cancelar: true })}
              />
            </Cartao>
          ))}

          {dados.disponiveis.length > 0 && <Subtitulo>Outras equipes</Subtitulo>}
          {dados.disponiveis.map((equipe) => (
            <Cartao key={equipe.id}>
              <Subtitulo>{equipe.nome}</Subtitulo>
              <Botao
                titulo="Pedir para entrar"
                variante="secundario"
                carregando={ocupada(equipe)}
                aoTocar={() => candidatura.mutate({ equipeId: equipe.id })}
              />
            </Cartao>
          ))}
        </>
      )}
    </Tela>
  );
}
